from __future__ import annotations

"""Build a non-spoiler, question-level coverage ledger.

The ledger answers a narrower question than mastery: after the listed lesson,
bridge unit, and visual evidence are available, is a question ready to enter
the student's independent-attempt flow?  It never contains answer text.
"""

from collections import Counter
from typing import Any

from .common import now_iso, save_json


def _q(group: str, number: int) -> str:
    return f"{group}{number}"


# This is the structured form of the worker-02 difficulty matrix.  Keeping the
# mapping explicit prevents a keyword scan from silently classifying a remote
# transfer question as a direct course exercise.
QUESTION_RULES: dict[str, dict[str, dict[str, Any]]] = {
    "1.1": {
        **{_q("A", n): {"unlock_class": "COURSE_DIRECT", "course_keys": ["space_vector_ops"]} for n in (1, 2, 3)},
        "B4": {"unlock_class": "COURSE_DIRECT", "course_keys": ["line_line_angle"]},
        "B5": {"unlock_class": "COURSE_DIRECT", "course_keys": ["line_line_angle"]},
        "B6": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["parallel_perpendicular", "line_line_angle", "plane_plane_angle"], "bridge_units": ["bridge-1.1-dihedral-definition"]},
        "B7": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["parallel_perpendicular", "line_line_angle", "plane_plane_angle"], "bridge_units": ["bridge-1.1-dihedral-definition"]},
        "B8": {"unlock_class": "MICRO_UNIT", "course_keys": ["line_line_angle"], "bridge_units": ["bridge-1.1-polarization"]},
        "B9": {"unlock_class": "COURSE_DIRECT", "course_keys": ["decomposition", "coplanar"]},
        "B10": {"unlock_class": "COURSE_DIRECT", "course_keys": ["decomposition"]},
        "B11": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["decomposition", "line_line_angle"], "bridge_units": ["bridge-1.1-centroid"]},
        "B12": {"unlock_class": "COURSE_DIRECT", "course_keys": ["decomposition", "line_line_angle"]},
        "C13": {"unlock_class": "MICRO_UNIT", "course_keys": ["decomposition", "coplanar"], "bridge_units": ["micro-four-point-coplanar"]},
        "C14": {"unlock_class": "MICRO_UNIT", "course_keys": ["decomposition", "parallel_perpendicular", "coplanar", "plane_equation_upper", "plane_equation_lower", "distance"], "bridge_units": ["micro-four-point-coplanar", "bridge-1.1-affine-intersection-ratio", "bridge-1.1-centroid", "bridge-1.1-positive-product-sum", "bridge-micro-sphere"]},
    },
    "1.2+1.3": {
        **{_q("A", n): {"unlock_class": "COURSE_DIRECT", "course_keys": ["coordinate_system", "coordinate_ops"]} for n in range(1, 5)},
        "B5": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["decomposition"]},
        "B6": {"unlock_class": "COURSE_DIRECT", "course_keys": ["coordinate_ops"]},
        "B7": {"unlock_class": "COURSE_DIRECT", "course_keys": ["coordinate_ops"]},
        "B8": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["coordinate_ops"]},
        "B9": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["decomposition"]},
        "B10": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["coordinate_ops"]},
        "B11": {"unlock_class": "COURSE_DIRECT", "course_keys": ["coordinate_system", "coordinate_ops"]},
        "B12": {"unlock_class": "COURSE_DIRECT", "course_keys": ["coordinate_ops"]},
        "B13": {"unlock_class": "COURSE_DIRECT", "course_keys": ["coordinate_system", "coordinate_ops"]},
        "C14": {"unlock_class": "MICRO_UNIT", "course_keys": ["decomposition", "coordinate_ops"], "bridge_units": ["micro-four-point-coplanar"]},
        "C15": {"unlock_class": "MICRO_UNIT", "course_keys": ["coordinate_ops"], "bridge_units": ["bridge-1.2-single-variable"]},
        "C16": {"unlock_class": "MICRO_UNIT", "course_keys": ["coordinate_ops"], "bridge_units": ["bridge-1.1-polarization", "bridge-1.2-single-variable", "bridge-1.2-apollonius"]},
    },
    "1.4": {
        "A1": {"unlock_class": "COURSE_DIRECT", "course_keys": ["direction_normal", "line_line_angle"]},
        "A2": {"unlock_class": "COURSE_DIRECT", "course_keys": ["coordinate_ops", "direction_normal"]},
        "B3": {"unlock_class": "COURSE_DIRECT", "course_keys": ["coordinate_ops", "line_line_angle"]},
        "B4": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["direction_normal", "plane_plane_angle"]},
        "B5": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["coordinate_ops"]},
        "B6": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["direction_normal", "distance"]},
        "B7": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["line_plane_angle"]},
        "B8": {"unlock_class": "MICRO_UNIT", "course_keys": ["distance", "plane_plane_angle"], "bridge_units": ["micro-skew-distance"]},
        "C9": {"unlock_class": "MICRO_UNIT", "course_keys": ["distance"], "bridge_units": ["bridge-1.4-folding", "micro-skew-distance"]},
        "C10": {"unlock_class": "MICRO_UNIT", "course_keys": ["plane_plane_angle", "distance"], "bridge_units": ["bridge-1.4-folding"]},
        "C11": {"unlock_class": "METHOD_BRIDGE_AND_MICRO", "course_keys": ["direction_normal", "plane_plane_angle"], "bridge_units": ["bridge-1.4-dihedral-trig", "bridge-micro-completion"]},
        "C12": {"unlock_class": "MICRO_UNIT", "course_keys": ["line_plane_angle", "distance"], "bridge_units": ["bridge-1.4-dihedral-trig", "bridge-micro-existence"]},
    },
    "micro专题1": {
        "B2": {"unlock_class": "MICRO_UNIT", "course_keys": ["moving_point", "plane_plane_angle"], "bridge_units": ["bridge-1.4-folding", "bridge-1.4-dihedral-trig"]},
        "B3": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["plane_equation_upper", "direction_normal"]},
        "B4": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["direction_normal", "plane_plane_angle"]},
        "B1": {"unlock_class": "METHOD_BRIDGE", "course_keys": ["moving_point"], "bridge_units": ["bridge-1.2-single-variable"]},
        "C5": {"unlock_class": "MICRO_UNIT", "course_keys": ["distance", "moving_point"], "bridge_units": ["bridge-1.2-apollonius", "micro-skew-distance", "bridge-micro-sphere"]},
        "C6": {"unlock_class": "MICRO_UNIT", "course_keys": ["moving_point", "distance"], "bridge_units": ["bridge-1.2-single-variable", "bridge-micro-existence"]},
        "C7": {"unlock_class": "MICRO_UNIT", "course_keys": ["moving_point", "plane_plane_angle"], "bridge_units": ["bridge-1.4-folding", "bridge-1.4-dihedral-trig", "bridge-micro-existence"]},
        "C8": {"unlock_class": "MICRO_UNIT", "course_keys": ["direction_normal", "plane_plane_angle"], "bridge_units": ["bridge-1.4-dihedral-trig", "bridge-micro-completion"]},
    },
}


BRIDGE_TITLES = {
    "micro-four-point-coplanar": "四点共面系数和=1",
    "micro-special-position": "特殊位置法",
    "micro-skew-distance": "异面直线距离",
    "micro-line-in-plane": "线在面内判定",
    "micro-existence-parameters": "存在性参数化",
}


BRIDGE_READY_STATUSES = {"VERIFIED", "SUPPLEMENT_READY"}


def _bridge_registry(manifest: dict[str, Any], bridge_catalog: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for section in manifest.get("sections", []):
        for bridge in section.get("bridge_units", []):
            registry[bridge["id"]] = {
                "id": bridge["id"],
                "title": bridge.get("title", bridge["id"]),
                "release_status": bridge.get("release_status", "UNKNOWN"),
                "source_status": bridge.get("source_status", "UNKNOWN"),
            }
    for bridge_id, title in BRIDGE_TITLES.items():
        registry.setdefault(bridge_id, {
            "id": bridge_id,
            "title": title,
            "release_status": "REQUIRED_SUPPLEMENT_NOT_VERIFIED",
            "source_status": "SYNTHESIZED_FROM_DIFFICULTY_MATRIX",
        })
    for rules in QUESTION_RULES.values():
        for rule in rules.values():
            for bridge_id in rule.get("bridge_units", []):
                registry.setdefault(bridge_id, {
                    "id": bridge_id,
                    "title": bridge_id,
                    "release_status": "REQUIRED_SUPPLEMENT_NOT_VERIFIED",
                    "source_status": "SYNTHESIZED_FROM_DIFFICULTY_MATRIX",
                })
    # The dedicated answer-free curriculum is authoritative for the current
    # lifecycle status.  The chapter manifest intentionally keeps its older,
    # conservative release_status values for audit history.
    for unit in (bridge_catalog or {}).get("units", []):
        bridge_id = unit.get("id")
        if not bridge_id:
            continue
        registry[bridge_id] = {
            "id": bridge_id,
            "title": unit.get("title", bridge_id),
            "release_status": unit.get("status", "UNKNOWN"),
            "source_status": unit.get("source_status", "UNKNOWN"),
            "curriculum_status": unit.get("status", "UNKNOWN"),
            "target_questions": unit.get("target_questions", []),
            "zero_base_status": unit.get("zero_base_status", "NOT_VERIFIED"),
            "zero_base_note": unit.get("zero_base_note"),
        }
    return registry


def build_question_coverage(
    manifest: dict[str, Any],
    catalog: dict[str, Any],
    packets: list[dict[str, Any]],
    *,
    bridge_catalog: dict[str, Any] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Create the authoritative, non-spoiler question coverage ledger."""
    transcripts = {
        item.get("course_key")
        for course in catalog.get("courses", [])
        for item in course.get("transcripts", [])
        if item.get("course_key")
    }
    packet_by_section = {packet.get("section"): packet for packet in packets}
    bridges = _bridge_registry(manifest, bridge_catalog)
    questions: list[dict[str, Any]] = []
    for section in manifest.get("sections", []):
        section_id = section["id"]
        rules = QUESTION_RULES.get(section_id, {})
        packet = packet_by_section.get(section_id, {})
        packet_questions = {
            _q(question.get("group", "?"), int(question.get("number", 0))): question
            for question in packet.get("questions", [])
        }
        expected: list[str] = []
        for group, bounds in section.get("question_groups", {}).items():
            expected.extend(_q(group, number) for number in range(bounds[0], bounds[1] + 1))
        for key in expected:
            rule = rules.get(key, {"unlock_class": "UNKNOWN", "course_keys": [], "bridge_units": []})
            packet_question = packet_questions.get(key, {})
            course_keys = list(dict.fromkeys(rule.get("course_keys", [])))
            missing_courses = [course_key for course_key in course_keys if course_key not in transcripts]
            bridge_ids = list(dict.fromkeys(rule.get("bridge_units", [])))
            bridge_records = [bridges[bridge_id] for bridge_id in bridge_ids]
            visual_status = packet_question.get("visual_status", "UNKNOWN")
            visual_ready = visual_status in {"READY_TEXT_ONLY", "VISION_VERIFIED"}
            bridge_statuses = {item.get("release_status") for item in bridge_records}
            zero_base_blocked = any(
                item.get("zero_base_status") == "NOT_CLOSED" for item in bridge_records
            )
            bridge_ready = (
                not bridge_records
                or (bridge_statuses.issubset(BRIDGE_READY_STATUSES) and not zero_base_blocked)
            )
            if not bridge_records:
                bridge_status = "NOT_REQUIRED"
            elif bridge_statuses == {"VERIFIED"}:
                bridge_status = "VERIFIED"
            elif zero_base_blocked:
                bridge_status = "NOT_CLOSED"
            elif bridge_ready and "SUPPLEMENT_READY" in bridge_statuses:
                # A supplemental answer-free method unit is a stronger
                # dependency than a source-method note; do not hide it under
                # SOURCE_METHOD_READY for mixed questions.
                bridge_status = "SUPPLEMENT_READY"
            elif bridge_ready:
                bridge_status = "SOURCE_METHOD_READY"
            else:
                bridge_status = "REQUIRED_NOT_VERIFIED"
            if not visual_ready:
                release_status = "BLOCKED_VISUAL"
            elif bridge_records and not bridge_ready:
                release_status = "BLOCKED_BRIDGE"
            elif rule.get("unlock_class") == "COURSE_DIRECT":
                release_status = "COURSE_READY_NOT_MASTERY"
            else:
                release_status = "READY_FOR_INDEPENDENT_ATTEMPT"
            questions.append({
                "question_key": key,
                "qid": packet_question.get("qid"),
                "section": section_id,
                "group": key[0],
                "number": int(key[1:]),
                "unlock_class": rule.get("unlock_class", "UNKNOWN"),
                "course_keys": course_keys,
                "course_transcript_status": "PRESENT" if not missing_courses else "MISSING_OR_UNVERIFIED",
                "missing_course_keys": missing_courses,
                "bridge_units": bridge_records,
                "bridge_status": bridge_status,
                "zero_base_status": "NOT_CLOSED" if zero_base_blocked else "NOT_APPLICABLE",
                "visual_status": visual_status,
                "visual_ready": visual_ready,
                "packet_status": packet.get("status", "MISSING"),
                "question_text_present": bool(str(packet_question.get("question_text", "")).strip()),
                "release_status": release_status,
                "mastery_status": "NOT_ASSESSED",
                "blockers": [
                    *(["visual_sidecar_required"] if not visual_ready else []),
                    *(["bridge_unit_not_verified"] if bridge_records and not bridge_ready else []),
                    *(["course_transcript_missing_or_unverified"] if missing_courses else []),
                ],
            })
    counts = Counter(item["release_status"] for item in questions)
    section_summary: list[dict[str, Any]] = []
    for section in manifest.get("sections", []):
        items = [item for item in questions if item["section"] == section["id"]]
        section_summary.append({
            "section": section["id"],
            "question_count": len(items),
            "release_status_counts": dict(Counter(item["release_status"] for item in items)),
            "visual_ready_count": sum(item["visual_ready"] for item in items),
            "bridge_blocked_count": sum("bridge_unit_not_verified" in item["blockers"] for item in items),
            "question_keys": [item["question_key"] for item in items],
        })
    result = {
        "schema_version": "7.1",
        "created_at": now_iso(),
        "artifact": "QUESTION_COVERAGE_LEDGER",
        "scope": "第一章四个批次；无答案、无解答、无 mastery 冒充",
        "question_count": len(questions),
        "questions": questions,
        "sections": section_summary,
        "summary": {
            "release_status_counts": dict(counts),
            "visual_ready_count": sum(item["visual_ready"] for item in questions),
            "bridge_ready_count": sum(
                item["bridge_status"] in {"NOT_REQUIRED", "VERIFIED", "SUPPLEMENT_READY"}
                and item.get("zero_base_status") != "NOT_CLOSED"
                for item in questions
            ),
            "attempt_ready_gate": all(item["release_status"] in {"COURSE_READY_NOT_MASTERY", "READY_FOR_INDEPENDENT_ATTEMPT"} for item in questions),
            "full_every_question_release_gate": all(item["release_status"] in {"COURSE_READY_NOT_MASTERY", "READY_FOR_INDEPENDENT_ATTEMPT"} for item in questions),
        },
        "rules": {
            "COURSE_READY_NOT_MASTERY": "课程/方法路径可进入独立尝试，不等于学生已经掌握。",
            "BLOCKED_VISUAL": "题面或图形尚未有可消费的视觉证据；不得猜图讲题。",
            "BLOCKED_BRIDGE": "现有课程不是完整覆盖，必须先完成指定桥接单元；SOURCE_METHOD_READY 只有来源方法骨架，不能放行独立作答。",
            "SUPPLEMENT_READY": "已具备无答案补充方法课，但仍必须做自造变式、视觉核验和独立作答；不等于视频课程已覆盖。",
            "NOT_CLOSED": "桥接文字存在但零基础放行门未闭合；必须完成对应检查点、无答案近迁移和定义域回代。",
            "mastery_status": "只有运行时独立作答、过程核验和延迟复测才能改变；本账本不写掌握结论。",
        },
    }
    if output_path:
        save_json(output_path, result)
    return result
