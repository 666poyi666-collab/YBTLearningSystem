#!/usr/bin/env python3
"""Fail-closed validator for parallel 一本通 Luna section deliveries."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA = "ybt-luna-section-delivery-v2"
MODEL = "combo/protect-luna"
EFFORT = "max"
PERSONAS = {
    "literal-zero-base",
    "recognition-weak",
    "algebra-weak",
    "visual-weak",
    "self-check-weak",
}
ITEM_FIELDS = {
    "item_key",
    "ordinal",
    "kind",
    "label",
    "cycle_sequence",
    "position",
    "course_refs",
    "knowledge_refs",
    "type_refs",
    "recognition_cues",
    "method_model",
    "first_written_line_template",
    "continuation_actions",
    "likely_blockers",
    "minimal_correction_prompts",
    "independent_self_checks",
    "visual_dependency",
    "route_version",
}
FORBIDDEN_KEYS = {
    "question_text",
    "teaching_text",
    "solution",
    "solution_text",
    "answer",
    "answer_text",
    "correct_option",
    "final_answer",
}
ANSWER_LEAK_RE = re.compile(
    r"(?:答案\s*[：:]|正确选项|应选\s*[A-F]|故选\s*[A-F]|最终答案|"
    r"answer_text|correct_option|final_answer|solution_text)",
    re.I,
)
ATTEMPT_FIELDS = {
    "item_key",
    "course_call",
    "recognition_statement",
    "first_line_attempt",
    "continuation_attempt",
    "self_check_attempt",
    "recognized_method",
    "first_line_written",
    "continuation_complete",
    "self_check_complete",
    "first_blocker",
    "correction_used",
    "verdict",
}
PASS_VERDICTS = {"passed", "passed_after_self_correction"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_project_file(project_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if not path.is_absolute():
        path = project_root / path
    path = path.resolve()
    try:
        path.relative_to(project_root)
    except ValueError:
        return None
    return path


def section_folder(section: str) -> str:
    return section.replace("+", "_")


def canonical_items(project_root: Path, section: str) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    packet_path = project_root / "data" / "packets" / section_folder(section) / "learning_packet.json"
    packet = load_json(packet_path)
    if packet.get("section") != section:
        raise ValueError(f"section mismatch in {packet_path}")
    canonical: dict[str, dict[str, Any]] = {}
    for item in packet.get("worked_examples", []):
        canonical[f"LI:{item['item_id']}"] = item
    for item in packet.get("direct_variants", []):
        key = f"LI:{item['item_id']}"
        if key in canonical:
            raise ValueError(f"duplicate canonical item in {section}: {key}")
        canonical[key] = item
    for item in packet.get("exercise_questions", []):
        key = f"Q:{item['qid']}"
        if key in canonical:
            raise ValueError(f"duplicate canonical item in {section}: {key}")
        canonical[key] = item
    hashes = {
        "learning_packet_sha256": sha256_file(packet_path),
        "packet_sha256": sha256_file(packet_path.parent / "packet.json"),
    }
    return canonical, hashes


def _walk_forbidden_keys(value: Any, path: str = "delivery") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                errors.append(f"forbidden key at {path}.{key}")
            errors.extend(_walk_forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk_forbidden_keys(child, f"{path}[{index}]"))
    return errors


def validate_assignment(project_root: Path, assignment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tasks = assignment.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return ["assignment has no tasks"]
    task_ids = [str(task.get("task_id") or "") for task in tasks]
    if len(task_ids) != len(set(task_ids)) or any(not task_id for task_id in task_ids):
        errors.append("assignment task IDs are empty or duplicated")
    seen_sections: Counter[str] = Counter()
    delivered_total = 0
    for task in tasks:
        sections = task.get("sections") or []
        expected = 0
        for section in sections:
            seen_sections[str(section)] += 1
            try:
                canonical, _ = canonical_items(project_root, str(section))
            except Exception as exc:
                errors.append(f"{task.get('task_id')} cannot load {section}: {exc}")
                continue
            expected += len(canonical)
        if int(task.get("expected_items", -1)) != expected:
            errors.append(
                f"{task.get('task_id')} expected_items={task.get('expected_items')} but canonical={expected}"
            )
        delivered_total += expected
    duplicates = sorted(section for section, count in seen_sections.items() if count != 1)
    if duplicates:
        errors.append(f"sections missing or duplicated inside assignment: {duplicates}")
    report_path = project_root / "reports" / "all_chapters" / "packet-build-current.json"
    report = load_json(report_path)
    all_sections = {str(row["section"]) for row in report.get("sections", [])}
    target_rows = assignment.get("target_sections")
    if target_rows is None:
        expected_sections = all_sections
    elif not isinstance(target_rows, list) or not target_rows:
        errors.append("assignment target_sections must be a non-empty list")
        expected_sections = set()
    else:
        expected_sections = {str(value) for value in target_rows}
        unknown_targets = sorted(expected_sections - all_sections)
        if unknown_targets:
            errors.append(f"assignment target_sections are unknown: {unknown_targets}")
    assigned_sections = set(seen_sections)
    if assigned_sections != expected_sections:
        errors.append(
            f"assignment section set mismatch missing={sorted(expected_sections-assigned_sections)} "
            f"unexpected={sorted(assigned_sections-expected_sections)}"
        )
    expected_total = 0
    for section in expected_sections:
        try:
            canonical, _ = canonical_items(project_root, section)
            expected_total += len(canonical)
        except Exception as exc:
            errors.append(f"cannot total target section {section}: {exc}")
    if delivered_total != expected_total:
        errors.append(f"assignment item total={delivered_total} but report={expected_total}")
    return errors


def _require_nonempty_list(item: dict[str, Any], key: str, errors: list[str], prefix: str) -> None:
    value = item.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix}.{key} must be a non-empty list")


def validate_item(
    item: dict[str, Any],
    source: dict[str, Any],
    course_keys: set[str],
    prefix: str,
) -> list[str]:
    errors: list[str] = []
    missing = sorted(ITEM_FIELDS - set(item))
    if missing:
        errors.append(f"{prefix} missing fields {missing}")
    if item.get("kind") not in {"worked_example", "direct_variant", "abc_exercise"}:
        errors.append(f"{prefix}.kind is invalid")
    _require_nonempty_list(item, "course_refs", errors, prefix)
    _require_nonempty_list(item, "recognition_cues", errors, prefix)
    _require_nonempty_list(item, "continuation_actions", errors, prefix)
    _require_nonempty_list(item, "likely_blockers", errors, prefix)
    _require_nonempty_list(item, "minimal_correction_prompts", errors, prefix)
    _require_nonempty_list(item, "independent_self_checks", errors, prefix)
    unknown_courses = sorted(set(item.get("course_refs") or []) - course_keys)
    if unknown_courses:
        errors.append(f"{prefix} references unknown courses {unknown_courses}")
    if not str(item.get("method_model") or "").strip():
        errors.append(f"{prefix}.method_model is empty")
    if not str(item.get("first_written_line_template") or "").strip():
        errors.append(f"{prefix}.first_written_line_template is empty")
    visual = item.get("visual_dependency")
    if not isinstance(visual, dict):
        errors.append(f"{prefix}.visual_dependency is missing")
    else:
        expected_visual = source.get("visual_status")
        if visual.get("status") != expected_visual:
            errors.append(
                f"{prefix}.visual status={visual.get('status')} but packet={expected_visual}"
            )
    serialized = json.dumps(item, ensure_ascii=False)
    if ANSWER_LEAK_RE.search(serialized):
        errors.append(f"{prefix} contains answer/solution leakage")
    errors.extend(_walk_forbidden_keys(item, prefix))
    return errors


def validate_ocr_vision(
    project_root: Path,
    section_id: str,
    section: dict[str, Any],
    delivered_items: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    summary = section.get("ocr_vision")
    if not isinstance(summary, dict):
        return [f"{section_id} ocr_vision evidence is missing"]
    mode = summary.get("mode")
    if mode not in {"luna_paddle_crosscheck", "paddle_glm_crosscheck"}:
        errors.append(f"{section_id} ocr_vision mode is invalid")
    if summary.get("paddle_status") != "passed":
        errors.append(f"{section_id} PaddleOCR is not passed")
    if summary.get("visual_status") != "passed":
        errors.append(f"{section_id} visual provider is not passed")
    if mode == "luna_paddle_crosscheck":
        if summary.get("luna_status") != "passed" or summary.get("visual_model") != MODEL:
            errors.append(f"{section_id} Luna vision is not passed")
    elif mode == "paddle_glm_crosscheck":
        if summary.get("luna_status") != "blocked":
            errors.append(f"{section_id} fallback must preserve Luna blocked status")
        if summary.get("visual_model") != "glm-4.6v-flash":
            errors.append(f"{section_id} fallback visual model is invalid")
        if not _nonempty_text(summary.get("luna_blocker")):
            errors.append(f"{section_id} fallback Luna blocker is missing")
    if summary.get("conflict_item_keys") != []:
        errors.append(f"{section_id} has unresolved OCR/vision conflicts")
    if summary.get("status") != "passed":
        errors.append(f"{section_id} ocr_vision status is not passed")
    evidence_path = resolve_project_file(project_root, summary.get("evidence_path"))
    if evidence_path is None or not evidence_path.is_file():
        return errors + [f"{section_id} ocr_vision evidence file is missing or outside project"]
    expected_sha = str(summary.get("evidence_sha256") or "").lower()
    actual_sha = sha256_file(evidence_path)
    if expected_sha != actual_sha:
        errors.append(f"{section_id} ocr_vision evidence hash is stale")
    try:
        evidence = load_json(evidence_path)
    except Exception as exc:
        return errors + [f"{section_id} cannot load ocr_vision evidence: {exc}"]
    if evidence.get("schema_version") != "ybt-ocr-vision-crosscheck-v1":
        errors.append(f"{section_id} ocr_vision evidence schema mismatch")
    records = evidence.get("records")
    if not isinstance(records, list):
        return errors + [f"{section_id} ocr_vision records are missing"]
    required_hashes: set[str] = set()
    for item in delivered_items:
        visual = item.get("visual_dependency") or {}
        required_hashes.update(str(value).lower() for value in visual.get("image_sha256", []))
    section_records = [
        row for row in records if isinstance(row, dict) and str(row.get("section")) == section_id
    ]
    by_hash: Counter[str] = Counter(str(row.get("image_sha256") or "").lower() for row in section_records)
    missing = sorted(required_hashes - set(by_hash))
    duplicated = sorted(value for value, count in by_hash.items() if value in required_hashes and count != 1)
    if missing:
        errors.append(f"{section_id} Luna/Paddle evidence misses images: {missing}")
    if duplicated:
        errors.append(f"{section_id} Luna/Paddle evidence duplicates images: {duplicated}")
    for index, row in enumerate(section_records):
        image_sha = str(row.get("image_sha256") or "").lower()
        if image_sha not in required_hashes:
            continue
        prefix = f"{section_id} ocr_vision.records[{index}]"
        luna = row.get("luna")
        fallback_visual = row.get("visual")
        paddle = row.get("paddle")
        visual = luna if mode == "luna_paddle_crosscheck" else fallback_visual
        if not isinstance(visual, dict) or visual.get("status") != "passed":
            errors.append(f"{prefix} visual observation is not passed")
        else:
            if mode == "luna_paddle_crosscheck" and (
                visual.get("model") != MODEL or visual.get("reasoning_effort") != EFFORT
            ):
                errors.append(f"{prefix} Luna model contract mismatch")
            if mode == "paddle_glm_crosscheck" and visual.get("model") != "glm-4.6v-flash":
                errors.append(f"{prefix} fallback visual model mismatch")
            meaningful = sum(
                len(visual.get(key) or []) for key in ("objects", "relations", "coordinates", "ranges", "text")
            )
            if meaningful == 0:
                errors.append(f"{prefix} visual observation is empty")
            if not isinstance(visual.get("uncertainties"), list):
                errors.append(f"{prefix} visual uncertainties are invalid")
        if mode == "paddle_glm_crosscheck":
            if not isinstance(luna, dict) or luna.get("status") != "blocked":
                errors.append(f"{prefix} fallback does not preserve Luna blocked status")
        if not isinstance(paddle, dict) or paddle.get("status") != "passed":
            errors.append(f"{prefix} Paddle observation is not passed")
        else:
            if not _nonempty_text(paddle.get("artifact_sha256")):
                errors.append(f"{prefix} Paddle artifact hash is missing")
        if row.get("conflicts") != []:
            errors.append(f"{prefix} has unresolved conflicts")
        if row.get("status") != "passed":
            errors.append(f"{prefix} status is not passed")
    return errors


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _attempt_signature(result: dict[str, Any]) -> str:
    return json.dumps(
        [
            result.get("course_call"),
            result.get("recognition_statement"),
            result.get("first_line_attempt"),
            result.get("continuation_attempt"),
            result.get("self_check_attempt"),
            result.get("first_blocker"),
            result.get("correction_used"),
        ],
        ensure_ascii=False,
        sort_keys=True,
    )


def validate_simulation(section: dict[str, Any], items_by_key: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    section_id = section.get("section")
    item_keys = set(items_by_key)
    simulation = section.get("simulation")
    if not isinstance(simulation, dict):
        return [f"{section_id} simulation missing"]
    if simulation.get("protocol") != "five-round-five-persona-v2":
        errors.append(f"{section_id} simulation protocol is not v2")
    rounds = simulation.get("rounds")
    if not isinstance(rounds, list) or len(rounds) != 5:
        return errors + [f"{section_id} simulation must have five rounds"]
    if sorted(row.get("round") for row in rounds) != [1, 2, 3, 4, 5]:
        errors.append(f"{section_id} round numbers are invalid")
    route_versions = {
        int(row.get("version")): str(row.get("route_hash") or "")
        for row in section.get("route_versions", [])
        if isinstance(row, dict) and isinstance(row.get("version"), int)
    }
    attempt_counts: Counter[str] = Counter()
    for round_row in rounds:
        round_number = round_row.get("round")
        route_version = round_row.get("route_version")
        route_hash = str(round_row.get("route_hash") or "")
        if route_versions.get(route_version) != route_hash:
            errors.append(f"{section_id} round {round_number} route binding is invalid")
        personas = round_row.get("personas")
        if not isinstance(personas, list) or len(personas) != 5:
            errors.append(f"{section_id} round {round_number} must have five personas")
            continue
        profiles = {persona.get("profile") for persona in personas if isinstance(persona, dict)}
        if profiles != PERSONAS:
            errors.append(f"{section_id} round {round_number} persona profiles mismatch")
        persona_ids = [persona.get("persona_id") for persona in personas if isinstance(persona, dict)]
        if len(persona_ids) != len(set(persona_ids)):
            errors.append(f"{section_id} round {round_number} persona IDs duplicated")
        failed_keys: set[str] = set()
        per_item_signatures: dict[str, set[str]] = {key: set() for key in item_keys}
        for persona in personas:
            results = persona.get("item_results") if isinstance(persona, dict) else None
            if not isinstance(results, list):
                errors.append(f"{section_id} round {round_number} persona results missing")
                continue
            keys = [str(result.get("item_key") or "") for result in results if isinstance(result, dict)]
            if len(keys) != len(set(keys)) or set(keys) != item_keys:
                errors.append(
                    f"{section_id} round {round_number} persona item coverage mismatch"
                )
            signature_counts: Counter[str] = Counter()
            for result in results:
                if not isinstance(result, dict):
                    errors.append(f"{section_id} round {round_number} result is not an object")
                    continue
                key = str(result.get("item_key") or "")
                attempt_counts[key] += 1
                missing = sorted(ATTEMPT_FIELDS - set(result))
                if missing:
                    errors.append(f"{section_id} round {round_number} {key} missing attempt fields {missing}")
                course_call = result.get("course_call")
                if not isinstance(course_call, list) or not course_call:
                    errors.append(f"{section_id} round {round_number} {key}.course_call is empty")
                else:
                    allowed_calls = set(items_by_key.get(key, {}).get("course_refs") or [])
                    if not set(str(value) for value in course_call).issubset(allowed_calls):
                        errors.append(f"{section_id} round {round_number} {key}.course_call is not route-bound")
                for field in ("recognition_statement", "first_line_attempt", "self_check_attempt"):
                    if not _nonempty_text(result.get(field)):
                        errors.append(f"{section_id} round {round_number} {key}.{field} is empty")
                continuation = result.get("continuation_attempt")
                if not isinstance(continuation, list) or not continuation or not all(
                    _nonempty_text(value) for value in continuation
                ):
                    errors.append(f"{section_id} round {round_number} {key}.continuation_attempt is empty")
                for field in (
                    "recognized_method",
                    "first_line_written",
                    "continuation_complete",
                    "self_check_complete",
                ):
                    if not isinstance(result.get(field), bool):
                        errors.append(
                            f"{section_id} round {round_number} {key}.{field} must be boolean"
                        )
                all_true = all(
                    result.get(field) is True
                    for field in (
                        "recognized_method",
                        "first_line_written",
                        "continuation_complete",
                        "self_check_complete",
                    )
                )
                verdict = result.get("verdict")
                blocker = result.get("first_blocker")
                correction = result.get("correction_used")
                if verdict == "passed":
                    if not all_true or blocker is not None or correction is not None:
                        errors.append(f"{section_id} round {round_number} {key} passed verdict is inconsistent")
                elif verdict == "passed_after_self_correction":
                    if not all_true or not _nonempty_text(blocker) or not _nonempty_text(correction):
                        errors.append(f"{section_id} round {round_number} {key} correction verdict is inconsistent")
                elif verdict in {"blocked", "failed"}:
                    if all_true or not _nonempty_text(blocker):
                        errors.append(f"{section_id} round {round_number} {key} failed verdict is inconsistent")
                else:
                    errors.append(f"{section_id} round {round_number} {key} verdict is invalid")
                if not all_true or verdict not in PASS_VERDICTS:
                    failed_keys.add(key)
                serialized = json.dumps(result, ensure_ascii=False)
                if ANSWER_LEAK_RE.search(serialized):
                    errors.append(f"{section_id} round {round_number} {key} contains answer leakage")
                signature = _attempt_signature(result)
                signature_counts[signature] += 1
                if key in per_item_signatures:
                    per_item_signatures[key].add(signature)
            if signature_counts and len(item_keys) >= 6:
                generic_limit = max(4, math.ceil(len(item_keys) * 0.65))
                if max(signature_counts.values()) >= generic_limit:
                    errors.append(
                        f"{section_id} round {round_number} {persona.get('persona_id')} attempts are excessively generic"
                    )
        if len(item_keys) >= 2:
            copied_across_personas = sorted(
                key for key, signatures in per_item_signatures.items() if len(signatures) < 2
            )
            if len(copied_across_personas) >= math.ceil(len(item_keys) * 0.65):
                errors.append(f"{section_id} round {round_number} persona attempts are copied in bulk")
        declared_failed = {str(value) for value in round_row.get("failed_item_keys", [])}
        if declared_failed != failed_keys:
            errors.append(
                f"{section_id} round {round_number} failed_item_keys mismatch "
                f"missing={sorted(failed_keys-declared_failed)} unexpected={sorted(declared_failed-failed_keys)}"
            )
        repairs = round_row.get("route_repairs")
        if not isinstance(repairs, list):
            errors.append(f"{section_id} round {round_number} route_repairs must be a list")
            repairs = []
        repaired_keys: set[str] = set()
        for index, repair in enumerate(repairs):
            if not isinstance(repair, dict):
                errors.append(f"{section_id} round {round_number} repair {index} is not an object")
                continue
            keys = {str(value) for value in repair.get("item_keys", [])}
            if not keys or not keys.issubset(failed_keys):
                errors.append(f"{section_id} round {round_number} repair {index} item_keys are invalid")
            repaired_keys.update(keys)
            for field in ("field", "before", "after", "reason"):
                if not _nonempty_text(repair.get(field)):
                    errors.append(f"{section_id} round {round_number} repair {index}.{field} is empty")
        if failed_keys and repaired_keys != failed_keys:
            errors.append(f"{section_id} round {round_number} repairs do not cover failed items")
        if not failed_keys and repairs:
            errors.append(f"{section_id} round {round_number} has repairs without failed items")
        if round_number == 5 and round_row.get("route_hash") != section.get("final_route_hash"):
            errors.append(f"{section_id} round 5 route hash is stale")
        if round_number == 5 and failed_keys:
            errors.append(f"{section_id} round 5 still has failed items")
    wrong_counts = sorted(key for key in item_keys if attempt_counts[key] != 25)
    if wrong_counts:
        errors.append(f"{section_id} items do not have 25 attempts: {wrong_counts}")
    declared_counts = simulation.get("actual_attempts_per_item")
    if not isinstance(declared_counts, dict) or any(
        int(declared_counts.get(key, -1)) != 25 for key in item_keys
    ):
        errors.append(f"{section_id} actual_attempts_per_item is invalid")
    if simulation.get("unresolved_item_keys") != []:
        errors.append(f"{section_id} unresolved_item_keys is not empty")
    if simulation.get("status") != "passed":
        errors.append(f"{section_id} simulation status is not passed")
    return errors


def validate_delivery(
    project_root: Path,
    assignment: dict[str, Any],
    task_id: str,
    delivery: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    task = next((row for row in assignment.get("tasks", []) if row.get("task_id") == task_id), None)
    if task is None:
        return [f"unknown task_id: {task_id}"]
    if assignment.get("status") != "ready":
        errors.append("assignment is not ready")
    if delivery.get("schema_version") != SCHEMA:
        errors.append("delivery schema mismatch")
    if delivery.get("task_id") != task_id:
        errors.append("delivery task_id mismatch")
    model = delivery.get("model_contract") or {}
    if model.get("model") != MODEL or model.get("reasoning_effort") != EFFORT:
        errors.append("delivery model contract is not combo/protect-luna + max")
    expected_top_binding = assignment.get("source_binding") or {}
    actual_top_binding = delivery.get("source_binding") or {}
    for key, expected in expected_top_binding.items():
        if actual_top_binding.get(key) != expected:
            errors.append(f"delivery source binding is stale: {key}")
    assigned = [str(value) for value in task.get("sections", [])]
    if [str(value) for value in delivery.get("assigned_sections", [])] != assigned:
        errors.append("assigned section order mismatch")
    catalog_path = project_root / "data" / "all_chapters_course_catalog.json"
    catalog = load_json(catalog_path)
    course_keys = {str(row.get("course_key")) for row in catalog.get("courses", [])}
    sections = delivery.get("sections")
    if not isinstance(sections, list):
        return errors + ["delivery sections missing"]
    by_section = {str(row.get("section")): row for row in sections if isinstance(row, dict)}
    if set(by_section) != set(assigned) or len(by_section) != len(sections):
        errors.append("delivery section set missing, duplicated, or unexpected")
    all_delivered_keys: list[str] = []
    for section_id in assigned:
        section = by_section.get(section_id)
        if section is None:
            continue
        canonical, expected_hashes = canonical_items(project_root, section_id)
        source_binding = section.get("source_binding") or {}
        for key, expected in expected_hashes.items():
            if source_binding.get(key) != expected:
                errors.append(f"{section_id} {key} is stale")
        items = section.get("items")
        if not isinstance(items, list):
            errors.append(f"{section_id} items missing")
            continue
        keys = [str(item.get("item_key") or "") for item in items if isinstance(item, dict)]
        if len(keys) != len(set(keys)):
            errors.append(f"{section_id} duplicate delivery item keys")
        if set(keys) != set(canonical):
            errors.append(
                f"{section_id} item mismatch missing={sorted(set(canonical)-set(keys))} "
                f"unexpected={sorted(set(keys)-set(canonical))}"
            )
        all_delivered_keys.extend(keys)
        signatures: Counter[str] = Counter()
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{section_id} item {index} is not an object")
                continue
            key = str(item.get("item_key") or "")
            source = canonical.get(key)
            if source is None:
                continue
            errors.extend(validate_item(item, source, course_keys, f"{section_id}.items[{index}]"))
            signatures[
                json.dumps(
                    [
                        item.get("recognition_cues"),
                        item.get("method_model"),
                        item.get("first_written_line_template"),
                        item.get("likely_blockers"),
                        item.get("independent_self_checks"),
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                )
            ] += 1
        if len(items) >= 6 and signatures:
            generic_limit = max(5, math.ceil(len(items) * 0.75))
            if max(signatures.values()) >= generic_limit:
                errors.append(f"{section_id} method records are excessively generic")
        errors.extend(validate_ocr_vision(project_root, section_id, section, items))
        delivered_by_key = {
            str(item.get("item_key") or ""): item for item in items if isinstance(item, dict)
        }
        errors.extend(validate_simulation(section, delivered_by_key))
        coverage = section.get("coverage") or {}
        if coverage.get("expected_items") != len(canonical) or coverage.get("delivered_items") != len(canonical):
            errors.append(f"{section_id} coverage counts mismatch")
        if section.get("status") != "passed":
            errors.append(f"{section_id} status is not passed")
    if len(all_delivered_keys) != int(task.get("expected_items", -1)):
        errors.append("task delivered item count mismatch")
    coverage = delivery.get("coverage") or {}
    if coverage.get("expected_items") != int(task.get("expected_items", -1)):
        errors.append("top-level expected_items mismatch")
    if coverage.get("delivered_items") != int(task.get("expected_items", -1)):
        errors.append("top-level delivered_items mismatch")
    for key in ("duplicate_items", "missing_items", "unexpected_items"):
        if coverage.get(key) != []:
            errors.append(f"top-level {key} must be empty")
    if delivery.get("proxy_simulation") != "passed":
        errors.append("proxy_simulation is not passed")
    for key in ("independent_acceptance", "human_acceptance", "cold_24h_retest"):
        if delivery.get(key) != "not_run":
            errors.append(f"{key} must remain not_run in a section-owner delivery")
    if delivery.get("status") != "passed":
        errors.append("delivery status is not passed")
    errors.extend(_walk_forbidden_keys(delivery))
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--assignment", required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--delivery")
    parser.add_argument("--assignment-only", action="store_true")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    assignment_path = Path(args.assignment)
    if not assignment_path.is_absolute():
        assignment_path = project_root / assignment_path
    assignment = load_json(assignment_path)
    errors = validate_assignment(project_root, assignment)
    if not args.assignment_only:
        if not args.task_id or not args.delivery:
            parser.error("--task-id and --delivery are required unless --assignment-only is used")
        delivery_path = Path(args.delivery)
        if not delivery_path.is_absolute():
            delivery_path = project_root / delivery_path
        delivery = load_json(delivery_path)
        errors.extend(validate_delivery(project_root, assignment, args.task_id, delivery))
    report = {
        "status": "passed" if not errors else "failed",
        "assignment": str(assignment_path),
        "task_id": args.task_id,
        "errors": sorted(set(errors)),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
