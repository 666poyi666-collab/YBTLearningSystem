#!/usr/bin/env python3
"""Audit course-first and learner-assistance contracts for all 38 sections."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COURSE_NUMBER_RE = re.compile(r"^(\d+(?:\.\d+){1,5})")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def course_sort_key(course: dict[str, Any], key: str) -> tuple[Any, ...]:
    number = str(course.get("course_id") or "")
    if not number:
        match = COURSE_NUMBER_RE.match(str(course.get("title") or key))
        number = match.group(1) if match else ""
    if not number:
        return (9999, key)
    match = re.match(r"^(\d+(?:\.\d+)+)(?:\.([a-z]))?$", number, re.I)
    if not match:
        return (9999, key)
    parts = [int(part) for part in match.group(1).split(".")]
    suffix_rank = ord(match.group(2).lower()) - 96 if match.group(2) else 0
    title = str(course.get("title") or key)
    segment_rank = next((rank for token, rank in (("（上）", 1), ("(上)", 1), ("（基础）", 1), ("(基础)", 1), ("（中）", 2), ("(中)", 2), ("（提高）", 2), ("(提高)", 2), ("（下）", 3), ("(下)", 3), ("（进阶）", 3), ("(进阶)", 3)) if token in title), 0)
    return (*parts, suffix_rank, segment_rank, key)


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def section_courses(section: dict[str, Any]) -> list[str]:
    values = [
        *[str(value) for value in section.get("required_course_keys", [])],
        *[str(value) for value in section.get("support_course_keys", [])],
    ]
    for cycle in section.get("learning_cycles", []):
        for field in ("course_keys", "prerequisite_course_keys", "optional_course_keys"):
            values.extend(str(value) for value in cycle.get(field, []))
    return unique(values)


def item_total(section: dict[str, Any]) -> int:
    counts = section.get("learning_item_counts") or {}
    return int(counts.get("total", counts.get("total_numbered_learning_items", 0)) or 0)


def type_labels(section: dict[str, Any]) -> list[str]:
    values = [str(value) for value in section.get("type_labels", []) if str(value).strip()]
    for row in section.get("type_training", []):
        if isinstance(row, dict) and str(row.get("type") or "").strip():
            values.append(str(row["type"]))
    for cycle in section.get("learning_cycles", []):
        values.extend(str(value) for value in cycle.get("type_refs", []) if str(value).strip())
    return unique(values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", default="reports/all_chapters/course-first-contract-audit.json")
    parser.add_argument(
        "--sol-review-status",
        choices=["not_run", "completed_requested_scope_with_findings"],
        default="not_run",
    )
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    catalog_payload = load_json(root / "data" / "all_chapters_course_catalog.json")
    catalog = {str(row["course_key"]): row for row in catalog_payload.get("courses", [])}
    cloud_source = (root / "cloud" / "mcp" / "src" / "index.ts").read_text(encoding="utf-8")
    handwriting_script = (root / "scripts" / "build_handwriting_annotation_html.py").read_text(encoding="utf-8")

    rows: list[dict[str, Any]] = []
    total_items = 0
    errors: list[str] = []
    for chapter in range(1, 6):
        manifest = load_json(root / f"chapter{chapter}_manifest.json")
        for section in manifest.get("sections", []):
            section_id = str(section.get("id") or "")
            courses = section_courses(section)
            unresolved = [key for key in courses if key not in catalog]
            unplaced = [str(key) for key in section.get("unplaced_course_keys", [])]
            source_order = courses
            recommended_order = sorted(courses, key=lambda key: course_sort_key(catalog.get(key, {}), key))
            types = type_labels(section)
            cycles = section.get("learning_cycles", [])
            count = item_total(section)
            total_items += count
            section_errors = []
            if not section_id:
                section_errors.append("missing_section_id")
            if count <= 0:
                section_errors.append("missing_item_total")
            if not cycles:
                section_errors.append("missing_learning_cycles")
            if unresolved:
                section_errors.append("unresolved_course_keys")
            if unplaced:
                section_errors.append("unplaced_course_keys_need_item_review")
            if not types:
                section_errors.append("missing_type_labels")
            status = "passed" if not section_errors else "needs_iteration"
            for error in section_errors:
                errors.append(f"chapter{chapter}:{section_id}:{error}")
            rows.append({
                "chapter": chapter,
                "section": section_id,
                "label": section.get("label"),
                "item_count": count,
                "cycle_count": len(cycles),
                "type_labels": types,
                "course_keys_in_source_route": source_order,
                "recommended_course_number_order": recommended_order,
                "course_reorder_recommended": source_order != recommended_order,
                "unresolved_course_keys": unresolved,
                "unplaced_course_keys": unplaced,
                "practice_policy": {
                    "optional": True,
                    "blocks_ybt_progress": False,
                    "available_for_chapter": chapter in {1, 2, 3},
                },
                "handwriting_policy": {
                    "transparent_html": True,
                    "first_wrong_required_for_proposed": True,
                    "uncertainty_disclosure_required": True,
                },
                "errors": section_errors,
                "status": status,
            })

    global_checks = {
        "practice_optional_flag": "practiceIsOptional: true" in cloud_source,
        "practice_non_blocking_flag": "blocksYbtProgress: false" in cloud_source,
        "handwriting_transparent_overlay": "transparent_svg_overlay" in cloud_source and "fill:none" in handwriting_script,
        "handwriting_uncertainty_gate": "uncertainty_disclosure_required" in cloud_source,
        "handwriting_first_error_gate": "first_wrong_step_required" in cloud_source,
    }
    if not all(global_checks.values()):
        errors.extend(f"global:{key}" for key, value in global_checks.items() if not value)
    payload = {
        "schema_version": "ybt-all-section-course-first-audit-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {"chapters": 5, "sections": len(rows), "items": total_items},
        "requested_semantic_reviewer": {
            "model": "gpt-5.6-sol",
            "status": args.sol_review_status,
            "review_kind": "section_cycle_semantic_audit",
            "reviewed_scope": "第一章第2节以后、第二章全部、第三至第五章全部",
            "reviewed_section_count": 37 if args.sol_review_status != "not_run" else 0,
            "individual_item_attempt_simulation": "not_run",
            "repairs_checked": [
                "course suffix .a/.b numeric ordering",
                "course segment 上/中/下 and 基础/提高/进阶 ordering",
                "practice page/item route consistency",
                "practice optional non-blocking semantics",
                "handwriting transparent HTML and uncertainty disclosure",
                "course-to-cycle semantic targets and disclosed unplaced courses",
            ] if args.sol_review_status != "not_run" else [],
        },
        "global_checks": global_checks,
        "summary": {
            "passed_sections": sum(row["status"] == "passed" for row in rows),
            "needs_iteration_sections": sum(row["status"] != "passed" for row in rows),
            "course_reorder_recommended_sections": sum(row["course_reorder_recommended"] for row in rows),
            "error_count": len(errors),
        },
        "sections": rows,
        "errors": errors,
        "status": "passed" if len(rows) == 38 and total_items == 1209 and not errors else "needs_iteration",
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = output.with_suffix(".md")
    lines = [
        "# 全章节课程优先合同审计", "",
        f"- 范围：{len(rows)} 节，{total_items} 个一本通项目",
        f"- 通过：{payload['summary']['passed_sections']} 节",
        f"- 待迭代：{payload['summary']['needs_iteration_sections']} 节",
        f"- 建议按课程编号重排：{payload['summary']['course_reorder_recommended_sections']} 节",
        f"- 状态：{payload['status']}", "",
        "| 章 | 节 | 项目 | 循环 | 题型数 | 课程重排 | 状态 |", "|---:|---|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['chapter']} | {row['section']} {row['label']} | {row['item_count']} | {row['cycle_count']} | {len(row['type_labels'])} | {'是' if row['course_reorder_recommended'] else '否'} | {row['status']} |")
    if errors:
        lines.extend(["", "## 待处理", "", *[f"- {value}" for value in errors]])
    markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "sections": len(rows), "items": total_items, "errors": len(errors), "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
