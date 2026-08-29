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

# High-confidence course-to-textbook targets from the semantic review. Courses
# omitted from a section stay in unplaced_course_keys instead of being spread
# across unrelated cycles just to exhaust the catalog.
COURSE_TARGET_OVERRIDES: dict[str, dict[str, int]] = {
    "2.1": {"slope_angle_relation": 1, "moving_line_region": 13},
    "2.2": {"line_five_forms": 1, "line_equation_application": 4, "line_parallel_perpendicular": 7},
    "2.3": {"point_line_distance": 4},
    "2.4": {
        "point_line_symmetry_upper": 1, "point_line_symmetry_lower": 1,
        "line_line_symmetry_upper": 3, "line_line_symmetry_lower": 3,
        "line_family_fixed_point": 5,
    },
    "2.5": {"circle_standard_general": 1, "circle_determination": 7},
    "2.6": {
        "line_circle_position": 1, "tangent": 2, "chord_length": 6,
        "longest_shortest_chord": 7, "line_circle_extreme": 10,
    },
    "2.7": {
        "circle_circle_position": 1, "pole_polar_chord": 1,
        "circle_equiv_algebra": 7, "circle_equiv_geometry": 8,
    },
    "ch3.s1": {"ellipse_definition": 1, "ellipse_standard_equations": 2},
    "ch3.s2": {
        "ellipse_eccentricity": 1,
        "intersection_algebra_upper": 5, "intersection_algebra_lower": 5,
    },
    "ch3.s3": {
        "focus_triangle_perimeter_area": 3,
        "chord_midpoint_slope_constant": 4,
    },
    "ch3.s4": {"hyperbola_definition_equation": 1},
    "ch3.s5": {
        "hyperbola_eccentricity_asymptote": 1,
        "intersection_algebra_upper": 4, "intersection_algebra_lower": 4,
    },
    "ch3.s6": {
        "focus_triangle_perimeter_area": 4,
        "chord_midpoint_slope_constant": 5, "chord_midpoint_extended": 6,
    },
    "ch3.s7": {"parabola_definition_equation": 1, "focal_radius_formula": 4, "focal_chord_area": 4},
    "ch3.s8": {"parabola_properties": 1},
    "ch3.s9": {
        "chord_midpoint_extended": 1,
        "polar_focal_chord_upper": 1, "polar_focal_chord_lower": 1,
        "dot_product_double_root": 2,
        "intersection_algebra_upper": 2, "intersection_algebra_lower": 2,
    },
    "ch3.s10": {
        "chord_length_formula": 1, "in_curve_triangle_area": 1,
        "in_curve_quad_area": 1, "evaluation_algebra": 1,
        "evaluation_geometry": 2,
        "intersection_algebra_upper": 2, "intersection_algebra_lower": 2,
    },
    "ch3.s11": {
        "constant_value_1": 1, "constant_value_2": 1, "fixed_point_1": 2,
        "fixed_point_2_upper": 2, "fixed_point_2_lower": 2,
        "pole_polar_upper": 3, "pole_polar_lower": 3,
        "intersection_algebra_upper": 3, "intersection_algebra_lower": 3,
    },
    "4.3": {"4.3.2.4 等差数列Sn的性质": 3},
    "4.5": {"4.3.3.4 等比数列Sn性质": 2},
    "4.7": {
        "4.4.3.1.a 分式裂项（上）": 1, "4.4.3.1.b 分式裂项（下）": 1,
        "4.4.3.2 根式裂项": 1,
        "4.4.5.1.a 错位相减法（上）": 2, "4.4.5.1.b 错位相减法（下）": 2,
        "4.4.4.1 分组求和法": 3, "4.4.4.2 倒序相加法": 4,
    },
    "4.8": {
        "4.4.4.1 分组求和法": 2,
        "4.4.1.1 累加法与累乘法": 3, "4.4.6.2 数列的周期性问题": 3,
        "4.4.7.1 不等式与恒成立问题": 5,
        "4.4.8.1 放缩为可裂项的数列": 5, "4.4.8.2 放缩为等比数列求和": 5,
    },
    "5.1": {
        "4.1.1.1 导数的定义（上）": 1, "4.1.1.1 导数的定义（下）": 1,
        "4.1.1.2 求在P点处的切线": 4, "4.1.1.3 求过P点的切线": 4,
        "4.1.1.4 判断切线条数问题": 4, "4.1.1.5 公切线问题": 4,
    },
    "5.2": {
        "4.1.2.1 基本初等函数的导数及运算法则": 1,
        "4.1.2.1 基本初等函数的导数及运算法则（进阶）": 1,
        "4.1.2.2 复合函数的导数": 5,
        "4.1.2.3 导数的原函数构造（基础）": 6,
        "4.1.2.3 导数的原函数构造（进阶）": 6,
    },
    "5.3": {
        "4.1.4.1 不含参数的函数的单调性": 1,
        "4.1.4.2 含参函数单调性讨论之可因式分解型（上）": 3,
        "4.1.4.2 含参函数单调性讨论之可因式分解型（中）": 3,
        "4.1.4.2 含参函数单调性讨论之可因式分解型（下）": 3,
        "4.1.4.3 含参函数单调性讨论之类二次型": 3,
        "4.1.4.4 含参函数单调性讨论之不可因式分解型（上）": 3,
        "4.1.4.4 含参函数单调性讨论之不可因式分解型（中）": 3,
        "4.1.4.4 含参函数单调性讨论之不可因式分解型（下）": 3,
        "4.1.4.5 含参函数单调性讨论之超越函数": 3,
        "4.1.4.6 已知单调性求参之导数为二次型": 3,
        "4.1.4.7 已知单调性求参之导数为非二次型": 3,
    },
    "5.4": {
        "4.1.4.8 极值与极值点（基础）": 1, "4.1.4.8 极值与极值点（进阶）": 1,
        "4.1.4.9 最值讨论与值域之具体函数": 3,
        "4.1.4.10 最值讨论与值域之含参函数": 3,
    },
    "5.5": {
        "4.2.1.2 参变分离法": 2,
        "4.2.2.1 主元法（基础）": 2, "4.2.2.1 主元法（进阶）": 2,
        "4.2.2.2 常用函数放缩": 2,
        "4.2.2.3 分离函数法": 5, "4.2.4.2 双变量的换元构造": 5,
        "4.2.4.1 极值点偏移模型（上）": 8, "4.2.4.1 极值点偏移模型（下）": 8,
        "4.2.5.1 单极值点问题": 8,
        "4.2.5.2 双极值点问题（上）": 8, "4.2.5.2 双极值点问题（下）": 8,
    },
    # 5.6 is a review set: it introduces no new mandatory course.
    "5.6": {},
}

SECTION_INHERITED_COURSES: dict[str, list[str]] = {
    "2.2": ["slope_angle_relation", "moving_line_region"],
    "2.3": ["line_parallel_perpendicular"],
    "2.4": ["point_line_distance"],
    "2.5": ["line_family_fixed_point"],
    "2.6": ["circle_determination"],
    "2.7": ["circle_standard_general", "line_circle_extreme"],
    "ch3.s3": ["ellipse_definition", "ellipse_standard_equations", "ellipse_eccentricity"],
    "ch3.s6": ["hyperbola_definition_equation", "hyperbola_eccentricity_asymptote"],
    "ch3.s7": ["parabola_definition_equation"],
    "4.3": ["4.3.2.1 等差数列的基本公式"],
    "4.5": ["4.3.3.1 等比数列的基本公式"],
    "5.4": ["4.1.4.1 不含参数的函数的单调性"],
    "5.6": [
        "4.1.2.1 基本初等函数的导数及运算法则", "4.1.2.2 复合函数的导数",
        "4.1.1.2 求在P点处的切线", "4.1.1.3 求过P点的切线",
        "4.1.4.1 不含参数的函数的单调性", "4.1.4.8 极值与极值点（基础）",
        "4.1.4.9 最值讨论与值域之具体函数", "4.2.2.2 常用函数放缩",
        "4.2.6.1 求和型放缩（上）", "4.2.6.1 求和型放缩（下）",
    ],
}

SECTION_COURSE_ADDITIONS: dict[str, list[str]] = {
    "ch3.s7": ["focal_radius_formula", "focal_chord_area"],
}

SECTION_COURSE_EXCLUSIONS: dict[str, set[str]] = {
    "2.3": {"line_family_fixed_point"},
    "2.5": {"circle_equiv_algebra", "circle_equiv_geometry"},
    "2.6": {"pole_polar_chord"},
    "ch3.s3": {"midpoint_idea", "focal_radius_formula", "focal_chord_area"},
    "ch3.s6": {"midpoint_idea", "focal_radius_formula", "focal_chord_area"},
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
        if number in type_owner:
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
        elif number in knowledge_owner:
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


def assign_reviewed_courses(section: dict[str, Any], blocks: list[dict[str, Any]], course_keys: list[str]) -> None:
    targets = COURSE_TARGET_OVERRIDES.get(str(section.get("id")))
    if targets is None:
        distribute_courses(blocks, course_keys)
        section["unplaced_course_keys"] = []
        section["course_mapping_status"] = "LEGACY_SOURCE_ORDER_NEEDS_SEMANTIC_REVIEW"
        return
    assigned: list[str] = []
    for key in course_keys:
        target_example = targets.get(key)
        if target_example is None:
            continue
        block = next((row for row in blocks if target_example in row.get("example_numbers", [])), None)
        if block is None:
            raise ValueError(f"{section['id']} course target example is missing: {key} -> {target_example}")
        block.setdefault("course_keys", []).append(key)
        assigned.append(key)
    inherited = set(SECTION_INHERITED_COURSES.get(str(section.get("id")), []))
    section["unplaced_course_keys"] = [key for key in course_keys if key not in assigned and key not in inherited]
    section["course_mapping_status"] = (
        "SEMANTIC_TARGETS_REVIEWED"
        if not section["unplaced_course_keys"] else "SEMANTIC_TARGETS_WITH_DISCLOSED_UNPLACED_COURSES"
    )


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
    assign_reviewed_courses(section, blocks, all_courses)

    cycles: list[dict[str, Any]] = []
    learned_courses: list[str] = list(SECTION_INHERITED_COURSES.get(str(section.get("id")), []))
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
                "type_refs": [],
                "unclassified_item_ids": [f"{group}{number}" for number in range(start, end + 1)],
                "type_mapping_status": "PENDING_ITEM_LEVEL_CLASSIFICATION",
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
    for key in SECTION_COURSE_ADDITIONS.get(section_id, []):
        if key not in required_keys and key not in support_keys:
            support_keys.append(key)
    exclusions = SECTION_COURSE_EXCLUSIONS.get(section_id, set())
    required_keys = [key for key in required_keys if key not in exclusions]
    support_keys = [key for key in support_keys if key not in exclusions]
    for key in SECTION_INHERITED_COURSES.get(section_id, []):
        if key not in required_keys and key not in support_keys:
            support_keys.append(key)
    section["required_course_keys"] = required_keys
    section["support_course_keys"] = support_keys
    section["learning_cycles"] = build_cycles(section, examples, groups)
    section["learning_cycles_status"] = section.get("course_mapping_status", "SOURCE_ORDER_BASELINE_CURRENT")
    section["coverage_status"] = "SOURCE_STRUCTURE_READY_SIMULATION_PENDING"
    section["coverage_gate"] = (
        "教材页、题号、例题和直属变式已按当前 OCR 与源页恢复层闭合；"
        "视觉题侧车、逐题零基础模拟和冷复测未通过前不得宣称掌握。"
    )
    section["coverage_gaps"] = [
        {
            "kind": "unplaced_course",
            "course_key": key,
            "reason": "语义审计未确认与具体教材循环的直接对应；课程仍保留在节次账本中。",
        }
        for key in section.get("unplaced_course_keys", [])
    ]


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
    source["ocr_root"] = str(OCR_ROOTS[chapter].relative_to(ROOT)).replace("\\", "/")
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
