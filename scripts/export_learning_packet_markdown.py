from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMG_SRC_RE = re.compile(r'(?P<prefix>src=["\'])imgs/(?P<name>[^"\']+)(?P<suffix>["\'])')
LEADING_HEADING_RE = re.compile(r"^#{1,6}\s+")
NUMBERED_BODY_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+(?=\d+[.．、])")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_embedded_images(text: str) -> str:
    return IMG_SRC_RE.sub(
        lambda match: f'{match.group("prefix")}../../ocr_live_current/first_chapter_69/imgs/{match.group("name")}{match.group("suffix")}',
        text,
    )


def clean_body_text(text: str) -> str:
    return NUMBERED_BODY_HEADING_RE.sub("", LEADING_HEADING_RE.sub("", text.strip()))


def render_instruction_text(text: str, *, sanitize_text_only: bool = False) -> str:
    if sanitize_text_only:
        # OCR/HTML source occasionally stores a literal backslash-n inside a table cell.
        # Only remove a literal OCR line-break marker; keep LaTeX commands
        # such as ``\neq`` intact.
        text = re.sub(r"\\n(?![A-Za-z])[ \t]*", "", text)
        text = text.replace(
            "则  \\(A, P\\)，",
            "则 \\(A, P, B\\) 共线当且仅当 \\(x+y=1\\)。",
        )
        text = text.replace(
            "则  \\(P, A, B\\)，",
            "则 \\(P, A, B, C\\) 共面当且仅当 \\(x+y+z=1\\)。",
        )
    lines = []
    for line in text.strip().splitlines():
        match = re.match(r"^#{1,6}\s+(.+)$", line)
        lines.append(f"**{match.group(1).strip()}**" if match else line)
    return "\n".join(lines)


def remove_visuals(text: str) -> str:
    """Keep the text-only preview free of textbook image payloads."""
    text = re.sub(r"<img\b[^>]*>", "", text, flags=re.IGNORECASE)
    return re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)


def append_images(lines: list[str], item: dict, source_text: str) -> None:
    for index, image in enumerate(item.get("image_refs", []), start=1):
        ref = str(image.get("ref", "")).replace("\\", "/")
        if not ref or ref in source_text:
            continue
        lines.extend(["", f"![配图{index}](../../ocr_live_current/first_chapter_69/imgs/{Path(ref).name})"])


def section_plan(plan: dict, section: str) -> dict:
    try:
        return next(item for item in plan.get("plan", []) if item.get("section") == section)
    except StopIteration as exc:
        raise ValueError(f"missing learning plan for section {section}") from exc


def course_index(plan_section: dict) -> dict[str, dict]:
    courses = plan_section.get("must_listen_courses") or [
        *plan_section.get("required_courses", []),
        *plan_section.get("support_courses", []),
    ]
    return {str(item.get("course_key")): item for item in courses}


def export_markdown(packet: dict, plan: dict, bridges: dict) -> str:
    section = str(packet.get("section", "unknown"))
    cycles = packet.get("learning_cycles") or []
    if not cycles:
        raise ValueError(f"section {section} has no verified learning_cycles mapping")

    plan_section = section_plan(plan, section)
    courses = course_index(plan_section)
    bridge_by_id = {str(item.get("id")): item for item in bridges.get("units", [])}
    knowledge_by_id = {str(item.get("id")): item for item in plan_section.get("knowledge_points", [])}
    type_by_name = {str(item.get("type")): item for item in plan_section.get("type_training", [])}
    counts = packet.get("counts", {})
    total_tasks = int(counts.get("total_numbered_learning_items", 0))
    task_width = max(2, len(str(total_tasks)))
    task_number = 0

    def next_task_label() -> str:
        nonlocal task_number
        task_number += 1
        return f"任务 {task_number:0{task_width}d}"

    def visual_note(status: str | None) -> str:
        return {
            "READY_TEXT_ONLY": "图形状态：纯文字可作答",
            "VISION_VERIFIED": "图形状态：视觉已核验",
            "NEEDS_VISION_SIDECAR": "图形状态：未完成视觉核验，禁止猜图；先补视觉侧车再作答",
        }.get(str(status or "UNKNOWN"), "图形状态：未确认，先核对原图再作答")

    lines = [
        f"# {plan_section.get('label', section)}：按课程循环学习路径",
        "",
        f"> 状态：`{packet.get('status', 'UNKNOWN')}`",
        f"> 共 {len(cycles)} 个学习循环；教学例题 {counts.get('worked_examples', 0)} 道、直接变式 {counts.get('direct_variants', 0)} 道、A/B/C 习题 {counts.get('abc_exercises', 0)} 道。",
        "> 这是一张完整路线图。实际学习时一次只执行“当前循环”的一个动作，本批未通过不得进入下一批。",
        "> `任务 01` 起为整节连续学习序号；例题、变式和 A/B/C 标签保留教材原编号，教材例号跳跃不代表漏题。",
        "",
        "## 执行规则",
        "",
        "1. 用户报出要学的小节后，先给当前循环需要看的视频，不一次性倾倒整节任务。",
        "2. 视频看完，立即学习本批知识点和右侧例题；例题教学阶段允许看完整解法。",
        "3. 随后独立完成本批直属变式和对应 A/B/C 习题，作答阶段隐藏答案。",
        "4. 只检查第一处断点并给最小提示；蒙对、提示后答对或看答案不算本批独立通过。",
        "5. 本批例题、直属变式、配套题和独立复测证据齐全后，才进入下一循环。",
        "",
    ]

    for cycle in cycles:
        sequence = cycle.get("sequence")
        title = cycle.get("title")
        lines.extend(["---", "", f"## 循环 {sequence}/{len(cycles)}：{title}", ""])

        lines.extend(["### 当前动作 1：看本批视频", ""])
        cycle_course_keys = list(cycle.get("course_keys", []))
        if cycle_course_keys:
            for key in cycle_course_keys:
                course = courses.get(str(key))
                if not course:
                    raise ValueError(f"cycle {cycle.get('cycle_id')} references unknown course {key}")
                course_id = course.get("original_course_id")
                files = course.get("recommended_video_files") or course.get("video_files") or []
                if not files:
                    raise ValueError(f"course {key} has no video file")
                lines.append(f"- `{course_id}` {Path(files[0]).stem}")
                lines.append(f"  - 文件：`{files[0]}`")
        else:
            lines.append("- 本循环没有新增视频，复用已通过的前置方法。")
        prerequisites = cycle.get("prerequisite_course_keys", [])
        if prerequisites:
            lines.append(f"- 前置方法必须已通过：`{', '.join(prerequisites)}`")
        lines.extend(["", "> 看完本批视频后停下来，不要提前观看下一循环。", ""])

        lines.extend(["### 当前动作 2：按本批做题路径推进", ""])
        knowledge_refs = cycle.get("knowledge_refs", [])
        prerequisite_knowledge_refs = cycle.get("prerequisite_knowledge_refs", [])
        type_refs = cycle.get("type_refs", [])
        if prerequisite_knowledge_refs:
            lines.append("本批复用的左侧知识点（前置循环必须已通过）：")
            prerequisite_blocks = {item.get("id"): item for item in cycle.get("prerequisite_knowledge_blocks", [])}
            for ref in prerequisite_knowledge_refs:
                block = prerequisite_blocks.get(ref, {})
                lines.append(f"- `{ref}` {block.get('label', ref)}")
        if knowledge_refs:
            lines.append("本批知识点：")
            for ref in knowledge_refs:
                item = knowledge_by_id.get(str(ref), {})
                lines.append(f"- `{ref}` {item.get('label', ref)}")
        if type_refs:
            lines.append("本批类型：")
            for ref in type_refs:
                item = type_by_name.get(str(ref), {})
                focus = item.get("focus")
                lines.append(f"- {ref}" + (f"：{focus}" if focus else ""))

        bridge_ids = cycle.get("bridge_unit_ids", [])
        if bridge_ids:
            lines.extend(["", "本批补充桥接："])
            for bridge_id in bridge_ids:
                bridge = bridge_by_id.get(str(bridge_id))
                if not bridge:
                    raise ValueError(f"cycle {cycle.get('cycle_id')} references unknown bridge {bridge_id}")
                lines.append(f"- **{bridge.get('title', bridge_id)}** (`{bridge_id}`)")
                for step in bridge.get("lesson_steps", []):
                    lines.append(f"  - {step}")

        variants_by_parent: dict[int, list[dict]] = {}
        for variant in cycle.get("direct_variants", []):
            variants_by_parent.setdefault(variant.get("parent_example_number"), []).append(variant)

        cycle_knowledge = {str(item.get("id")): item for item in cycle.get("knowledge_blocks", [])}
        shown_knowledge: set[str] = set()
        shown_types: set[str] = set()
        for item in cycle.get("worked_examples", []):
            role_ref = str(item.get("role_ref", ""))
            if item.get("role") == "knowledge_example" and role_ref not in shown_knowledge:
                block = cycle_knowledge.get(role_ref)
                if not block:
                    raise ValueError(f"cycle {cycle.get('cycle_id')} missing knowledge block {role_ref}")
                lines.extend([
                    "",
                    f"#### 左侧知识点｜`{role_ref}` {block.get('label', role_ref)}",
                    "",
                    render_instruction_text(str(block.get("text", ""))),
                    "",
                    f"> 对应教材例题：{', '.join(block.get('example_labels', []))}",
                ])
                shown_knowledge.add(role_ref)
            elif item.get("role") == "type_example" and role_ref not in shown_types:
                type_item = type_by_name.get(role_ref, {})
                focus = type_item.get("focus")
                lines.extend(["", f"#### 方法类型｜{role_ref}" + (f"：{focus}" if focus else "")])
                shown_types.add(role_ref)
            lines.extend(["", f"#### {next_task_label()}｜{item.get('label', '例题')}", ""])
            teaching = clean_body_text(str(item.get("teaching_text") or item.get("question_text") or ""))
            lines.append(normalize_embedded_images(teaching))
            append_images(lines, item, teaching)
            for variant in variants_by_parent.get(item.get("example_number"), []):
                parent = variant.get("parent_example_number")
                lines.extend(["", f"##### {next_task_label()}｜紧跟：{variant.get('label', '变式')}（对应例{parent}，无解答）", ""])
                question = clean_body_text(str(variant.get("question_text", "")))
                lines.append(normalize_embedded_images(question))
                append_images(lines, variant, question)

        if not cycle.get("direct_variants", []):
            lines.extend(["", "- 本批例题没有直属变式，按路线进入对应配套题。"])

        for checkpoint in cycle.get("method_checkpoints", []):
            lines.extend([
                "",
                f"#### 方法检查｜`{checkpoint.get('id')}` {checkpoint.get('label', '')}（不计入教材题量）",
                "",
                clean_body_text(str(checkpoint.get("question_text", ""))),
                "",
                "> 独立作答，不提供答案；未通过时停在本循环。",
            ])

        lines.extend(["", "### 当前动作 3：做本批对应 A/B/C 习题（无答案）", ""])
        route_refs = [
            *cycle.get("prerequisite_knowledge_refs", []),
            *cycle.get("knowledge_refs", []),
            *cycle.get("type_refs", []),
        ]
        if route_refs:
            lines.extend([f"> 本批配套题承接：{', '.join(route_refs)}", ""])
        exercises = cycle.get("exercise_questions", [])
        if not exercises:
            lines.append("- 当前覆盖账本没有为本批单独分配 A/B/C 题；用本批例题过程与未见变式验收，不从题名猜题。")
        current_group = None
        for item in exercises:
            group = str(item.get("group", "?"))
            if group != current_group:
                current_group = group
                lines.extend(["", f"#### {group}组"])
            number = item.get("number", "?")
            lines.extend(["", f"##### {next_task_label()}｜{group}{number}", ""])
            question = clean_body_text(str(item.get("question_text", "")))
            lines.append(normalize_embedded_images(question))
            append_images(lines, item, question)

        lines.extend(
            [
                "",
                "### 当前动作 4：本批验收",
                "",
                "- [ ] 能闭卷复述本批方法及适用条件。",
                "- [ ] 教学例题能解释关键步骤，不只是记住结论。",
                "- [ ] 直属变式和对应习题有独立过程。",
                "- [ ] 若使用过提示或答案，已用未见题或延迟闭卷复测补证。",
                "- [ ] 当前循环没有未解决的第一断点。",
                "",
                f"> **推进门：** {cycle.get('advance_gate')}",
                f"> **失败处理：** {cycle.get('failure_rule')}",
                "> 未满足推进门时停在本循环，不展示下一循环的当前动作。",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "## 小节收尾",
            "",
            "所有循环通过后，再做未见近迁移；至少间隔 24 小时后执行闭卷复测。",
            "课程看完、题包可消费或同会话提示后答对，都不能单独替代掌握证据。",
            "",
        ]
    )
    if task_number != total_tasks:
        raise ValueError(f"numbered task count mismatch: rendered={task_number}, expected={total_tasks}")
    return "\n".join(lines)


def _export_without_questions_legacy(packet: dict, plan: dict, bridges: dict) -> str:
    """Render the full study order while omitting every question body and solution."""
    section = str(packet.get("section", "unknown"))
    cycles = packet.get("learning_cycles") or []
    if not cycles:
        raise ValueError(f"section {section} has no verified learning_cycles mapping")

    plan_section = section_plan(plan, section)
    courses = course_index(plan_section)
    bridge_by_id = {str(item.get("id")): item for item in bridges.get("units", [])}
    type_by_name = {str(item.get("type")): item for item in plan_section.get("type_training", [])}
    counts = packet.get("counts", {})
    total_tasks = int(counts.get("total_numbered_learning_items", 0))
    task_width = max(2, len(str(total_tasks)))
    task_number = 0

    def next_task_label() -> str:
        nonlocal task_number
        task_number += 1
        return f"任务 {task_number:0{task_width}d}"

    lines = [
        f"# {plan_section.get('label', section)}：无题目学习路线预览",
        "",
        f"> 共 {len(cycles)} 个学习循环；教学例题 {counts.get('worked_examples', 0)} 道、直接变式 {counts.get('direct_variants', 0)} 道、A/B/C 习题 {counts.get('abc_exercises', 0)} 道。",
        "> 本文件只展示视频、左栏知识、方法桥接和做题编号顺序，不展示任何题干、选项、解答、答案、出处年份或题目配图。",
        "",
        "## 使用顺序",
        "",
        "1. 只看当前循环列出的视频。",
        "2. 学完当前循环的左栏知识和补充桥接。",
        "3. 按编号依次完成例题、直属变式和 A/B/C 题。",
        "4. 当前循环验收通过后再进入下一循环。",
        "",
    ]

    shown_knowledge: set[str] = set()
    for cycle in cycles:
        sequence = cycle.get("sequence")
        title = cycle.get("title")
        lines.extend(["---", "", f"## 循环 {sequence}/{len(cycles)}：{title}", ""])

        lines.extend(["### 1. 视频", ""])
        course_keys = list(cycle.get("course_keys", []))
        if course_keys:
            for key in course_keys:
                course = courses.get(str(key))
                if not course:
                    raise ValueError(f"cycle {cycle.get('cycle_id')} references unknown course {key}")
                files = course.get("recommended_video_files") or course.get("video_files") or []
                if not files:
                    raise ValueError(f"course {key} has no video file")
                lines.append(f"- `{course.get('original_course_id')}` {Path(files[0]).stem}")
                lines.append(f"  - 文件：`{files[0]}`")
        else:
            lines.append("- 无新增视频，复用前面已经通过的方法。")
        prerequisites = cycle.get("prerequisite_course_keys", [])
        if prerequisites:
            lines.append(f"- 前置课程：`{', '.join(prerequisites)}`")

        lines.extend(["", "### 2. 左栏知识与方法", ""])
        prerequisite_blocks = {item.get("id"): item for item in cycle.get("prerequisite_knowledge_blocks", [])}
        for ref in cycle.get("prerequisite_knowledge_refs", []):
            block = prerequisite_blocks.get(ref, {})
            lines.append(f"- 复用 `{ref}` {block.get('label', ref)}")

        cycle_blocks = {str(item.get("id")): item for item in cycle.get("knowledge_blocks", [])}
        for ref in cycle.get("knowledge_refs", []):
            block = cycle_blocks.get(str(ref))
            if not block:
                raise ValueError(f"cycle {cycle.get('cycle_id')} missing knowledge block {ref}")
            lines.extend(["", f"#### 左侧知识点｜`{ref}` {block.get('label', ref)}", ""])
            if ref not in shown_knowledge:
                lines.append(remove_visuals(render_instruction_text(str(block.get("text", "")))))
                shown_knowledge.add(str(ref))
            lines.extend(["", f"> 对应教材例题编号：{', '.join(block.get('example_labels', []))}"])

        for ref in cycle.get("type_refs", []):
            type_item = type_by_name.get(str(ref), {})
            focus = type_item.get("focus")
            lines.append(f"- {ref}" + (f"：{focus}" if focus else ""))

        bridge_ids = cycle.get("bridge_unit_ids", [])
        if bridge_ids:
            lines.extend(["", "#### 补充桥接", ""])
            for bridge_id in bridge_ids:
                bridge = bridge_by_id.get(str(bridge_id))
                if not bridge:
                    raise ValueError(f"cycle {cycle.get('cycle_id')} references unknown bridge {bridge_id}")
                lines.append(f"- **{bridge.get('title', bridge_id)}** (`{bridge_id}`)")
                for step in bridge.get("lesson_steps", []):
                    lines.append(f"  - {step}")
                targets = []
                for target in bridge.get("target_questions", []):
                    target = str(target)
                    prefix = f"{section}-"
                    if target.startswith(prefix):
                        targets.append(target[len(prefix):])
                if targets:
                    lines.append(f"  - 服务题号：{', '.join(targets)}")

        lines.extend(["", "### 3. 做题编号顺序", ""])
        variants_by_parent: dict[int, list[dict]] = {}
        for variant in cycle.get("direct_variants", []):
            variants_by_parent.setdefault(variant.get("parent_example_number"), []).append(variant)

        for item in cycle.get("worked_examples", []):
            role_ref = item.get("role_ref")
            suffix = f"｜承接：{role_ref}" if role_ref else ""
            lines.append(f"- `{next_task_label()}` 教材{item.get('label', '例题')}{suffix}")
            for variant in variants_by_parent.get(item.get("example_number"), []):
                parent = variant.get("parent_example_number")
                lines.append(f"- `{next_task_label()}` {variant.get('label', '变式')}({parent})")

        for checkpoint in cycle.get("method_checkpoints", []):
            lines.append(f"- 方法检查：{checkpoint.get('label', checkpoint.get('id'))}（内容隐藏）")

        exercises = cycle.get("exercise_questions", [])
        if exercises:
            for item in exercises:
                group = str(item.get("group", "?"))
                number = item.get("number", "?")
                lines.append(f"- `{next_task_label()}` {group}{number}")
        elif not cycle.get("worked_examples", []) and not cycle.get("method_checkpoints", []):
            lines.append("- 本循环没有单独分配教材题。")

        lines.extend([
            "",
            "### 4. 验收",
            "",
            "- [ ] 能闭卷复述本循环知识和方法的适用条件。",
            "- [ ] 已按上面的编号顺序独立完成全部项目。",
            "- [ ] 使用过提示的项目已经完成未见迁移或延迟复测。",
            "- [ ] 没有未解决的第一断点。",
            f"- 推进门：{cycle.get('advance_gate')}",
            f"- 失败处理：{cycle.get('failure_rule')}",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 小节完成门",
        "",
        "全部循环通过后，再做未见近迁移；至少间隔 24 小时完成闭卷复测。",
        "",
    ])
    if task_number != total_tasks:
        raise ValueError(f"numbered task count mismatch: rendered={task_number}, expected={total_tasks}")
    return "\n".join(lines)


def export_without_questions(
    packet: dict,
    plan: dict,
    bridges: dict,
    coverage: dict | None = None,
) -> str:
    """Export the user-facing route in the textbook's knowledge-to-exercise order."""
    section = str(packet.get("section", "unknown"))
    cycles = packet.get("learning_cycles") or []
    if not cycles:
        raise ValueError(f"section {section} has no verified learning_cycles mapping")

    plan_section = section_plan(plan, section)
    courses = course_index(plan_section)
    bridge_by_id = {str(item.get("id")): item for item in bridges.get("units", [])}
    type_by_name = {str(item.get("type")): item for item in plan_section.get("type_training", [])}
    plan_knowledge_by_id = {
        str(item.get("id")): item for item in plan_section.get("knowledge_points", [])
    }
    coverage_by_key = {
        str(item.get("question_key")): item
        for item in (coverage or {}).get("questions", [])
        if item.get("section") == section
    }
    counts = packet.get("counts", {})
    total_tasks = int(counts.get("total_numbered_learning_items", 0))
    task_width = max(2, len(str(total_tasks)))
    task_number = 0
    rendered_examples: set[str] = set()
    rendered_variants: set[str] = set()
    rendered_exercises: set[str] = set()
    shown_knowledge: set[str] = set()
    group_titles = {
        "A": "A 组 夯实基础",
        "B": "B 组 强化能力",
        "C": "C 组 拓展提升",
    }
    unlock_titles = {
        "COURSE_DIRECT": "听完直接对应课程并完成前置例题后",
        "METHOD_BRIDGE": "完成本批方法桥接后",
        "MICRO_UNIT": "完成本批专项微单元后",
    }

    def next_task_label() -> str:
        nonlocal task_number
        task_number += 1
        return f"任务 {task_number:0{task_width}d}"

    def visual_note(status: str | None) -> str:
        return {
            "READY_TEXT_ONLY": "图形状态：纯文字可作答",
            "VISION_VERIFIED": "图形状态：视觉已核验",
            "NEEDS_VISION_SIDECAR": "图形状态：未完成视觉核验，禁止猜图；先补视觉侧车再作答",
        }.get(str(status or "UNKNOWN"), "图形状态：未确认，先核对原图再作答")

    def knowledge_title(ref: str, block: dict | None = None) -> str:
        source = block or plan_knowledge_by_id.get(str(ref), {})
        label = str(source.get("label") or ref)
        match = re.search(r"[-_]k(\d+)$", str(ref))
        if match:
            return f"知识点 {match.group(1)}：{label}"
        return label

    def course_title(course: dict) -> str:
        files = course.get("recommended_video_files") or course.get("video_files") or []
        if not files:
            return str(course.get("original_course_id") or course.get("course_key"))
        stem = Path(files[0]).stem
        course_id = str(course.get("original_course_id") or "")
        return stem[len(course_id):].lstrip(" .") if course_id and stem.startswith(course_id) else stem

    def course_summary(course: dict) -> str:
        course_id = str(course.get("original_course_id") or "未知课程编号")
        role = "必听主课" if course.get("role") == "required" else "补充课程"
        return f"`{course_id}` {course_title(course)}（{role}）"

    def course_summaries(keys: list[str]) -> list[str]:
        result: list[str] = []
        for key in keys:
            course = courses.get(str(key))
            if not course:
                raise ValueError(f"unknown course {key} in section {section}")
            summary = course_summary(course)
            if summary not in result:
                result.append(summary)
        return result

    def method_family(*values: str) -> str:
        text = " ".join(str(value) for value in values if value)
        if "外接球" in text or "压轴综合" in text:
            return "综合题"
        if "二面角" in text:
            return "二面角"
        if "求长度" in text and "求角" in text:
            return "长度与角综合"
        if "求长度" in text or "距离" in text:
            return "长度与距离"
        if "求角" in text:
            return "求角"
        if "数量积" in text or "投影" in text or "极化" in text:
            return "数量积"
        if "共面" in text:
            return "共面"
        if "线性运算" in text or "线性" in text:
            return "线性运算"
        if "平行" in text or "共线" in text:
            return "平行与共线"
        return "通用向量方法"

    def knowledge_thinking(title_text: str) -> tuple[str, str, str]:
        family = method_family(title_text)
        if "相关概念" in title_text:
            return (
                "先把题目中的向量关系翻译成‘方向、长度、相等或相反’中的一种，不急着套后面的类型题。",
                "第一行写清要比较的两个向量及其起点、终点；第二行按定义逐项核对方向和模；最后列出满足条件的向量。",
                "检查是否把向量方向写反、是否漏掉同方向且等长的对象，以及零向量或单位向量的特殊规定。",
            )
        if "线性运算" in title_text:
            return (
                "先找课程里对应的三角形法则、平行四边形法则或数乘意义，判断题目是在做向量合并还是拆分。",
                "第一行把目标向量写出来；第二行先统一起点或首尾相接，遇到减号和括号先逐项写出变号后的向量；第三行再合并系数，并写出最后的几何向量。",
                "检查每个向量的方向、正负号、起终点和系数；遇到中点或分点先核对比例关系，确认结果仍然是向量而不是数。",
            )
        if "共线" in title_text or "共面" in title_text:
            return (
                "先判断题目要证明的是共线/平行还是共面，再回到课程中的方向向量或系数和判据。",
                "第一行选定不为零的方向向量或一组基向量；第二行把目标向量表示成它们的线性组合；第三行写出系数关系并说明判据。",
                "检查所选基向量是否满足非零或不共线条件，系数和是否写对，最后的几何结论是否回到了题目对象。",
            )
        if "数量积" in title_text or "投影" in title_text:
            return (
                "先分清题目要的是数量积、夹角、长度还是投影，再选择课程中的定义、分配律或投影公式。",
                "第一行写目标量和所选向量；第二行写数量积定义或展开式；第三行代入模长、夹角或投影关系，最后整理成题目要求。若是投影，还要同时写投影向量与投影长度的区别。",
                "检查向量是否非零、分母是否有意义、投影向量和投影长度有没有混淆，以及结果的符号和范围。",
            )
        return (
            f"先确认这道题要调用‘{family}’中的哪个定义或公式，再把题目条件翻译成向量关系。",
            "第一行写已知对象和目标量；第二行写对应的定义、等式或参数表示；随后逐步代入并在最后写出题目要求的结论。",
            "检查每一步是否说明了使用条件，符号、方向、定义域和最终结论是否一致。",
        )

    def method_thinking(method_text: str, focus: str = "") -> tuple[str, str, str]:
        family = method_family(method_text, focus)
        if family == "线性运算":
            return (
                f"先把题目归入‘{method_text}’，找出共同起点、首尾相接或平行六面体中的基本向量；若出现括号，先保留外层正负号再展开。",
                "第一行写目标向量；第二行用同一起点或基向量表示每一项，逐项处理减号和括号；第三行按系数合并，最后写成目标方向的向量。图形终点不清时先固定一个公共起点再定位终点。",
                "检查是否统一了起点、每个方向是否一致、括号内每一项是否正确变号、分点比例是否写在正确方向，且结论仍是向量。",
            )
        if family == "平行与共线":
            return (
                f"结合‘{method_text}’，先找题目要证明的两条直线并各取一个非零方向向量；若出现‘任意向量’或零向量，先单独检查特殊情形。",
                "第一行写两条目标向量；第二行把它们统一到同一基向量或公共起点，设其中一个等于另一个的实数倍；第三行说明该倍数关系如何回到平行或三点共线。",
                "检查方向向量不能取零向量，不能把共线关系当作无条件传递；倍数关系、起终点和证明对象必须与题目要求对应。",
            )
        if family == "共面":
            return (
                f"结合‘{method_text}’，先区分‘自由向量共面’与‘点落在同一平面’，再选两个不共线的基向量或统一公共起点。",
                "第一行写目标向量或点的位置向量；第二行设为基向量的线性组合并逐项比较系数；若判断点面位置，再单独检查位置向量系数和条件，最后落回共面结论。",
                "检查基向量条件、系数是否唯一、位置向量系数和是否满足题目平面，不能把向量共面直接写成点共面。",
            )
        if family == "数量积":
            return (
                f"结合‘{method_text}’，先圈出题目真正要求的是数量积、投影、长度、角还是最值，再选一条公式；若题设有两垂直平面，先找公共棱并判断两面内垂直公共棱的方向。",
                "第一行写所选向量和目标量；第二行写数量积定义、分配律或极化恒等式，非平方型乘积也要逐项展开；若平方展开，先列三个自项和三个交叉项再合并；第三行代入已知关系，最后整理并回到几何对象。",
                "检查非零条件、模长平方、乘积展开是否漏项、两垂直平面推出的正交条件是否有合法依据、投影方向、分母和最值等号条件，确认数值没有代错对象。",
            )
        if family == "长度与距离":
            return (
                f"结合‘{method_text}’，先把所求长度或距离翻译成一个向量的模，判断是否需要垂足或法向量。",
                "第一行写出代表目标线段的向量；第二行用中点、分点或模长平方表示，并逐项列出交叉项；第三行代入并开方，最后注明距离取非负值。",
                "检查向量方向不影响长度、根式非负、分点参数范围、垂足/垂直条件成立，以及求的是线段长度还是点面距离。",
            )
        if family == "求角":
            return (
                f"结合‘{method_text}’，先分别取两条目标直线的方向向量，并确认最后要的是直线的锐角。",
                "第一行写两条方向向量；第二行写 cos 角等于数量积除以两模之积；第三行代入并根据直线夹角取合适范围。",
                "检查方向向量是否非零、分母是否正确、绝对值或方向调整是否必要，最后角的范围应符合题意。",
            )
        if family == "二面角":
            return (
                f"结合‘{method_text}’，先确认二面角的棱，再判断截面是否由同一点出发且两条射线都垂直于棱；两个垂足不同先做平移。",
                "第一行写合法截面的取法；第二行在两个面内分别取垂棱射线，若端点不在同一棱点要保留棱上中间线段；第三行用平面角或法向量夹角求值，并说明锐钝取值。",
                "检查截面条件、射线同起点、不同垂足的平移和距离拆分、法向量夹角与二面角是否互为补角，不能看到一个角就直接套公式。",
            )
        if family == "长度与角综合":
            return (
                f"结合‘{method_text}’，先把综合题拆成长度/距离子目标和求角子目标，按先建向量、后计算的顺序推进。",
                "第一行建立统一的基向量或坐标表示；中间分别写模长、数量积或垂直关系；最后用题目要求的角度或距离公式收束。",
                "检查每个子目标的对象、方向和定义域，确认前一步的向量确实服务于后一步，不能跨步写结果。",
            )
        if family == "综合题":
            return (
                f"结合‘{method_text}’，先把题目拆成共面/参数、数量积、距离或最值等小目标，按教材方法链逐段识别。",
                "第一行先写选用的基向量或参数；每完成一个小目标就写出中间关系，再进入下一个目标；最后统一回代题目条件。",
                "检查参数范围、分母非零、几何位置、等号条件和最终回代，确认每个桥接方法都真正用到了。",
            )
        return (
            f"先结合课程把题目归类为‘{method_text}’，说出要调用的定义或方法，再开始计算。",
            "第一行写目标量和已知关系；第二行写方法公式或向量表示；随后逐步变形，最后写出题目要求。",
            "检查使用条件、符号、方向、定义域和结论是否闭合。",
        )

    def cycle_course_context(cycle: dict, extra_keys: list[str] | None = None) -> str:
        keys: list[str] = []
        for key in [*(extra_keys or []), *cycle.get("course_keys", []), *cycle.get("prerequisite_course_keys", [])]:
            value = str(key)
            if value not in keys:
                keys.append(value)
        summaries = course_summaries(keys)
        if summaries:
            return "；".join(summaries)
        return "前面已经听过并通过的课程方法"

    def exercise_signal(method_text: str, focus: str = "") -> str:
        """Give a method-family prompt shared by a whole exercise block.

        This must stay independent of the printed question number.  A
        question-keyed prompt turns the no-question route into an answer hint
        sheet, especially for figure-heavy B/C exercises.
        """
        family = method_family(method_text, focus)
        return {
            "线性运算": "先问自己：是否需要统一起点、方向和基向量，再决定合并还是拆分。",
            "平行与共线": "先问自己：目标对象的非零方向向量是什么，能否写成同一方向的倍数。",
            "共面": "先问自己：应选哪些不共线基向量，点的位置系数是否满足题目要求的共面条件。",
            "数量积": "先问自己：目标是数量积、投影、长度、角还是最值，哪条定义或恒等式的使用条件已经具备。",
            "长度与距离": "先问自己：怎样把目标翻译成向量模、垂直分解或距离公式，定义域和非负性在哪里检查。",
            "求角": "先问自己：两条目标直线的方向向量如何选，最后角度的范围和方向是否需要调整。",
            "二面角": "先问自己：公共棱和合法截面如何确认，两条射线是否同起点且都垂直于棱。",
            "长度与角综合": "先问自己：综合题可以拆成哪些长度、距离、数量积和角度子目标，先后依赖是什么。",
            "综合题": "先问自己：每个小问属于哪条方法链，参数范围、等号条件和几何回代分别放在哪里。",
        }.get(family, "先根据课程方法族归型，再写出目标、已知关系和需要检查的使用条件。")

    def append_task_guidance(
        kind: str,
        *,
        cycle: dict,
        course_text: str,
        knowledge_text: str = "",
        method_text: str = "",
        focus: str = "",
        parent_label: str = "",
        bridge_text: str = "",
        exercise_key: str = "",
        example_number: int | None = None,
    ) -> None:
        if kind == "knowledge_example":
            thinking, writing, checking = knowledge_thinking(knowledge_text)
            thinking = f"听完课程 {course_text} 后，{thinking}"
        elif kind == "variant":
            family = method_family(method_text, knowledge_text)
            thinking = (
                f"先不看前一题过程，用一句话复述{parent_label}的‘{family}’模型，再指出本变式相对它改变了什么条件。"
            )
            writing = (
                f"先写出{parent_label}对应的通用关系，再只替换本变式改变的对象、系数或位置；若题设给同一直线上的分点比例，先设整段向量为 t 倍，再把剩余段写成 (1-t) 倍并解 t；每一步都写出依据，不能只写结果。"
            )
            checking = (
                "检查是否真正独立重建了模型，分点比例的方向和参数范围是否正确，变动条件有没有同步传到后续各行，最后的几何结论是否仍满足题意。"
            )
        elif kind == "type_example":
            if example_number == 14:
                thinking = (
                    "先识别这是‘任意点 + 数量积最值’，"
                    "把两个向量的和改写成中点关系，再决定使用全空间最值还是受区域限制的最值。"
                )
                writing = (
                    "第一行设相关线段的中点并把向量和写成两倍中点向量；"
                    "第二行展开数量积或使用极化恒等式，把目标化成模长平方；"
                    "第三行说明等号条件。若动点有区域限制，另列区域内端点、顶点和内部点的可行性检查。"
                )
                checking = (
                    "检查中点向量方向、全空间与区域型最值是否分清、等号点是否在定义域内，"
                    "不能只报一个最值数值。"
                )
            else:
                thinking, writing, checking = method_thinking(method_text, focus)
            thinking = f"听完课程 {course_text} 后，{thinking}"
        elif kind == "checkpoint":
            source = f"课程 {course_text}"
            if bridge_text:
                source += f"；课程外补充方法‘{bridge_text}’"
            thinking = f"这是‘{method_text}’的放行检查，先回忆{source}中的对应方法链，再用自己的话说出每一步为什么成立。"
            writing = "按‘已知/目标 → 选用定义或参数 → 逐步关系 → 几何条件回代’写完整过程；只写方法，不跳到结论。"
            checking = "检查定义、参数范围、等式来源和最后的几何解释是否齐全；不能只凭看过文字就算通过。"
        else:
            thinking, writing, checking = method_thinking(method_text or cycle.get("title", ""), focus)
            if exercise_key:
                thinking = f"先观察：{exercise_signal(method_text, focus)} 结合课程 {course_text}，{thinking}"
            else:
                thinking = f"结合课程 {course_text}，{thinking}"
            if bridge_text:
                thinking += f" 题目前还要先复述：{bridge_text}。"
        lines.extend([
            f"  - **思考入口：** {thinking}",
            f"  - **书写骨架：** {writing}",
            f"  - **检查点：** {checking}",
        ])

    def cycle_task_labels(cycle: dict) -> list[str]:
        labels: list[str] = []
        variants_by_parent: dict[int, list[dict]] = {}
        for variant in cycle.get("direct_variants", []):
            variants_by_parent.setdefault(variant.get("parent_example_number"), []).append(variant)

        knowledge_examples: dict[str, list[dict]] = {}
        type_examples: dict[str, list[dict]] = {}
        for item in cycle.get("worked_examples", []):
            role = str(item.get("role", ""))
            role_ref = str(item.get("role_ref", ""))
            if role == "knowledge_example":
                knowledge_examples.setdefault(role_ref, []).append(item)
            elif role == "type_example":
                type_examples.setdefault(role_ref, []).append(item)

        for ref in cycle.get("knowledge_refs", []):
            for item in knowledge_examples.get(str(ref), []):
                number = item.get("example_number", "?")
                labels.append(f"教材{item.get('label', f'例{number}')}")
                labels.extend(
                    f"{variant.get('label', '变式')}（对应例{number}）"
                    for variant in variants_by_parent.get(number, [])
                )

        type_order = [str(ref) for ref in cycle.get("type_refs", [])]
        for item in cycle.get("worked_examples", []):
            if item.get("role") == "type_example" and str(item.get("role_ref")) not in type_order:
                type_order.append(str(item.get("role_ref")))
        for ref in type_order:
            for item in type_examples.get(ref, []):
                number = item.get("example_number", "?")
                labels.append(f"教材{item.get('label', f'例{number}')}")
                labels.extend(
                    f"{variant.get('label', '变式')}（对应例{number}）"
                    for variant in variants_by_parent.get(number, [])
                )

        labels.extend(f"方法检查：{item.get('label', item.get('id'))}" for item in cycle.get("method_checkpoints", []))
        labels.extend(
            f"{item.get('group', '?')}{item.get('number', '?')}"
            for item in cycle.get("exercise_questions", [])
        )
        return labels

    def knowledge_summaries(refs: list[str], blocks: dict[str, dict] | None = None) -> list[str]:
        result: list[str] = []
        for ref in refs:
            title = knowledge_title(str(ref), (blocks or {}).get(str(ref)))
            if title not in result:
                result.append(title)
        return result

    def visible_bridge_targets(bridge: dict) -> list[str]:
        """Show textbook labels without leaking internal bridge identifiers."""
        result: list[str] = []
        prefix = f"{section}-"
        for target in bridge.get("target_questions", []):
            value = str(target)
            if "-" in value and not value.startswith(prefix):
                continue
            if value.startswith(prefix):
                value = value[len(prefix):]
            if value not in result:
                result.append(value)
        for target in bridge.get("target_learning_items", []):
            value = str(target).strip()
            if value and value not in result:
                result.append(value)
        return result

    def bridge_gate_note(bridge: dict) -> str:
        status = str(bridge.get("status") or "UNKNOWN")
        zero_base_status = str(bridge.get("zero_base_status") or "NOT_VERIFIED")
        if zero_base_status == "NOT_CLOSED":
            return str(
                bridge.get("zero_base_note")
                or "补充材料已存在，但零基础放行条件尚未闭合；必须完成检查点和无答案近变式。"
            )
        if status == "SOURCE_METHOD_READY":
            return "只有方法骨架，不能作为零基础已学会的依据；先补成完整无答案微课。"
        if status == "SUPPLEMENT_READY":
            return "补充课文字已具备；仍须通过本桥接的检查标准，不能用视频观看记录替代掌握证据。"
        return "状态未确认，不能据此放行目标题。"

    def cycle_task_range(cycle: dict) -> str:
        count = (
            len(cycle.get("worked_examples", []))
            + len(cycle.get("direct_variants", []))
            + len(cycle.get("exercise_questions", []))
        )
        if count == 0:
            return "无连续编号任务"
        start = 1
        for previous in cycles:
            if previous is cycle:
                break
            start += (
                len(previous.get("worked_examples", []))
                + len(previous.get("direct_variants", []))
                + len(previous.get("exercise_questions", []))
            )
        end = start + count - 1
        return f"任务 {start:0{task_width}d}—任务 {end:0{task_width}d}"

    def cycle_exercise_labels(cycle: dict) -> str:
        labels = [
            f"{item.get('group', '?')}{item.get('number', '?')}"
            for item in cycle.get("exercise_questions", [])
        ]
        return "、".join(labels) or "本循环没有教材 A/B/C 题"

    def cycle_order_note(cycle: dict) -> str:
        exercise_keys = {
            f"{item.get('group', '?')}{item.get('number', '?')}"
            for item in cycle.get("exercise_questions", [])
        }
        # 1.2+1.3 的 B6/B7/B12/C14 与 1.1 同题号不同内容：题号安排说明必须按本节题面写，
        # 不得沿用 1.1 的“二面角平面角”模板文案（1.2+1.3 的 B6/B7/B12 均无桥接要求）。
        if section == "1.2+1.3":
            if "B7" in exercise_keys:
                return "B7（投影向量）、B10（数量积求值）均为数量积坐标表示题，承接例8/例9，安排在类型Ⅲ 数量积的坐标表示循环；均无桥接要求。"
            if "B6" in exercise_keys:
                return "B6（a⊥b、b∥c 翻译条件后求模，与例11 同型）、B11（异面直线夹角）承接类型Ⅴ，安排在类型Ⅴ 夹角与模循环；均无桥接要求。"
            if "B12" in exercise_keys:
                return "B12（平行/垂直条件翻译）、B13（建系证垂直并求夹角）承接例10 及其变式，安排在类型Ⅳ 平行与垂直的坐标判定循环；均无桥接要求。"
            if "C14" in exercise_keys:
                return "C14 是本节综合题（四点共面截线系数），依赖前面循环的基底分解、坐标运算与‘四点共面系数和=1’补充方法；不依赖法向量与距离。"
            return ""
        if "B12" in exercise_keys:
            return "教材书面编号把 B12 放在 B6、B7 后面；本路线先安排 B12，是因为它承接数量积求长度/求角，尚未进入二面角平面角定义。"
        if {"B6", "B7"}.intersection(exercise_keys):
            return "B6、B7 首次使用二面角平面角；必须先听 3.1.4.5 平面与平面的夹角并完成‘二面角平面角的定义与合法截面’补充方法，所以路线任务号晚于教材书面题号 B12。"
        if "C14" in exercise_keys:
            return "C14 是本节综合题，必须等前面循环的共面、数量积、法向量、距离和课程外补充方法全部通过后再做。"
        return ""

    course_order_keys: list[str] = []
    course_cycle_roles: dict[str, list[str]] = {}
    for cycle in cycles:
        sequence = int(cycle.get("sequence", 0))
        for role, keys in (
            ("前置", cycle.get("prerequisite_course_keys", [])),
            ("主课", cycle.get("course_keys", [])),
            ("可选方法课", cycle.get("optional_course_keys", [])),
        ):
            for key in keys:
                key = str(key)
                if key not in course_order_keys:
                    course_order_keys.append(key)
                use = f"循环 {sequence} {role}"
                if use not in course_cycle_roles.setdefault(key, []):
                    course_cycle_roles[key].append(use)
    course_order_keys.sort(
        key=lambda key: [
            int(part) if part.isdigit() else part
            for part in re.split(r"(\d+)", str(courses[key].get("original_course_id", key)))
        ]
    )
    if not course_order_keys:
        raise ValueError(f"section {section} has no course route")

    route_bridge_ids: list[str] = []
    for cycle in cycles:
        for bridge_id in cycle.get("bridge_unit_ids", []):
            value = str(bridge_id)
            if value not in route_bridge_ids:
                route_bridge_ids.append(value)

    def plain_course_summaries(keys: list[str]) -> list[str]:
        result: list[str] = []
        for key in keys:
            course = courses.get(str(key))
            if not course:
                raise ValueError(f"unknown course {key} in section {section}")
            value = f"{course.get('original_course_id', '未知课程编号')} {course_title(course)}"
            if value not in result:
                result.append(value)
        return result

    overview_rows = [
        '<table class="overview-table">',
        "<thead><tr><th>学习循环</th><th>先听/复习</th><th>课后按顺序写这些</th><th>本批连续任务</th></tr></thead>",
        "<tbody>",
    ]
    for cycle in cycles:
        current_keys = [str(key) for key in cycle.get("course_keys", [])]
        prerequisite_keys = [str(key) for key in cycle.get("prerequisite_course_keys", [])]
        listen_parts: list[str] = []
        if current_keys:
            listen_parts.append(f"主课：{'；'.join(plain_course_summaries(current_keys))}")
        if prerequisite_keys:
            listen_parts.append(f"前置：{'；'.join(plain_course_summaries(prerequisite_keys))}")
        optional_keys = [str(key) for key in cycle.get("optional_course_keys", [])]
        if optional_keys:
            listen_parts.append(f"可选方法课：{'；'.join(plain_course_summaries(optional_keys))}")
        listen_text = "<br>".join(listen_parts) or "复用前面已经通过的课程方法"
        task_text = "、".join(cycle_task_labels(cycle)) or "本循环没有教材题，只做方法检查"
        overview_rows.append(
            "<tr>"
            f"<th scope=\"row\">循环 {cycle.get('sequence')}<br>{cycle.get('title')}</th>"
            f"<td>{listen_text}</td>"
            f"<td>{task_text}</td>"
            f"<td>{cycle_task_range(cycle)}</td>"
            "</tr>"
        )
    overview_rows.extend(["</tbody>", "</table>"])

    lines = [
        f"# {plan_section.get('label', section)}：无题目学习路线预览",
        "",
        f"> 共 {len(cycles)} 个学习循环；教学例题 {counts.get('worked_examples', 0)} 道、直接变式 {counts.get('direct_variants', 0)} 道、A/B/C 习题 {counts.get('abc_exercises', 0)} 道。",
        "> 本文件严格按《一本通》的版式逻辑展示：课程 → 知识点 → 知识点右侧例题 → 类型题 → A/B/C 习题。只展示路线、题号和学生作答动作，不展示任何题干、选项、解答、答案、出处年份或题目配图。",
        "",
        "## 一眼总览",
        "",
        "先看下面这张表：每一行就是“听课/复习 → 按顺序写题 → 通过本批检查”。其中“课后按顺序写这些”列出了本批实际要完成的教材例题、直属变式、方法检查和 A/B/C 题。",
        "",
        *overview_rows,
        "",
        "## 每道题怎么写",
        "",
        "1. **思考入口：** 听完当前课程后，先从题目特征判断它调用哪个知识点或方法，不先猜结果。",
        "2. **书写骨架：** 第一行写目标量和已知关系，第二行写定义/公式/参数表示，之后逐步变形；每个关键等式都要能说出依据。",
        "3. **检查点：** 做完后回代题目条件，核对方向、正负号、定义域、范围和题目问句；使用提示后要用未见题或延迟复测补证。",
        "下面每个任务都把这三步翻译成当前知识点或题型的具体动作；题干仍需在《一本通》原书中查看。",
        "",
        "## 先听哪一节课",
        "",
        f"第一节先听：{course_summary(courses[course_order_keys[0]])}。它先建立本节后续所有向量方法的共同语言。",
        "",
        "## 全部课程顺序",
        "",
    ]
    for index, key in enumerate(course_order_keys, start=1):
        course = courses[key]
        uses_text = "；".join(course_cycle_roles.get(key, []))
        files = course.get("recommended_video_files") or course.get("video_files") or []
        lines.append(f"{index}. {course_summary(course)}｜{uses_text}")
        if files:
            lines.append(f"   - 文件：`{files[0]}`")
    lines.extend([
        "",
        "> 上面的编号是本路线实际的听课/复习顺序；课程计划里的“必听主课/补充课程”只是分组字段，不能把分组数组顺序当成播放顺序。视频来源仍严格限定为 Downloads\\课程合集\\3.1 空间向量与立体几何。",
    ])

    lines.extend(["", "## 课程之外的补充前置", ""])
    lines.append(
        "下面这些内容不是《课程合集》里的新视频，而是课程与《一本通》题目之间必须补上的无答案方法课。"
    )
    lines.append(
        "`SUPPLEMENT_READY` 只表示补充文字已准备；零基础能否放行还要看每个补充前置自己的检查标准。"
    )
    for bridge_id in route_bridge_ids:
        bridge = bridge_by_id.get(bridge_id)
        if not bridge:
            raise ValueError(f"route references unknown bridge {bridge_id}")
        targets = visible_bridge_targets(bridge)
        target_text = "、".join(targets) or "本节未指定题号"
        status = str(bridge.get("status") or "UNKNOWN")
        lines.append(
            f"- **{bridge.get('title', '未命名补充方法')}**｜课程外前置｜文字状态：`{status}`｜服务教材项目/题号：{target_text}"
        )
        lines.append(f"  - 零基础放行：{bridge_gate_note(bridge)}")

    lines.extend([
        "",
        "## 教材书面题号与学习循环对应表",
        "",
    ])
    if section == "1.2+1.3":
        print_order_note = "教材印刷顺序是 A1-A4、B5-B13、C14-C16；本路线的连续任务号按课程依赖和知识闭环安排，因此连续任务号不等于教材题号，也不强行按 B5 到 B13 的表面顺序推进。"
    else:
        print_order_note = "教材印刷顺序是 A1-A3、B4-B12、C13-C14；本路线的连续任务号按课程依赖和知识闭环安排，因此连续任务号不等于教材题号，也不强行按 B4 到 B12 的表面顺序推进。"
    lines.append(f"> {print_order_note}")
    for cycle in cycles:
        labels = cycle_exercise_labels(cycle)
        note = cycle_order_note(cycle) or "按本循环的课程、知识点例题、类型训练和前置条件推进。"
        lines.append(
            f"- 循环 {cycle.get('sequence')}「{cycle.get('title')}」｜教材书面题号：{labels}｜连续任务：{cycle_task_range(cycle)}｜安排说明：{note}"
        )

    lines.extend([
        "",
        "## 使用顺序",
        "",
        "1. 按上面的课程顺序听课；第一门是当前唯一的起点。",
        "2. 每门课听完，只进入它对应的当前循环；先学知识点，再立刻做该知识点右侧的教材例题。",
        "3. 知识点例题完成后，再做该例题的直属变式和本类型训练。",
        "4. 类型训练完成后，最后做本循环分配的 A/B/C 习题。",
        "5. 只记录第一处卡点并给最小提示；本循环推进门未通过，不提前进入下一循环。",
        "",
    ])

    for cycle in cycles:
        sequence = cycle.get("sequence")
        title = cycle.get("title")
        cycle_course_text = cycle_course_context(cycle)
        lines.extend(["---", "", f"## 循环 {sequence}/{len(cycles)}：{title}", ""])
        order_note = cycle_order_note(cycle)
        if order_note:
            lines.extend([f"> **题号安排说明：** {order_note}", ""])

        lines.extend(["### 1. 本循环先听的视频", ""])
        course_keys = [str(key) for key in cycle.get("course_keys", [])]
        if course_keys:
            for key in course_keys:
                course = courses.get(key)
                if not course:
                    raise ValueError(f"cycle {cycle.get('cycle_id')} references unknown course {key}")
                files = course.get("recommended_video_files") or course.get("video_files") or []
                if not files:
                    raise ValueError(f"course {key} has no video file")
                lines.append(f"- {course_summary(course)}")
                lines.append(f"  - 文件：`{files[0]}`")
        else:
            lines.append("- 本循环没有新增视频；复用前面已经通过的课程方法，但不能把旧课程观看记录当成当前循环掌握证据。")
        prerequisites = [str(key) for key in cycle.get("prerequisite_course_keys", [])]
        if prerequisites:
                lines.append(f"- 先复习的前置课程：{'；'.join(course_summaries(prerequisites))}")
        optional_keys = [str(key) for key in cycle.get("optional_course_keys", [])]
        if optional_keys:
            lines.append(
                f"- 可选方法课（不作为本循环所有题目的统一阻断条件）：{'；'.join(course_summaries(optional_keys))}"
            )

        bridge_ids = [str(value) for value in cycle.get("bridge_unit_ids", [])]
        lines.extend(["", "### 2. 本循环补充桥接", ""])
        if bridge_ids:
            for bridge_id in bridge_ids:
                bridge = bridge_by_id.get(bridge_id)
                if not bridge:
                    raise ValueError(f"cycle {cycle.get('cycle_id')} references unknown bridge {bridge_id}")
                lines.extend([
                    f"#### 补充方法：{bridge.get('title', '未命名桥接')}",
                    "",
                    "这部分不是新的教材题号，但必须在对应习题前完成，用来补齐课程和《一本通》题目之间的缺口。",
                ])
                status = str(bridge.get("status") or "UNKNOWN")
                status_note = {
                    "SUPPLEMENT_READY": "已有无答案补充课；先完成下方检查标准，不能只凭看过文字就进入目标题。",
                    "SOURCE_METHOD_READY": "目前只有来源方法骨架，不能把它当成零基础学生已经学会；必须先补成完整无答案微课。",
                }.get(status, "状态未确认，不能据此放行目标题。")
                lines.append(f"- 当前状态：`{status}`｜{status_note}")
                lines.append(f"- 零基础放行状态：{bridge_gate_note(bridge)}")
                prerequisites_text = "、".join(str(value) for value in bridge.get("prerequisites", []))
                if prerequisites_text:
                    lines.append(f"- 前置知识：{prerequisites_text}")
                for step in bridge.get("lesson_steps", []):
                    lines.append(f"- {step}")
                if bridge.get("self_made_variant"):
                    lines.append(f"- 无答案自造变式：{bridge.get('self_made_variant')}")
                for variant in bridge.get("self_made_variants", []):
                    lines.append(f"- 无答案自造变式：{variant}")
                checks = bridge.get("method_check", [])
                if checks:
                    lines.append("- 学完后的检查标准：")
                    lines.extend(f"  - {check}" for check in checks)
                release_requirements = bridge.get("release_requirements", [])
                if release_requirements:
                    lines.append("- 进入目标题前必须具备：")
                    lines.extend(f"  - {requirement}" for requirement in release_requirements)
                targets = visible_bridge_targets(bridge)
                if targets:
                    lines.append(f"- 服务教材项目/题号：{', '.join(targets)}")
        else:
            lines.append("- 本循环没有额外桥接；直接按知识点、类型题和 A/B/C 习题顺序推进。")

        lines.extend(["", "### 3. 知识点与知识点右侧的紧跟例题", ""])
        prerequisite_blocks = {
            str(item.get("id")): item for item in cycle.get("prerequisite_knowledge_blocks", [])
        }
        for ref in cycle.get("prerequisite_knowledge_refs", []):
            lines.append(
                f"- 先复习：{knowledge_title(str(ref), prerequisite_blocks.get(str(ref)))}（完整知识内容已在前面首次出现，本循环只调用其中的方法。）"
            )

        cycle_blocks = {str(item.get("id")): item for item in cycle.get("knowledge_blocks", [])}
        knowledge_examples: dict[str, list[dict]] = {}
        type_examples: dict[str, list[dict]] = {}
        variants_by_parent: dict[int, list[dict]] = {}
        for variant in cycle.get("direct_variants", []):
            variants_by_parent.setdefault(variant.get("parent_example_number"), []).append(variant)
        for item in cycle.get("worked_examples", []):
            role = str(item.get("role", ""))
            role_ref = str(item.get("role_ref", ""))
            if role == "knowledge_example":
                knowledge_examples.setdefault(role_ref, []).append(item)
            elif role == "type_example":
                type_examples.setdefault(role_ref, []).append(item)

        def append_knowledge_example(item: dict, title_text: str) -> None:
            number = item.get("example_number", "?")
            rendered_examples.add(str(item.get("item_id") or f"example:{number}"))
            task_label = next_task_label()
            lines.append(
                f"- `{task_label}` 教材{item.get('label', f'例{number}')}｜对应知识点：{title_text}｜位置：学完这个知识点后立即完成的右侧例题｜{visual_note(item.get('visual_status'))}"
            )
            append_task_guidance(
                "knowledge_example",
                cycle=cycle,
                course_text=cycle_course_text,
                knowledge_text=title_text,
                example_number=int(number) if str(number).isdigit() else None,
            )
            for variant in variants_by_parent.get(number, []):
                parent = variant.get("parent_example_number")
                rendered_variants.add(str(variant.get("item_id") or f"variant:{parent}"))
                variant_task_label = next_task_label()
                lines.append(
                    f"- `{variant_task_label}` {variant.get('label', '变式')}({parent})｜直属于教材例{parent}｜位置：完成该例题后立即独立完成的无答案变式｜{visual_note(variant.get('visual_status'))}"
                )
                append_task_guidance(
                    "variant",
                    cycle=cycle,
                    course_text=cycle_course_text,
                    knowledge_text=title_text,
                    method_text=title_text,
                    parent_label=f"教材例{parent}",
                )

        for ref in cycle.get("knowledge_refs", []):
            ref = str(ref)
            block = cycle_blocks.get(ref)
            if not block:
                raise ValueError(f"cycle {cycle.get('cycle_id')} missing knowledge block {ref}")
            title_text = knowledge_title(ref, block)
            lines.extend(["", f"#### 左侧知识点｜{title_text}", ""])
            if ref not in shown_knowledge:
                lines.append(
                    remove_visuals(
                        render_instruction_text(str(block.get("text", "")), sanitize_text_only=True)
                    )
                )
                shown_knowledge.add(ref)
            else:
                lines.append("本循环复用前面已经完整展开的知识内容；下面仍保留本循环的题目位置，不重复计入知识点。")
            example_labels = block.get("example_labels", []) or [
                item.get("label") for item in knowledge_examples.get(ref, [])
            ]
            lines.extend([
                "",
                f"> 《一本通》这一知识点右侧紧跟的例题：{', '.join(example_labels) or '本循环没有新的右侧例题'}",
            ])
            for item in knowledge_examples.get(ref, []):
                append_knowledge_example(item, title_text)
        if not cycle.get("knowledge_refs"):
            lines.append("- 本循环不新增左栏知识点；先按上面列出的前置知识点复习，再进入本循环的类型训练或习题。")

        type_order = [str(ref) for ref in cycle.get("type_refs", [])]
        for item in cycle.get("worked_examples", []):
            if item.get("role") == "type_example" and str(item.get("role_ref")) not in type_order:
                type_order.append(str(item.get("role_ref")))
        lines.extend(["", "### 4. 类型题训练（在知识点例题之后）", ""])
        if not type_order:
            lines.append("- 本循环没有新的类型题例题；完成方法检查后进入最后的 A/B/C 习题。")
        for ref in type_order:
            type_item = type_by_name.get(ref, {})
            focus = str(type_item.get("focus") or "按《一本通》该类型的典型方法完成")
            examples = type_examples.get(ref, [])
            labels = [str(item.get("label")) for item in examples]
            lines.extend([
                "",
                f"#### {ref}",
                f"- 训练重点：{focus}",
                f"- 《一本通》对应类型例题：{', '.join(labels) or '本循环没有单独列出的类型例题'}",
            ])
            for item in examples:
                number = item.get("example_number", "?")
                rendered_examples.add(str(item.get("item_id") or f"example:{number}"))
                task_label = next_task_label()
                lines.append(
                    f"- `{task_label}` 教材{item.get('label', f'例{number}')}｜所属类型：{ref}｜本题作用：把前面知识点转成该类型的标准解题模型｜{visual_note(item.get('visual_status'))}"
                )
                append_task_guidance(
                    "type_example",
                    cycle=cycle,
                    course_text=cycle_course_text,
                    method_text=ref,
                    focus=focus,
                    example_number=int(number) if str(number).isdigit() else None,
                )
                for variant in variants_by_parent.get(number, []):
                    parent = variant.get("parent_example_number")
                    rendered_variants.add(str(variant.get("item_id") or f"variant:{parent}"))
                    variant_task_label = next_task_label()
                    lines.append(
                        f"- `{variant_task_label}` {variant.get('label', '变式')}({parent})｜直属于教材例{parent}｜本题作用：检验同一类型方法能否独立迁移｜{visual_note(variant.get('visual_status'))}"
                    )
                    append_task_guidance(
                        "variant",
                        cycle=cycle,
                        course_text=cycle_course_text,
                        method_text=ref,
                        focus=focus,
                        parent_label=f"教材例{parent}",
                    )

        for checkpoint in cycle.get("method_checkpoints", []):
            checkpoint_label = str(checkpoint.get("label", checkpoint.get("id")))
            lines.append(f"- 方法检查：{checkpoint_label}（不计入教材题量；通过后再做本循环习题）")
            checkpoint_bridges = [
                str(bridge_by_id[bridge_id].get("title"))
                for bridge_id in cycle.get("bridge_unit_ids", [])
                if bridge_id in bridge_by_id
            ]
            append_task_guidance(
                "checkpoint",
                cycle=cycle,
                course_text=cycle_course_text,
                method_text=checkpoint_label,
                bridge_text="；".join(checkpoint_bridges),
            )

        lines.extend(["", "### 5. 最后做本循环对应的 A/B/C 习题", ""])
        exercises = cycle.get("exercise_questions", [])
        if exercises:
            route_blocks = {
                str(item.get("id")): item
                for item in [
                    *cycle.get("prerequisite_knowledge_blocks", []),
                    *cycle.get("knowledge_blocks", []),
                ]
            }
            route_titles = knowledge_summaries(
                [*cycle.get("prerequisite_knowledge_refs", []), *cycle.get("knowledge_refs", [])],
                route_blocks,
            )
            for item in exercises:
                group = str(item.get("group", "?"))
                number = item.get("number", "?")
                question_key = f"{group}{number}"
                coverage_item = coverage_by_key.get(question_key, {})
                details = [
                    f"题组：{group_titles.get(group, f'{group} 组')}",
                    "完成位置：知识点例题和类型训练之后",
                    f"本题承接知识：{'、'.join(route_titles) or '本循环已完成的方法'}",
                ]
                question_courses = [str(key) for key in coverage_item.get("course_keys", [])]
                if question_courses:
                    details.append(f"对应课程：{'；'.join(course_summaries(question_courses))}")
                bridge_titles: list[str] = []
                for bridge_ref in coverage_item.get("bridge_units", []):
                    bridge_id = bridge_ref.get("id") if isinstance(bridge_ref, dict) else bridge_ref
                    bridge = bridge_by_id.get(str(bridge_id))
                    if bridge and bridge.get("title") not in bridge_titles:
                        bridge_titles.append(str(bridge.get("title")))
                if bridge_titles:
                    details.append(f"先完成桥接：{'；'.join(bridge_titles)}")
                    not_closed = [
                        str(bridge.get("title"))
                        for bridge in bridge_by_id.values()
                        if bridge.get("title") in bridge_titles
                        and str(bridge.get("zero_base_status") or "") == "NOT_CLOSED"
                    ]
                    if not_closed:
                        details.append(f"零基础放行未闭合：{'；'.join(not_closed)}")
                unlock_class = str(coverage_item.get("unlock_class", ""))
                if unlock_class == "METHOD_BRIDGE" and not bridge_titles:
                    if cycle.get("method_checkpoints"):
                        details.append("放行条件：先通过本循环方法检查")
                    else:
                        details.append("放行条件：完成本循环课程、知识点例题和类型训练后")
                elif unlock_class in unlock_titles:
                    details.append(f"放行条件：{unlock_titles[unlock_class]}")
                details.append(visual_note(coverage_item.get("visual_status")))
                rendered_exercises.add(question_key)
                task_label = next_task_label()
                lines.append(f"- `{task_label}` {question_key}｜{'｜'.join(details)}")
                exercise_course_text = cycle_course_context(cycle, question_courses)
                exercise_method_text = "；".join(
                    f"{ref}：{type_by_name.get(ref, {}).get('focus', '')}".rstrip("：")
                    for ref in cycle.get("type_refs", [])
                ) or str(cycle.get("title", "本循环方法"))
                append_task_guidance(
                    "exercise",
                    cycle=cycle,
                    course_text=exercise_course_text,
                    method_text=exercise_method_text,
                    bridge_text="；".join(bridge_titles),
                    exercise_key=question_key,
                )
        else:
            lines.append("- 本循环没有单独分配教材 A/B/C 题；本循环只完成上面的前置方法检查，不进入教材习题。")

        lines.extend([
            "",
            "### 6. 本循环验收",
            "",
            "- [ ] 能闭卷复述本循环知识和方法的适用条件。",
            "- [ ] 已按“知识点 → 右侧例题 → 直属变式 → 类型训练 → A/B/C 习题”的顺序独立完成全部项目。",
            "- [ ] 使用过提示的项目已经完成未见迁移或延迟复测。",
            "- [ ] 没有未解决的第一断点。",
            f"- 推进门：{cycle.get('advance_gate')}",
            f"- 失败处理：{cycle.get('failure_rule')}",
            "",
        ])

    expected_examples = {
        str(item.get("item_id") or f"example:{item.get('example_number')}")
        for cycle in cycles for item in cycle.get("worked_examples", [])
    }
    expected_variants = {
        str(item.get("item_id") or f"variant:{item.get('parent_example_number')}")
        for cycle in cycles for item in cycle.get("direct_variants", [])
    }
    expected_exercises = {
        f"{item.get('group')}" f"{item.get('number')}"
        for cycle in cycles for item in cycle.get("exercise_questions", [])
    }
    if rendered_examples != expected_examples:
        raise ValueError("detailed route did not render every worked example exactly once")
    if rendered_variants != expected_variants:
        raise ValueError("detailed route did not render every direct variant exactly once")
    if rendered_exercises != expected_exercises:
        raise ValueError("detailed route did not render every A/B/C exercise exactly once")
    lines.extend([
        "---",
        "",
        "## 小节完成门",
        "",
        "全部循环通过后，再做未见近迁移；至少间隔 24 小时完成闭卷复测。",
        "",
    ])
    if task_number != total_tasks:
        raise ValueError(f"numbered task count mismatch: rendered={task_number}, expected={total_tasks}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a course-by-course sequential learning path as Markdown")
    parser.add_argument("--section", default="1.1")
    parser.add_argument("--output")
    parser.add_argument("--without-questions", action="store_true")
    args = parser.parse_args()

    packet_dir = ROOT / "data" / "packets" / args.section.replace("+", "_")
    source = packet_dir / "learning_packet.json"
    default_name = "learning_path_without_questions.md" if args.without_questions else "learning_packet.md"
    output = Path(args.output) if args.output else packet_dir / default_name
    packet = load_json(source)
    plan = load_json(ROOT / "data" / "chapter1_learning_plan.json")
    bridges = load_json(ROOT / "data" / "bridge_micro_lessons.json")
    if args.without_questions:
        coverage = load_json(ROOT / "data" / "question_coverage.json")
        rendered = export_without_questions(packet, plan, bridges, coverage)
    else:
        rendered = export_markdown(packet, plan, bridges)
    output.write_text(rendered, encoding="utf-8-sig", newline="\r\n")
    print(json.dumps({"source": str(source), "output": str(output), "cycles": len(packet.get("learning_cycles", [])), "bytes": output.stat().st_size}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
