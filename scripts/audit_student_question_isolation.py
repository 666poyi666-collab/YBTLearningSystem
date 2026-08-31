#!/usr/bin/env python3
"""Audit every learner question projection before route simulation."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ybt_learning.isolated_simulation import (
    build_answer_free_packet,
    cycle_items,
    item_identity,
    iter_sections,
    load_json,
    save_json,
    section_folder,
    sha256_file,
)


def build_report(root: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    section_counts: Counter[str] = Counter()
    blocked_sections: set[str] = set()
    for ref in iter_sections(root):
        section_id = str(ref.section["id"])
        folder = root / "data" / "packets" / section_folder(section_id)
        learning_path = folder / "student_learning_items.json"
        exercise_path = folder / "student_packet.json"
        packet = build_answer_free_packet(
            ref.section,
            load_json(learning_path),
            load_json(exercise_path),
        )
        for cycle in packet["learning_cycles"]:
            for item in cycle_items(cycle):
                item_key, label, kind = item_identity(item)
                quality = dict(item.get("source_quality") or {})
                status = str(quality.get("status") or "blocked")
                section_counts[section_id] += 1
                if status != "passed":
                    blocked_sections.add(section_id)
                rows.append({
                    "chapter": ref.chapter,
                    "section": section_id,
                    "cycle_id": cycle["cycle_id"],
                    "item_key": item_key,
                    "item_id": item.get("item_id") or item.get("qid"),
                    "label": label,
                    "kind": kind,
                    "source_docs": item.get("source_docs", []),
                    "source_question_text_sha256": quality.get("source_question_text_sha256"),
                    "learner_question_text_sha256": quality.get("learner_question_text_sha256"),
                    "status": status,
                    "reasons": quality.get("reasons", []),
                })
    blocked = [row for row in rows if row["status"] != "passed"]
    return {
        "schema_version": "ybt-student-question-isolation-audit-v1",
        "scope": "all_five_chapters",
        "source_bindings": {
            "manifests": {
                f"chapter{chapter}": sha256_file(root / f"chapter{chapter}_manifest.json")
                for chapter in range(1, 6)
            },
        },
        "summary": {
            "chapters": 5,
            "sections": len(section_counts),
            "items": len(rows),
            "passed": len(rows) - len(blocked),
            "blocked": len(blocked),
            "blocked_sections": sorted(blocked_sections),
        },
        "blocked_items": blocked,
        "rows": rows,
        "status": "passed" if len(rows) == 1209 and not blocked else "blocked",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument(
        "--output",
        default="reports/deep_simulation/student-question-isolation.json",
    )
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    report = build_report(root)
    save_json(output, report)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
