#!/usr/bin/env python3
"""Merge the ten validated Luna section deliveries into book-order artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "reports" / "luna_dispatch"
SECTIONS_ROOT = ROOT / "reports" / "luna_sections"
PACKET_BUILD = ROOT / "reports" / "all_chapters" / "packet-build-current.json"
COURSE_CATALOG = ROOT / "data" / "all_chapters_course_catalog.json"
READY = DISPATCH / "READY.json"
ASSIGNMENTS = DISPATCH / "assignments.json"
OUTPUT_MD = DISPATCH / "learning_path_without_questions_all_chapters.md"
OUTPUT_HTML = DISPATCH / "learning_path_without_questions_all_chapters.html"
OUTPUT_JSON = DISPATCH / "full-book-merge.json"
OUTPUT_EVIDENCE = DISPATCH / "full-book-merge-evidence.md"

EXPECTED_TASKS = 10
EXPECTED_SECTIONS = 38
EXPECTED_ITEMS = 1209
EXPECTED_SIMULATION_PROTOCOL = "five-round-five-persona-v1"
EXPECTED_ATTEMPTS_PER_ITEM = 25
CHAPTER_TITLES = {
    1: "空间向量与立体几何",
    2: "直线与圆的方程",
    3: "圆锥曲线的方程与解析几何综合",
    4: "数列",
    5: "一元函数的导数及其应用",
}
SECTION_HEADING_RE = re.compile(r"^(#{1,2})\s+(.+?)\s*$")
ITEM_HEADING_RE = re.compile(r"^####\s+(.+?)\s*$")
LEAK_RE = re.compile(
    r"答案\s*[：:]|解法\s*[一二两三四五六七八九十百\d]+\s*[：:]|"
    r"解析\s*[：:]|解答\s*[：:]|最终答案|正确选项|故选\s*[A-D]"
)
INTERNAL_ID_RE = re.compile(r"(?:LI|Q):(?:LI:)?[0-9a-f]{8,}|Q-[0-9a-f]{8,}", re.I)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def section_folder(section: str) -> str:
    return section.replace("+", "_")


def item_display_label(item: dict[str, Any], question_labels: dict[str, str]) -> str:
    if item.get("kind") != "abc_exercise":
        return str(item.get("label") or "教材项目")
    key = str(item.get("item_key") or "")
    return question_labels.get(key, f"{item.get('label', '习题')}组第{item.get('ordinal', '?')}题")


def question_labels_for(section: str) -> dict[str, str]:
    packet = ROOT / "data" / "packets" / section_folder(section) / "student_packet.json"
    if not packet.is_file():
        return {}
    questions = load_json(packet).get("questions") or []
    labels: dict[str, str] = {}
    for question in questions:
        if not isinstance(question, dict):
            continue
        qid = str(question.get("qid") or "")
        group = str(question.get("group") or "")
        number = question.get("number")
        if qid and group and number is not None:
            labels[f"Q:{qid}"] = f"{group}组第{number}题"
    return labels


def validate_section_simulation(section: dict[str, Any]) -> dict[str, Any]:
    """Validate the complete five-round proxy simulation for one section."""
    section_id = str(section.get("section") or "")
    item_keys = {str(item.get("item_key") or "") for item in section.get("items") or []}
    if "" in item_keys:
        raise ValueError(f"{section_id}: empty canonical item key")
    simulation = section.get("simulation") or {}
    if simulation.get("protocol") != EXPECTED_SIMULATION_PROTOCOL:
        raise ValueError(f"{section_id}: simulation protocol mismatch")
    if simulation.get("status") != "passed":
        raise ValueError(f"{section_id}: simulation status is not passed")
    rounds = simulation.get("rounds") or []
    if len(rounds) != 5 or [item.get("round") for item in rounds] != [1, 2, 3, 4, 5]:
        raise ValueError(f"{section_id}: simulation must contain ordered rounds 1-5")
    for current_round in rounds:
        personas = current_round.get("personas") or []
        if len(personas) != 5 or len({str(item.get("persona_id")) for item in personas}) != 5:
            raise ValueError(f"{section_id}: round {current_round.get('round')} must contain five distinct personas")
        seen_persona_items: set[str] = set()
        for persona in personas:
            results = persona.get("item_results") or []
            keys = [str(item.get("item_key") or "") for item in results]
            if len(keys) != len(item_keys) or set(keys) != item_keys or len(set(keys)) != len(keys):
                raise ValueError(f"{section_id}: round {current_round.get('round')} item closure mismatch")
            seen_persona_items.update(keys)
        if seen_persona_items != item_keys:
            raise ValueError(f"{section_id}: round {current_round.get('round')} does not cover every item")

    actual_attempts = simulation.get("actual_attempts_per_item") or {}
    if set(str(key) for key in actual_attempts) != item_keys:
        raise ValueError(f"{section_id}: actual attempt ledger item closure mismatch")
    if any(value != EXPECTED_ATTEMPTS_PER_ITEM for value in actual_attempts.values()):
        raise ValueError(f"{section_id}: an item does not have {EXPECTED_ATTEMPTS_PER_ITEM} attempts")
    if simulation.get("expected_attempts_per_item") != EXPECTED_ATTEMPTS_PER_ITEM:
        raise ValueError(f"{section_id}: expected attempt count mismatch")
    if simulation.get("unresolved_item_keys"):
        raise ValueError(f"{section_id}: unresolved simulation items remain")

    final_round = rounds[-1]
    if final_round.get("failed_item_keys"):
        raise ValueError(f"{section_id}: final proxy round still has failed items")
    for persona in final_round.get("personas") or []:
        for result in persona.get("item_results") or []:
            if result.get("verdict") != "passed" or any(
                result.get(field) is not True
                for field in ("recognized_method", "first_line_written", "continuation_complete", "self_check_complete")
            ):
                raise ValueError(f"{section_id}: final proxy round item did not pass")
    final_route_hash = str(section.get("final_route_hash") or "")
    if not final_route_hash or final_round.get("route_hash") != final_route_hash:
        raise ValueError(f"{section_id}: final route hash is not bound to round 5")
    return {
        "section": section_id,
        "protocol": EXPECTED_SIMULATION_PROTOCOL,
        "rounds": len(rounds),
        "personas_per_round": 5,
        "items": len(item_keys),
        "attempts_per_item": EXPECTED_ATTEMPTS_PER_ITEM,
        "attempts": len(item_keys) * EXPECTED_ATTEMPTS_PER_ITEM,
        "final_route_hash": final_route_hash,
        "status": "passed",
    }


def course_display_map() -> dict[str, str]:
    catalog = load_json(COURSE_CATALOG)
    display: dict[str, str] = {}
    for course in catalog.get("courses") or []:
        if not isinstance(course, dict):
            continue
        key = str(course.get("course_key") or "")
        if not key:
            continue
        title = str(course.get("title") or key)
        video = Path(str(course.get("video_file") or "")).name
        display[key] = f"{title}（视频：{video}）" if video else title
    return display


def replace_course_tokens(text: str, display: dict[str, str]) -> str:
    for key in sorted(display, key=len, reverse=True):
        text = text.replace(key, display[key])
    return text


def section_blocks(markdown: str, expected_count: int) -> list[list[str]]:
    lines = markdown.splitlines()
    headings: list[int] = []
    for index, line in enumerate(lines):
        match = SECTION_HEADING_RE.match(line)
        if index == 0:
            continue
        if match and not match.group(2).strip().startswith(("循环", "一眼总览", "完成门")):
            headings.append(index)
    if len(headings) < expected_count:
        raise ValueError(f"markdown section count {len(headings)} < {expected_count}")
    blocks: list[list[str]] = []
    for position, start in enumerate(headings[:expected_count]):
        end = headings[position + 1] if position + 1 < len(headings) else len(lines)
        blocks.append(lines[start:end])
    return blocks


def renumber_section_block(
    block: list[str], section: dict[str, Any], label: str, course_display: dict[str, str]
) -> list[str]:
    lines = list(block)
    original_heading = SECTION_HEADING_RE.match(lines[0])
    if original_heading and len(original_heading.group(1)) == 1:
        for index in range(1, len(lines)):
            if lines[index].startswith("#"):
                lines[index] = "#" + lines[index]
    lines[0] = f"## {label}"
    item_indexes = [index for index, line in enumerate(lines) if ITEM_HEADING_RE.match(line)]
    items = section.get("items") or []
    if len(item_indexes) != len(items):
        raise ValueError(
            f"{section.get('section')}: markdown items {len(item_indexes)} != delivery items {len(items)}"
        )
    question_labels = question_labels_for(str(section["section"]))
    for index, item_index in enumerate(item_indexes):
        item = items[index]
        display = item_display_label(item, question_labels)
        position = str(item.get("position") or "学习项目")
        lines[item_index] = f"#### {display}｜{position}"
    lines = [replace_course_tokens(line, course_display) for line in lines]
    return lines


def markdown_table_of_contents(rows: list[dict[str, Any]], course_display: dict[str, str]) -> list[str]:
    lines = [
        "# 一本通全书学习路径（无题面答案版）",
        "",
        "本路线按教材真实章节顺序组织。每个项目只保留听课入口、识别方法、首行模板、继续动作、卡点、纠错和自检，不复制题面、解答或结论。",
        "",
        "## 总览",
        "",
        f"- 覆盖范围：5 章、{len(rows)} 节、{EXPECTED_ITEMS} 个编号学习项目。",
        "- 固定顺序：知识点 → 右侧例题 → 直属变式 → 类型题 → A/B/C。",
        "- 模拟状态：每节 5 轮 × 5 种零基础人格，每题 25 次代理尝试；真人学习与 24 小时冷复测保持 `not_run`。",
        "",
        "### 全局首次听课顺序",
        "",
    ]
    seen_courses: set[str] = set()
    course_number = 0
    for row in rows:
        for course in row["course_calls"]:
            if course in seen_courses:
                continue
            seen_courses.add(course)
            course_number += 1
            lines.append(f"{course_number}. {course_display.get(course, course)}")
    lines.extend(["", "### 按教材顺序执行", ""])
    current_chapter: int | None = None
    for row in rows:
        chapter = int(row["chapter"])
        if chapter != current_chapter:
            current_chapter = chapter
            lines.extend([f"#### 第{chapter}章 {CHAPTER_TITLES.get(chapter, '数学内容')}", ""])
        overview = row["overview"]
        new_courses = row["section_new_courses"]
        learned_courses = row["section_other_courses"]
        lines.append(f"##### {row['label']}")
        first_course = str(overview.get("first_course") or "")
        lines.append(f"- 首先听：{course_display.get(first_course, first_course) or '按本节第一个循环的课程调用开始'}")
        lines.append(
            "- 本节首次引入："
            + ("；".join(course_display.get(course, course) for course in new_courses) if new_courses else "无，沿用已学课程")
        )
        lines.append(
            "- 本节还会调用："
            + ("；".join(course_display.get(course, course) for course in learned_courses) if learned_courses else "无")
        )
        labels = [item_display_label(item, row["question_labels"]) for item in row["delivery_section"]["items"]]
        lines.append(f"- 教材项目顺序（{len(labels)} 项）：" + "、".join(labels))
        coverage = row["delivery_section"]["coverage"]
        items = row["delivery_section"].get("items") or []
        worked_examples = sum(item.get("kind") == "worked_example" for item in items)
        direct_variants = sum(item.get("kind") == "direct_variant" for item in items)
        abc_exercises = sum(item.get("kind") == "abc_exercise" for item in items)
        lines.append(
            f"- 覆盖核对：例题 {worked_examples}，直属变式 {direct_variants}，A/B/C {abc_exercises}，合计 {coverage['delivered_items']}。"
        )
        lines.append("")
    return lines


def main() -> int:
    assignments = load_json(ASSIGNMENTS)
    ready = load_json(READY)
    packet_build = load_json(PACKET_BUILD)
    course_display = course_display_map()
    tasks = assignments.get("tasks") or []
    if len(tasks) != EXPECTED_TASKS or ready.get("status") != "ready":
        raise ValueError("dispatch is not ready for full-book merge")

    task_rows: dict[str, dict[str, Any]] = {}
    all_items: dict[str, str] = {}
    simulation_rows: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task["task_id"])
        delivery_path = SECTIONS_ROOT / task_id / "delivery.json"
        if not delivery_path.is_file():
            raise FileNotFoundError(delivery_path)
        delivery = load_json(delivery_path)
        if delivery.get("status") != "passed":
            raise ValueError(f"{task_id} is not passed")
        if delivery.get("proxy_simulation") != "passed":
            raise ValueError(f"{task_id} proxy simulation is not passed")
        for section in delivery.get("sections") or []:
            section_id = str(section["section"])
            if section_id in task_rows:
                raise ValueError(f"duplicate delivery section: {section_id}")
            for item in section.get("items") or []:
                key = str(item.get("item_key") or "")
                if not key or key in all_items:
                    raise ValueError(f"duplicate or empty item key: {key}")
                all_items[key] = section_id
            simulation_rows.append(validate_section_simulation(section))
            task_rows[section_id] = {
                "task_id": task_id,
                "delivery": delivery,
                "delivery_section": section,
                "markdown": (SECTIONS_ROOT / task_id / "learning_path_without_questions.md").read_text(encoding="utf-8-sig"),
            }

    source_rows = packet_build.get("sections") or []
    if len(source_rows) != EXPECTED_SECTIONS or len(task_rows) != EXPECTED_SECTIONS:
        raise ValueError(f"section count mismatch: source={len(source_rows)} delivered={len(task_rows)}")
    if len(all_items) != EXPECTED_ITEMS:
        raise ValueError(f"item count mismatch: {len(all_items)}")
    if len(simulation_rows) != EXPECTED_SECTIONS:
        raise ValueError(f"simulation section count mismatch: {len(simulation_rows)}")
    if sum(item["items"] for item in simulation_rows) != EXPECTED_ITEMS:
        raise ValueError("simulation item count does not match the canonical book total")

    ordered_rows: list[dict[str, Any]] = []
    global_course_seen: set[str] = set()
    for source in source_rows:
        section_id = str(source["section"])
        task_row = task_rows.get(section_id)
        if task_row is None:
            raise ValueError(f"missing source section delivery: {section_id}")
        delivery_section = task_row["delivery_section"]
        delivery = task_row["delivery"]
        overview = delivery_section.get("overview") or {}
        calls = list(dict.fromkeys(
            [str(overview.get("first_course") or "")]
            + [str(value) for value in overview.get("new_courses_in_section_order") or []]
            + [str(value) for value in overview.get("already_learned_dependencies") or []]
        ))
        calls = [value for value in calls if value]
        section_new: list[str] = []
        for course in calls:
            if course not in global_course_seen:
                global_course_seen.add(course)
                section_new.append(course)
        section_other = [course for course in calls if course not in section_new]
        question_labels = question_labels_for(section_id)
        ordered_rows.append({
            "section": section_id,
            "chapter": int(source["chapter"]),
            "label": str(source["label"]),
            "task_id": task_row["task_id"],
            "overview": overview,
            "delivery": delivery,
            "delivery_section": delivery_section,
            "markdown": task_row["markdown"],
            "course_calls": calls,
            "section_new_courses": section_new,
            "section_other_courses": section_other,
            "question_labels": question_labels,
        })

    output_lines = markdown_table_of_contents(ordered_rows, course_display)
    output_lines.extend(["## 详细学习路径", ""])
    for row in ordered_rows:
        blocks = section_blocks(row["markdown"], len(row["delivery"]["sections"]))
        section_index = next(
            index for index, item in enumerate(row["delivery"]["sections"])
            if str(item["section"]) == row["section"]
        )
        output_lines.extend(
            renumber_section_block(
                blocks[section_index], row["delivery_section"], row["label"], course_display
            )
        )
        output_lines.extend(["", "---", ""])

    output_lines.extend([
        "## 全书验收状态",
        "",
        f"- 分节交付：{EXPECTED_SECTIONS}/{EXPECTED_SECTIONS}，全部 validator `passed`。",
        f"- 编号学习项目：{len(all_items)}/{EXPECTED_ITEMS}，无重复、无缺失、无越界。",
        "- 代理模拟：每节 5 轮 × 5 人格；真人学习、独立真人验收与 24 小时冷复测仍为 `not_run`。",
        "- 源状态：READY、packet-build、课程目录、视觉侧车和分节源绑定均以当前哈希为准。",
        "",
    ])
    merged_markdown = "\n".join(output_lines)
    # Repair the two source-derived missing inline delimiters without changing the source packet.
    merged_markdown = merged_markdown.replace(r"\(k=f'(x_0))", r"\(k=f'(x_0)\)")
    if LEAK_RE.search(merged_markdown) or INTERNAL_ID_RE.search(merged_markdown):
        raise ValueError("learner-facing merged Markdown contains answer or internal-id marker")
    if merged_markdown.count("\\(") != merged_markdown.count("\\)"):
        raise ValueError("unbalanced inline LaTeX delimiters")
    if merged_markdown.count("\\[") != merged_markdown.count("\\]"):
        raise ValueError("unbalanced display LaTeX delimiters")
    OUTPUT_MD.write_text(merged_markdown + "\n", encoding="utf-8", newline="\n")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.export_learning_preview_html import export_preview

    export_preview(OUTPUT_MD, OUTPUT_HTML)
    html_text = OUTPUT_HTML.read_text(encoding="utf-8")
    if '<meta charset="utf-8">' not in html_text or '<meta name="viewport"' not in html_text:
        raise ValueError("merged HTML missing charset or viewport")
    if LEAK_RE.search(html_text) or INTERNAL_ID_RE.search(html_text):
        raise ValueError("learner-facing merged HTML contains answer or internal-id marker")

    payload = {
        "schema_version": "ybt-luna-full-book-merge-v1",
        "status": "passed",
        "chapters": 5,
        "sections": EXPECTED_SECTIONS,
        "items": EXPECTED_ITEMS,
        "task_count": EXPECTED_TASKS,
        "task_ids": sorted({task_rows[section]["task_id"] for section in task_rows}),
        "ready_sha256": sha256(READY),
        "packet_build_sha256": sha256(PACKET_BUILD),
        "course_catalog_sha256": sha256(COURSE_CATALOG),
        "markdown_sha256": sha256(OUTPUT_MD),
        "html_sha256": sha256(OUTPUT_HTML),
        "source_order": [row["section"] for row in ordered_rows],
        "proxy_simulation": {
            "status": "passed",
            "protocol": EXPECTED_SIMULATION_PROTOCOL,
            "sections": len(simulation_rows),
            "items": sum(item["items"] for item in simulation_rows),
            "rounds": 5,
            "personas_per_round": 5,
            "attempts_per_item": EXPECTED_ATTEMPTS_PER_ITEM,
            "attempts": sum(item["attempts"] for item in simulation_rows),
            "section_rows": simulation_rows,
        },
        "human_acceptance": "not_run",
        "cold_24h_retest": "not_run",
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evidence = [
        "# 全书合并证据",
        "",
        f"- 状态：`{payload['status']}`",
        f"- 分节任务：{EXPECTED_TASKS}/{EXPECTED_TASKS}，分节：{EXPECTED_SECTIONS}/{EXPECTED_SECTIONS}。",
        f"- 编号学习项目：{EXPECTED_ITEMS}/{EXPECTED_ITEMS}。",
        f"- READY SHA256：`{payload['ready_sha256']}`",
        f"- packet-build SHA256：`{payload['packet_build_sha256']}`",
        f"- 课程目录 SHA256：`{payload['course_catalog_sha256']}`",
        f"- Markdown SHA256：`{payload['markdown_sha256']}`",
        f"- HTML SHA256：`{payload['html_sha256']}`",
        "- 分节 validator：10/10 `passed`，无重复、缺失或越界项目。",
        f"- 代理模拟：{len(simulation_rows)}/{EXPECTED_SECTIONS} 节、{sum(item['items'] for item in simulation_rows)}/{EXPECTED_ITEMS} 项、{sum(item['attempts'] for item in simulation_rows)} 次当前源尝试；协议 `five-round-five-persona-v1`，第 5 轮全部通过。",
        "- learner-facing 答案与内部 ID 扫描：`passed`。",
        "- UTF-8、MathJax 分隔符、HTML charset/viewport：`passed`。",
        "- 真人学习、独立真人验收、24 小时冷复测：`not_run`。",
    ]
    OUTPUT_EVIDENCE.write_text("\n".join(evidence) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
