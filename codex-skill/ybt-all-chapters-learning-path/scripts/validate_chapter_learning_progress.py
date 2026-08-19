#!/usr/bin/env python3
"""Fail-closed validation for the persistent growing learner chapter ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from chapter_learning_progress import PROGRESS_SCHEMA, chapter_facts, load_json


COURSE_STATES = {"planned", "in_progress", "simulated_completed", "blocked"}
SECTION_STATES = {"not_started", "in_progress", "passed", "blocked"}
CHAPTER_STATES = {"not_started", "in_progress", "completed", "blocked"}
HUMAN_STATES = {"not_started", "in_progress", "completed", "blocked"}
COLD_STATES = {"not_run", "scheduled", "passed", "failed", "blocked"}
PROFILE_LIST_FIELDS = {
    "confirmed_strengths",
    "confirmed_gaps",
    "uncertainties",
    "hint_dependencies",
    "self_check_gaps",
}


def _strings(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return None
    return value


def validate_progress(project_root: Path, progress: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if progress.get("schema_version") != PROGRESS_SCHEMA:
        return ["progress schema mismatch"]
    chapter = progress.get("chapter")
    if not isinstance(chapter, int):
        return ["chapter must be an integer"]
    try:
        facts = chapter_facts(project_root, chapter)
    except Exception as exc:
        return [f"cannot derive current chapter facts: {exc}"]

    if progress.get("source_binding") != facts["source_binding"]:
        errors.append("source binding is stale")

    learner = progress.get("learner")
    if not isinstance(learner, dict):
        errors.append("learner is missing")
        learner = {}
    if not str(learner.get("learner_id") or "").strip():
        errors.append("learner_id is empty")
    if learner.get("mode") != "persistent_zero_base_proxy":
        errors.append("learner mode mismatch")
    if learner.get("initial_assumptions") != ["zero_base"]:
        errors.append("initial assumptions must contain only zero_base")
    profile_version = learner.get("profile_version")
    if not isinstance(profile_version, int) or profile_version < 1:
        errors.append("profile_version must be a positive integer")
        profile_version = 0
    for field in PROFILE_LIST_FIELDS:
        if not isinstance(learner.get(field), list):
            errors.append(f"learner.{field} must be a list")
    history = learner.get("profile_history")
    if not isinstance(history, list) or not history:
        errors.append("profile_history is missing")
        history = []
    history_versions: list[int] = []
    for index, row in enumerate(history):
        if not isinstance(row, dict):
            errors.append(f"profile_history[{index}] is not an object")
            continue
        version = row.get("version")
        if not isinstance(version, int) or version < 1:
            errors.append(f"profile_history[{index}].version is invalid")
            continue
        history_versions.append(version)
        if not str(row.get("reason") or "").strip():
            errors.append(f"profile_history[{index}].reason is empty")
        evidence = row.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"profile_history[{index}].evidence must be a list")
        elif version > 1 and not evidence:
            errors.append(f"profile_history[{index}] changes profile without evidence")
    if history_versions:
        if history_versions != sorted(set(history_versions)) or history_versions[0] != 1:
            errors.append("profile history versions are not monotonic from 1")
        if history_versions[-1] != profile_version:
            errors.append("profile history does not end at profile_version")

    ledger = progress.get("course_ledger")
    if not isinstance(ledger, dict):
        errors.append("course_ledger is missing")
        ledger = {}
    expected_courses = facts["required_course_keys"]
    if ledger.get("required_course_keys") != expected_courses:
        errors.append("required course order or coverage is stale")
    records = ledger.get("records")
    if not isinstance(records, list):
        errors.append("course records are missing")
        records = []
    by_course: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            errors.append(f"course record {index} is not an object")
            continue
        course_key = str(row.get("course_key") or "")
        if not course_key or course_key in by_course:
            errors.append(f"course record {index} has empty or duplicate course_key")
            continue
        by_course[course_key] = row
        status = row.get("status")
        if status not in COURSE_STATES:
            errors.append(f"course {course_key} has invalid status")
        if row.get("first_section") != facts["first_section"].get(course_key):
            errors.append(f"course {course_key} first_section is stale")
        evidence = row.get("completion_evidence")
        if not isinstance(evidence, list):
            errors.append(f"course {course_key} completion_evidence must be a list")
        elif status == "simulated_completed" and not evidence:
            errors.append(f"course {course_key} is completed without evidence")
    if list(by_course) != expected_courses:
        errors.append("course records do not exactly follow the required course set")
    expected_unfinished = [
        key for key in expected_courses
        if by_course.get(key, {}).get("status") != "simulated_completed"
    ]
    if ledger.get("unfinished_course_keys") != expected_unfinished:
        errors.append("unfinished_course_keys is inconsistent")
    statuses = [by_course.get(key, {}).get("status") for key in expected_courses]
    if not expected_unfinished:
        expected_ledger_status = "completed"
    elif "blocked" in statuses:
        expected_ledger_status = "blocked"
    elif "in_progress" in statuses or "simulated_completed" in statuses:
        expected_ledger_status = "in_progress"
    else:
        expected_ledger_status = "not_started"
    if ledger.get("status") != expected_ledger_status:
        errors.append("course ledger status is inconsistent")

    section_rows = progress.get("sections")
    if not isinstance(section_rows, list):
        errors.append("sections are missing")
        section_rows = []
    section_ids = [str(row.get("section") or "") for row in section_rows if isinstance(row, dict)]
    if section_ids != facts["manifest_sections"]:
        errors.append("section order or coverage is stale")

    attempted_total = 0
    passed_total = 0
    unresolved_total = 0
    previous_profile_after: int | None = None
    all_sections_passed = True
    for index, row in enumerate(section_rows):
        if not isinstance(row, dict):
            errors.append(f"section row {index} is not an object")
            all_sections_passed = False
            continue
        section = str(row.get("section") or "")
        canonical = set(facts["section_items"].get(section, []))
        attempted_values = _strings(row.get("attempted_item_keys"))
        passed_values = _strings(row.get("passed_item_keys"))
        unresolved_values = _strings(row.get("unresolved_item_keys"))
        if attempted_values is None or len(attempted_values) != len(set(attempted_values)):
            errors.append(f"{section} attempted_item_keys is invalid")
            attempted_values = []
        if passed_values is None or len(passed_values) != len(set(passed_values)):
            errors.append(f"{section} passed_item_keys is invalid")
            passed_values = []
        if unresolved_values is None or len(unresolved_values) != len(set(unresolved_values)):
            errors.append(f"{section} unresolved_item_keys is invalid")
            unresolved_values = []
        attempted = set(attempted_values)
        passed = set(passed_values)
        unresolved = set(unresolved_values)
        if not attempted.issubset(canonical):
            errors.append(f"{section} attempted items include non-canonical keys")
        if not passed.issubset(attempted):
            errors.append(f"{section} passed items were not attempted")
        if not unresolved.issubset(attempted) or unresolved.intersection(passed):
            errors.append(f"{section} unresolved items are inconsistent")
        attempted_total += len(attempted)
        passed_total += len(passed)
        unresolved_total += len(unresolved)

        before = row.get("profile_version_before")
        after = row.get("profile_version_after")
        if not isinstance(before, int) or not isinstance(after, int) or before < 1 or after < before:
            errors.append(f"{section} profile version binding is invalid")
        elif previous_profile_after is not None and before != previous_profile_after:
            errors.append(f"{section} does not continue the prior profile version")
        if isinstance(after, int):
            previous_profile_after = after

        status = row.get("status")
        if status not in SECTION_STATES:
            errors.append(f"{section} has invalid status")
        if status == "passed":
            if passed != canonical or attempted != canonical or unresolved:
                errors.append(f"{section} passed status is inconsistent")
        else:
            all_sections_passed = False
        if status == "not_started" and (attempted or passed or unresolved):
            errors.append(f"{section} not_started status has attempt evidence")
        if status == "blocked" and not unresolved:
            errors.append(f"{section} blocked status has no unresolved items")
    if previous_profile_after is not None and previous_profile_after != profile_version:
        errors.append("section profile versions do not end at learner profile_version")

    coverage = progress.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("coverage is missing")
        coverage = {}
    expected_coverage = {
        "canonical_items": facts["canonical_item_count"],
        "attempted_items": attempted_total,
        "passed_items": passed_total,
        "unresolved_items": unresolved_total,
        "remaining_items": facts["canonical_item_count"] - passed_total,
    }
    for key, expected in expected_coverage.items():
        if coverage.get(key) != expected:
            errors.append(f"coverage.{key} is inconsistent")

    if expected_ledger_status == "completed" and all_sections_passed:
        expected_chapter_status = "completed"
    elif expected_ledger_status == "blocked" or any(
        isinstance(row, dict) and row.get("status") == "blocked" for row in section_rows
    ):
        expected_chapter_status = "blocked"
    elif attempted_total == 0 and expected_ledger_status == "not_started":
        expected_chapter_status = "not_started"
    else:
        expected_chapter_status = "in_progress"
    if progress.get("simulated_learning_status") != expected_chapter_status:
        errors.append("simulated_learning_status is inconsistent")
    if progress.get("status") != expected_chapter_status:
        errors.append("chapter status is inconsistent")
    if progress.get("human_learning_status") not in HUMAN_STATES:
        errors.append("human_learning_status is invalid")
    if progress.get("cold_24h_retest") not in COLD_STATES:
        errors.append("cold_24h_retest is invalid")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--progress", required=True)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    progress_path = Path(args.progress)
    if not progress_path.is_absolute():
        progress_path = project_root / progress_path
    progress = load_json(progress_path)
    errors = validate_progress(project_root, progress)
    report = {
        "status": "passed" if not errors else "failed",
        "progress": str(progress_path),
        "chapter": progress.get("chapter"),
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
