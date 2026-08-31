#!/usr/bin/env python3
"""Generate compact, answer-free learner routes for all textbook sections."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def all_sections() -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    for chapter in range(1, 6):
        manifest = load_json(ROOT / f"chapter{chapter}_manifest.json")
        rows.extend((chapter, section) for section in manifest.get("sections", []))
    return rows


def course_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    course_id = str(row.get("course_id") or "")
    match = re.match(r"^(\d+(?:\.\d+)+)(?:\.([a-z]))?$", course_id, re.I)
    if not match:
        return (9999, str(row.get("title") or row.get("course_key") or ""))
    parts = tuple(int(value) for value in match.group(1).split("."))
    suffix = ord(match.group(2).lower()) - 96 if match.group(2) else 0
    return (*parts, suffix, str(row.get("title") or ""))


def guidance(title: str) -> tuple[str, str, str, str]:
    rules = (
        (("导数", "切线"), "先判断目标是瞬时变化率、切线斜率还是导函数。", "第一行写导数定义、求导公式或切点条件。", "按求导、符号判断、区间或极值条件继续。", "检查定义域、不可导点、端点和等号条件。"),
        (("求和不等式",), "先找能由函数或导数推出的单项不等式，再决定逐项相加还是构造可相消的比较项。", "第一行把待证和式写成通项，并写出希望建立的逐项比较。", "由前问或构造函数证明单项不等式，再按相同下标范围累加。", "检查不等号方向、严格性、起止下标和累加后的端项。"),
        (("等差",), "先找首项、公差、通项或前 n 项和之间的关系。", "第一行设首项和公差，写通项或求和公式。", "把已知下标条件化为方程后消元。", "检查下标、项数和公差为零的情形。"),
        (("等比",), "先找首项、公比，并判断公比是否允许为 0 或 1。", "第一行设首项和公比，写通项或求和公式。", "按下标条件列式，必要时分类讨论。", "检查公比、项数、分母和符号。"),
        (("数列",), "先识别递推、通项、求和、周期还是数列单调性模型。", "第一行写目标量和相邻项、通项或前 n 项和关系。", "选择作差、作商、累加、累乘、错位相减、裂项或分组继续。", "检查首项、正负、公比、下标范围和边界项。"),
        (("单调",), "先把单调性转成导数符号与区间问题。", "第一行写定义域并求导。", "解导数不等式，按分界点列区间。", "检查端点、空区间和导数为零处。"),
        (("极值", "最大", "最小"), "先区分极值、最值和参数成立条件。", "第一行写定义域并求导，列出临界点。", "用符号变化或端点比较完成判断。", "检查极值点左右符号、端点和参数范围。"),
        (("归纳",), "先分清归纳起点和由 k 到 k+1 的递推目标。", "第一行验证起始值，再假设 n=k 成立。", "只使用归纳假设推到 n=k+1。", "检查起点、使用假设的位置和结论范围。"),
        (("椭圆", "双曲线", "抛物线", "圆锥曲线"), "先由焦点、准线、离心率或几何性质识别曲线与方向。", "第一行写标准方程及参数关系。", "把点、弦、切线或焦点条件代入，再消元。", "检查焦点轴、参数正值、判别式和根的几何意义。"),
        (("圆",), "先识别圆心半径、弦、切线或两圆位置关系。", "第一行把圆化为标准式并写圆心、半径。", "再用距离、垂径、切线或根轴关系。", "检查半径为正、位置关系和切点条件。"),
        (("斜率", "倾斜角"), "先判断斜率是否存在，再连接倾斜角、方向向量和两点式。", "第一行写斜率定义或两点斜率公式。", "再处理平行、垂直、范围或图形判定。", "检查竖直线、角度范围、分母和方向。"),
        (("直线", "距离", "对称"), "先确认题目需要哪种直线方程、位置关系或距离。", "第一行选合适的直线形式并标明参数条件。", "联立、代入距离公式或用中点垂直关系继续。", "检查斜率不存在、系数同倍和距离绝对值。"),
        (("向量", "共线", "共面", "数量积", "二面角"), "先把几何关系翻译成向量的线性表示、数量积或法向量。", "第一行选基底、方向向量或法向量并写目标关系。", "统一起点后比较系数，或按数量积/坐标逐项计算。", "检查方向、非零条件、系数和及锐钝角。"),
    )
    for tokens, recognition, first_line, continuation, self_check in rules:
        if any(token in title for token in tokens):
            return recognition, first_line, continuation, self_check
    return (
        "先说出题型名称、已知量和目标量，再选择对应定义或公式。",
        "第一行写清已知、目标和准备使用的关系式。",
        "逐步代入、变形并在结尾回到题目要求。",
        "检查使用条件、定义域、符号和结论是否完整。",
    )


def render_section(
    chapter: int,
    section: dict[str, Any],
    packet: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> str:
    section_id = str(section["id"])
    cycles = packet.get("learning_cycles") or []
    if packet.get("status") != "VERIFIED" or not cycles:
        raise ValueError(f"section is not route-ready: {section_id}")
    knowledge = {str(row.get("id")): row for row in section.get("knowledge_points", [])}
    counts = packet.get("counts") or {}
    used_courses = list(dict.fromkeys(
        str(key)
        for cycle in cycles
        for field in ("course_keys", "prerequisite_course_keys", "optional_course_keys")
        for key in cycle.get(field, [])
    ))
    missing_courses = [key for key in used_courses if key not in catalog]
    if missing_courses:
        raise ValueError(f"{section_id} missing courses: {missing_courses}")
    ordered_courses = sorted((catalog[key] for key in used_courses), key=course_sort_key)

    lines = [
        f"# 第{chapter}章 · {section.get('label', section_id)}",
        "",
        "> 当天目标：完成本节当前可执行的全部循环；卡住时停在第一处断点，不提前看答案或跳循环。",
        "> 状态区分：课程覆盖不等于已经听完；模拟通过不等于真实用户通过；24 小时复测单独记录。",
        "> 执行方式：结合课程顺序完成对应教材项目；语音中的选项、上下标或符号有歧义时先确认再判错。",
        "",
        "## 一眼总览",
        "",
        "| 循环 | 课程 | 例题 | 直属变式 | A/B/C |",
        "|---:|---:|---:|---:|---:|",
        f"| {len(cycles)} | {len(ordered_courses)} | {counts.get('worked_examples', 0)} | {counts.get('direct_variants', 0)} | {counts.get('abc_exercises', 0)} |",
        "",
        "## 本节课程顺序",
        "",
    ]
    if ordered_courses:
        for index, course in enumerate(ordered_courses, start=1):
            lines.append(f"{index}. `{course.get('course_id')}` {course.get('title')}")
    else:
        lines.append("- 本节不新增独立课程，复用前置课程。")

    seen_items: set[str] = set()
    rendered_count = 0
    for index, cycle in enumerate(cycles, start=1):
        title = str(cycle.get("title") or f"循环{index}")
        recognition, first_line, continuation, self_check = guidance(title + " " + " ".join(cycle.get("type_refs", [])))
        new_courses = [catalog[str(key)] for key in cycle.get("course_keys", [])]
        prerequisite_courses = [catalog[str(key)] for key in cycle.get("prerequisite_course_keys", [])]
        knowledge_labels = [
            str((knowledge.get(str(ref)) or {}).get("label") or ref)
            for ref in cycle.get("knowledge_refs", [])
        ]
        type_labels = [str(value) for value in cycle.get("type_refs", [])]
        examples = cycle.get("worked_examples", [])
        variants = cycle.get("direct_variants", [])
        exercises = cycle.get("exercise_questions", [])
        for item in [*examples, *variants, *exercises]:
            item_key = str(item.get("item_id") or item.get("qid") or "")
            if not item_key or item_key in seen_items:
                raise ValueError(f"{section_id} duplicate or missing item identity in {cycle.get('cycle_id')}")
            seen_items.add(item_key)
            rendered_count += 1

        lines.extend(["", "---", "", f"## 循环 {index} · {title}", ""])
        lines.append("### 先听")
        if new_courses:
            for course in sorted(new_courses, key=course_sort_key):
                lines.append(f"- `{course.get('course_id')}` {course.get('title')}")
        else:
            lines.append("- 本循环无新增课程，直接复用已学方法。")
        if prerequisite_courses:
            lines.append("- 前置复习：" + "；".join(f"`{row.get('course_id')}` {row.get('title')}" for row in sorted(prerequisite_courses, key=course_sort_key)))

        lines.extend(["", "### 再做", ""])
        if knowledge_labels:
            lines.append("- 知识点及右侧例题：" + "；".join(knowledge_labels))
        if type_labels:
            lines.append("- 类型题：" + "；".join(type_labels))
        if examples:
            lines.append("- 例题：" + "、".join(str(row.get("label") or f"例{row.get('example_number')}") for row in examples))
        if variants:
            lines.append("- 直属变式：" + "、".join(
                f"例{row.get('parent_example_number')} {row.get('label')}" for row in variants
            ))
        if exercises:
            lines.append("- 强化训练：" + "、".join(f"{row.get('group')}{row.get('number')}" for row in exercises))
        if not any((knowledge_labels, type_labels, examples, variants, exercises)):
            lines.append("- 本循环只做方法检查，不新增教材题号。")

        lines.extend([
            "",
            "### 卡住时怎么写",
            "",
            f"- 识别入口：{recognition}",
            f"- 第一行：{first_line}",
            f"- 继续步骤：{continuation}",
            f"- 自检：{self_check}",
            "",
            "### 通过门",
            "",
            "- [ ] 指定课程已确认听完。",
            "- [ ] 例题方法能闭卷复述，变式和强化题独立完成。",
            "- [ ] 使用过提示的题已安排未见迁移或延迟复测。",
            "- [ ] 没有未确认的语音识别错误或题面歧义。",
        ])

    expected = int(counts.get("total_numbered_learning_items", 0))
    if rendered_count != expected:
        raise ValueError(f"{section_id} item coverage mismatch: {rendered_count}/{expected}")
    lines.extend([
        "",
        "---",
        "",
        "## 本节完成",
        "",
        f"- [ ] {expected} 个教材项目均有真实作答或明确延后记录。",
        "- [ ] 必听课程无遗漏；支持课程只在对应题型首次出现时调用。",
        "- [ ] 真实用户状态、内部模拟状态和 24 小时复测没有混写。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section")
    parser.add_argument("--skip-html", action="store_true")
    args = parser.parse_args()
    catalog_payload = load_json(ROOT / "data/all_chapters_course_catalog.json")
    catalog = {str(row["course_key"]): row for row in catalog_payload.get("courses", [])}
    selected = [row for row in all_sections() if not args.section or str(row[1]["id"]) == args.section]
    if not selected:
        raise SystemExit(f"section not found: {args.section}")
    outputs = []
    for chapter, section in selected:
        section_id = str(section["id"])
        folder = ROOT / "data/packets" / section_folder(section_id)
        packet = load_json(folder / "learning_packet.json")
        markdown = folder / "learning_path_without_questions.md"
        markdown.write_text(render_section(chapter, section, packet, catalog), encoding="utf-8")
        if not args.skip_html:
            subprocess.run([sys.executable, str(ROOT / "scripts/export_learning_preview_html.py"), "--section", section_id], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        outputs.append({"chapter": chapter, "section": section_id, "cycles": len(packet.get("learning_cycles", [])), "items": packet.get("counts", {}).get("total_numbered_learning_items"), "markdown": markdown.relative_to(ROOT).as_posix()})
    summary = {"sections": len(outputs), "items": sum(int(row["items"] or 0) for row in outputs), "outputs": outputs}
    report = ROOT / "reports/all_chapters/route-export-current.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
