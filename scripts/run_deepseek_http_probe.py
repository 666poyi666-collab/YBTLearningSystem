from __future__ import annotations

import json
import hashlib
import copy
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ybt_learning.deepseek_context import validate_context, verify_worker_understanding, _question_prefix


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_PATH = ROOT / "data" / "contexts" / "1.1.json"
RAW_PATH = ROOT / "data" / "deepseek_http_probe_1.1.raw.json"
REPORT_PATH = ROOT / "data" / "deepseek_http_probe_1.1.json"
RESPONSE_PATH = ROOT / "data" / "deepseek_http_probe_1.1.response.json"
ENDPOINT = "http://127.0.0.1:10100/v1/chat/completions"
MODEL = "opencode-go/deepseek-v4-flash"
EFFORT = "max"
CONTEXT_WINDOW = 1_000_000


PROMPT = """
你正在独立消费下面唯一提供的 DEEPSEEK_STUDENT_CONTEXT JSON。不要访问本机其它文件，不要修改文件，不要调用工具。
不要解任何题，不要输出任何答案、解析或答案册内容。先完整阅读 context，再只返回一个合法 JSON 对象，禁止 Markdown 围栏和额外文字。
字段要求：
1. runtime: {model:"opencode-go/deepseek-v4-flash", reasoning_effort:"max", context_window:1000000}
2. context_sha256: 原样复制 evidence.context_sha256
3. canary: 原样复制 evidence.canary
4. probe_tokens: 原样复制 evidence.probe_tokens（不要自行计算）
5. question_echo: 对 questions 中每一道题按 qid 返回 question_key、group、number、question_text_prefix（必须逐字复制投影中同题的规范化前80字符，不得缩短、改写或自行补全）和 visual_status（原样复制）
6. understanding_summary: 返回 section、question_count、expected_groups、must_listen_course_keys、knowledge_point_ids、type_training（完整顺序数组）、exercise_order（完整对象数组）和 mastery_not_assessed:true；不得写答案或解题过程。
若内容不完整，只返回 {"error":"..."}。

下面是完整上下文：
""".strip()


def _output_text(payload: dict) -> str:
    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                chunks.append(str(content.get("text", "")))
    if chunks:
        return chunks[-1].strip()
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"].strip()
    choices = payload.get("choices", [])
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message", {})
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"].strip()
    return ""


def _parse_json(text: str) -> tuple[dict | None, str | None]:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            candidate = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, f"model_output_not_json:{exc.msg}"
    if not isinstance(value, dict):
        return None, "model_output_not_object"
    return value, None


def _normalize_understanding_response(response: dict, context: dict) -> tuple[dict, list[str]]:
    """Normalize harmless shape drift without inventing semantic fields."""
    normalized = copy.deepcopy(response)
    changes: list[str] = []
    known = {str(q.get("qid")): q for q in context.get("questions", []) if q.get("qid")}
    raw_echoes = normalized.get("question_echo")
    if isinstance(raw_echoes, (list, dict)):
        mapped: dict[str, dict] = {}
        iterable = enumerate(raw_echoes) if isinstance(raw_echoes, list) else raw_echoes.items()
        for raw_key, raw_item in iterable:
            if not isinstance(raw_item, dict):
                continue
            candidate_values = [raw_key, raw_item.get("qid"), raw_item.get("question_key")]
            qid = next((str(candidate) for candidate in candidate_values if str(candidate) in known), None)
            if qid is None:
                continue
            entry = dict(raw_item)
            question = known[qid]
            entry["qid"] = qid
            entry["question_key"] = f"{question.get('group')}{question.get('number')}"
            changes.append(f"question_echo[{qid}].qid_to_group_key")
            mapped[qid] = entry
        normalized["question_echo"] = mapped
        if isinstance(raw_echoes, list):
            changes.append("question_echo:list_to_qid_map")
        else:
            changes.append("question_echo:dict_key_normalized")
    return normalized, changes


def _request(context_text: str) -> dict:
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT + "\n\n只读上下文投影JSON：\n" + context_text}],
        "reasoning_effort": EFFORT,
        "max_tokens": 50000,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))


RETRYABLE_HTTP_CODES = {408, 429, 500, 502, 503, 504}


def _request_with_retry(context_text: str, *, max_attempts: int = 3) -> tuple[dict, int]:
    """Retry only transient gateway/provider failures; never relax verification."""
    for attempt in range(1, max_attempts + 1):
        try:
            return _request(context_text), attempt
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP_CODES or attempt == max_attempts:
                raise
            time.sleep(3 * attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == max_attempts:
                raise
            time.sleep(3 * attempt)
    raise RuntimeError("deepseek_request_retry_exhausted")


def main() -> int:
    context_check = validate_context(CONTEXT_PATH)
    report: dict = {
        "schema_version": "7.1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "endpoint": ENDPOINT,
        "requested_model": MODEL,
        "requested_reasoning_effort": EFFORT,
        "configured_context_window": CONTEXT_WINDOW,
        "context": context_check,
        "transport": {},
    }
    if context_check.get("status") != "passed":
        report["errors"] = ["context_not_consumable"]
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"path": str(REPORT_PATH), "status": "failed", "errors": report["errors"]}, ensure_ascii=False))
        return 1
    canonical = json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
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
    projection_prefixes = {q["qid"]: q["question_text_prefix"] for q in projection["questions"] if q.get("qid")}
    try:
        raw, request_attempts = _request_with_retry(context_text)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        report["errors"] = [f"transport_error:{str(exc)[:300]}"]
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"path": str(REPORT_PATH), "status": "failed", "errors": report["errors"]}, ensure_ascii=False))
        return 1
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    transport_status = "completed" if raw.get("status") == "completed" or (raw.get("choices") and raw["choices"][0].get("finish_reason") == "stop") else "incomplete"
    report["transport"] = {
        "id": raw.get("id"),
        "object": raw.get("object"),
        "status": transport_status,
        "returned_model": raw.get("model"),
        "usage": raw.get("usage"),
        "raw_path": str(RAW_PATH),
        "response_contract": "chat_completions_completed_or_incomplete_recorded",
        "projection_sha256": hashlib.sha256(context_text.encode("utf-8")).hexdigest(),
        "request_attempts": request_attempts,
    }
    text = _output_text(raw)
    response, parse_error = _parse_json(text)
    report["model_output_text_present"] = bool(text)
    report["model_output_parse_error"] = parse_error
    if response is not None:
        response, normalization = _normalize_understanding_response(response, canonical)
        response["runtime"] = response.get("runtime") or {
            "model": raw.get("model"),
            "reasoning_effort": EFFORT,
            "context_window": CONTEXT_WINDOW,
        }
        # Keep a durable normalized receipt so the report never points to a
        # deleted temporary verifier input.
        RESPONSE_PATH.write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        verification = verify_worker_understanding(CONTEXT_PATH, RESPONSE_PATH, transport={
            "requested_model": MODEL,
            "returned_model": raw.get("model"),
            "status": transport_status,
        }, expected_question_prefixes=projection_prefixes)
        report["response"] = response
        report["response_normalization"] = normalization
        report["verification"] = verification
        report["response_artifact_path"] = str(RESPONSE_PATH)
        report["status"] = verification["status"] if transport_status == "completed" else "failed"
    else:
        report["verification"] = {"status": "failed", "errors": [parse_error or "empty_model_output"]}
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(REPORT_PATH), "status": report["status"], "response_id": raw.get("id"), "errors": report["verification"].get("errors", [])}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
