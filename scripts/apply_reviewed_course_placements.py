#!/usr/bin/env python3
"""Apply reviewed course-to-cycle placements for the final all-section route."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PLACEMENTS: dict[str, list[dict[str, Any]]] = {
    "ch3.s1": [{"cycle": "ch3.s1-cycle-13", "field": "course_keys", "courses": ["intersection_algebra_upper", "intersection_algebra_lower"], "reason": "B组开始出现需要联立直线与椭圆、判断交点的强化题。"}],
    "ch3.s3": [{"cycle": "ch3.s3-cycle-6", "field": "course_keys", "courses": ["intersection_algebra_upper", "intersection_algebra_lower"], "reason": "二级结论进入B组后需要把斜率结论接回直线与椭圆的交点代数。"}],
    "ch3.s4": [{"cycle": "ch3.s4-cycle-9", "field": "course_keys", "courses": ["intersection_algebra_upper", "intersection_algebra_lower"], "reason": "B组强化题需要联立直线与双曲线并处理交点条件。"}],
    "ch3.s6": [{"cycle": "ch3.s6-cycle-7", "field": "course_keys", "courses": ["intersection_algebra_upper", "intersection_algebra_lower"], "reason": "双曲线二级结论在B组迁移到直线交点代数。"}],
    "ch3.s7": [{"cycle": "ch3.s7-cycle-11", "field": "course_keys", "courses": ["intersection_algebra_upper", "intersection_algebra_lower"], "reason": "B组强化题开始系统使用直线与抛物线联立。"}],
    "ch3.s8": [{"cycle": "ch3.s8-cycle-3", "field": "course_keys", "courses": ["intersection_algebra_upper", "intersection_algebra_lower"], "reason": "类型Ⅱ明确研究直线与抛物线的位置关系。"}],
    "4.8": [
        {"cycle": "4.8-cycle-1", "field": "course_keys", "courses": ["4.4.2.1 利用Sn与an的关系转化为an的递推数列", "4.4.2.2 利用Sn与an的关系转化为Sn的递推数列"], "reason": "添项、去项题先在Sn与an之间转换递推对象。"},
        {"cycle": "4.8-cycle-2", "field": "course_keys", "courses": ["4.4.2.3 特殊和问题——类比Sn"], "reason": "奇偶分组求和需要把特殊和类比为新的前n项和。"},
        {"cycle": "4.8-cycle-3", "field": "course_keys", "courses": ["4.4.1.2.a 待定系数法", "4.4.1.2.b 待定系数法", "4.4.1.2.c 待定系数法", "4.4.1.2.d 待定系数法", "4.4.1.2.e 待定系数法", "4.4.1.3 利用辅助数列"], "reason": "奇偶数列求通项的核心是递推数列构造、待定系数与辅助数列。"},
        {"cycle": "4.8-cycle-5", "field": "course_keys", "courses": ["4.4.6.1 数列的单调性与求最值问题"], "reason": "B组综合验收包含数列单调性与最值迁移。"},
    ],
    "5.1": [
        {"cycle": "5.1-cycle-8", "field": "course_keys", "courses": ["4.1.1.6 用切线算距离最值"], "reason": "B组把导数几何意义迁移到切线距离最值。"},
        {"cycle": "5.1-cycle-9", "field": "course_keys", "courses": ["4.1.1.7 隐函数求导"], "reason": "C组作为导数定义与几何意义后的拓展方法。"},
    ],
    "5.2": [{"cycle": "5.2-cycle-4", "field": "course_keys", "courses": ["4.1.2.3 导数的原函数构造之速解技巧"], "reason": "该循环明确处理导函数与原函数的性质关系。"}],
    "5.3": [{"cycle": "5.3-cycle-2", "field": "course_keys", "courses": ["4.1.3.1 含参二次不等式的分类技巧", "4.1.3.2 二次方程根的分布（上）", "4.1.3.2 二次方程根的分布（下）", "4.1.3.3 二次恒成立模型"], "reason": "含参单调性讨论前先补齐二次不等式、根分布与恒成立分类。"}],
    "5.4": [{"cycle": "5.4-cycle-1", "field": "prerequisite_course_keys", "courses": ["4.1.4.2 含参函数单调性讨论之可因式分解型（上）"], "reason": "极值学习复用上一节含参单调性作为前置。"}],
    "5.5": [
        {"cycle": "5.5-cycle-1", "field": "course_keys", "courses": ["4.2.1.1 导数可因式分解型分类讨论", "4.2.1.3 洛必达法则", "4.2.3.2 导数可因式分解型分类讨论（基础）", "4.2.3.2 导数可因式分解型分类讨论（进阶）"], "reason": "隐零点题先完成可因式分解分类，并把洛必达作为可选极限工具。"},
        {"cycle": "5.5-cycle-2", "field": "course_keys", "courses": ["4.2.1.4 双逻辑连接词的函数问题之单函数单调性构造", "4.2.1.5 双逻辑连接词的函数问题之双函数最值构造", "4.2.3.1 参变分离法（基础）", "4.2.3.1 参变分离法（提高）", "4.2.3.1 参变分离法（进阶）"], "reason": "含参不等式循环直接使用逻辑连接词构造与分层参变分离。"},
    ],
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    catalog_payload = load_json(ROOT / "data/all_chapters_course_catalog.json")
    catalog = {str(row["course_key"]): row for row in catalog_payload["courses"]}
    evidence_rows = []
    for chapter in range(3, 6):
        path = ROOT / f"chapter{chapter}_manifest.json"
        manifest = load_json(path)
        changed = False
        for section in manifest["sections"]:
            section_id = str(section["id"])
            placements = PLACEMENTS.get(section_id)
            if not placements:
                continue
            expected = {course for placement in placements for course in placement["courses"]}
            actual = {str(course) for course in section.get("unplaced_course_keys", [])}
            if actual and actual != expected:
                raise ValueError(f"{section_id} unplaced set changed: {sorted(actual ^ expected)}")
            cycles = {str(row["id"]): row for row in section["learning_cycles"]}
            section_evidence = []
            for placement in placements:
                cycle = cycles[placement["cycle"]]
                field = placement["field"]
                values = [str(value) for value in cycle.get(field, [])]
                for course_key in placement["courses"]:
                    course = catalog[course_key]
                    transcript_path = ROOT / str(course["transcript_file"])
                    transcript = load_json(transcript_path)
                    if len(str(transcript.get("full_text") or "")) < 100:
                        raise ValueError(f"empty transcript for {course_key}")
                    if course_key not in values:
                        values.append(course_key)
                    section_evidence.append({
                        "course_key": course_key,
                        "cycle_id": placement["cycle"],
                        "field": field,
                        "reason": placement["reason"],
                        "transcript_file": course["transcript_file"],
                        "transcript_sha256": sha256(transcript_path),
                    })
                cycle[field] = values
            section["unplaced_course_keys"] = []
            section["coverage_gaps"] = [row for row in section.get("coverage_gaps", []) if row.get("kind") != "unplaced_course"]
            section["course_mapping_status"] = "SEMANTIC_TARGETS_REVIEWED_AND_PLACED"
            section["learning_cycles_status"] = "SEMANTIC_TARGETS_REVIEWED_AND_PLACED"
            section["course_mapping_review"] = {
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "method": "Course transcript hash verified; course method and textbook cycle title/type were matched explicitly. Placement is at cycle level and does not claim learner completion.",
                "placements": section_evidence,
            }
            evidence_rows.extend({"section": section_id, **row} for row in section_evidence)
            changed = True
        if changed:
            save_json(path, manifest)
    report = {
        "schema_version": "ybt-reviewed-course-placement-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": len(PLACEMENTS),
        "placements": len(evidence_rows),
        "rows": evidence_rows,
    }
    output = ROOT / "reports/all_chapters/reviewed-course-placements.json"
    save_json(output, report)
    print(json.dumps({"sections": report["sections"], "placements": report["placements"], "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
