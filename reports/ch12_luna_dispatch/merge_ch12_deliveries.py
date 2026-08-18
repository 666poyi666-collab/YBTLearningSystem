#!/usr/bin/env python3
"""Merge validated chapter 1-2 deliveries in textbook order."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DISPATCH = ROOT / "reports" / "ch12_luna_dispatch"
ASSIGNMENT_PATH = DISPATCH / "assignments.json"
SECTIONS_ROOT = ROOT / "reports" / "ch12_luna_sections"
CATALOG_PATH = ROOT / "data" / "all_chapters_course_catalog.json"
VALIDATOR_PATH = Path(r"C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py")
OUTPUT_MD = DISPATCH / "learning_path_without_questions_chapters_1_2.md"
OUTPUT_HTML = DISPATCH / "learning_path_without_questions_chapters_1_2.html"
OUTPUT_JSON = DISPATCH / "acceptance_chapters_1_2.json"

SECTION_TITLES = {
    "1.1": "第1节 空间向量及其运算",
    "1.2+1.3": "第2节 空间向量基本定理与坐标表示",
    "1.4": "第3节 空间向量的应用",
    "micro专题1": "微专题1 立体几何综合题",
    "2.1": "第1节 直线的倾斜角与斜率",
    "2.2": "第2节 直线的方程",
    "2.3": "第3节 交点坐标与距离公式",
    "2.4": "第4节 直线有关的对称问题",
    "2.5": "第5节 圆的方程",
    "2.6": "第6节 直线与圆的位置关系",
    "2.7": "第7节 圆与圆的位置关系",
}

SECTION_TAB_TITLES = {
    "1.1": "第1节 向量及其运算",
    "1.2+1.3": "第2节 基本定理与坐标",
    "1.4": "第3节 空间向量应用",
    "micro专题1": "微专题 立体几何",
    "2.1": "第1节 倾斜角与斜率",
    "2.2": "第2节 直线方程",
    "2.3": "第3节 交点与距离",
    "2.4": "第4节 对称问题",
    "2.5": "第5节 圆的方程",
    "2.6": "第6节 直线与圆",
    "2.7": "第7节 圆与圆",
}


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_validator():
    spec = importlib.util.spec_from_file_location("ybt_validator_v2", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shift_headings(lines: list[str], amount: int = 2) -> list[str]:
    result = []
    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not match:
            result.append(line)
            continue
        level = min(6, len(match.group(1)) + amount)
        result.append("#" * level + " " + match.group(2))
    return result


def strip_leading_title(text: str) -> list[str]:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines.pop(0)
    return lines


def section_title(section: str, row: dict) -> str:
    return SECTION_TITLES.get(section) or str(row.get("label") or section)


def render_table_cell(value: str) -> str:
    rendered = escape(value.strip(), quote=False)
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    return rendered


def convert_markdown_tables(text: str) -> str:
    lines = text.splitlines()
    result: list[str] = []
    index = 0
    separator_cell = re.compile(r"^:?-{3,}:?$")
    while index < len(lines):
        header_line = lines[index].strip()
        if index + 1 >= len(lines) or not header_line.startswith("|"):
            result.append(lines[index])
            index += 1
            continue
        separator_line = lines[index + 1].strip()
        header = [cell.strip() for cell in header_line.strip("|").split("|")]
        separators = [cell.strip() for cell in separator_line.strip("|").split("|")]
        if len(header) != len(separators) or not separators or not all(
            separator_cell.fullmatch(cell) for cell in separators
        ):
            result.append(lines[index])
            index += 1
            continue
        rows: list[list[str]] = []
        cursor = index + 2
        while cursor < len(lines):
            row_line = lines[cursor].strip()
            if not row_line.startswith("|"):
                break
            cells = [cell.strip() for cell in row_line.strip("|").split("|")]
            if len(cells) != len(header):
                break
            rows.append(cells)
            cursor += 1
        table = ["<table><thead><tr>"]
        table.extend(f"<th>{render_table_cell(cell)}</th>" for cell in header)
        table.append("</tr></thead><tbody>")
        for row in rows:
            table.append("<tr>")
            table.extend(f"<td>{render_table_cell(cell)}</td>" for cell in row)
            table.append("</tr>")
        table.append("</tbody></table>")
        result.append("".join(table))
        index = cursor
    return "\n".join(result)


def split_task_markdown(task: dict, delivery: dict) -> dict[str, str]:
    source = (SECTIONS_ROOT / task["task_id"] / "learning_path_without_questions.md").read_text(
        encoding="utf-8-sig"
    )
    sections = [str(value) for value in task["sections"]]
    labels = {
        str(row["section"]): section_title(str(row["section"]), row)
        for row in delivery["sections"]
    }
    if len(sections) == 1:
        section = sections[0]
        body = shift_headings(strip_leading_title(source), 2)
        return {section: f"### {labels[section]}\n\n" + "\n".join(body).strip() + "\n"}

    lines = source.splitlines()
    starts: dict[str, int] = {}
    for index, line in enumerate(lines):
        for section in sections:
            if re.match(rf"^##\s+{re.escape(section)}(?:\s|$)", line):
                starts[section] = index
    if set(starts) != set(sections):
        raise ValueError(f"cannot split multi-section Markdown for {task['task_id']}: {starts}")
    ordered = sorted(((index, section) for section, index in starts.items()))
    result: dict[str, str] = {}
    for position, (start, section) in enumerate(ordered):
        end = ordered[position + 1][0] if position + 1 < len(ordered) else len(lines)
        body = lines[start + 1 : end]
        while body and not body[0].strip():
            body.pop(0)
        body = shift_headings(body, 2)
        result[section] = f"### {labels[section]}\n\n" + "\n".join(body).strip() + "\n"
    return result


def inject_reader_layout(
    html_text: str,
    target_sections: list[str],
    section_by_id: dict[str, dict],
    catalog_by_key: dict[str, dict],
) -> str:
    marker = "<!-- ch12-section-reader -->"
    if marker in html_text:
        return html_text

    overview_start = html_text.find("<h2>总览</h2>")
    chapter_one_heading = "<h2>第1章 空间向量与立体几何</h2>"
    chapter_two_heading = "<h2>第2章 直线与圆的方程</h2>"
    chapter_one_start = html_text.find(chapter_one_heading)
    main_end = html_text.find("</main>")
    if min(overview_start, chapter_one_start, main_end) < 0:
        raise ValueError("cannot locate reader layout boundaries")

    section_positions: list[tuple[int, str, str]] = []
    for section in target_sections:
        row = section_by_id[section]
        title_candidates = [section_title(section, row), str(row.get("label") or section)]
        rendered_heading = ""
        position = -1
        for title in dict.fromkeys(title_candidates):
            candidate = f"<h3>{escape(title, quote=False)}</h3>"
            candidate_position = html_text.find(candidate, chapter_one_start)
            if candidate_position >= 0:
                rendered_heading = candidate
                position = candidate_position
                break
        if position < 0:
            raise ValueError(f"cannot locate rendered section heading: {section} {title_candidates}")
        section_positions.append((position, section, rendered_heading))
    if section_positions != sorted(section_positions):
        raise ValueError("rendered section order differs from assignment")

    nav_rows = []
    mobile_groups = []
    for chapter, chapter_sections in ((1, target_sections[:4]), (2, target_sections[4:])):
        buttons = []
        options = []
        for section in chapter_sections:
            index = target_sections.index(section) + 1
            target = f"section-{index}"
            buttons.append(
                f'<button type="button" class="reader-tab" data-reader-target="{target}" '
                f'aria-controls="{target}" aria-selected="false">'
                f'{escape(SECTION_TAB_TITLES[section])}</button>'
            )
            options.append(
                f'<option value="{target}">{escape(SECTION_TAB_TITLES[section])}</option>'
            )
        nav_rows.append(
            f'<div class="reader-nav-row"><span class="reader-chapter-label">第{chapter}章</span>'
            f'<div class="reader-tabs">{"".join(buttons)}</div></div>'
        )
        mobile_groups.append(f'<optgroup label="第{chapter}章">{"".join(options)}</optgroup>')
    nav_html = (
        marker
        + '<nav class="reader-nav" aria-label="章节与小节导航">'
        + '<div class="reader-nav-primary">'
        + '<button type="button" class="reader-tab reader-tab-overview is-active" '
        + 'data-reader-target="reader-overview" aria-controls="reader-overview" '
        + 'aria-selected="true">总览</button>'
        + '<span class="reader-current" aria-live="polite">当前：<strong id="reader-current-label">总览</strong></span>'
        + "</div>"
        + '<select class="reader-mobile-select" aria-label="选择小节">'
        + '<option value="reader-overview">总览</option>'
        + "".join(mobile_groups)
        + "</select>"
        + "".join(nav_rows)
        + "</nav>"
    )

    overview_html = html_text[overview_start:chapter_one_start]
    rebuilt = [
        html_text[:overview_start],
        nav_html,
        '<section class="reader-panel overview-panel is-active" id="reader-overview" '
        'data-reader-label="总览">',
        overview_html,
        "</section>",
    ]
    for index, (start, section, rendered_heading) in enumerate(section_positions):
        end = section_positions[index + 1][0] if index + 1 < len(section_positions) else main_end
        panel_html = html_text[start:end]
        panel_html = panel_html.replace(chapter_one_heading, "").replace(chapter_two_heading, "")
        row = section_by_id[section]
        first_key = str(row.get("overview", {}).get("first_course") or "")
        first_course = catalog_by_key.get(first_key, {}).get("title") or first_key or "按本节课程表"
        chapter = 1 if index < 4 else 2
        metadata = (
            '<div class="section-meta" aria-label="本节概况">'
            f'<span>第{chapter}章</span><span>{row["coverage"]["delivered_items"]} 项</span>'
            f'<span>首课：{escape(str(first_course))}</span><span>代理模拟已通过</span>'
            "</div>"
        )
        panel_html = panel_html.replace(rendered_heading, rendered_heading + metadata, 1)
        previous_target = "reader-overview" if index == 0 else f"section-{index}"
        previous_label = "返回总览" if index == 0 else "上一节"
        next_target = "reader-overview" if index == len(section_positions) - 1 else f"section-{index + 2}"
        next_label = "回到总览" if index == len(section_positions) - 1 else "下一节"
        pager = (
            '<nav class="section-pager" aria-label="小节翻页">'
            f'<button type="button" data-reader-target="{previous_target}">← {previous_label}</button>'
            f'<span>{index + 1} / {len(section_positions)}</span>'
            f'<button type="button" data-reader-target="{next_target}">{next_label} →</button>'
            "</nav>"
        )
        rebuilt.extend(
            [
                f'<section class="reader-panel section-panel" id="section-{index + 1}" '
                f'data-reader-label="{escape(section_title(section, row), quote=True)}" hidden>',
                panel_html,
                pager,
                "</section>",
            ]
        )
    rebuilt.append(html_text[main_end:])
    html_text = "".join(rebuilt)

    reader_css = """
/* ch12-reader-layout */
body{background:#eef1f3;color:#20262d;}
main.report-page{max-width:1160px;padding:30px 44px 80px;}
.reader-nav{position:sticky;top:0;z-index:20;margin:1.4rem -44px 2rem;padding:.85rem 44px 1rem;background:rgba(255,255,255,.98);border-top:1px solid #d9e2ec;border-bottom:1px solid #cbd5df;box-shadow:0 7px 18px rgba(31,41,51,.08);}
.reader-nav-primary,.reader-nav-row{display:flex;align-items:center;gap:.8rem;min-width:0;}
.reader-nav-primary{justify-content:space-between;margin-bottom:.65rem;}
.reader-nav-row+.reader-nav-row{margin-top:.45rem;}
.reader-chapter-label{flex:0 0 3.5rem;color:#52606d;font-weight:700;font-size:.86rem;}
.reader-tabs{display:flex;gap:.4rem;min-width:0;overflow-x:auto;padding:.1rem 0 .25rem;scrollbar-width:thin;}
.reader-tab,.section-pager button{min-height:34px;border:1px solid #c8d3dc;border-radius:5px;background:#fff;color:#334e68;padding:.42rem .7rem;font:inherit;font-size:.88rem;line-height:1.25;cursor:pointer;white-space:nowrap;}
.reader-tab:hover,.section-pager button:hover{border-color:#0f766e;color:#0f766e;background:#f2fbf9;}
.reader-tab.is-active{border-color:#0f766e;background:#0f766e;color:#fff;box-shadow:0 2px 7px rgba(15,118,110,.2);}
.reader-current{color:#52606d;font-size:.9rem;}
.reader-current strong{color:#243b53;}
.reader-mobile-select{display:none;}
.reader-panel[hidden]{display:none!important;}
.reader-panel{animation:reader-enter .16s ease-out;}
@keyframes reader-enter{from{opacity:.45;transform:translateY(4px)}to{opacity:1;transform:none}}
body.reader-section-active main.report-page>h1,body.reader-section-active main.report-page>blockquote{display:none;}
body.reader-section-active .reader-nav{margin-top:-30px;}
.overview-panel>ol{columns:2;column-gap:3rem;}
.section-panel>h3:first-child{margin:0;padding:0 0 .7rem;border-bottom:3px solid #0f766e;color:#1f3a4d;font-size:1.5rem;}
.section-meta{display:flex;flex-wrap:wrap;gap:.5rem 1.15rem;margin:.9rem 0 2.1rem;padding:.75rem 0;border-bottom:1px solid #d9e2ec;color:#52606d;font-size:.9rem;}
.section-panel>blockquote:first-of-type{display:none;}
.cycle-index{display:flex;align-items:center;gap:.55rem;margin:-.9rem 0 2rem;padding:.65rem .75rem;background:#f5f8fa;border:1px solid #d9e2ec;border-radius:5px;overflow-x:auto;}
.cycle-index strong{flex:0 0 auto;color:#52606d;font-size:.88rem;}
.cycle-index button{flex:0 0 auto;border:0;border-bottom:2px solid transparent;background:transparent;color:#315c67;padding:.35rem .25rem;font:inherit;font-size:.86rem;cursor:pointer;white-space:nowrap;}
.cycle-index button:hover{color:#0f766e;border-bottom-color:#0f766e;}
.section-panel h4{margin:3rem 0 1.25rem;padding:.75rem 1rem;border-left:5px solid #0f766e;background:#edf7f5;color:#214e52;font-size:1.2rem;}
.section-panel h5{margin:2.3rem 0 .85rem;padding:.2rem 0 .45rem;border-bottom:1px solid #d9e2ec;color:#2b5876;font-size:1.08rem;}
.section-panel h6{margin:1.8rem 0 .65rem;color:#5b3b16;font-size:1rem;}
.section-panel p{max-width:84ch;margin:.85rem 0;line-height:1.85;}
.section-panel ul,.section-panel ol{max-width:88ch;margin:.75rem 0 1.35rem;}
.section-panel li{margin:.42rem 0;line-height:1.75;}
.section-panel hr{margin:3rem 0;border-color:#d9e2ec;}
.section-pager{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:1rem;margin:4rem 0 0;padding-top:1.2rem;border-top:1px solid #cbd5df;}
.section-pager button:first-child{justify-self:start;}.section-pager button:last-child{justify-self:end;}.section-pager span{color:#7b8794;font-size:.88rem;}
@media(max-width:720px){
 main.report-page{padding:22px 16px 56px;}
 .reader-nav{position:relative;margin:1.1rem -16px 1.5rem;padding:.75rem 16px .85rem;box-shadow:none;}
 body.reader-section-active .reader-nav{margin-top:-22px;}
 .reader-nav-primary{align-items:flex-start;}.reader-current{max-width:68%;text-align:right;}
 .reader-mobile-select{display:block;width:100%;min-height:42px;margin-top:.55rem;padding:.55rem .7rem;border:1px solid #b8c5cf;border-radius:5px;background:#fff;color:#243b53;font:inherit;}
 .reader-nav-row{display:none;}
 .overview-panel>ol{columns:1;}
 .section-panel>h3:first-child{font-size:1.3rem;line-height:1.45;}
 .section-meta{display:grid;grid-template-columns:1fr 1fr;gap:.45rem .8rem;margin-bottom:1.4rem;}
 .cycle-index{margin:-.35rem -16px 1.5rem;padding:.6rem 16px;border-left:0;border-right:0;border-radius:0;}
 .section-panel h4{margin:2.2rem 0 1rem;padding:.65rem .75rem;font-size:1.08rem;}
 .section-panel h5{margin-top:1.8rem;font-size:1rem;}
 .section-panel p,.section-panel li{line-height:1.75;}
 .section-pager{grid-template-columns:1fr 1fr;}.section-pager span{display:none;}
}
"""
    html_text = html_text.replace("</style>", reader_css + "</style>", 1)
    reader_script = r"""
<script data-reader-controller>
(() => {
  const panels = [...document.querySelectorAll('.reader-panel')];
  const controls = [...document.querySelectorAll('[data-reader-target]')];
  const current = document.getElementById('reader-current-label');
  const mobileSelect = document.querySelector('.reader-mobile-select');
  const validTargets = new Set(panels.map((panel) => panel.id));
  document.querySelectorAll('.section-panel').forEach((panel, panelIndex) => {
    const cycleHeadings = [...panel.querySelectorAll('h4,h5')].filter((heading) => /^循环\s*\d/.test(heading.textContent.trim()));
    if (!cycleHeadings.length) return;
    const cycleIndex = document.createElement('nav');
    cycleIndex.className = 'cycle-index';
    cycleIndex.setAttribute('aria-label', '本节循环');
    cycleIndex.innerHTML = '<strong>本节循环</strong>';
    cycleHeadings.forEach((heading, cycleNumber) => {
      heading.id = `reader-cycle-${panelIndex + 1}-${cycleNumber + 1}`;
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = heading.textContent.trim().replace(/^循环\s*/, '循环');
      button.addEventListener('click', () => heading.scrollIntoView({behavior: 'smooth', block: 'start'}));
      cycleIndex.appendChild(button);
    });
    panel.querySelector('.section-meta')?.insertAdjacentElement('afterend', cycleIndex);
  });
  function activate(target, updateHash = true) {
    if (!validTargets.has(target)) target = 'reader-overview';
    panels.forEach((panel) => {
      const active = panel.id === target;
      panel.hidden = !active;
      panel.classList.toggle('is-active', active);
    });
    controls.forEach((control) => {
      const active = control.dataset.readerTarget === target;
      control.classList.toggle('is-active', active);
      if (control.classList.contains('reader-tab')) control.setAttribute('aria-selected', String(active));
    });
    const panel = document.getElementById(target);
    current.textContent = panel?.dataset.readerLabel || '总览';
    if (mobileSelect) mobileSelect.value = target;
    document.body.classList.toggle('reader-section-active', target !== 'reader-overview');
    if (updateHash) history.replaceState(null, '', `#${target}`);
    window.scrollTo({top: 0, behavior: 'smooth'});
  }
  controls.forEach((control) => control.addEventListener('click', () => activate(control.dataset.readerTarget)));
  mobileSelect?.addEventListener('change', () => activate(mobileSelect.value));
  window.addEventListener('hashchange', () => activate(location.hash.slice(1), false));
  activate(location.hash.slice(1) || 'reader-overview', false);
})();
</script>
"""
    return html_text.replace("</body>", reader_script + "</body>", 1)


def main() -> int:
    assignment = load_json(ASSIGNMENT_PATH)
    catalog = load_json(CATALOG_PATH)
    validator = load_validator()
    catalog_by_key = {str(row["course_key"]): row for row in catalog.get("courses", [])}
    task_by_section: dict[str, dict] = {}
    delivery_by_task: dict[str, dict] = {}
    section_by_id: dict[str, dict] = {}
    section_markdown: dict[str, str] = {}
    task_reports = []

    assignment_errors = validator.validate_assignment(ROOT, assignment)
    for task in assignment.get("tasks", []):
        task_id = str(task["task_id"])
        delivery_path = SECTIONS_ROOT / task_id / "delivery.json"
        delivery = load_json(delivery_path)
        delivery_by_task[task_id] = delivery
        errors = validator.validate_delivery(ROOT, assignment, task_id, delivery)
        task_reports.append(
            {
                "task_id": task_id,
                "status": "passed" if not errors else "failed",
                "errors": errors,
                "delivery": str(delivery_path.relative_to(ROOT)).replace("\\", "/"),
                "delivery_sha256": sha256_file(delivery_path),
            }
        )
        for row in delivery.get("sections", []):
            section = str(row["section"])
            task_by_section[section] = task
            section_by_id[section] = row
        section_markdown.update(split_task_markdown(task, delivery))

    target_sections = [str(value) for value in assignment.get("target_sections", [])]
    expected_items = sum(int(task["expected_items"]) for task in assignment.get("tasks", []))
    expected_attempts = expected_items * 25
    missing_sections = sorted(set(target_sections) - set(section_by_id))
    unexpected_sections = sorted(set(section_by_id) - set(target_sections))
    total_items = sum(int(section_by_id[section]["coverage"]["delivered_items"]) for section in target_sections)
    total_attempts = sum(
        sum(int(value) for value in section_by_id[section]["simulation"]["actual_attempts_per_item"].values())
        for section in target_sections
    )
    visual_records = 0
    course_order: list[str] = []
    seen_courses: set[str] = set()
    for section in target_sections:
        row = section_by_id[section]
        for key in row.get("overview", {}).get("new_courses_in_section_order", []):
            key = str(key)
            if key not in seen_courses:
                seen_courses.add(key)
                course_order.append(key)
        evidence = load_json(ROOT / row["ocr_vision"]["evidence_path"])
        visual_records += len(
            [record for record in evidence.get("records", []) if str(record.get("section")) == section]
        )

    lines = [
        "# 一本通第一、二章学习路径（无题面答案版）",
        "",
        "> 按批准的 1.1 母版生成。先看全局课程与小节总览，实际学习时严格逐循环推进；不含题面、答案、选项或内部 ID。",
        "",
        "## 总览",
        "",
        f"- 覆盖：2 章、{len(target_sections)} 个题包单元、{total_items} 个 canonical 学习项目。",
        f"- 代理模拟：每项 5 轮 × 5 人格，共 {total_attempts} 条当前源尝试记录。",
        f"- 视觉：{visual_records} 张绑定图使用 PaddleOCR + READY 绑定 GLM exact-SHA 回退；当前 Luna worker 图像输入为 blocked。",
        "- 固定学习顺序：知识点 → 紧邻例题 → 直属变式 → 类型题 → A/B/C → 循环验收。",
        "",
        "## 全局首次听课顺序",
        "",
    ]
    for index, key in enumerate(course_order, start=1):
        course = catalog_by_key.get(key)
        if course is None:
            raise ValueError(f"unknown course key in delivery: {key}")
        lines.append(f"{index}. {course['title']}（视频：{Path(course['video_file']).name}）")

    lines.extend(
        [
            "",
            "## 小节执行总览",
            "",
            "<table><thead><tr><th>章</th><th>小节</th><th>项目</th><th>首课</th><th>模拟</th><th>视觉</th></tr></thead><tbody>",
        ]
    )
    for section in target_sections:
        row = section_by_id[section]
        first_key = str(row.get("overview", {}).get("first_course") or "")
        first = catalog_by_key.get(first_key, {})
        chapter = 1 if section.startswith("1.") or section.startswith("micro") else 2
        lines.append(
            "<tr>"
            f"<td>第{chapter}章</td><td>{row.get('label') or section}</td>"
            f"<td>{row['coverage']['delivered_items']}</td>"
            f"<td>{first.get('title', first_key)}</td>"
            f"<td>{row['simulation']['status']}</td>"
            f"<td>{row['ocr_vision']['mode']}</td></tr>"
        )
    lines.extend(["</tbody></table>", ""])

    for chapter, chapter_sections in (
        (1, target_sections[:4]),
        (2, target_sections[4:]),
    ):
        chapter_title = "空间向量与立体几何" if chapter == 1 else "直线与圆的方程"
        lines.extend([f"## 第{chapter}章 {chapter_title}", ""])
        for section in chapter_sections:
            lines.append(section_markdown[section].rstrip())
            lines.extend(["", "---", ""])

    text = convert_markdown_tables("\n".join(lines)).rstrip() + "\n"
    OUTPUT_MD.write_text(text, encoding="utf-8", newline="\r\n")
    leak_patterns = {
        "answer_marker": r"(?:答案|正确选项|最终答案)\s*[：:]",
        "internal_id": r"(?:LI:|Q:Q-|\bitem_key\b)",
        "replacement_char": "�",
    }
    scans = {name: len(re.findall(pattern, text, re.I)) for name, pattern in leak_patterns.items()}
    latex = {
        "inline_open": text.count(r"\("),
        "inline_close": text.count(r"\)"),
        "display_open": text.count(r"\["),
        "display_close": text.count(r"\]"),
    }
    latex["balanced"] = latex["inline_open"] == latex["inline_close"] and latex["display_open"] == latex["display_close"]
    overall = (
        not assignment_errors
        and all(row["status"] == "passed" for row in task_reports)
        and not missing_sections
        and not unexpected_sections
        and total_items == expected_items
        and total_attempts == expected_attempts
        and all(value == 0 for value in scans.values())
        and latex["balanced"]
    )
    report = {
        "schema_version": "ybt-ch12-acceptance-v1",
        "status": "passed" if overall else "failed",
        "assignment": str(ASSIGNMENT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "assignment_sha256": sha256_file(ASSIGNMENT_PATH),
        "skill_contract_sha256": assignment["source_binding"]["skill_contract_sha256"],
        "target_sections": target_sections,
        "coverage": {
            "expected_items": expected_items,
            "delivered_items": total_items,
            "missing_sections": missing_sections,
            "unexpected_sections": unexpected_sections,
        },
        "simulation": {
            "expected_attempts": expected_attempts,
            "actual_attempts": total_attempts,
            "proxy": "passed" if total_attempts == expected_attempts else "failed",
            "human_acceptance": "not_run",
            "cold_24h_retest": "not_run",
        },
        "visual": {
            "record_count": visual_records,
            "mode": "paddle_glm_crosscheck",
            "luna_image_input": "blocked",
        },
        "learner_artifact_scan": scans,
        "latex": latex,
        "assignment_errors": assignment_errors,
        "tasks": task_reports,
        "markdown": str(OUTPUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "markdown_sha256": sha256_file(OUTPUT_MD),
    }
    if OUTPUT_HTML.is_file():
        html_text = OUTPUT_HTML.read_text(encoding="utf-8")
        html_changed = False
        responsive_marker = "/* ch12-responsive-overflow */"
        if responsive_marker not in html_text:
            responsive_css = (
                responsive_marker
                + "html,body{max-width:100%;overflow-x:hidden;}"
                + ".table-wrap{max-width:100%;overflow-x:auto;overscroll-behavior-inline:contain;}"
                + "mjx-container{max-width:100%;overflow-x:auto;overflow-y:hidden;}"
            )
            html_text = html_text.replace("</style>", responsive_css + "</style>", 1)
            html_changed = True
        reader_html = inject_reader_layout(html_text, target_sections, section_by_id, catalog_by_key)
        if reader_html != html_text:
            html_text = reader_html
            html_changed = True
        if html_changed:
            OUTPUT_HTML.write_text(html_text, encoding="utf-8", newline="\r\n")
        report["html"] = str(OUTPUT_HTML.relative_to(ROOT)).replace("\\", "/")
        report["html_sha256"] = sha256_file(OUTPUT_HTML)
        report["html_static"] = {
            "utf8_meta": '<meta charset="utf-8">' in html_text,
            "viewport_meta": 'name="viewport"' in html_text,
            "mathjax": "MathJax" in html_text and "tex-chtml.js" in html_text,
            "replacement_char_count": html_text.count("�"),
            "script_tag_count": html_text.lower().count("<script"),
            "reader_nav": 'class="reader-nav"' in html_text,
            "reader_panel_count": html_text.count('class="reader-panel'),
            "section_tab_count": html_text.count('class="reader-tab"'),
            "pager_count": html_text.count('class="section-pager"'),
        }
        if not all(
            (
                report["html_static"]["utf8_meta"],
                report["html_static"]["viewport_meta"],
                report["html_static"]["mathjax"],
                report["html_static"]["replacement_char_count"] == 0,
                report["html_static"]["reader_nav"],
                report["html_static"]["reader_panel_count"] == 12,
                report["html_static"]["section_tab_count"] == 11,
                report["html_static"]["pager_count"] == 11,
            )
        ):
            report["status"] = "failed"
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
