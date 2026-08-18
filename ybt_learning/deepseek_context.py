from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


BARE_ANSWER_LINE_RE = re.compile(r"(?im)^\s*#{0,6}\s*\d{1,2}\s*[.．、]\s*[A-D]\s*$")
CANARY_RE = re.compile(r"^[0-9a-f]{16}$")
CONTEXT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _context_binding_hash(context: dict[str, Any]) -> str:
    """Hash the exact context payload, excluding only its self-hash field."""
    payload = dict(context)
    evidence = dict(payload.get("evidence") or {})
    evidence.pop("context_sha256", None)
    payload["evidence"] = evidence
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derived_probe(canary: str, qid: str) -> str:
    """Derive a context-bound, answer-free worker probe token."""
    return hashlib.sha256(f"{canary}{qid}".encode("utf-8")).hexdigest()[:8]


def _question_prefix(text: str, length: int = 80) -> str:
    return " ".join(str(text).split())[:length]


def _equivalent_question_prefix(actual: Any, expected: str) -> bool:
    """Allow tiny model truncation/escaping drift without accepting paraphrase."""
    if actual == expected:
        return True
    if not isinstance(actual, str) or not isinstance(expected, str):
        return False
    if not actual or not expected:
        return False
    common = 0
    for left, right in zip(actual, expected):
        if left != right:
            break
        common += 1
    ratio = SequenceMatcher(None, actual, expected, autojunk=False).ratio()
    if common >= min(72, len(actual), len(expected)) and ratio >= 0.965 and abs(len(actual) - len(expected)) <= 3:
        return True
    return False


def _project_support(student_packet_path: Path, section: str) -> dict[str, Any]:
    """Load non-answer route metadata beside the canonical student packet.

    The independent context must tell DeepSeek which lessons and numbered
    exercise groups belong to the section.  It must not pull in answer-sidecar
    or lesson-packet content.
    """
    project_root = student_packet_path.parents[3]
    data_root = project_root / "data"
    support: dict[str, Any] = {
        "learning_plan": None,
        "sequential_learning_packet": None,
        "question_coverage": [],
        "bridge_micro_lessons": [],
    }
    plan_path = data_root / "chapter1_learning_plan.json"
    if plan_path.exists():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            support["learning_plan"] = next((item for item in plan.get("plan", []) if item.get("section") == section), None)
        except json.JSONDecodeError:
            support["learning_plan"] = {"status": "malformed"}
    learning_packet_path = student_packet_path.with_name("learning_packet.json")
    if learning_packet_path.exists():
        try:
            learning_packet = json.loads(learning_packet_path.read_text(encoding="utf-8"))
            cycles = learning_packet.get("learning_cycles", [])
            active_cycle_id = None
            state_path = data_root / "main_state.json"
            if state_path.exists():
                try:
                    state = json.loads(state_path.read_text(encoding="utf-8"))
                    if state.get("target_identity", {}).get("section") == section:
                        active_cycle_id = state.get("active_batch", {}).get("batch_id")
                except json.JSONDecodeError:
                    active_cycle_id = None
            current_cycle = next((item for item in cycles if item.get("cycle_id") == active_cycle_id), None)
            if current_cycle is None and cycles:
                current_cycle = cycles[0]

            current_projection = None
            if current_cycle is not None:
                current_projection = {
                    "cycle_id": current_cycle.get("cycle_id"),
                    "sequence": current_cycle.get("sequence"),
                    "title": current_cycle.get("title"),
                    "course_keys": current_cycle.get("course_keys", []),
                    "prerequisite_course_keys": current_cycle.get("prerequisite_course_keys", []),
                    "knowledge_refs": current_cycle.get("knowledge_refs", []),
                    "prerequisite_knowledge_refs": current_cycle.get("prerequisite_knowledge_refs", []),
                    "type_refs": current_cycle.get("type_refs", []),
                    "example_numbers": [item.get("example_number") for item in current_cycle.get("worked_examples", [])],
                    "variant_item_ids": [item.get("item_id") for item in current_cycle.get("direct_variants", [])],
                    "exercise_keys": [f"{item.get('group')}{item.get('number')}" for item in current_cycle.get("exercise_questions", [])],
                    "bridge_unit_ids": current_cycle.get("bridge_unit_ids", []),
                    "method_checkpoint_ids": [item.get("id") for item in current_cycle.get("method_checkpoints", [])],
                    "action_order": current_cycle.get("action_order", []),
                    "advance_gate": current_cycle.get("advance_gate"),
                    "failure_rule": current_cycle.get("failure_rule"),
                }
            support["sequential_learning_packet"] = {
                "path": str(learning_packet_path),
                "status": learning_packet.get("status"),
                "counts": learning_packet.get("counts", {}),
                "workflow_order": learning_packet.get("workflow_order", []),
                "planning_scope": "complete_section_route",
                "execution_scope": "current_cycle_only",
                "cycle_count": len(cycles),
                "current_cycle": current_projection,
            }
        except json.JSONDecodeError:
            support["sequential_learning_packet"] = {"status": "malformed"}
    coverage_path = data_root / "question_coverage.json"
    if coverage_path.exists():
        try:
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            support["question_coverage"] = [item for item in coverage.get("questions", []) if item.get("section") == section]
        except json.JSONDecodeError:
            support["question_coverage"] = [{"status": "malformed"}]
    bridge_path = data_root / "bridge_micro_lessons.json"
    if bridge_path.exists():
        try:
            bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
            support["bridge_micro_lessons"] = [item for item in bridge.get("units", []) if section in item.get("sections", [])]
        except json.JSONDecodeError:
            support["bridge_micro_lessons"] = [{"status": "malformed"}]
    return support


def _validate_route_support(context: dict[str, Any]) -> dict[str, Any]:
    """Validate the non-spoiler course/question routing layer separately."""
    support = context.get("route_support")
    errors: list[str] = []
    if not isinstance(support, dict):
        errors.append("route_support_missing")
        return {"status": "failed", "errors": errors}
    plan = support.get("learning_plan")
    if not isinstance(plan, dict):
        errors.append("learning_plan_missing")
    else:
        for field in ("must_listen_courses", "type_training"):
            if not plan.get(field):
                errors.append(f"learning_plan_{field}_missing")
    learning_packet = support.get("sequential_learning_packet")
    if not isinstance(learning_packet, dict) or learning_packet.get("status") != "VERIFIED":
        errors.append("sequential_learning_packet_missing")
    elif not isinstance(learning_packet.get("current_cycle"), dict):
        errors.append("current_learning_cycle_missing")
    coverage = support.get("question_coverage")
    if not isinstance(coverage, list) or not coverage or any(not item.get("question_key") for item in coverage if isinstance(item, dict)):
        errors.append("question_coverage_missing")
    bridges = support.get("bridge_micro_lessons")
    if not isinstance(bridges, list):
        errors.append("bridge_route_missing")
    route_text = json.dumps(support, ensure_ascii=False)
    if re.search(r"answer_text|最终答案|答案为|解析：|解答：", route_text, flags=re.I):
        errors.append("route_answer_leak")
    return {"status": "passed" if not errors else "failed", "errors": errors}


def _load_student_learning_items(student_packet_path: Path) -> dict[str, Any]:
    """Load the separate answer-free example/variant projection when present.

    Temporary unit-test packets from before this projection existed remain
    valid with an empty set.  Real generated packets always write the file;
    the acceptance layer checks its counts and current source hash.
    """
    path = student_packet_path.with_name("student_learning_items.json")
    if not path.is_file():
        return {"status": "MISSING", "worked_examples": [], "direct_variants": [], "counts": {"total": 0}}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"status": "MALFORMED", "worked_examples": [], "direct_variants": [], "counts": {"total": 0}}
    if data.get("packet_type") != "DEEPSEEK_STUDENT_LEARNING_ITEMS":
        return {"status": "MALFORMED", "worked_examples": [], "direct_variants": [], "counts": {"total": 0}}
    return data


def build_context(student_packet_path: str | Path, *, output_path: str | Path | None = None) -> dict[str, Any]:
    packet_path = Path(student_packet_path)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if packet.get("packet_type") != "DEEPSEEK_STUDENT_PACKET":
        raise ValueError("only student_packet.json may enter independent DeepSeek context")
    if packet.get("answer_sidecar") is not None:
        raise ValueError("answer_sidecar must remain absent")
    learning_item_packet = _load_student_learning_items(packet_path)
    learning_items = [
        *learning_item_packet.get("worked_examples", []),
        *learning_item_packet.get("direct_variants", []),
    ]

    def _enriched_pages() -> list[dict[str, Any]]:
        """知识页优先采用已过答案泄漏门禁的 knowledge_and_type_pages。

        学生包把"方法册教学续页"整页替换成中性锚点，会把该页左栏知识点定义
        （如投影向量、数量积性质）一起剥掉；这些定义是零基础学生做题的前置知识，
        不是答案。KAT 页已通过 _redact_student_text 泄漏门禁，可直接进入独立上下文；
        无 KAT 覆盖的页保持原样（含锚点兜底）。
        """
        kat_by_doc: dict[Any, dict[str, Any]] = {}
        kat_path = packet_path.with_name("learning_packet.json")
        if kat_path.exists():
            try:
                kat = json.loads(kat_path.read_text(encoding="utf-8")).get("knowledge_and_type_pages", [])
                kat_by_doc = {p.get("ocr_doc"): p for p in kat if str(p.get("text", "")).strip()}
            except (json.JSONDecodeError, OSError):
                kat_by_doc = {}
        pages: list[dict[str, Any]] = []
        for p in packet.get("pages", []):
            text = p.get("text", "")
            if "为方法册教学续页" in str(text):
                kp = kat_by_doc.get(p.get("ocr_doc"))
                if kp is not None:
                    pages.append({
                        "ocr_doc": p["ocr_doc"],
                        "text": kp.get("text", ""),
                        "image_refs": kp.get("image_refs") or p.get("image_refs") or [],
                        "math_errors": kp.get("math_errors") or p.get("math_errors") or [],
                    })
                    continue
            pages.append({
                "ocr_doc": p["ocr_doc"],
                "text": text,
                "image_refs": p.get("image_refs", []),
                "math_errors": p.get("math_errors", []),
            })
        return pages

    context = {
        "schema_version": "7.1",
        "consumer": "deepseek_worker",
        "packet_type": "DEEPSEEK_STUDENT_CONTEXT",
        "model_contract": {"model": "opencode-go/deepseek-v4-flash", "reasoning_effort": "max", "context_window": 1000000},
        "section": packet["section"],
        "evidence": {
            "canary": "",
            "binding": "worker must echo canary and answer derived probes from this exact context",
            "probe_qids": [question.get("qid") for question in packet.get("questions", [])[:3] if question.get("qid")],
        },
        "status": packet["status"],
        "manifest": packet["manifest"],
        "pages": _enriched_pages(),
        "questions": packet["questions"],
        "learning_items": learning_items,
        "learning_items_manifest": {
            "status": learning_item_packet.get("status", "MISSING"),
            "counts": learning_item_packet.get("counts", {"total": len(learning_items)}),
            "source_packet_type": learning_item_packet.get("packet_type"),
        },
        "unresolved": packet["unresolved"],
        "route_support": _project_support(packet_path, packet["section"]),
        "instructions": [
            "先核对 status；UNVERIFIED 只可报告缺口，不可讲题或报答案。",
            "question_text、page text 和 vision_sidecar/vision_sidecars 是唯一输入；不要假设看到了原图。",
            "缺失图片、乱码公式、题号不确定必须标记 unknown/E0。",
            "课程覆盖不能替代学生 mastery；猜中、提示后、看答案必须保持污染。",
            "route_support.learning_plan 只用于核对整节路线；实际回复只执行 route_support.sequential_learning_packet.current_cycle，不展示或推进后续循环。",
            "当前循环按 course_keys→knowledge_refs/type_refs→例题及其紧跟变式→exercise_keys→本批验收推进。",
            "learning_items 是完整章节路线中的无答案例题/直属变式题面；教学阶段必须先学习例题方法，独立作答阶段不得读取 teaching_text 或任何答案字段。",
            "每个 learning_items 记录都必须按 visual_status 执行；NEEDS_VISION_SIDECAR、MISSING_OCR_ANCHOR 或 UNVERIFIED 只能记录 BLOCKED，不能猜图。",
            "独立作答前必须由编排器单独完成 route_support.sequential_learning_packet 指向的知识页、例题教学和无答案直接变式；不得在独立作答阶段重新读取例题解法。",
            "route_support.question_coverage 只表示解锁/阻断，不表示学生已经掌握。",
            "route_support.bridge_micro_lessons 只提供无答案方法骨架；SUPPLEMENT_READY 表示补充课文本已具备，不表示学生 mastery；SUPPLEMENT_REQUIRED 表示仍缺课。",
            "独立消费探针：先回显 evidence.canary；对指定 qid 计算 sha256(canary+qid) 前8位，并只复述该题当前可见字段；不得输出答案册内容。",
        ],
    }
    # 确定性 canary：由"去掉 canary 后的上下文"哈希派生，而不是随机数。
    # 同内容重建得到同 canary/同绑定哈希，避免构建 worker 重跑 build-* 时把
    # 正在进行的模拟与探针全部作废（随机 canary 曾导致探针竞态失败）。
    evidence_payload = dict(context["evidence"])
    evidence_payload.pop("canary", None)
    canonical_no_canary = json.dumps({**context, "evidence": evidence_payload}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    context["evidence"]["canary"] = hashlib.sha256(canonical_no_canary.encode("utf-8")).hexdigest()[:16]
    context["evidence"]["probe_tokens"] = {
        qid: derived_probe(context["evidence"]["canary"], qid)
        for qid in context["evidence"]["probe_qids"]
    }
    context["evidence"]["context_sha256"] = _context_binding_hash(context)
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return context


def context_path_for_student_packet(student_packet_path: str | Path, *, root: str | Path | None = None) -> Path:
    """Return the sole canonical context path for a student packet.

    Older packet-local context.json files are intentionally not reused; they
    predate the current student packet schema and can carry stale qids.
    """
    packet = Path(student_packet_path)
    project_root = Path(root) if root is not None else packet.parents[3]
    return project_root / "data" / "contexts" / f"{packet.parent.name}.json"


def validate_context(path: str | Path) -> dict[str, Any]:
    context = json.loads(Path(path).read_text(encoding="utf-8"))
    errors: list[str] = []
    if context.get("consumer") != "deepseek_worker":
        errors.append("wrong_consumer")
    if context.get("packet_type") != "DEEPSEEK_STUDENT_CONTEXT":
        errors.append("wrong_packet_type")
    if context.get("model_contract", {}).get("model") != "opencode-go/deepseek-v4-flash":
        errors.append("wrong_model_contract")
    if context.get("model_contract", {}).get("reasoning_effort") != "max":
        errors.append("wrong_reasoning_effort")
    if context.get("model_contract", {}).get("context_window") != 1000000:
        errors.append("wrong_context_window")
    evidence = context.get("evidence")
    if not isinstance(evidence, dict) or not CANARY_RE.fullmatch(str(evidence.get("canary", ""))):
        errors.append("evidence_canary_missing")
    else:
        expected_hash = _context_binding_hash(context)
        if evidence.get("context_sha256") != expected_hash:
            errors.append("context_binding_hash_mismatch")
        probe_qids = evidence.get("probe_qids", [])
        if not isinstance(probe_qids, list) or any(not isinstance(qid, str) or not qid for qid in probe_qids):
            errors.append("evidence_probe_qids_invalid")
    if context.get("status") != "VERIFIED":
        errors.append("context_status_not_verified")
    manifest = context.get("manifest", {})
    questions = context.get("questions", [])
    if manifest.get("question_count") is not None and manifest.get("question_count") != len(questions):
        errors.append("question_count_mismatch")
    if any(not str(question.get("question_text", "")).strip() for question in questions):
        errors.append("empty_question_text")
    if any(question.get("visual_status") not in {"READY_TEXT_ONLY", "VISION_VERIFIED"} for question in questions):
        errors.append("visual_not_consumable")
    learning_items = context.get("learning_items", [])
    if not isinstance(learning_items, list):
        errors.append("learning_items_invalid")
        learning_items = []
    learning_ids = [str(item.get("item_id")) for item in learning_items if isinstance(item, dict)]
    if len(learning_ids) != len(set(learning_ids)):
        errors.append("learning_item_duplicate_id")
    item_counts = context.get("learning_items_manifest", {}).get("counts", {})
    if item_counts.get("total") is not None and item_counts.get("total") != len(learning_items):
        errors.append("learning_item_count_mismatch")
    for item in learning_items:
        if not isinstance(item, dict) or not str(item.get("item_id", "")).strip():
            errors.append("learning_item_id_missing")
            continue
        if not str(item.get("question_text", "")).strip():
            errors.append(f"empty_learning_item:{item.get('item_id')}")
        if item.get("kind") not in {"example", "direct_variant"}:
            errors.append(f"learning_item_kind_invalid:{item.get('item_id')}")
        if item.get("visual_status") not in {"READY_TEXT_ONLY", "VISION_VERIFIED", "NEEDS_VISION_SIDECAR", "MISSING_OCR_ANCHOR", "UNVERIFIED"}:
            errors.append(f"learning_item_visual_status_invalid:{item.get('item_id')}")
    if context.get("unresolved"):
        errors.append("unresolved_items")
    raw = json.dumps({"pages": context.get("pages", []), "questions": context.get("questions", []), "learning_items": learning_items, "route_support": context.get("route_support", {})}, ensure_ascii=False)
    leakage_patterns = [
        r"answer_text",
        r"(?m)^\s*(?:解法\s*[一二两12]|证明|证明过程|解答)\s*[：:]",
        r"(?m)^\s*(?:答案|解析|解答|点评|反思)\s*[：:]",
        r"(?:最终答案|故答案|答案为|所以其余弦值|因此得到|故得|故为)",
    ]
    text_fields = [
        str(page.get("text", "")) for page in context.get("pages", [])
    ] + [
        str(question.get("question_text", "")) for question in context.get("questions", [])
    ] + [
        str(item.get("question_text", "")) for item in learning_items
    ] + [
        str(context.get("route_support", {}).get("learning_plan", "")),
        *(str(item) for item in context.get("route_support", {}).get("bridge_micro_lessons", [])),
    ]
    if any(re.search(pattern, raw, flags=re.I) for pattern in leakage_patterns) or any(BARE_ANSWER_LINE_RE.search(value) for value in text_fields):
        errors.append("answer_leak")
    route = _validate_route_support(context)
    return {"status": "passed" if not errors else "failed", "errors": errors, "route_status": route["status"], "route_errors": route["errors"], "path": str(path)}


def verify_worker_probe(context_path: str | Path, response_path: str | Path) -> dict[str, Any]:
    """Verify a real DeepSeek response against one canonical context.

    This is intentionally separate from ``validate_context``: a valid input
    artifact does not prove that a worker actually received or understood it.
    The response must echo every question's answer-free identity and the
    context-bound canary/probes under the exact runtime contract.
    """
    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    response = json.loads(Path(response_path).read_text(encoding="utf-8"))
    errors: list[str] = []
    context_check = validate_context(context_path)
    if context_check["status"] != "passed":
        errors.append("context_not_consumable")
    contract = context.get("model_contract", {})
    runtime = response.get("runtime", {}) if isinstance(response, dict) else {}
    for field in ("model", "reasoning_effort", "context_window"):
        if runtime.get(field) != contract.get(field):
            errors.append(f"runtime_{field}_mismatch")
    evidence = context.get("evidence", {})
    if response.get("context_sha256") != evidence.get("context_sha256"):
        errors.append("response_context_hash_mismatch")
    if response.get("canary") != evidence.get("canary"):
        errors.append("response_canary_mismatch")
    probes = response.get("qid_probes", {})
    if not isinstance(probes, dict):
        errors.append("qid_probes_missing")
    else:
        for qid in evidence.get("probe_qids", []):
            if probes.get(qid) != derived_probe(str(evidence.get("canary")), qid):
                errors.append(f"probe_mismatch:{qid}")
    questions = {str(item.get("qid")): item for item in context.get("questions", []) if item.get("qid")}
    echoes = response.get("question_echo", {})
    if not isinstance(echoes, dict) or set(echoes) != set(questions):
        errors.append("question_echo_incomplete")
    else:
        for qid, question in questions.items():
            echo = echoes.get(qid, {})
            expected_text_hash = hashlib.sha256(str(question.get("question_text", "")).encode("utf-8")).hexdigest()
            if echo.get("question_text_sha256") != expected_text_hash:
                errors.append(f"question_echo_hash_mismatch:{qid}")
            if echo.get("visual_status") != question.get("visual_status"):
                errors.append(f"question_echo_visual_mismatch:{qid}")
    response_text = json.dumps(response, ensure_ascii=False)
    if re.search(r"answer_text|最终答案|答案为|解析：|解答：|故答案", response_text, flags=re.I):
        errors.append("response_answer_leak")
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "context": context_check,
        "path": str(response_path),
    }


def verify_worker_understanding(
    context_path: str | Path,
    response_path: str | Path,
    *,
    transport: dict[str, Any] | None = None,
    expected_question_prefixes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Verify a tool-free DeepSeek understanding receipt.

    Pure HTTP workers may not have a hashing tool.  This contract therefore
    tests exact context binding plus semantic coverage: every question's key,
    number, visual gate and text prefix, followed by the ordered study route.
    The outer transport record independently proves the requested model and
    completed API response.
    """
    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    response = json.loads(Path(response_path).read_text(encoding="utf-8"))
    errors: list[str] = []
    context_check = validate_context(context_path)
    if context_check["status"] != "passed":
        errors.append("context_not_consumable")
    contract = context.get("model_contract", {})
    runtime = response.get("runtime", {}) if isinstance(response, dict) else {}
    expected_model = str(contract.get("model", ""))
    accepted_models = {expected_model, expected_model.rsplit("/", 1)[-1]}
    if runtime.get("model") not in accepted_models:
        errors.append("runtime_model_mismatch")
    if runtime.get("reasoning_effort") != contract.get("reasoning_effort"):
        errors.append("runtime_reasoning_effort_mismatch")
    if runtime.get("context_window") != contract.get("context_window"):
        errors.append("runtime_context_window_mismatch")
    if transport:
        if transport.get("requested_model") != expected_model:
            errors.append("transport_requested_model_mismatch")
        if transport.get("status") != "completed":
            errors.append("transport_not_completed")
        returned_model = transport.get("returned_model")
        if returned_model not in accepted_models:
            errors.append("transport_returned_model_mismatch")
    evidence = context.get("evidence", {})
    if response.get("context_sha256") != evidence.get("context_sha256"):
        errors.append("response_context_hash_mismatch")
    if response.get("canary") != evidence.get("canary"):
        errors.append("response_canary_mismatch")
    if response.get("probe_tokens") != evidence.get("probe_tokens"):
        errors.append("probe_token_echo_mismatch")
    questions = {str(item.get("qid")): item for item in context.get("questions", []) if item.get("qid")}
    echoes = response.get("question_echo", {})
    if not isinstance(echoes, dict) or set(echoes) != set(questions):
        errors.append("question_echo_incomplete")
    else:
        for qid, question in questions.items():
            echo = echoes.get(qid, {})
            expected_key = f"{question.get('group')}{question.get('number')}"
            if echo.get("question_key") != expected_key:
                errors.append(f"question_key_mismatch:{qid}")
            if echo.get("group") != question.get("group") or echo.get("number") != question.get("number"):
                errors.append(f"question_number_mismatch:{qid}")
            if echo.get("visual_status") != question.get("visual_status"):
                errors.append(f"question_visual_mismatch:{qid}")
            expected_prefix = (expected_question_prefixes or {}).get(qid, _question_prefix(question.get("question_text", "")))
            actual_prefix = echo.get("question_text_prefix")
            if actual_prefix != expected_prefix:
                # The echo is a binding receipt, not a summary.  A shortened
                # prefix can hide a changed/omitted clause, so accept only an
                # exact byte-for-byte copy of the canonical projection.
                errors.append(f"question_prefix_mismatch:{qid}")
    summary = response.get("understanding_summary", {})
    support = context.get("route_support", {})
    plan = support.get("learning_plan", {}) if isinstance(support, dict) else {}
    if not isinstance(summary, dict):
        errors.append("understanding_summary_missing")
    else:
        if summary.get("section") != context.get("section"):
            errors.append("summary_section_mismatch")
        if summary.get("question_count") != len(questions):
            errors.append("summary_question_count_mismatch")
        if summary.get("expected_groups") != context.get("manifest", {}).get("expected_groups"):
            errors.append("summary_group_ranges_mismatch")
        expected_courses = [item.get("course_key") for item in plan.get("must_listen_courses", []) if item.get("course_key")]
        if summary.get("must_listen_course_keys") != expected_courses:
            errors.append("summary_course_route_mismatch")
        expected_points = [item.get("id") for item in plan.get("knowledge_points", []) if item.get("id")]
        if summary.get("knowledge_point_ids") != expected_points:
            errors.append("summary_knowledge_points_mismatch")
        expected_types = [item.get("type") for item in plan.get("type_training", []) if item.get("type")]
        if summary.get("type_training") != expected_types:
            errors.append("summary_type_route_mismatch")
        expected_exercises = plan.get("exercise_order")
        if summary.get("exercise_order") != expected_exercises:
            errors.append("summary_exercise_order_mismatch")
        if summary.get("mastery_not_assessed") is not True:
            errors.append("summary_mastery_boundary_missing")
    response_text = json.dumps(response, ensure_ascii=False)
    if re.search(r"answer_text|最终答案|答案为|解析：|解答：|故答案", response_text, flags=re.I):
        errors.append("response_answer_leak")
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "context": context_check,
        "path": str(response_path),
        "verification_kind": "standalone_understanding_receipt",
    }
