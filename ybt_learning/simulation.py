from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .catalog import select_section_plan
from .common import load_json, now_iso, save_json
from .deepseek_context import validate_context
from .manifest import load_manifest
from .ocr import ocr_config_status
from .packet import verify_packet
from .vision import test_vision_config


ZERO_BASE_PERSONAS = [
    ("Z1", "1.1", "空间向量运算零基础"),
    ("Z2", "1.2+1.3", "基底与坐标表示零基础"),
    ("Z3", "1.4", "空间向量应用零基础"),
    ("Z4", "micro专题1", "立体几何综合题零基础"),
    ("Z5", "全章", "全章零基础总裁判"),
]

BRIDGE_RELEASE_READY_STATUSES = {"SUPPLEMENT_READY", "VERIFIED"}


# Each row has a different execution policy.  These are deterministic proxy
# strategies, not ten invented human transcripts.  Keeping the policy in the
# artifact makes it possible to tell whether the rows actually exercised
# different failure paths.
PROXY_STRATEGIES = {
    "Z1": {"strategy_id": "zero_base_slow_start", "course_first": True, "visual_policy": "block_until_visual", "hint_policy": "H0_then_H1", "review_policy": "same_day_recap"},
    "Z2": {"strategy_id": "zero_base_coordinate_first", "course_first": True, "visual_policy": "block_only_image_questions", "hint_policy": "first_break_only", "review_policy": "next_day_cold_recall"},
    "Z3": {"strategy_id": "zero_base_geometry_check", "course_first": False, "visual_policy": "recheck_geometry_before_attempt", "hint_policy": "H0_only", "review_policy": "error_log_then_recall"},
    "Z4": {"strategy_id": "zero_base_bridge_first", "course_first": True, "visual_policy": "require_sidecar_or_stop", "hint_policy": "bridge_patch_after_two_blocks", "review_policy": "near_variant_then_recall"},
    "Z5": {"strategy_id": "zero_base_full_chapter_audit", "course_first": True, "visual_policy": "chapter_wide_fail_closed", "hint_policy": "one_task_at_a_time", "review_policy": "section_exit_gates"},
}


# Conservative question-to-knowledge-point index for the report.  It is an
# exposure/coverage index, not a claim that the learner has mastered the
# point.  A question can intentionally appear under more than one point.
KNOWLEDGE_POINT_QUESTION_MAP = {
    "1.1": {
        "1.1-k1": ["A1", "A2", "A3"],
        "1.1-k2": ["A2", "A3", "B4", "B5", "B7", "B9", "B10", "B11", "B12", "C13"],
        "1.1-k3": ["B9", "B10", "C13", "C14"],
        "1.1-k4": ["B4", "B5", "B6", "B7", "B8", "B11", "B12", "C14"],
    },
    "1.2+1.3": {
        "1.2-k1": ["A1", "A2", "A3", "A4", "B5", "B8", "B9", "B10", "C14"],
        "1.3-k1": ["A1", "A2", "A3", "A4", "B6", "B11", "B12", "B13", "C15", "C16"],
        "1.3-k2": ["A1", "A2", "A3", "A4", "B6", "B7", "B10", "B11", "B12", "B13", "C15", "C16"],
    },
    "1.4": {
        "1.4-k1": ["A1", "A2", "B3", "B4", "B5", "B8", "C11", "C12"],
        "1.4-k2": ["A2", "B4", "B5", "B6", "B8", "C9", "C10", "C11", "C12"],
        "1.4-k3": ["A1", "A2", "B3", "B4", "B5", "B6", "B7", "B8", "C9", "C10", "C11", "C12"],
    },
    "micro专题1": {
        "micro-k1": ["B1", "B2", "C6", "C7"],
        "micro-k2": ["B3", "B4", "C5", "C6", "C7", "C8"],
        "micro-k3": ["B2", "C7", "C8"],
    },
}


def _folder(section: str) -> str:
    return section.replace("+", "_")


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _existing(paths: list[str]) -> list[str]:
    return [path for path in paths if Path(path).is_file()]


def _bridge_curriculum(root: Path) -> dict[str, Any]:
    path = root / "data" / "bridge_micro_lessons.json"
    if not path.exists():
        return {"status": "missing", "path": str(path), "units": []}
    data = load_json(path)
    units = data.get("units", []) if isinstance(data, dict) else []
    return {
        "status": "ready" if isinstance(units, list) and units and all(
            isinstance(item, dict)
            and item.get("id")
            and item.get("status") in {"SOURCE_METHOD_READY", "SUPPLEMENT_REQUIRED", "SUPPLEMENT_READY", "VERIFIED"}
            and isinstance(item.get("lesson_steps"), list)
            for item in units
        ) else "invalid",
        "path": str(path),
        "unit_count": len(units) if isinstance(units, list) else 0,
        "units": units if isinstance(units, list) else [],
    }


def _real_user_observation_contract(root: Path) -> dict[str, Any]:
    """Load the human-observation contract without fabricating observations."""
    path = root / "data" / "real_user_observations.json"
    if not path.exists():
        return {"status": "missing", "path": str(path), "required_zero_base_users": 5, "records": []}
    data = load_json(path)
    records = data.get("records", []) if isinstance(data, dict) else []
    return {
        "status": data.get("status", "invalid") if isinstance(data, dict) else "invalid",
        "path": str(path),
        "required_zero_base_users": data.get("required_zero_base_users", 5) if isinstance(data, dict) else 5,
        "record_count": len(records) if isinstance(records, list) else 0,
        "records": records if isinstance(records, list) else [],
    }


def _answer_status(section: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "data" / "packets" / _folder(section) / "answer_sidecar.json"
    if not path.exists():
        return {"status": "missing", "path": str(path), "total": 0, "nonempty": 0, "evidence": {}}
    data = load_json(path)
    answers = data.get("answers", [])
    evidence: dict[str, int] = {}
    nonempty = 0
    for answer in answers:
        kind = answer.get("answer_kind") or "none"
        evidence[kind] = evidence.get(kind, 0) + 1
        if str(answer.get("answer_text", "")).strip():
            nonempty += 1
    return {"status": "passed" if answers and nonempty == len(answers) else "failed", "path": str(path), "total": len(answers), "nonempty": nonempty, "evidence": evidence}


def _section_snapshot(section: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    folder = _folder(section["id"])
    packet_path = root / "data" / "packets" / folder / "student_packet.json"
    context_path = root / "data" / "contexts" / f"{folder}.json"
    packet = load_json(packet_path) if packet_path.exists() else {}
    context = validate_context(context_path) if context_path.exists() else {"status": "missing", "errors": ["context_missing"]}
    packet_check = verify_packet(packet_path) if packet_path.exists() else {"status": "missing", "errors": ["student_packet_missing"]}
    visual_counts: dict[str, int] = {}
    for question in packet.get("questions", []):
        status = question.get("visual_status", "UNKNOWN")
        visual_counts[status] = visual_counts.get(status, 0) + 1
    selected = select_section_plan(plan, section["id"])
    required_courses = selected.get("required_courses", [])
    support_courses = selected.get("support_courses", [])
    courses = required_courses + support_courses
    course_records = []
    for item in courses:
        recommended_videos = item.get("recommended_video_files", [])
        transcript_files = item.get("transcript_files", [])
        course_records.append({
            "course_key": item.get("course_key"),
            "role": item.get("role"),
            "recommended_variant": item.get("recommended_variant"),
            "recommended_video_files": recommended_videos,
            "transcript_files": transcript_files,
            "video_files_present": _existing(recommended_videos),
            "transcript_files_present": _existing(transcript_files),
            "ready": bool(_existing(recommended_videos)) and bool(_existing(transcript_files)),
        })
    course_ready = bool(required_courses) and all(item["ready"] for item in course_records)
    bridges = section.get("bridge_units", [])
    bridge_curriculum = _bridge_curriculum(root)
    bridge_units = [item for item in bridge_curriculum.get("units", []) if section["id"] in item.get("sections", [])]
    bridge_ids = {item.get("id") for item in bridges}
    applicable_bridge_units = [item for item in bridge_units if item.get("id") in bridge_ids]
    bridge_ready = not bridges or (bridge_curriculum.get("status") == "ready" and all(item.get("status") in BRIDGE_RELEASE_READY_STATUSES for item in applicable_bridge_units))
    answers = _answer_status(section["id"])
    coverage_path = root / "data" / "question_coverage.json"
    coverage = load_json(coverage_path) if coverage_path.exists() else {"questions": []}
    question_coverage = [item for item in coverage.get("questions", []) if item.get("section") == section["id"]]
    question_results = [{
        "question_key": item.get("question_key"),
        "qid": item.get("qid"),
        "release_status": item.get("release_status"),
        "blockers": item.get("blockers", []),
        "result": "BLOCKED" if item.get("blockers") else ("READY_FOR_ATTEMPT_NOT_MASTERY" if item.get("release_status") in {"COURSE_READY_NOT_MASTERY", "READY_FOR_INDEPENDENT_ATTEMPT"} else "NOT_ASSESSED"),
    } for item in question_coverage]
    point_map = KNOWLEDGE_POINT_QUESTION_MAP.get(section["id"], {})
    knowledge_point_results = [{
        "id": item.get("id"),
        "label": item.get("label"),
        "examples": item.get("examples", []),
        "question_keys": point_map.get(item.get("id"), []),
        "result": (
            "BLOCKED" if any(q.get("question_key") in point_map.get(item.get("id"), []) and q.get("blockers") for q in question_coverage)
            else ("READY_FOR_ATTEMPT_NOT_MASTERY" if any(q.get("question_key") in point_map.get(item.get("id"), []) for q in question_coverage) else "NOT_ASSESSED")
        ),
    } for item in section.get("knowledge_points", [])]
    question_result_summary = {
        "total": len(question_results),
        "blocked": sum(item.get("result") == "BLOCKED" for item in question_results),
        "ready_for_attempt_not_mastery": sum(item.get("result") == "READY_FOR_ATTEMPT_NOT_MASTERY" for item in question_results),
        "not_assessed": sum(item.get("result") == "NOT_ASSESSED" for item in question_results),
    }
    knowledge_point_result_summary = {
        "total": len(knowledge_point_results),
        "blocked": sum(item.get("result") == "BLOCKED" for item in knowledge_point_results),
        "ready_for_attempt_not_mastery": sum(item.get("result") == "READY_FOR_ATTEMPT_NOT_MASTERY" for item in knowledge_point_results),
        "not_assessed": sum(item.get("result") == "NOT_ASSESSED" for item in knowledge_point_results),
    }
    return {
        "section": section["id"],
        "packet": {"status": packet.get("status", "missing"), "check": packet_check, "path": str(packet_path)},
        "deepseek_context": {"check": context, "path": str(context_path)},
        "answers": answers,
        "visual": {"counts": visual_counts, "all_consumable": bool(packet.get("questions")) and all(q.get("visual_status") in {"READY_TEXT_ONLY", "VISION_VERIFIED"} for q in packet.get("questions", []))},
        "courses": {
            "required_count": len(required_courses),
            "support_count": len(support_courses),
            "must_listen_count": len(courses),
            "ready": course_ready,
            "records": course_records,
            "source": "Downloads/课程合集",
            "all_files_present": all(Path(path).is_file() for item in courses for path in item.get("video_files", []) + item.get("transcript_files", [])),
        },
        "bridges": {
            "count": len(bridges),
            "named_unit_count": len(bridge_units),
            "ready": bridge_ready,
            "unverified": [item.get("id") for item in applicable_bridge_units if item.get("status") not in BRIDGE_RELEASE_READY_STATUSES],
            "named_units": [{"id": item.get("id"), "title": item.get("title"), "status": item.get("status"), "target_questions": item.get("target_questions", []), "required_by_section": item.get("id") in bridge_ids} for item in bridge_units],
        },
        "question_results": question_results,
        "knowledge_point_results": knowledge_point_results,
        "question_result_summary": question_result_summary,
        "knowledge_point_result_summary": knowledge_point_result_summary,
    }


def _release_gaps(snapshot: dict[str, Any], browser: dict[str, Any], ocr: dict[str, Any], vision: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if snapshot["packet"]["status"] != "VERIFIED" or snapshot["packet"]["check"].get("status") != "passed":
        gaps.append("packet_not_verified")
    if snapshot["deepseek_context"]["check"].get("status") != "passed":
        gaps.append("deepseek_context_not_consumable")
    if not snapshot["visual"]["all_consumable"]:
        gaps.append("visual_sidecar_incomplete")
    if snapshot["answers"]["status"] != "passed":
        gaps.append("answer_sidecar_incomplete")
    if not snapshot["courses"]["ready"]:
        gaps.append("required_course_or_transcript_missing")
    if not snapshot["bridges"]["ready"]:
        gaps.append("bridge_units_not_verified")
    if browser.get("8.5", {}).get("status") != "passed":
        gaps.append("browser_8.5_missing")
    if browser.get("8.5课程", {}).get("status") != "passed":
        gaps.append("browser_8.5_course_missing")
    if ocr.get("active_provider") != "paddle_ai_studio" or not ocr.get("active_provider_live_verified"):
        gaps.append("paddle_ai_studio_live_not_verified")
    if not vision.get("live_verified"):
        gaps.append("vision_live_not_verified")
    return list(dict.fromkeys(gaps))


def _synthetic_trace(snapshot: dict[str, Any], strategy: dict[str, Any]) -> list[dict[str, Any]]:
    """Create an explicit proxy trace without inventing correctness answers."""
    trace: list[dict[str, Any]] = []
    for course in snapshot["courses"].get("records", []):
        trace.append({"action": "course_navigation_available", "course_key": course.get("course_key"), "source": "Downloads/课程合集", "status": "ready" if course.get("ready") else "blocked", "strategy": strategy["strategy_id"]})
    trace.append({"action": "visual_gate", "policy": strategy["visual_policy"], "status": "passed" if snapshot["visual"]["all_consumable"] else "blocked", "counts": snapshot["visual"]["counts"]})
    for item in snapshot.get("question_results", []):
        trace.append({
            "action": "question_decision",
            "question_key": item.get("question_key"),
            "decision": "independent_attempt_allowed" if item.get("result") == "READY_FOR_ATTEMPT_NOT_MASTERY" else "blocked_before_attempt",
            "result": item.get("result"),
            "hint_policy": strategy["hint_policy"],
            "mastery_observed": False,
        })
    trace.append({"action": "delayed_review_plan", "policy": strategy["review_policy"], "status": "planned_not_observed"})
    return trace


def run_ten_person_simulation(output_path: str | Path | None = None) -> dict[str, Any]:
    """Run reproducible proxy simulations against current gates.

    These are five zero-base workflow preflights, not claims that five humans
    were physically observed. A row passes only if
    the same release gates needed for every-question mastery are green.
    """
    root = Path(__file__).resolve().parents[1]
    manifest = load_manifest(root / "chapter1_manifest.json")
    plan = load_json(root / "data" / "chapter1_learning_plan.json")
    browser = load_json(root / "data" / "browser_evidence.json") if (root / "data" / "browser_evidence.json").exists() else {}
    ocr = ocr_config_status()
    vision = test_vision_config()
    real_user_e2e = _real_user_observation_contract(root)
    section_snapshots = {section["id"]: _section_snapshot(section, plan) for section in manifest["sections"]}
    rows: list[dict[str, Any]] = []
    for kind, personas in (("zero_base_student_agent", ZERO_BASE_PERSONAS),):
        for persona_id, scope, description in personas:
            relevant = list(section_snapshots.values()) if scope == "全章" else [section_snapshots[scope]]
            gates = [f"{snapshot['section']}:{gap}" for snapshot in relevant for gap in _release_gaps(snapshot, browser, ocr, vision)]
            unique_gates = list(dict.fromkeys(gates))
            passed = not unique_gates
            question_results = [item for snapshot in relevant for item in snapshot.get("question_results", [])]
            knowledge_point_results = [item for snapshot in relevant for item in snapshot.get("knowledge_point_results", [])]
            question_result_summary = {
                "total": len(question_results),
                "blocked": sum(item.get("result") == "BLOCKED" for item in question_results),
                "ready_for_attempt_not_mastery": sum(item.get("result") == "READY_FOR_ATTEMPT_NOT_MASTERY" for item in question_results),
                "not_assessed": sum(item.get("result") == "NOT_ASSESSED" for item in question_results),
            }
            knowledge_point_result_summary = {
                "total": len(knowledge_point_results),
                "blocked": sum(item.get("result") == "BLOCKED" for item in knowledge_point_results),
                "ready_for_attempt_not_mastery": sum(item.get("result") == "READY_FOR_ATTEMPT_NOT_MASTERY" for item in knowledge_point_results),
                "not_assessed": sum(item.get("result") == "NOT_ASSESSED" for item in knowledge_point_results),
            }
            strategy = PROXY_STRATEGIES[persona_id]
            trace = [_synthetic_trace(snapshot, strategy) for snapshot in relevant]
            flat_trace = [event for section_trace in trace for event in section_trace]
            attempted = sum(event.get("decision") == "independent_attempt_allowed" for event in flat_trace)
            blocked_before_attempt = sum(event.get("decision") == "blocked_before_attempt" for event in flat_trace)
            observed_mastery = False
            can_release = passed and observed_mastery
            artifact_paths = [
                *(snapshot["packet"]["path"] for snapshot in relevant),
                *(snapshot["deepseek_context"]["path"] for snapshot in relevant),
                str(root / "data" / "question_coverage.json"),
                str(root / "data" / "bridge_micro_lessons.json"),
                str(root / "data" / "real_user_observations.json"),
            ]
            artifact_hashes = {path: _sha256(Path(path)) for path in artifact_paths}
            rows.append({
                "id": persona_id,
                "kind": kind,
                "scope": scope,
                "description": description,
                "strategy": strategy,
                "status": "PASS" if can_release else ("PARTIAL" if attempted else "FAIL"),
                "release_gates_passed": passed,
                "mastery_observed": observed_mastery,
                "can_complete_every_question": can_release,
                "can_master_all_knowledge_points": can_release,
                "gate_failures": unique_gates,
                "question_results": question_results,
                "knowledge_point_results": knowledge_point_results,
                "question_result_summary": question_result_summary,
                "knowledge_point_result_summary": knowledge_point_result_summary,
                "attempted_count": attempted,
                "blocked_before_attempt_count": blocked_before_attempt,
                "mastered_count": 0,
                "synthetic_trace": flat_trace,
                "observation_level": "synthetic_trace_only",
                "human_observed_evidence": [],
                "artifact_hashes": artifact_hashes,
                "evidence_mode": "current_artifact_gate_simulation_with_distinct_proxy_strategy",
            })
    result = {
        "schema_version": "7.2",
        "created_at": now_iso(),
        "type": "5_zero_base_student_agent_preflights",
        "model_contract": {"agent_type": "deepseek_worker", "model": "opencode-go/deepseek-v4-flash", "reasoning_effort": "max", "context_window": 1000000},
        "honesty_boundary": "五个代理模拟零基础学生阅读流程，不是假装真人观看视频或完成延迟复测。PASS 必须同时有当前门禁和代理独立作答证据；静态预检最多只能 PARTIAL。",
        "artifact_gates": {"sections": section_snapshots, "browser": browser, "ocr": ocr, "vision": vision, "bridge_curriculum": _bridge_curriculum(root), "real_user_e2e": real_user_e2e},
        "real_user_e2e": real_user_e2e,
        "rows": rows,
        "summary": {"total": len(rows), "pass": sum(row["status"] == "PASS" for row in rows), "fail": sum(row["status"] == "FAIL" for row in rows), "partial": sum(row["status"] == "PARTIAL" for row in rows)},
        "verdict": "PASS" if all(row["status"] == "PASS" for row in rows) else "NOT_READY_FOR_ZERO_BASE_MASTERY_CLAIM",
    }
    if output_path:
        save_json(output_path, result)
    return result
