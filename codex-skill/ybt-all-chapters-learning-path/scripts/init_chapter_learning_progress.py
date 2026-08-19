#!/usr/bin/env python3
"""Initialize an evidence-empty growing learner for an active 一本通 chapter."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from chapter_learning_progress import PROGRESS_SCHEMA, chapter_facts


def build_initial_progress(project_root: Path, chapter: int) -> dict:
    facts = chapter_facts(project_root, chapter)
    courses = facts["required_course_keys"]
    return {
        "schema_version": PROGRESS_SCHEMA,
        "chapter": chapter,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_binding": facts["source_binding"],
        "learner": {
            "learner_id": "primary-user-proxy",
            "mode": "persistent_zero_base_proxy",
            "profile_version": 1,
            "initial_assumptions": ["zero_base"],
            "confirmed_strengths": [],
            "confirmed_gaps": [],
            "uncertainties": [],
            "hint_dependencies": [],
            "self_check_gaps": [],
            "profile_history": [
                {
                    "version": 1,
                    "reason": "initialized_with_zero_base_assumption_only",
                    "evidence": [],
                }
            ],
        },
        "course_ledger": {
            "required_course_keys": courses,
            "records": [
                {
                    "course_key": course_key,
                    "first_section": facts["first_section"][course_key],
                    "status": "planned",
                    "completion_evidence": [],
                }
                for course_key in courses
            ],
            "unfinished_course_keys": courses,
            "status": "not_started",
        },
        "sections": [
            {
                "section": section,
                "status": "not_started",
                "profile_version_before": 1,
                "profile_version_after": 1,
                "attempted_item_keys": [],
                "passed_item_keys": [],
                "unresolved_item_keys": [],
            }
            for section in facts["manifest_sections"]
        ],
        "coverage": {
            "canonical_items": facts["canonical_item_count"],
            "attempted_items": 0,
            "passed_items": 0,
            "unresolved_items": 0,
            "remaining_items": facts["canonical_item_count"],
        },
        "simulated_learning_status": "not_started",
        "human_learning_status": "not_started",
        "cold_24h_retest": "not_run",
        "status": "not_started",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--output")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    output = Path(args.output) if args.output else Path(f"data/learner_progress/chapter{args.chapter}.json")
    if not output.is_absolute():
        output = project_root / output
    if output.exists() and not args.force:
        raise SystemExit(f"progress file already exists: {output}; use --force only for an intentional reset")

    progress = build_initial_progress(project_root, args.chapter)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "initialized",
        "chapter": args.chapter,
        "required_courses": len(progress["course_ledger"]["required_course_keys"]),
        "canonical_items": progress["coverage"]["canonical_items"],
        "output": str(output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
