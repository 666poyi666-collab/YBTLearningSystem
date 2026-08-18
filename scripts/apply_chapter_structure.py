#!/usr/bin/env python3
"""Merge current OCR structure evidence into chapter 2-5 manifests."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OCR_ROOTS = {
    2: ROOT / "data" / "ocr_live_current" / "second_chapter_109",
    3: ROOT / "data" / "ocr_live_current" / "third_chapter_180",
    4: ROOT / "data" / "ocr_live_current" / "chapter4_100",
    5: ROOT / "data" / "ocr_live_current" / "chapter5_95",
}
GROUP_OVERRIDES = {
    "2.3": {"A": [1, 4], "B": [5, 20], "C": [21, 22]},
    "2.4": {"A": [1, 4], "B": [5, 11], "C": [12, 15]},
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def question_keys(groups: dict[str, list[int]]) -> list[str]:
    return [
        f"{group}{number}"
        for group in ("A", "B", "C")
        if group in groups
        for number in range(groups[group][0], groups[group][1] + 1)
    ]


def clean_course_lists(chapter: int, manifest: dict[str, Any], section: dict[str, Any]) -> tuple[list[str], list[str]]:
    if chapter == 2:
        courses = manifest.get("course_inventory", {}).get("courses", [])
        key_by_id = {str(row.get("course_id")): str(row.get("course_key")) for row in courses}
        required_ids = [str(value) for value in section.get("required_course_ids") or []]
        support_ids = [str(value) for value in section.get("support_course_ids") or []]
        required = [key_by_id.get(value, value) for value in required_ids]
        support = [key_by_id.get(value, value) for value in support_ids]
        return list(dict.fromkeys(required)), list(dict.fromkeys(support))
    if chapter == 3:
        flattened = [row for rows in manifest.get("courses", {}).values() for row in rows]
        key_by_id = {str(row.get("course_id")): str(row.get("course_key")) for row in flattened}
        required_ids = [str(value) for value in section.get("course_mapping_preliminary") or []]
        support_ids = [str(value) for value in section.get("course_mapping_common_tools") or []]
        required = [key_by_id.get(value, value) for value in required_ids]
        support = [key_by_id.get(value, value) for value in support_ids]
        section["required_course_ids"] = required_ids
        section["support_course_ids"] = support_ids
        return list(dict.fromkeys(required)), list(dict.fromkeys(support))
    required = [str(value).strip() for value in section.get("required_course_ids") or [] if str(value).strip()]
    support = [str(value).strip() for value in section.get("support_course_ids") or [] if str(value).strip()]
    return list(dict.fromkeys(required)), list(dict.fromkeys(support))


def direct_variant_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        parent = row.get("parent_example")
        if not isinstance(parent, int):
            continue
        target = grouped.setdefault(parent, {"example": f"例{parent}", "variants": [], "ocr_docs": []})
        target["variants"].append(row.get("label") or "变式")
        target["ocr_docs"].extend(row.get("pages") or [])
    return [
        {
            **grouped[parent],
            "variants": list(grouped[parent]["variants"]),
            "ocr_docs": sorted(set(grouped[parent]["ocr_docs"])),
        }
        for parent in sorted(grouped)
    ]


def ordered_example_blocks(section: dict[str, Any], example_numbers: list[int]) -> list[dict[str, Any]]:
    knowledge_owner: dict[int, tuple[str, str]] = {}
    for point in section.get("knowledge_points") or []:
        for value in point.get("examples") or []:
            match = re.search(r"\d+", str(value))
            if match:
                knowledge_owner[int(match.group())] = (str(point["id"]), str(point["label"]))
    type_owner: dict[int, str] = {}
    for row in section.get("type_training") or []:
        for number in row.get("example_numbers") or []:
            type_owner[int(number)] = str(row["type"])

    blocks: list[dict[str, Any]] = []
    for number in sorted(example_numbers):
        if number in knowledge_owner:
            ref, label = knowledge_owner[number]
            identity = ("knowledge", ref)
            block = {
                "kind": "knowledge",
                "identity": identity,
                "title": label,
                "knowledge_refs": [ref],
                "type_refs": [],
                "example_numbers": [],
            }
        elif number in type_owner:
            ref = type_owner[number]
            identity = ("type", ref)
            block = {
                "kind": "type",
                "identity": identity,
                "title": ref,
                "knowledge_refs": [],
                "type_refs": [ref],
                "example_numbers": [],
            }
        else:
            identity = ("supplement", "source_order")
            block = {
                "kind": "supplement",
                "identity": identity,
                "title": "教材补充例题",
                "knowledge_refs": [],
                "type_refs": [],
                "example_numbers": [],
            }
        if not blocks or blocks[-1]["identity"] != identity:
            blocks.append(block)
        blocks[-1]["example_numbers"].append(number)
    return blocks


def distribute_courses(blocks: list[dict[str, Any]], course_keys: list[str]) -> None:
    if not blocks:
        return
    for index, key in enumerate(course_keys):
        target = min(len(blocks) - 1, (index * len(blocks)) // max(len(course_keys), 1))
        blocks[target].setdefault("course_keys", []).append(key)


def build_cycles(section: dict[str, Any], example_numbers: list[int], groups: dict[str, list[int]]) -> list[dict[str, Any]]:
    required = list(section.get("required_course_keys") or [])
    support = list(section.get("support_course_keys") or [])
    all_courses = list(dict.fromkeys([*required, *support]))
    blocks = ordered_example_blocks(section, example_numbers)
    if not blocks:
        blocks.append(
            {
                "kind": "supplement",
                "identity": ("supplement", "source_order"),
                "title": "教材方法与例题",
                "knowledge_refs": [],
                "type_refs": [],
                "example_numbers": [],
            }
        )
    distribute_courses(blocks, all_courses)

    cycles: list[dict[str, Any]] = []
    learned_courses: list[str] = []
    for block in blocks:
        new_courses = list(block.get("course_keys") or [])
        cycle = {
            "id": f"{section['id']}-cycle-{len(cycles) + 1}",
            "title": block["title"],
            "course_keys": new_courses,
            "prerequisite_course_keys": list(learned_courses),
            "knowledge_refs": block["knowledge_refs"],
            "type_refs": block["type_refs"],
            "example_numbers": block["example_numbers"],
            "exercise_keys": [],
            "bridge_unit_ids": [],
            "method_checkpoints": [],
        }
        cycles.append(cycle)
        learned_courses.extend(key for key in new_courses if key not in learned_courses)

    for group in ("A", "B", "C"):
        if group not in groups:
            continue
        start, end = groups[group]
        cycles.append(
            {
                "id": f"{section['id']}-cycle-{len(cycles) + 1}",
                "title": f"{group}组 {'夯实基础' if group == 'A' else '强化能力' if group == 'B' else '拓展提升'}",
                "course_keys": [],
                "prerequisite_course_keys": list(learned_courses),
                "knowledge_refs": [],
                "type_refs": [str(row["type"]) for row in section.get("type_training") or []],
                "example_numbers": [],
                "exercise_keys": [f"{group}{number}" for number in range(start, end + 1)],
                "bridge_unit_ids": [],
                "method_checkpoints": [],
            }
        )
    return cycles


def apply_section(
    chapter: int,
    manifest: dict[str, Any],
    section: dict[str, Any],
    structure: dict[str, Any],
    recovery_keys: set[tuple[str, str, int]],
) -> None:
    section_id = str(section["id"])
    groups = GROUP_OVERRIDES.get(section_id, structure.get("question_groups") or {})
    examples = [int(row["number"]) for row in structure.get("examples") or []]
    variants = structure.get("variants") or []
    expected_keys = set(question_keys(groups))
    observed_keys = {
        f"{group}{number}"
        for group, numbers in (structure.get("observed_question_numbers") or {}).items()
        for number in numbers
        if f"{group}{number}" in expected_keys
    }
    missing_keys = expected_keys - observed_keys
    unrecovered = [key for key in sorted(missing_keys) if (section_id, key[0], int(key[1:])) not in recovery_keys]
    if unrecovered:
        raise ValueError(f"{section_id} has source-unanchored questions: {unrecovered}")

    section["pdf_pages"] = structure.get("pdf_pages")
    section["ocr_docs"] = structure.get("ocr_docs")
    section["specialized_pdf_pages"] = section["pdf_pages"][1] - section["pdf_pages"][0] + 1
    section["question_groups"] = groups
    section["question_groups_status"] = "SOURCE_ANCHORED_CURRENT_OCR"
    section["verified_question_count"] = len(expected_keys)
    section["knowledge_points"] = structure.get("knowledge_points") or []
    section["type_training"] = [
        {
            "type": f"类型{row['type']} {row['title']}".strip(),
            "example_numbers": row.get("example_numbers") or [],
            "focus": row.get("title") or f"类型{row['type']}",
        }
        for row in structure.get("types") or []
    ]
    section["type_labels"] = [row["type"] for row in section["type_training"]]
    section["direct_variants"] = direct_variant_groups(variants)
    section["learning_item_counts"] = {
        "worked_examples": len(examples),
        "direct_variants": len(variants),
        "abc_exercises": len(expected_keys),
        "total": len(examples) + len(variants) + len(expected_keys),
    }
    required_keys, support_keys = clean_course_lists(chapter, manifest, section)
    section["required_course_keys"] = required_keys
    section["support_course_keys"] = support_keys
    section["learning_cycles"] = build_cycles(section, examples, groups)
    section["learning_cycles_status"] = "SOURCE_ORDER_BASELINE_CURRENT"
    section["coverage_status"] = "SOURCE_STRUCTURE_READY_SIMULATION_PENDING"
    section["coverage_gate"] = (
        "教材页、题号、例题和直属变式已按当前 OCR 与源页恢复层闭合；"
        "视觉题侧车、逐题零基础模拟和冷复测未通过前不得宣称掌握。"
    )
    section["coverage_gaps"] = []


def apply_chapter(chapter: int, backup_root: Path) -> dict[str, Any]:
    manifest_path = ROOT / f"chapter{chapter}_manifest.json"
    structure_path = ROOT / "reports" / "builds" / f"ch{chapter}-structure-current.json"
    manifest = load_json(manifest_path)
    structure = load_json(structure_path)
    structure_by_id = {row["section"]: row for row in structure.get("sections") or []}
    recovery_data = load_json(ROOT / "data" / "question_number_recoveries.json")
    recoveries = recovery_data["known_visual_recoveries"]
    question_corrections = recovery_data.get("derived_question_corrections", [])
    chapter_prefix = "ch3." if chapter == 3 else f"{chapter}."
    chapter_recoveries = [row for row in recoveries if str(row["section"]).startswith(chapter_prefix)]
    chapter_question_corrections = [
        row for row in question_corrections if str(row["section"]).startswith(chapter_prefix)
    ]
    recovery_keys = {(str(row["section"]), str(row["group"]), int(row["number"])) for row in chapter_recoveries}

    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_path, backup_root / manifest_path.name)
    for section in manifest.get("sections") or []:
        row = structure_by_id.get(section.get("id"))
        if not row:
            raise ValueError(f"chapter {chapter} section missing from structure: {section.get('id')}")
        apply_section(chapter, manifest, section, row, recovery_keys)

    source = manifest.setdefault("source_evidence", {})
    source["ocr_root"] = str(OCR_ROOTS[chapter])
    source["ocr_doc_range"] = [0, int(source.get("merged_pdf_pages", 0)) - 1]
    source["ocr_status"] = "PADDLE_AI_STUDIO_CURRENT_COMPLETE"
    source["question_number_recovery_source"] = "data/question_number_recoveries.json"
    source["manual_review_flags"] = []
    totals = defaultdict(int)
    for section in manifest.get("sections") or []:
        counts = section["learning_item_counts"]
        for key in ("worked_examples", "direct_variants", "abc_exercises"):
            totals[key] += int(counts[key])
    totals["total_numbered_learning_items"] = totals["worked_examples"] + totals["direct_variants"] + totals["abc_exercises"]
    source["learning_item_counts"] = dict(totals)
    manifest["known_visual_recoveries"] = chapter_recoveries
    manifest["derived_question_corrections"] = chapter_question_corrections
    manifest["structure_applied_at"] = datetime.now(timezone.utc).isoformat()
    manifest["structure_source"] = str(structure_path.relative_to(ROOT)).replace("\\", "/")
    save_json(manifest_path, manifest)
    return {
        "chapter": chapter,
        "sections": len(manifest.get("sections") or []),
        "counts": dict(totals),
        "recoveries": len(chapter_recoveries),
        "question_corrections": len(chapter_question_corrections),
        "manifest": str(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", choices=["2", "3", "4", "5", "all"], default="all")
    args = parser.parse_args()
    chapters = [2, 3, 4, 5] if args.chapter == "all" else [int(args.chapter)]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = ROOT / "tmp" / "manifest_backups" / stamp
    results = [apply_chapter(chapter, backup_root) for chapter in chapters]
    print(json.dumps({"backup": str(backup_root), "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
