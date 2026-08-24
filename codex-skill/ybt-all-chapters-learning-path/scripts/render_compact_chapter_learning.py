#!/usr/bin/env python3
"""Render compact, answer-free chapter 1-2 learning documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import OrderedDict
from html import escape
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from chapter_learning_progress import chapter_facts, load_json, sha256_file


FORBIDDEN_RE = re.compile(
    r"(?:LI:|Q:Q-|\bitem_key\b|答案\s*[：:]|正确选项|最终答案|"
    r"answer_text|correct_option|final_answer|solution_text)",
    re.I,
)
ROLE_ORDER = ("知识点右侧例题", "直属变式", "类型题", "A/B/C习题")
STATUS_LABELS = {
    "planned": "待学",
    "in_progress": "学习中",
    "simulated_completed": "模拟已学",
    "blocked": "受阻",
    "not_started": "未开始",
    "passed": "已通过",
    "completed": "已完成",
}
VISUAL_LABELS = {
    "VISION_VERIFIED": "图形已核验",
    "READY_TEXT_ONLY": "文本可用",
    "BLOCKED": "受阻",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lines(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_text(value) for value in values if _text(value)]


def _anchor(value: str) -> str:
    ascii_part = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return ascii_part or hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]


def _display_path(path: Path, project_root: Path) -> str:
    try:
        value = path.relative_to(project_root)
    except ValueError:
        value = path
    return str(value).replace("\\", "/")


def _chapter_title(manifest: dict[str, Any], chapter: int) -> str:
    target = manifest.get("target_identity") or {}
    return _text(target.get("chapter")) or f"第{chapter}章"


def _catalog(project_root: Path) -> dict[str, dict[str, Any]]:
    catalog = load_json(project_root / "data" / "all_chapters_course_catalog.json")
    return {str(row["course_key"]): row for row in catalog.get("courses", [])}


def _course_name(catalog: dict[str, dict[str, Any]], key: str) -> str:
    row = catalog.get(key) or {}
    return _text(row.get("title")) or key


def _course_video(catalog: dict[str, dict[str, Any]], key: str) -> str:
    row = catalog.get(key) or {}
    value = _text(row.get("video_file"))
    return Path(value).name if value else ""


def _course_label(catalog: dict[str, dict[str, Any]], key: str) -> str:
    """Show the catalogue's lesson number beside its readable title."""
    title = _course_name(catalog, key)
    video = _course_video(catalog, key)
    match = re.match(r"^(\d+(?:\.\d+)+(?:\.[a-z])?)\s*(.*)$", Path(video).stem)
    if match:
        number, video_title = match.groups()
        if title.startswith(number):
            return f"{number} {title[len(number):].lstrip()}".strip()
        return f"{number} {title or video_title}".strip()
    return title


def _course_number(catalog: dict[str, dict[str, Any]], key: str) -> str:
    video = _course_video(catalog, key)
    match = re.match(r"^(\d+(?:\.\d+)+(?:\.[a-z])?)", Path(video).stem)
    return match.group(1) if match else "课程"


def _course_title(catalog: dict[str, dict[str, Any]], key: str) -> str:
    title = _course_name(catalog, key)
    number = _course_number(catalog, key)
    if number != "课程" and title.startswith(number):
        return title[len(number):].lstrip() or title
    return title


def _section_rows(facts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = facts.get("section_deliveries")
    if not isinstance(rows, dict):
        raise ValueError("chapter facts do not expose section deliveries")
    return rows


def _cycle_items(section: dict[str, Any], sequence: int) -> list[dict[str, Any]]:
    rows = [
        item for item in section.get("items", [])
        if isinstance(item, dict) and item.get("cycle_sequence") == sequence
    ]
    return sorted(rows, key=lambda item: int(item.get("ordinal") or 0))


def _group_labels(items: list[dict[str, Any]]) -> list[tuple[str, list[str]]]:
    grouped: OrderedDict[str, list[str]] = OrderedDict((role, []) for role in ROLE_ORDER)
    for item in items:
        role = _text(item.get("position")) or _text(item.get("kind"))
        grouped.setdefault(role, []).append(_text(item.get("label")))
    return [(role, labels) for role, labels in grouped.items() if labels]


def _course_status(progress: dict[str, Any]) -> dict[str, str]:
    return {
        str(row.get("course_key")): str(row.get("status"))
        for row in progress.get("course_ledger", {}).get("records", [])
        if isinstance(row, dict)
    }


def _section_course_keys(section: dict[str, Any], required_order: list[str]) -> list[str]:
    used = {
        str(key)
        for item in section.get("items", []) if isinstance(item, dict)
        for key in item.get("course_refs", [])
    }
    for cycle in section.get("cycles", []):
        if not isinstance(cycle, dict):
            continue
        used.update(str(key) for key in cycle.get("course_keys", []))
        used.update(str(key) for key in cycle.get("prerequisite_course_keys", []))
    return [key for key in required_order if key in used]


def _course_cycle_entries(
    section: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
    required_order: list[str],
) -> dict[str, list[tuple[int, str]]]:
    entries: dict[str, list[tuple[int, str]]] = {key: [] for key in _section_course_keys(section, required_order)}
    for cycle in sorted(section.get("cycles", []), key=lambda row: int(row.get("sequence") or 0)):
        sequence = int(cycle.get("sequence") or 0)
        items = _cycle_items(section, sequence)
        keys = _cycle_course_keys(items, cycle)
        for key in keys:
            if key in entries:
                entries[key].append((sequence, _text(cycle.get("title"))))
    return entries


def _markdown_item(item: dict[str, Any], catalog: dict[str, dict[str, Any]]) -> list[str]:
    label = _text(item.get("label"))
    position = _text(item.get("position"))
    topic = _item_topic(item, {})
    visual_status = _text((item.get("visual_dependency") or {}).get("status"))
    courses = "、".join(_course_label(catalog, str(key)) for key in item.get("course_refs", []))
    lines = [
        f"<details class=\"item-detail\"><summary><strong>{label}</strong> · {topic} · {position}</summary>",
        "",
    ]
    fields = [
        ("课程", courses),
        ("识别", "；".join(_lines(item.get("recognition_cues")))),
        ("方法", _text(item.get("method_model"))),
        ("第一行", _text(item.get("first_written_line_template"))),
        ("继续", "；".join(_lines(item.get("continuation_actions")))),
        ("卡点", "；".join(_lines(item.get("likely_blockers")))),
        ("提示", "；".join(_lines(item.get("minimal_correction_prompts")))),
        ("自检", "；".join(_lines(item.get("independent_self_checks")))),
    ]
    lines.extend(f"- **{name}**：{value}" for name, value in fields if value)
    lines.extend(["", "</details>", ""])
    return lines


def render_markdown(
    manifest: dict[str, Any],
    facts: dict[str, Any],
    progress: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> str:
    chapter = int(progress["chapter"])
    title = _chapter_title(manifest, chapter)
    required = list(progress["course_ledger"]["required_course_keys"])
    statuses = _course_status(progress)
    lines = [
        f"# {title}学习路径",
        "",
        f"> 本章必修课程 {len(required)} 门；教材项目 {facts['canonical_item_count']} 项；"
        "交互式学习进度在 HTML 页面中按循环和题目记录。",
        "",
        "## 课程账本",
        "",
        "| 顺序 | 课程 | 视频 | 状态 |",
        "|---:|---|---|---|",
    ]
    for index, key in enumerate(required, start=1):
        status = statuses.get(key, "planned")
        lines.append(
            f"| {index} | {_course_label(catalog, key)} | `{_course_video(catalog, key)}` | "
            f"{STATUS_LABELS.get(status, status)} |"
        )
    lines.extend(["", "未完成课程：" + "、".join(_course_label(catalog, key) for key in progress["course_ledger"]["unfinished_course_keys"]), ""])

    section_by_id = _section_rows(facts)
    progress_by_section = {str(row["section"]): row for row in progress.get("sections", [])}
    for manifest_section in manifest.get("sections", []):
        section_id = str(manifest_section["id"])
        section = section_by_id[section_id]
        section_progress = progress_by_section[section_id]
        section_courses = _section_course_keys(section, required)
        lines.extend([
            f"## {_text(manifest_section.get('label')) or section_id}",
            "",
            f"- **状态**：{STATUS_LABELS.get(section_progress['status'], section_progress['status'])}",
            f"- **课程**：{' → '.join(_course_label(catalog, key) for key in section_courses)}",
            f"- **项目**：{section['coverage']['delivered_items']} 项",
            "",
        ])
        for cycle in sorted(section.get("cycles", []), key=lambda row: int(row.get("sequence") or 0)):
            sequence = int(cycle.get("sequence") or 0)
            items = _cycle_items(section, sequence)
            cycle_courses = []
            for item in items:
                for key in item.get("course_refs", []):
                    if key not in cycle_courses:
                        cycle_courses.append(str(key))
            lines.extend([
                f"### 循环 {sequence}｜{_text(cycle.get('title'))}",
                "",
                f"- **课程调用**：{'、'.join(_course_label(catalog, key) for key in cycle_courses) or '无新增课程'}",
                f"- **知识/类型**：{'、'.join(_lines(cycle.get('knowledge_labels'))) or '按教材项目推进'}",
            ])
            for role, labels in _group_labels(items):
                lines.append(f"- **{role}**：{'、'.join(labels)}")
            if items:
                lines.extend([
                    "",
                    "#### 教材对应",
                    "",
                    "| 项目 | 所属知识/类型 | 教材角色 | 内容状态 |",
                    "|---|---|---|---|",
                ])
                for item in items:
                    visual_status = _text((item.get("visual_dependency") or {}).get("status"))
                    lines.append(
                        f"| {_text(item.get('label'))} | {_item_topic(item, cycle)} | "
                        f"{_text(item.get('position'))} | {VISUAL_LABELS.get(visual_status, visual_status)} |"
                    )
            checks = _lines(cycle.get("acceptance_checks"))
            if checks:
                lines.append(f"- **循环验收**：{'；'.join(checks)}")
            lines.append("")
            lines.append("<details class=\"cycle-items\"><summary><strong>展开逐题方法</strong></summary>")
            lines.append("")
            for item in items:
                lines.extend(_markdown_item(item, catalog))
            lines.extend(["</details>", ""])
    result = "\n".join(lines).rstrip() + "\n"
    match = FORBIDDEN_RE.search(result)
    if match:
        raise ValueError(f"learner-facing Markdown contains forbidden content: {match.group(0)}")
    return result


def _html_list(values: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{escape(value)}</li>" for value in values) + "</ul>"


def _item_topic(item: dict[str, Any], cycle: dict[str, Any]) -> str:
    type_refs = _lines(item.get("type_refs"))
    knowledge_refs = _lines(item.get("knowledge_refs"))
    if type_refs:
        return "、".join(type_refs)
    if knowledge_refs:
        return "、".join(knowledge_refs)
    return "、".join(_lines(cycle.get("knowledge_labels"))) or "本循环综合应用"


def _cycle_course_keys(items: list[dict[str, Any]], cycle: dict[str, Any] | None = None) -> list[str]:
    keys: list[str] = []
    for key in (cycle or {}).get("course_keys", []):
        value = str(key)
        if value not in keys:
            keys.append(value)
    for item in items:
        for key in item.get("course_refs", []):
            value = str(key)
            if value not in keys:
                keys.append(value)
    return keys


def _cycle_state_token(section_id: str, sequence: int) -> str:
    return _anchor(f"{section_id}|cycle|{sequence}")


def _item_state_token(section_id: str, sequence: int, item: dict[str, Any]) -> str:
    return _anchor(f"{section_id}|cycle|{sequence}|item|{item.get('ordinal')}|{item.get('label')}")


def _item_order(items: list[dict[str, Any]]) -> str:
    return " → ".join(_text(item.get("label")) for item in items if _text(item.get("label")))


def _course_lines_html(catalog: dict[str, dict[str, Any]], keys: list[str]) -> str:
    if not keys:
        return '<span class="empty-course">沿用已学课程</span>'
    return "".join(
        '<span class="course-line">'
        f'<span class="course-code">{escape(_course_number(catalog, key))}</span>'
        f'<span class="course-title">{escape(_course_title(catalog, key))}</span>'
        '</span>'
        for key in keys
    )


def _cycle_topics(items: list[dict[str, Any]], cycle: dict[str, Any]) -> list[str]:
    topics: list[str] = []
    for item in items:
        refs = _lines(item.get("type_refs")) or _lines(item.get("knowledge_refs"))
        refs = refs or _lines(cycle.get("knowledge_labels")) or ["本循环方法检查"]
        for topic in refs:
            if topic not in topics:
                topics.append(topic)
    return topics or _lines(cycle.get("knowledge_labels")) or ["本循环方法检查"]


def _html_item(
    item: dict[str, Any],
    cycle: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
    state_token: str,
) -> str:
    courses = "、".join(_course_label(catalog, str(key)) for key in item.get("course_refs", []))
    visual_status = _text((item.get("visual_dependency") or {}).get("status"))
    visual = VISUAL_LABELS.get(visual_status, visual_status)
    topic = _item_topic(item, cycle)
    fields: list[tuple[str, str]] = [
        ("课程", escape(courses)),
        ("识别", escape("；".join(_lines(item.get("recognition_cues"))))),
        ("方法", escape(_text(item.get("method_model")))),
        ("第一行", escape(_text(item.get("first_written_line_template")))),
        ("继续", _html_list(_lines(item.get("continuation_actions")))),
        ("常见卡点", _html_list(_lines(item.get("likely_blockers")))),
        ("最小提示", _html_list(_lines(item.get("minimal_correction_prompts")))),
        ("独立自检", _html_list(_lines(item.get("independent_self_checks")))),
    ]
    body = "".join(f"<dt>{escape(name)}</dt><dd>{value}</dd>" for name, value in fields if value and value != "<ul></ul>")
    return (
        f'<details class="item-detail" data-item-state="{escape(state_token)}">'
        '<summary>'
        f'<button type="button" class="item-star" data-star-item="{escape(state_token)}" aria-pressed="false" aria-label="标记题目" title="标记题目">☆</button>'
        f'<span class="item-label">{escape(_text(item.get("label")))}</span>'
        f'<span class="item-topic">{escape(topic)}</span>'
        f'<span class="item-position">{escape(_text(item.get("position")))}</span>'
        f'<span class="visual-state">{escape(visual)}</span>'
        '</summary>'
        f'<dl class="item-body">{body}</dl>'
        '<div class="item-actions">'
        f'<button type="button" class="item-pass" data-pass-item="{escape(state_token)}" aria-pressed="false">标记项目已通过</button>'
        '</div>'
        '</details>'
    )


def _interaction_script() -> str:
    return r"""
(() => {
  const sectionButtons = [...document.querySelectorAll('[data-section-target]')];
  const sectionPanels = [...document.querySelectorAll('[data-section-panel]')];
  const sectionSelect = document.querySelector('#section-select');
  const workspace = document.querySelector('.workspace');
  const chapter = document.body.dataset.chapter || 'unknown';
  const storageKey = `ybt-learning-state-v2-chapter-${chapter}`;
  const emptyState = {cycles: {}, items: {}, questions: {}};

  function loadState() {
    try {
      return {...emptyState, ...(JSON.parse(localStorage.getItem(storageKey) || '{}'))};
    } catch (error) {
      return {...emptyState};
    }
  }

  let state = loadState();

  function saveState() {
    try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch (error) { /* file URLs may block storage */ }
  }

  function cycleState(token) {
    return state.cycles[token] || {};
  }

  function courseIsComplete(row) {
    const tokens = (row.dataset.courseCycles || '').split(' ').filter(Boolean);
    return tokens.some((token) => Boolean(cycleState(token).listened));
  }

  function applyCycleState() {
    document.querySelectorAll('[data-cycle-state]').forEach((row) => {
      const token = row.dataset.cycleState;
      const entry = cycleState(token);
      const listened = Boolean(entry.listened);
      const starred = Boolean(entry.starred);
      row.classList.toggle('is-listened', listened);
      row.classList.toggle('is-starred', starred);
      row.querySelectorAll(`[data-listen-cycle="${token}"]`).forEach((button) => {
        button.setAttribute('aria-pressed', String(listened));
        button.textContent = listened ? '✓ 已听完' : '标记已听完';
        button.classList.toggle('is-active', listened);
      });
      row.querySelectorAll(`[data-star-cycle="${token}"]`).forEach((button) => {
        button.setAttribute('aria-pressed', String(starred));
        button.textContent = starred ? '★' : '☆';
        button.classList.toggle('is-active', starred);
      });
    });
  }

  function applyItemState() {
    document.querySelectorAll('[data-item-state]').forEach((item) => {
      const token = item.dataset.itemState;
      const starred = Boolean(state.items[token]?.starred);
      const passed = Boolean(state.items[token]?.passed);
      item.classList.toggle('is-starred', starred);
      item.classList.toggle('is-passed', passed);
      const button = item.querySelector(`[data-star-item="${token}"]`);
      if (button) {
        button.setAttribute('aria-pressed', String(starred));
        button.textContent = starred ? '★' : '☆';
        button.classList.toggle('is-active', starred);
      }
      item.querySelectorAll(`[data-pass-item="${token}"]`).forEach((passButton) => {
        passButton.setAttribute('aria-pressed', String(passed));
        passButton.textContent = passed ? '✓ 项目已通过' : '标记项目已通过';
        passButton.classList.toggle('is-active', passed);
      });
    });
  }

  function applyCourseState() {
    document.querySelectorAll('[data-course-row]').forEach((row) => {
      const complete = courseIsComplete(row);
      row.classList.toggle('is-complete', complete);
      row.querySelectorAll('[data-course-status]').forEach((status) => {
        status.textContent = complete ? '已听完' : '待学习';
      });
    });
  }

  function applyQuestions() {
    document.querySelectorAll('[data-cycle-question]').forEach((textarea) => {
      textarea.value = state.questions[textarea.dataset.cycleQuestion] || '';
    });
  }

  function updateProgress() {
    const allCycles = [...document.querySelectorAll('.outline-row[data-cycle-state]')];
    const listened = allCycles.filter((row) => cycleState(row.dataset.cycleState).listened).length;
    const allItems = [...document.querySelectorAll('[data-item-state]')];
    const passedItems = allItems.filter((item) => state.items[item.dataset.itemState]?.passed).length;
    const allCourses = [...document.querySelectorAll('[data-course-row]')]
      .filter((row, index, rows) => rows.findIndex((candidate) => candidate.dataset.courseKey === row.dataset.courseKey) === index);
    const completedCourses = allCourses.filter(courseIsComplete).length;
    const allSections = [...document.querySelectorAll('[data-section-panel]')];
    const completedSections = allSections.filter((panel) => {
      const cycles = [...panel.querySelectorAll('.outline-row[data-cycle-state]')];
      const items = [...panel.querySelectorAll('[data-item-state]')];
      return cycles.length > 0 && cycles.every((row) => cycleState(row.dataset.cycleState).listened)
        && items.length > 0 && items.every((item) => state.items[item.dataset.itemState]?.passed);
    }).length;
    const percent = allCycles.length ? Math.round((listened / allCycles.length) * 100) : 0;
    document.querySelectorAll('[data-cycle-progress-label]').forEach((label) => {
      label.textContent = `${listened}/${allCycles.length}`;
    });
    document.querySelectorAll('[data-cycle-progress-fill]').forEach((fill) => {
      fill.style.width = `${percent}%`;
    });
    document.querySelectorAll('[data-dashboard-course-progress]').forEach((label) => {
      label.textContent = `${completedCourses}/${allCourses.length}`;
    });
    document.querySelectorAll('[data-dashboard-item-progress]').forEach((label) => {
      label.textContent = `${passedItems}/${allItems.length}`;
    });
    document.querySelectorAll('[data-dashboard-section-progress]').forEach((label) => {
      label.textContent = `${completedSections}/${allSections.length}`;
    });
    document.querySelectorAll('[data-dashboard-cycle-progress]').forEach((label) => {
      label.textContent = `${listened}/${allCycles.length}`;
    });
    sectionPanels.forEach((panel) => {
      const cycles = [...panel.querySelectorAll('.outline-row[data-cycle-state]')];
      const done = cycles.filter((row) => cycleState(row.dataset.cycleState).listened).length;
      const next = cycles.find((row) => !cycleState(row.dataset.cycleState).listened);
      const label = panel.querySelector('[data-section-progress-label]');
      const fill = panel.querySelector('[data-section-progress-fill]');
      if (label) label.textContent = `${done}/${cycles.length} 循环已听完`;
      if (fill) fill.style.width = `${cycles.length ? (done / cycles.length) * 100 : 0}%`;
      const nextBox = panel.querySelector('[data-next-step]');
      if (nextBox) {
        const nextIndex = next ? cycles.indexOf(next) + 1 : cycles.length;
        const cycleLabel = nextBox.querySelector('[data-next-cycle]');
        const titleLabel = nextBox.querySelector('[data-next-title]');
        const courseLabel = nextBox.querySelector('[data-next-course]');
        const orderLabel = nextBox.querySelector('[data-next-order]');
        nextBox.classList.toggle('is-complete', !next);
        if (cycleLabel) cycleLabel.textContent = next ? `循环 ${nextIndex}` : '本节完成';
        if (titleLabel) titleLabel.textContent = next?.dataset.cycleTitle || '所有循环均已听完';
        if (courseLabel) courseLabel.textContent = next ? `先听：${next.dataset.cycleCourses}` : '继续完成未通过题目';
        if (orderLabel) orderLabel.textContent = next?.dataset.cycleOrder || '检查本节项目状态';
      }
    });
  }

  function refreshState() {
    applyCycleState();
    applyItemState();
    applyCourseState();
    applyQuestions();
    updateProgress();
  }

  function toggleCycle(token, field) {
    state.cycles[token] = {...cycleState(token), [field]: !cycleState(token)[field]};
    saveState();
    refreshState();
  }

  function activateCycle(sectionPanel, cycle, updateHistory) {
    const target = String(cycle || 'outline');
    sectionPanel.classList.toggle('showing-cycle-detail', target !== 'outline');
    sectionPanel.querySelectorAll('[data-cycle-panel]').forEach((panel) => {
      panel.hidden = panel.dataset.cyclePanel !== target;
    });
    sectionPanel.querySelectorAll('.cycle-tab').forEach((button) => {
      button.setAttribute('aria-selected', String(button.dataset.cycleTarget === target));
    });
    if (updateHistory) {
      const section = sectionPanel.dataset.sectionPanel;
      const suffix = target === 'outline' ? '' : `/cycle-${target}`;
      history.pushState(null, '', `#${section}${suffix}`);
    }
  }

  function activateSection(section, cycle, updateHistory, scrollIntoView) {
    const target = sectionPanels.some((panel) => panel.dataset.sectionPanel === section)
      ? section
      : sectionPanels[0]?.dataset.sectionPanel;
    if (!target) return;
    sectionPanels.forEach((panel) => { panel.hidden = panel.dataset.sectionPanel !== target; });
    sectionButtons.forEach((button) => {
      button.setAttribute('aria-selected', String(button.dataset.sectionTarget === target));
    });
    if (sectionSelect) sectionSelect.value = target;
    const panel = sectionPanels.find((candidate) => candidate.dataset.sectionPanel === target);
    activateCycle(panel, cycle || 'outline', false);
    if (updateHistory) {
      const suffix = cycle && cycle !== 'outline' ? `/cycle-${cycle}` : '';
      history.pushState(null, '', `#${target}${suffix}`);
    }
    if (scrollIntoView) workspace.scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  function stateFromHash() {
    const raw = decodeURIComponent(location.hash.slice(1));
    const [section, cycleToken] = raw.split('/');
    const cycle = cycleToken?.startsWith('cycle-') ? cycleToken.slice(6) : 'outline';
    return {section, cycle};
  }

  function helpPrompt(panel) {
    const sectionKey = panel.closest('[data-section-panel]')?.dataset.sectionPanel || '当前节次';
    const course = panel.querySelector('[data-help-courses]')?.textContent?.trim() || '按本循环课程';
    const order = panel.querySelector('[data-help-order]')?.textContent?.trim() || '按教材顺序';
    const question = panel.querySelector('[data-cycle-question]')?.value?.trim() || '（尚未填写）';
    const title = panel.querySelector('.cycle-heading h3')?.textContent?.trim() || '当前循环';
    return `你是“数学选择性必修一”项目里的高中数学学习辅助老师。\n\n资料读取优先级：\n1. 如果已连接“数学一本通学习” MCP，先调用 math_get_system_status 和 math_get_current_task；\n2. 用 math_get_section_overview 读取 ${sectionKey} 的完整循环、题号和课程映射；\n3. 根据题号映射当前项目，再调用 math_get_item_content 读取无答案题面和题图；\n4. 调用 math_get_course_transcript 读取本循环绑定课程的完整老师文稿；\n5. 调用 math_get_progress 区分当前学习进度与资料覆盖；\n6. 需要配套讲义时先调用 math_get_course_handout 或 math_search_handout 定位，再调用 math_get_handout_page 查看原页图，不能只信 OCR。\n只有 MCP 不可用时，才使用 @GitHub 读取仓库 666poyi666-collab/ybt-learning-system-v7；8.5 对话文件只作为辅助经验参考，不作为本节事实来源。\n\n当前节次：${sectionKey}\n当前循环：${title}\n先听课程：${course}\n做题顺序：${order}\n我的疑问：${question}\n\n请按以下格式回答：\n1. 判断我卡在概念、方法入口、计算、图形识别还是书写；\n2. 指出我当前做对或做错的第一步；\n3. 只给一个最小提示，不直接公布结果；\n4. 让我先提交自己的下一步；\n5. 只安排一个下一动作。\n如果我确认做错、卡住或依赖提示，立即调用 math_record_wrong_question，同时记录错因与题型；语音误识别和未确认猜测不得落账。我说“整理当前错题”时调用 math_export_wrong_questions。我明确跳过循环时调用 math_defer_cycle，标为暂缓而不是完成。若资料不足，明确指出缺什么，不要猜。除非我明确确认，不调用写回工具；不要输出答案侧车、内部题目 ID、五人格压力测试或整章长报告。`;
  }

  function progressPrompt() {
    const sections = sectionPanels.map((panel) => {
      const title = panel.querySelector('h2')?.textContent?.trim() || '未知节次';
      const cycles = [...panel.querySelectorAll('.outline-row[data-cycle-state]')];
      const items = [...panel.querySelectorAll('[data-item-state]')];
      const listened = cycles.filter((row) => cycleState(row.dataset.cycleState).listened).length;
      const passed = items.filter((item) => state.items[item.dataset.itemState]?.passed).length;
      const starred = items.filter((item) => state.items[item.dataset.itemState]?.starred)
        .map((item) => item.querySelector('.item-label')?.textContent?.trim()).filter(Boolean);
      const questions = [...panel.querySelectorAll('[data-cycle-question]')]
        .map((textarea) => textarea.value.trim()).filter(Boolean);
      return `${title}：循环听完 ${listened}/${cycles.length}；项目通过 ${passed}/${items.length}；星标 ${starred.join('、') || '无'}；未解决疑问 ${questions.length}`;
    });
    return `请优先使用已连接的“数学一本通学习” MCP：先调用 math_get_system_status、math_get_current_task 和 math_get_progress，再按当前节次调用 math_get_section_overview；讲题前读取当前项目的无答案题面/题图和所有绑定课程的完整老师文稿。只有 MCP 不可用时，才使用 @GitHub 读取仓库 666poyi666-collab/ybt-learning-system-v7，并先核对 data/chatgpt_context/chapter12_complete_audit.json。下面是本浏览器导出的实时学习进度快照，它只代表当前用户操作，不等于仓库证据账本或内部模拟进度。\n\n章节：${document.querySelector('.brand h1')?.textContent?.trim() || `第${chapter}章`}\n${sections.join('\n')}\n\n先核对快照与云端差异；只有我明确确认同步时才调用 math_sync_progress_snapshot，并在写入后重新读取 math_get_current_task 和 math_get_progress，报告实际投影状态。若我确认错误或卡点，调用 math_record_wrong_question；我要求整理错题时调用 math_export_wrong_questions。解释必须采用网课老师的方法顺序；先看我的尝试，只给一个最小提示，不直接公布结果。`;
  }

  sectionButtons.forEach((button) => {
    button.addEventListener('click', () => activateSection(button.dataset.sectionTarget, 'outline', true, true));
  });
  sectionSelect?.addEventListener('change', () => activateSection(sectionSelect.value, 'outline', true, true));
  document.querySelectorAll('[data-cycle-target]').forEach((button) => {
    if (button.classList.contains('section-tab')) return;
    button.addEventListener('click', () => {
      const sectionPanel = button.closest('[data-section-panel]');
      activateCycle(sectionPanel, button.dataset.cycleTarget, true);
      const targetPanel = sectionPanel.querySelector(`[data-cycle-panel="${button.dataset.cycleTarget}"]`);
      const targetHeading = targetPanel?.querySelector('.back-to-route') || targetPanel?.querySelector('.cycle-heading');
      targetHeading?.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
  });
  document.querySelectorAll('[data-cycle-back]').forEach((button) => {
    button.addEventListener('click', () => {
      const sectionPanel = button.closest('[data-section-panel]');
      activateCycle(sectionPanel, 'outline', true);
      sectionPanel.querySelector('.outline-heading')?.scrollIntoView({behavior: 'smooth', block: 'start'});
    });
  });
  document.querySelectorAll('[data-listen-cycle]').forEach((button) => {
    button.addEventListener('click', (event) => { event.preventDefault(); event.stopPropagation(); toggleCycle(button.dataset.listenCycle, 'listened'); });
  });
  document.querySelectorAll('[data-star-cycle]').forEach((button) => {
    button.addEventListener('click', (event) => { event.preventDefault(); event.stopPropagation(); toggleCycle(button.dataset.starCycle, 'starred'); });
  });
  document.querySelectorAll('[data-star-item]').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const token = button.dataset.starItem;
      state.items[token] = {...(state.items[token] || {}), starred: !state.items[token]?.starred};
      saveState();
      refreshState();
    });
  });
  document.querySelectorAll('[data-pass-item]').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const token = button.dataset.passItem;
      state.items[token] = {...(state.items[token] || {}), passed: !state.items[token]?.passed};
      saveState();
      refreshState();
    });
  });
  document.querySelectorAll('[data-cycle-question]').forEach((textarea) => {
    textarea.addEventListener('input', () => {
      state.questions[textarea.dataset.cycleQuestion] = textarea.value;
      saveState();
      const saved = textarea.closest('.question-box')?.querySelector('.question-saved');
      if (saved) saved.textContent = textarea.value.trim() ? '已保存到本机' : '';
    });
  });
  document.querySelectorAll('[data-copy-help]').forEach((button) => {
    button.addEventListener('click', async () => {
      const panel = button.closest('[data-cycle-panel]');
      const prompt = helpPrompt(panel);
      try {
        await navigator.clipboard.writeText(prompt);
        button.textContent = '已复制提示词';
        setTimeout(() => { button.textContent = '复制给 ChatGPT'; }, 1800);
      } catch (error) {
        button.textContent = '请手动复制';
      }
    });
  });
  document.querySelector('[data-copy-progress]')?.addEventListener('click', async (event) => {
    const button = event.currentTarget;
    try {
      await navigator.clipboard.writeText(progressPrompt());
      button.textContent = '已复制进度';
      setTimeout(() => { button.textContent = '复制进度'; }, 1800);
    } catch (error) {
      button.textContent = '请手动复制';
    }
  });
  window.addEventListener('popstate', () => { const stateFromUrl = stateFromHash(); activateSection(stateFromUrl.section, stateFromUrl.cycle, false, false); });
  window.addEventListener('hashchange', () => { const stateFromUrl = stateFromHash(); activateSection(stateFromUrl.section, stateFromUrl.cycle, false, false); });
  window.addEventListener('storage', (event) => { if (event.key === storageKey) { state = loadState(); refreshState(); } });

  const courseDialog = document.querySelector('#course-dialog');
  document.querySelector('[data-open-course-dialog]')?.addEventListener('click', () => courseDialog?.showModal());
  document.querySelector('[data-close-course-dialog]')?.addEventListener('click', () => courseDialog?.close());
  refreshState();
  const initial = stateFromHash();
  activateSection(initial.section, initial.cycle, false, false);
})();
"""


def render_html(
    manifest: dict[str, Any],
    facts: dict[str, Any],
    progress: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
    css: str,
) -> str:
    chapter = int(progress["chapter"])
    title = _chapter_title(manifest, chapter)
    required = list(progress["course_ledger"]["required_course_keys"])
    statuses = _course_status(progress)
    completed = sum(statuses.get(key) == "simulated_completed" for key in required)
    section_by_id = _section_rows(facts)
    progress_by_section = {str(row["section"]): row for row in progress.get("sections", [])}
    chapter_cycle_count = sum(
        len(section_by_id[section_id].get("cycles", []))
        for section_id in facts["manifest_sections"]
    )

    nav = []
    mobile_options = []
    sections_html = []
    for section_index, manifest_section in enumerate(manifest.get("sections", [])):
        section_id = str(manifest_section["id"])
        section_title = _text(manifest_section.get("label")) or section_id
        anchor = f"section-{_anchor(section_id)}"
        nav.append(
            f'<button type="button" role="tab" class="section-tab" data-section-target="{anchor}" '
            f'aria-controls="{anchor}" aria-selected="{str(section_index == 0).lower()}">{escape(section_title)}</button>'
        )
        mobile_options.append(f'<option value="{anchor}">{escape(section_title)}</option>')
        section = section_by_id[section_id]
        section_progress = progress_by_section[section_id]
        section_courses = _section_course_keys(section, required)
        course_cycles = _course_cycle_entries(section, catalog, required)
        cycles = sorted(section.get("cycles", []), key=lambda row: int(row.get("sequence") or 0))
        outline_rows = []
        cycle_panels = []
        for cycle in cycles:
            sequence = int(cycle.get("sequence") or 0)
            cycle_token = _cycle_state_token(section_id, sequence)
            items = _cycle_items(section, sequence)
            cycle_courses = _cycle_course_keys(items, cycle)
            topics = _cycle_topics(items, cycle)
            course_text = "、".join(_course_label(catalog, key) for key in cycle_courses) or "沿用已学课程"
            course_lines = _course_lines_html(catalog, cycle_courses)
            order_text = _item_order(items) or "完成本循环方法检查"
            grouped = _group_labels(items)
            outline_rows.append(
                f'<div class="outline-row" data-cycle-state="{escape(cycle_token)}" '
                f'data-cycle-title="{escape(_text(cycle.get("title")))}" '
                f'data-cycle-courses="{escape(course_text)}" data-cycle-order="{escape(order_text)}">'
                f'<div class="route-marker"><span>{sequence:02d}</span></div>'
                f'<button type="button" class="outline-main" data-cycle-target="{sequence}">'
                f'<span class="outline-cycle"><strong>{escape(_text(cycle.get("title")))}</strong><span>循环 {sequence} · {len(items)} 个教材项目</span></span>'
                f'<span class="outline-column outline-courses"><strong>先听课程</strong>{course_lines}</span>'
                f'<span class="outline-column outline-order"><strong>做题顺序</strong><span>{escape(order_text)}</span><small>{escape("、".join(topics))}</small></span>'
                '</button>'
                '<div class="route-actions">'
                f'<button type="button" class="cycle-star" data-star-cycle="{escape(cycle_token)}" aria-pressed="false" aria-label="标记循环" title="标记循环">☆</button>'
                f'<button type="button" class="cycle-listen" data-listen-cycle="{escape(cycle_token)}" aria-pressed="false">标记已听完</button>'
                '</div>'
                '</div>'
            )
            sequence_html = "".join(
                f'<div class="sequence-line"><strong>{escape(role)}</strong><span>{escape("、".join(labels))}</span></div>'
                for role, labels in grouped
            )
            sequence_html = (
                f'<div class="sequence-line sequence-order"><strong>题序</strong><span data-help-order>{escape(order_text)}</span></div>'
                + sequence_html
            )
            checks = _lines(cycle.get("acceptance_checks"))
            acceptance = (
                '<div class="acceptance"><strong>循环验收</strong>' + _html_list(checks) + '</div>'
                if checks else ""
            )
            mapping_rows = "".join(
                '<tr class="mapping-row">'
                f'<td><strong>{escape(_text(item.get("label")))}</strong></td>'
                f'<td>{escape(_item_topic(item, cycle))}</td>'
                f'<td>{escape(_text(item.get("position")))}</td>'
                f'<td>{escape(VISUAL_LABELS.get(_text((item.get("visual_dependency") or {}).get("status")), _text((item.get("visual_dependency") or {}).get("status"))))}</td>'
                '</tr>'
                for item in items
            )
            mapping = (
                '<h4 class="mapping-heading">教材对应</h4>'
                '<table class="mapping-table"><thead><tr><th>项目</th><th>所属知识/类型</th><th>教材角色</th><th>内容状态</th></tr></thead>'
                f'<tbody>{mapping_rows}</tbody></table>'
                if items else ""
            )
            cycle_panels.append(
                f'<section class="cycle-panel" data-cycle-panel="{sequence}" data-cycle-state="{escape(cycle_token)}" hidden>'
                '<button type="button" class="back-to-route" data-cycle-back>← 返回本节学习路线</button>'
                '<div class="cycle-heading"><div class="cycle-heading-copy">'
                f'<h3>循环 {sequence}｜{escape(_text(cycle.get("title")))}</h3>'
                f'<p>{len(items)} 个教材项目</p></div>'
                '<div class="cycle-heading-actions">'
                f'<button type="button" class="cycle-star" data-star-cycle="{escape(cycle_token)}" aria-pressed="false" aria-label="标记循环" title="标记循环">☆</button>'
                f'<button type="button" class="cycle-listen" data-listen-cycle="{escape(cycle_token)}" aria-pressed="false">标记循环已听完</button>'
                '</div>'
                '<dl class="cycle-facts">'
                f'<div><dt>听课</dt><dd data-help-courses>{course_lines}</dd></div>'
                f'<div><dt>知识/类型</dt><dd>{escape("、".join(topics))}</dd></div>'
                '</dl></div>'
                f'<div class="sequence-list">{sequence_html}</div>'
                '<div class="question-box">'
                '<div class="question-heading"><strong>本循环疑问</strong><span class="question-saved" aria-live="polite"></span></div>'
                f'<textarea data-cycle-question="{escape(cycle_token)}" placeholder="写下你哪里不懂，做题顺序和课程依据会自动带入 ChatGPT。"></textarea>'
                '<div class="question-actions"><button type="button" class="copy-help" data-copy-help>复制给 ChatGPT</button><span>粘贴到项目“数学选择性必修一”的新聊天</span></div>'
                '</div>'
                f'{acceptance}{mapping}'
                + ('<h4 class="items-heading">逐题方法</h4>' if items else '')
                + '<div class="items">'
                + "".join(_html_item(item, cycle, catalog, _item_state_token(section_id, sequence, item)) for item in items)
                + '</div></section>'
            )
        section_course_rows = []
        for course_index, key in enumerate(section_courses, start=1):
            cycle_entries = course_cycles.get(key, [])
            cycle_tokens = " ".join(_cycle_state_token(section_id, sequence) for sequence, _ in cycle_entries)
            cycle_labels = "、".join(f"循环 {sequence}" for sequence, _ in cycle_entries) or "本节前置"
            section_course_rows.append(
                f'<div class="section-course-row" data-course-row data-course-key="{escape(key)}" '
                f'data-course-cycles="{escape(cycle_tokens)}">'
                f'<span class="course-index">{course_index:02d}</span>'
                f'<span class="course-code">{escape(_course_number(catalog, key))}</span>'
                f'<span class="course-name">{escape(_course_title(catalog, key))}</span>'
                f'<span class="course-cycle">{escape(cycle_labels)}</span>'
                '<span class="course-state" data-course-status>待学习</span>'
                '</div>'
            )
        status = str(section_progress["status"])
        overview_panel = (
            '<section class="cycle-panel" data-cycle-panel="outline">'
            '<div class="outline-heading">'
            '<div><span class="eyebrow">按顺序完成</span><h3>本节学习路线</h3></div>'
            f'<p>{len(cycles)} 个循环，先听对应课程，再按题序完成教材项目。</p>'
            '</div>'
            f'<div class="outline-table">{"".join(outline_rows)}</div>'
            '</section>'
        )
        sections_html.append(
            f'<section class="section-panel" data-section-panel="{anchor}" '
            f'{"" if section_index == 0 else "hidden"}>'
            '<div class="section-header"><div>'
            f'<span class="section-breadcrumb">第 {chapter} 章 / {escape(section_id)}</span>'
            f'<h2>{escape(section_title)}</h2>'
            f'<p>本节 {section["coverage"]["delivered_items"]} 项题目 · <span data-section-progress-label>0/{len(cycles)} 循环已听完</span></p>'
            f'</div><span class="section-scope">SECTION {escape(section_id)}</span></div>'
            '<div class="section-progress"><div class="progress-track"><span data-section-progress-fill></span></div></div>'
            '<section class="next-step" data-next-step>'
            '<div class="next-step-label"><span>下一步</span><strong data-next-cycle>循环 1</strong></div>'
            '<div class="next-step-main"><h3 data-next-title>开始本节第一个循环</h3><p data-next-course>先听对应课程</p></div>'
            '<div class="next-step-order"><span>随后完成</span><strong data-next-order>按教材顺序推进</strong></div>'
            '</section>'
            + overview_panel
            + '<aside class="section-course-path"><div class="section-block-heading">'
            '<div><span class="eyebrow">本节资源</span><h3>课程队列</h3></div>'
            f'<span>{len(section_courses)} 门</span></div>'
            '<div class="section-course-table">'
            '<div class="section-course-head"><span>序号</span><span>课程编号</span><span>课程名称</span><span>使用位置</span><span>状态</span></div>'
            + "".join(section_course_rows)
            + '</div></aside>'
            + "".join(cycle_panels)
            + '</section>'
        )

    course_list = "".join(
        '<div class="course-row">'
        f'<span>{index}</span>'
        f'<span>{escape(_course_label(catalog, key))}<small>{escape(_course_video(catalog, key))}</small></span>'
        f'<span class="status status-{escape(statuses.get(key, "planned"))}">'
        f'{escape(STATUS_LABELS.get(statuses.get(key, "planned"), statuses.get(key, "planned")))}</span>'
        '</div>'
        for index, key in enumerate(required, start=1)
    )
    human = str(progress["human_learning_status"])
    script = _interaction_script()
    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{escape(title)}学习路径</title>
  <style>{css}</style>
  <script defer src="../../data/assets/mathjax/3.2.2/es5/tex-chtml-full.js"></script>
</head>
<body data-chapter="{chapter}">
  <header class="app-header">
    <div class="brand"><span class="brand-kicker">一本通 · 学习工作台</span><h1>{escape(title)}</h1></div>
    <div class="header-actions">
      <button type="button" class="progress-trigger" data-copy-progress>复制进度</button>
      <button type="button" class="course-trigger" data-open-course-dialog>本章课程</button>
    </div>
  </header>
  <section class="chapter-dashboard" aria-label="章节学习看板">
    <div class="chapter-dashboard-heading">
      <span class="eyebrow">章节进度</span>
      <h2>本章学习概览</h2>
      <p>课程、题目和循环分别记录，互不混淆。</p>
    </div>
    <div class="dashboard-stat dashboard-stat-course"><span>本章课程</span><strong data-dashboard-course-progress>0/{len(required)}</strong><small>听完课程</small></div>
    <div class="dashboard-stat dashboard-stat-item"><span>教材项目</span><strong data-dashboard-item-progress>0/{facts['canonical_item_count']}</strong><small>通过项目</small></div>
    <div class="dashboard-stat dashboard-stat-section"><span>节次完成</span><strong data-dashboard-section-progress>0/{len(facts['manifest_sections'])}</strong><small>完成节次</small></div>
    <div class="dashboard-stat dashboard-stat-cycle"><span>循环完成</span><strong data-dashboard-cycle-progress>0/{chapter_cycle_count}</strong><small>循环已听完</small></div>
  </section>
  <div class="mobile-section-picker">
    <label for="section-select">当前节次</label>
    <select id="section-select">{''.join(mobile_options)}</select>
  </div>
  <div class="app-shell">
    <aside class="section-rail"><span class="rail-kicker">第 {chapter} 章</span><p class="rail-label">{escape(title)}</p><nav class="section-tabs">{''.join(nav)}</nav></aside>
    <main class="workspace">{''.join(sections_html)}</main>
  </div>
  <dialog class="course-dialog" id="course-dialog">
    <div class="dialog-header"><h2>本章课程清单</h2><button type="button" class="dialog-close" data-close-course-dialog aria-label="关闭">×</button></div>
    <div class="dialog-body">{course_list}</div>
  </dialog>
  <script>{script}</script>
</body>
</html>
'''
    match = FORBIDDEN_RE.search(html)
    if match:
        raise ValueError(f"learner-facing HTML contains forbidden content: {match.group(0)}")
    return html


def render_chapter(project_root: Path, chapter: int, output_root: Path) -> dict[str, Any]:
    facts = chapter_facts(project_root, chapter)
    manifest = load_json(project_root / f"chapter{chapter}_manifest.json")
    progress_path = project_root / "data" / "learner_progress" / f"chapter{chapter}.json"
    progress = load_json(progress_path)
    if progress.get("source_binding") != facts["source_binding"]:
        raise ValueError(f"chapter {chapter} progress is stale")
    catalog = _catalog(project_root)
    css_path = Path(__file__).resolve().parents[1] / "assets" / "chapter-report.css"
    css = css_path.read_text(encoding="utf-8")
    markdown = render_markdown(manifest, facts, progress, catalog)
    html = render_html(manifest, facts, progress, catalog, css)

    output_root.mkdir(parents=True, exist_ok=True)
    markdown_path = output_root / f"chapter{chapter}.md"
    html_path = output_root / f"chapter{chapter}.html"
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return {
        "chapter": chapter,
        "status": progress["status"],
        "required_courses": len(progress["course_ledger"]["required_course_keys"]),
        "unfinished_courses": len(progress["course_ledger"]["unfinished_course_keys"]),
        "canonical_items": facts["canonical_item_count"],
        "sections": len(facts["manifest_sections"]),
        "markdown": _display_path(markdown_path, project_root),
        "markdown_sha256": sha256_file(markdown_path),
        "html": _display_path(html_path, project_root),
        "html_sha256": sha256_file(html_path),
        "progress_sha256": sha256_file(progress_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chapter", type=int, action="append")
    parser.add_argument("--output-root", default="reports/learner_compact")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = project_root / output_root
    chapters = args.chapter or [1, 2]
    reports = [render_chapter(project_root, chapter, output_root) for chapter in chapters]
    manifest = {
        "schema_version": "ybt-compact-learning-output-v1",
        "status": "passed",
        "chapters": reports,
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
