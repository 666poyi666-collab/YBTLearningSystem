from __future__ import annotations

"""第一章全章 DeepSeek 独立消费探针（只属于 scripts/deepseek 的新文件）。

设计目标
--------
对第一章四个批次（1.1 / 1.2_1.3 / 1.4 / micro专题1）逐一执行与
scripts/run_deepseek_http_probe.py 完全相同的消费门禁与独立理解探针：

1. 门禁不降级：validate_context 原样执行；只有 status=VERIFIED、无 unresolved、
   且每题 visual_status 属于 {READY_TEXT_ONLY, VISION_VERIFIED} 的 context 才会
   派发 HTTP 探针。被门禁拦下的节只记录缺口，绝不派发、绝不声称已消费。
2. 不泄露答案：探针只携带无答案投影（qid/组/题号/前80字符题面/视觉状态/图片数 +
   课程/知识点/类型题/A-B-C 顺序路由元数据），不携带页 OCR 全文与答案册；发送前
   再做一次防泄漏扫描，任何命中都直接失败且不派发。
3. 逐题绑定：模型必须回显 context_sha256、canary、probe_tokens，并对每题回显
   question_key/group/number/question_text_prefix/visual_status；
   verify_worker_understanding 逐题校验。
4. 课程/知识点/类型题/A-B-C 顺序：understanding_summary 必须返回
   must_listen_course_keys、knowledge_point_ids、type_training（有序）、
   exercise_order（A/B/C 分组有序）、expected_groups，且 mastery_not_assessed=true。

运行：python scripts/deepseek/chapter_probe.py
输出：scripts/deepseek/out/chapter_probe_latest.json（固定路径）
      scripts/deepseek/out/chapter_probe_<utc>.json（时间戳副本）
      scripts/deepseek/out/raw_<section>.json（每次实际派发的原始 HTTP 响应）

汇总原则：chapter_consumption_ready 只有在四个节全部通过时才为 true；
1.1 单节通过绝不扩大为全章通过。
"""

import hashlib
import json
import re
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT))

from ybt_learning.deepseek_context import validate_context, verify_worker_understanding, _question_prefix  # noqa: E402
from run_deepseek_http_probe import (  # noqa: E402
    PROMPT,
    ENDPOINT,
    MODEL,
    EFFORT,
    CONTEXT_WINDOW,
    _output_text,
    _parse_json,
    _normalize_understanding_response,
    _request_with_retry,
    _request,
)

DATA = PROJECT_ROOT / "data"
CONTEXTS = DATA / "contexts"
OUT_DIR = PROJECT_ROOT / "scripts" / "deepseek" / "out"
MANIFEST = PROJECT_ROOT / "chapter1_manifest.json"
LATEST_OUT = OUT_DIR / "chapter_probe_latest.json"

LEAK_PATTERNS = [
    r"answer_text",
    r"最终答案",
    r"答案为",
    r"解析[：:]",
    r"解答[：:]",
    r"答案[：:]",
    r"故答案",
]


def section_context_files() -> list[tuple[str, Path]]:
    """按 chapter1_manifest.json 的章节顺序返回 (section, context 文件)。"""
    names: list[str] = []
    if MANIFEST.is_file():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            names = [item["id"] for item in manifest.get("sections", []) if item.get("id")]
        except json.JSONDecodeError:
            names = []
    if not names:
        names = ["1.1", "1.2_1.3", "1.4", "micro专题1"]
    return [(section_id, CONTEXTS / (section_id.replace("+", "_") + ".json")) for section_id in names]


def build_projection(canonical: dict) -> tuple[str, dict[str, str]]:
    """与 run_deepseek_http_probe.py 完全相同的无答案理解投影。"""
    plan = (canonical.get("route_support") or {}).get("learning_plan") or {}
    projection = {
        "schema": "canonical_context_understanding_projection",
        "note": "此投影由当前 canonical context 生成；不含答案册和完整页 OCR，只用于独立理解探针。",
        "schema_version": canonical.get("schema_version"),
        "consumer": canonical.get("consumer"),
        "model_contract": canonical.get("model_contract"),
        "section": canonical.get("section"),
        "status": canonical.get("status"),
        "evidence": canonical.get("evidence"),
        "manifest": canonical.get("manifest"),
        "unresolved": canonical.get("unresolved"),
        "questions": [
            {
                "qid": q.get("qid"),
                "section": q.get("section"),
                "group": q.get("group"),
                "number": q.get("number"),
                "question_text_prefix": _question_prefix(q.get("question_text", "")),
                "visual_status": q.get("visual_status"),
                "image_count": len(q.get("image_refs", [])),
            }
            for q in canonical.get("questions", [])
        ],
        "route_support": {
            "must_listen_course_keys": [item.get("course_key") for item in plan.get("must_listen_courses", [])],
            "knowledge_point_ids": [item.get("id") for item in plan.get("knowledge_points", [])],
            "type_training": [item.get("type") for item in plan.get("type_training", [])],
            "exercise_order": plan.get("exercise_order"),
            "bridge_micro_lessons": [
                {"id": item.get("id"), "status": item.get("status")}
                for item in ((canonical.get("route_support") or {}).get("bridge_micro_lessons") or [])
            ],
        },
    }
    context_text = json.dumps(projection, ensure_ascii=False, separators=(",", ":"))
    prefixes = {q["qid"]: q["question_text_prefix"] for q in projection["questions"] if q.get("qid")}
    return context_text, prefixes


def projection_has_answer_leak(context_text: str) -> list[str]:
    hits = [pattern for pattern in LEAK_PATTERNS if re.search(pattern, context_text, flags=re.I)]
    if re.search(r"(?m)^\s*[A-D][.．、]\s*$", context_text):
        hits.append("bare_option_line")
    return hits


def gap_detail(canonical: dict) -> dict:
    bad = [
        {
            "qid": q.get("qid"),
            "question_key": f"{q.get('group')}{q.get('number')}",
            "visual_status": q.get("visual_status"),
        }
        for q in canonical.get("questions", [])
        if q.get("visual_status") == "NEEDS_VISION_SIDECAR"
    ]
    return {
        "status": canonical.get("status"),
        "unresolved": canonical.get("unresolved"),
        "needs_vision_sidecar_questions": bad,
        "question_count": len(canonical.get("questions", [])),
    }


def probe_section(section: str, context_path: Path) -> dict:
    record: dict = {
        "section": section,
        "context_path": str(context_path),
        "status": "blocked",
        "gate": None,
        "dispatch": False,
        "errors": [],
    }
    if not context_path.is_file():
        record["errors"] = ["context_file_missing"]
        return record
    canonical = json.loads(context_path.read_text(encoding="utf-8"))
    gate = validate_context(context_path)
    record["gate"] = gate
    if gate.get("status") != "passed":
        record["errors"] = list(gate.get("errors", []))
        record["gap_detail"] = gap_detail(canonical)
        return record
    context_text, projection_prefixes = build_projection(canonical)
    leak_hits = projection_has_answer_leak(context_text)
    if leak_hits:
        record["errors"] = ["projection_answer_leak:" + ",".join(leak_hits)]
        return record
    safe_section = section.replace("+", "_")
    attempts: list[dict] = []
    final_raw: dict | None = None
    final_transport: dict | None = None
    final_response: dict | None = None
    final_verification: dict = {"status": "failed", "errors": ["no_probe_attempt"]}
    final_normalization: list[str] = []
    # Provider output can be syntactically malformed or truncate one field
    # while the HTTP transport itself is completed. Retry the section as a
    # fresh independent request, preserving each raw response for audit. A
    # section is released only after the full semantic verifier passes.
    for probe_attempt in range(1, 4):
        try:
            raw, request_attempts = _request_with_retry(context_text)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            attempts.append({"attempt": probe_attempt, "status": "transport_failed", "error": str(exc)[:300]})
            if probe_attempt == 3:
                record["errors"] = ["transport_error:" + str(exc)[:300]]
            continue
        raw_path = OUT_DIR / f"raw_{safe_section}_attempt{probe_attempt}.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        transport_status = (
            "completed"
            if raw.get("status") == "completed" or (raw.get("choices") and raw["choices"][0].get("finish_reason") == "stop")
            else "incomplete"
        )
        transport = {
            "id": raw.get("id"),
            "object": raw.get("object"),
            "status": transport_status,
            "returned_model": raw.get("model"),
            "usage": raw.get("usage"),
            "raw_path": str(raw_path),
            "response_contract": "chat_completions_completed_or_incomplete_recorded",
            "projection_sha256": hashlib.sha256(context_text.encode("utf-8")).hexdigest(),
            "request_attempts": request_attempts,
            "probe_attempt": probe_attempt,
        }
        record["dispatch"] = True
        output_text = _output_text(raw)
        response, parse_error = _parse_json(output_text)
        attempt_record = {
            "attempt": probe_attempt,
            "transport_status": transport_status,
            "raw_path": str(raw_path),
            "response_text_present": bool(output_text),
            "parse_error": parse_error,
        }
        if response is None:
            attempts.append(attempt_record)
            if probe_attempt == 3:
                record["model_output_text_present"] = bool(output_text)
                record["model_output_parse_error"] = parse_error
                record["errors"] = [parse_error or "empty_model_output"]
            continue

        response, normalization = _normalize_understanding_response(response, canonical)
        response["runtime"] = response.get("runtime") or {
            "model": raw.get("model"),
            "reasoning_effort": EFFORT,
            "context_window": CONTEXT_WINDOW,
        }
        response_path = OUT_DIR / f"response_{safe_section}_attempt{probe_attempt}.json"
        response_path.write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        verification = verify_worker_understanding(
            context_path,
            response_path,
            transport={
                "requested_model": MODEL,
                "returned_model": raw.get("model"),
                "status": transport_status,
            },
            expected_question_prefixes=projection_prefixes,
        )
        attempt_record["response_path"] = str(response_path)
        attempt_record["verification_status"] = verification.get("status")
        attempt_record["verification_errors"] = verification.get("errors", [])
        attempts.append(attempt_record)
        final_raw = raw
        final_transport = transport
        final_response = response
        final_verification = verification
        final_normalization = normalization
        if verification.get("status") == "passed" and transport_status == "completed":
            break

    record["attempts"] = attempts
    if final_transport is not None:
        record["transport"] = final_transport
    if final_response is not None:
        record["response"] = final_response
        record["response_normalization"] = final_normalization
        record["verification"] = final_verification
        record["errors"] = list(final_verification.get("errors", []))
        record["status"] = final_verification["status"] if final_transport and final_transport["status"] == "completed" else "failed"
    elif not record.get("errors"):
        record["errors"] = ["probe_exhausted_without_valid_response"]
    record.setdefault("verification", {"status": "failed", "errors": record["errors"]})
    return record


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    checked_at = datetime.now(timezone.utc).isoformat()
    sections = [probe_section(section, context_path) for section, context_path in section_context_files()]
    gate_passed = sum(1 for item in sections if (item.get("gate") or {}).get("status") == "passed")
    dispatched = sum(1 for item in sections if item.get("dispatch"))
    passed = sum(1 for item in sections if item.get("status") == "passed")
    report = {
        "schema_version": "7.1",
        "kind": "CHAPTER_DEEPSEEK_CONSUMPTION_PROBE",
        "checked_at": checked_at,
        "endpoint": ENDPOINT,
        "requested_model": MODEL,
        "requested_reasoning_effort": EFFORT,
        "configured_context_window": CONTEXT_WINDOW,
        "gate_policy": "validate_context 门禁原样执行；被门禁拦下的节不派发 HTTP、只记录缺口；不降低门禁、不把单节通过扩大为全章。",
        "sections": sections,
        "summary": {
            "total_sections": len(sections),
            "gate_passed": gate_passed,
            "dispatched": dispatched,
            "consumption_passed": passed,
            "chapter_consumption_ready": passed == len(sections) and dispatched == len(sections),
        },
        "gaps": [
            {
                "section": item["section"],
                "errors": item.get("errors", []),
                "gap_detail": item.get("gap_detail"),
            }
            for item in sections
            if item.get("status") != "passed"
        ],
    }
    LATEST_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stamped = OUT_DIR / ("chapter_probe_" + checked_at.replace(":", "-").replace("+", "-") + ".json")
    stamped.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(LATEST_OUT),
                "summary": report["summary"],
                "per_section": [
                    {"section": item["section"], "status": item["status"], "errors": item.get("errors", [])}
                    for item in sections
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["summary"]["chapter_consumption_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
