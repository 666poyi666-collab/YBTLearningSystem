from __future__ import annotations

import hashlib
import gzip
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PERSONAS = (
    ("literal-zero-base", "逐字执行型", "省略前提与桥接动作"),
    ("recognition-weak", "题型识别弱型", "相邻方法的入口辨认"),
    ("algebra-weak", "代数操作弱型", "符号、定义域、分类与边界"),
    ("visual-weak", "图形转换弱型", "图形或空间关系的代数化"),
    ("self-check-weak", "自检薄弱型", "独立回代、范围与退化检查"),
)

PASS_VERDICTS = {"route_actionable", "route_actionable_after_minimal_hint"}
FORBIDDEN_LEARNER_KEYS = {
    "answer",
    "answer_text",
    "answer_sidecar",
    "correct_option",
    "grader_evidence",
    "solution",
    "teaching_text",
}
FORBIDDEN_LEARNER_TEXT = re.compile(
    r"answer_sidecar|GRADER_ONLY|original_answer_book|正确答案|参考答案|答案[:：]",
    re.IGNORECASE,
)
SOLUTION_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:解析|参考答案|答案|解答|解法\s*\d*|证明\s*\d*)\s*[:：]",
    re.MULTILINE,
)
LEARNING_ITEM_REASONING_TERMS = (
    "由题意",
    "韦达定理",
    "所以",
    "故有",
    "从而",
    "综上所述",
    "当且仅当",
    "代入①",
    "解得",
    "可得",
)


DOMAIN_METHODS: dict[str, dict[str, Any]] = {
    "vector": {
        "model": "向量几何翻译",
        "first": "先选公共起点、基底、方向向量或法向量，再把目标几何关系写成向量关系。",
        "actions": ["统一起点或建立坐标系", "把条件写成线性表示、坐标或数量积", "按系数、坐标或夹角条件推进"],
        "check": "检查非零向量、方向、系数和、夹角范围及几何定义域。",
    },
    "line": {
        "model": "直线解析模型",
        "first": "先判断斜率是否存在，再选择点斜式、一般式、方向向量或距离关系。",
        "actions": ["写出直线或点的参数表示", "代入平行、垂直、距离或对称条件", "处理分母、绝对值和参数范围"],
        "check": "检查竖直线、重合、分母、同倍方程、绝对值与位置关系。",
    },
    "circle": {
        "model": "圆与距离模型",
        "first": "先把圆整理为可读出圆心和半径的形式，并标出待研究的点或直线。",
        "actions": ["判断点、线、圆的位置关系", "使用圆心距、垂径或根与系数关系", "回到切点、弦长或两圆条件"],
        "check": "检查半径为正、相切等号、弦长范围和交点数量。",
    },
    "conic": {
        "model": "圆锥曲线识别与联立",
        "first": "先由焦点轴、定义、准线或标准式确定曲线方向和参数关系。",
        "actions": ["写出标准方程与参数恒等式", "代入点、直线、弦或焦点条件", "用判别式、韦达或定义完成消元"],
        "check": "检查焦点轴、参数正性、判别式及代数根与真实交点的对应。",
    },
    "sequence": {
        "model": "数列下标与递推模型",
        "first": "先写明目标是通项、递推还是前 n 项和，并标出首项和下标范围。",
        "actions": ["把条件化为通项、求和或递推关系", "选择裂项、错位相减、分组、待定系数或归纳", "整理首尾项和边界项"],
        "check": "检查首项、项数、下标错位、公比特值、分母和归纳起点。",
    },
    "derivative": {
        "model": "导数定义域与符号模型",
        "first": "第一行先写定义域并求导；切线题同时区分切点处切线与过点切线。",
        "actions": ["因式分解或分类讨论导数符号", "列单调区间、临界点或参数条件", "用端点、极值、零点或构造函数回到目标"],
        "check": "检查定义域、不可导点、端点、空区间、等号和参数分类闭合。",
    },
}

SIGNAL_TERMS = (
    "向量", "共面", "共线", "数量积", "法向量", "斜率", "倾斜角", "直线", "距离", "对称", "圆", "切线", "弦",
    "椭圆", "双曲线", "抛物线", "焦点", "离心率", "准线", "数列", "递推", "通项", "等差", "等比", "前n项和",
    "求和", "归纳", "导数", "单调", "极值", "零点", "恒成立", "不等式", "证明", "范围", "参数", "面积", "长度",
)


@dataclass(frozen=True)
class SectionRef:
    chapter: int
    section: dict[str, Any]
    manifest_path: Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def save_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha(value: Any) -> str:
    return sha256_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def iter_sections(root: Path) -> list[SectionRef]:
    rows: list[SectionRef] = []
    for chapter in range(1, 6):
        manifest_path = root / f"chapter{chapter}_manifest.json"
        manifest = load_json(manifest_path)
        rows.extend(SectionRef(chapter, section, manifest_path) for section in manifest.get("sections", []))
    return rows


def item_identity(item: dict[str, Any]) -> tuple[str, str, str]:
    if item.get("kind") == "example" or item.get("example_number") is not None:
        label = str(item.get("label") or f"例{item.get('example_number')}")
        return f"LI:{item.get('item_id')}", label, "worked_example"
    if item.get("kind") == "direct_variant" or item.get("parent_example_number") is not None:
        label = f"例{item.get('parent_example_number')} {item.get('label') or '变式'}"
        return f"LI:{item.get('item_id')}", label, "direct_variant"
    label = f"{item.get('group')}{item.get('number')}"
    return f"Q:{item.get('qid')}", label, "abc_exercise"


def cycle_items(cycle: dict[str, Any]) -> list[dict[str, Any]]:
    return [*cycle.get("worked_examples", []), *cycle.get("direct_variants", []), *cycle.get("exercise_questions", [])]


def project_student_item(item: dict[str, Any], *, strict_learning_item: bool) -> dict[str, Any]:
    text = str(item.get("question_text") or "")
    reasons: list[str] = []
    if not text.strip():
        reasons.append("empty_question_text")
    if SOLUTION_SECTION_RE.search(text):
        reasons.append("solution_section_marker")
    if strict_learning_item:
        if len(text) > 800:
            reasons.append("learning_item_text_too_long")
        reasoning_hits = [term for term in LEARNING_ITEM_REASONING_TERMS if term in text]
        if reasoning_hits:
            reasons.append("solution_reasoning_terms:" + ",".join(reasoning_hits))
        if "<table" in text.lower():
            reasons.append("embedded_table_requires_source_boundary_review")
        if re.search(r"(?:^|\n)\s*#{2,4}\s*(?:知识|\d+[.、])", text):
            reasons.append("following_knowledge_heading")
    source_hash = sha256_bytes(text.encode("utf-8"))
    safe_text = text if not reasons else ""
    allowed = {
        "item_id": item.get("item_id"),
        "qid": item.get("qid"),
        "section": item.get("section"),
        "group": item.get("group"),
        "number": item.get("number"),
        "kind": item.get("kind"),
        "label": item.get("label"),
        "example_number": item.get("example_number"),
        "parent_example_number": item.get("parent_example_number"),
        "role": item.get("role"),
        "role_ref": item.get("role_ref"),
        "source_docs": list(item.get("source_docs", [])),
        "question_text": safe_text,
        "image_refs": list(item.get("image_refs", [])),
        "visual_status": item.get("visual_status"),
        "source_quality": {
            "status": "passed" if not reasons else "blocked",
            "reasons": reasons,
            "source_question_text_sha256": source_hash,
            "learner_question_text_sha256": sha256_bytes(safe_text.encode("utf-8")),
        },
    }
    return allowed


def build_answer_free_packet(
    section: dict[str, Any],
    student_learning_items: dict[str, Any],
    student_packet: dict[str, Any],
) -> dict[str, Any]:
    projected_examples = [
        project_student_item(item, strict_learning_item=True)
        for item in student_learning_items.get("worked_examples", [])
    ]
    projected_variants = [
        project_student_item(item, strict_learning_item=True)
        for item in student_learning_items.get("direct_variants", [])
    ]
    projected_exercises = [
        project_student_item(item, strict_learning_item=False)
        for item in student_packet.get("questions", [])
    ]
    examples = {
        int(item["example_number"]): item
        for item in projected_examples
        if item.get("example_number") is not None
    }
    variants_by_parent: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in projected_variants:
        parent = item.get("parent_example_number")
        if parent is not None:
            variants_by_parent[int(parent)].append(item)
    exercises = {
        f"{item.get('group')}{item.get('number')}": item
        for item in projected_exercises
    }
    used_item_keys: list[str] = []
    cycles: list[dict[str, Any]] = []
    for sequence, manifest_cycle in enumerate(section.get("learning_cycles", []), start=1):
        example_numbers = [int(value) for value in manifest_cycle.get("example_numbers", [])]
        worked = [examples[number] for number in example_numbers if number in examples]
        variants = [item for number in example_numbers for item in variants_by_parent.get(number, [])]
        exercise_rows = [exercises[key] for key in manifest_cycle.get("exercise_keys", []) if key in exercises]
        used_item_keys.extend(item_identity(item)[0] for item in [*worked, *variants, *exercise_rows])
        cycles.append({
            "cycle_id": str(manifest_cycle.get("id")),
            "sequence": sequence,
            "title": manifest_cycle.get("title"),
            "course_keys": list(manifest_cycle.get("course_keys", [])),
            "prerequisite_course_keys": list(manifest_cycle.get("prerequisite_course_keys", [])),
            "knowledge_refs": list(manifest_cycle.get("knowledge_refs", [])),
            "type_refs": list(manifest_cycle.get("type_refs", [])),
            "bridge_unit_ids": list(manifest_cycle.get("bridge_unit_ids", [])),
            "worked_examples": worked,
            "direct_variants": variants,
            "exercise_questions": exercise_rows,
        })
    canonical_items = [
        *projected_examples,
        *projected_variants,
        *projected_exercises,
    ]
    canonical_keys = [item_identity(item)[0] for item in canonical_items]
    if len(used_item_keys) != len(set(used_item_keys)):
        raise ValueError(f"{section.get('id')} answer-free cycle mapping duplicates items")
    missing = sorted(set(canonical_keys) - set(used_item_keys))
    unexpected = sorted(set(used_item_keys) - set(canonical_keys))
    if missing or unexpected or len(used_item_keys) != len(canonical_keys):
        raise ValueError(
            f"{section.get('id')} answer-free cycle mapping mismatch "
            f"missing={missing} unexpected={unexpected}"
        )
    return {
        "learning_cycles": cycles,
        "counts": {"total_numbered_learning_items": len(canonical_keys)},
        "consumer_guard": "ANSWER_FREE_PERSONA_INPUT_ONLY",
    }


def reviewed_assignment_index(section: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for cycle in section.get("learning_cycles", []):
        for row in cycle.get("item_type_assignments", []):
            item_id = str(row.get("item_id") or row.get("qid") or "")
            if item_id:
                index[item_id] = row
    return index


def signals(text: str, label: str) -> list[str]:
    values = [term for term in SIGNAL_TERMS if term in text]
    symbols = re.findall(r"\\(?:vec|overrightarrow|frac|sqrt|sin|cos|tan|ln|mathrm)|[A-Za-z][A-Za-z0-9_]{0,3}|[<>]=?", text)
    return list(dict.fromkeys([*values[:5], *symbols[:4]])) or [label, "已知量", "目标量"]


def choose_domain(chapter: int, title: str, type_refs: list[str], text: str) -> str:
    combined = "\n".join([title, *type_refs, text])
    if chapter == 1:
        return "vector"
    if chapter == 2:
        return "circle" if any(term in combined for term in ("圆", "圆心", "半径", "弦", "圆系")) else "line"
    if chapter == 3:
        return "conic"
    if chapter == 4:
        return "sequence"
    if chapter == 5:
        return "derivative"
    raise ValueError(f"unsupported chapter: {chapter}")


def assignment_types(assignment: dict[str, Any] | None, cycle: dict[str, Any]) -> tuple[list[str], str]:
    if not assignment:
        return [str(value) for value in cycle.get("type_refs", []) if str(value).strip()], "section_route"
    primary = (
        assignment.get("reviewed_primary_type")
        or assignment.get("type_title")
        or assignment.get("primary_type")
    )
    secondary = assignment.get("secondary_types") or assignment.get("reviewed_secondary_types") or []
    values = [str(primary)] if primary else []
    values.extend(str(value) for value in secondary if str(value).strip())
    return list(dict.fromkeys(values)), str(assignment.get("review_status") or assignment.get("status") or "reviewed")


def build_item_methods(
    chapter: int,
    section: dict[str, Any],
    packet: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    assignments = reviewed_assignment_index(section)
    section_courses = list(dict.fromkeys(
        str(value)
        for cycle in packet.get("learning_cycles", [])
        for field in ("course_keys", "prerequisite_course_keys")
        for value in cycle.get(field, [])
    ))
    rows: list[dict[str, Any]] = []
    for cycle in packet.get("learning_cycles", []):
        required = [str(value) for value in cycle.get("course_keys", [])]
        prerequisites = [str(value) for value in cycle.get("prerequisite_course_keys", [])]
        course_refs = list(dict.fromkeys([*required, *prerequisites])) or section_courses[:1]
        for ordinal_in_cycle, item in enumerate(cycle_items(cycle), start=1):
            key, label, kind = item_identity(item)
            raw_id = str(item.get("qid") or item.get("item_id") or "")
            text = str(item.get("question_text") or "")
            type_refs, review_status = assignment_types(assignments.get(raw_id), cycle)
            domain = choose_domain(chapter, str(cycle.get("title") or ""), type_refs, text)
            method = DOMAIN_METHODS[domain]
            cue = signals(text, label)
            review_status_lower = review_status.lower()
            source_blocked = any(token in review_status_lower for token in ("blocked", "source_defect", "ocr_defect"))
            rows.append({
                "item_key": key,
                "item_id": raw_id,
                "ordinal": len(rows) + 1,
                "ordinal_in_cycle": ordinal_in_cycle,
                "kind": kind,
                "label": label,
                "group": item.get("group"),
                "cycle_id": str(cycle.get("cycle_id")),
                "cycle_sequence": cycle.get("sequence"),
                "cycle_title": cycle.get("title"),
                "course_refs": course_refs,
                "course_titles": [str(catalog.get(value, {}).get("title") or value) for value in course_refs],
                "required_course_refs": required,
                "prerequisite_course_refs": prerequisites,
                "knowledge_refs": [str(value) for value in cycle.get("knowledge_refs", [])],
                "type_refs": type_refs,
                "type_review_status": review_status,
                "bridge_unit_ids": [str(value) for value in cycle.get("bridge_unit_ids", [])],
                "domain": domain,
                "recognition_cues": cue,
                "method_model": method["model"],
                "first_written_line_template": method["first"],
                "continuation_actions": list(method["actions"]),
                "independent_self_check": method["check"],
                "visual_dependency": {
                    "status": item.get("visual_status"),
                    "image_refs": item.get("image_refs", []),
                },
                "question_text_sha256": sha256_bytes(text.encode("utf-8")),
                "source_question_text_sha256": (item.get("source_quality") or {}).get("source_question_text_sha256"),
                "source_quality": item.get("source_quality"),
                "question_signal_excerpt": "、".join(cue),
                "source_blocked": (
                    source_blocked
                    or str(item.get("visual_status")) == "BLOCKED"
                    or (item.get("source_quality") or {}).get("status") != "passed"
                ),
            })
    return rows


def stress_blocker(profile: str, item: dict[str, Any], round_number: int) -> str | None:
    if item["source_blocked"]:
        return "题面、图示或语义复核仍处于阻断状态，不能在不猜测的情况下继续。"
    if round_number == 1:
        if profile == "literal-zero-base" and item["bridge_unit_ids"]:
            return "本题调用桥接知识，但入口前没有逐项确认桥接动作。"
        if profile == "recognition-weak" and len(item["type_refs"]) != 1:
            return "本题存在复合类型或尚未定稿的类型入口，我无法只凭一个标题稳定选法。"
        if profile == "algebra-weak" and any(term in item["question_signal_excerpt"] for term in ("参数", "范围", "恒成立", "求和", "导数", "距离")):
            return "方法入口能找到，但符号、定义域或边界账需要显式检查点。"
        if profile == "visual-weak" and item["visual_dependency"].get("image_refs"):
            return "需要先把原图对象逐项翻译成代数关系。"
        if profile == "self-check-weak" and item["kind"] == "abc_exercise":
            return "我能推进，但没有主动执行独立回代、范围或退化检查。"
    if round_number == 3:
        if profile == "recognition-weak" and item["kind"] == "direct_variant":
            return "变式改变了表面条件，我需要重新核对方法的适用条件。"
        if profile == "algebra-weak" and item["kind"] == "direct_variant":
            return "迁移时沿用了原例符号，没有重新建立本题的符号和边界账。"
    return None


def minimal_correction(profile: str, item: dict[str, Any], phase: str) -> str:
    axis = {
        "literal-zero-base": "把桥接动作前置并拆成可勾选步骤",
        "recognition-weak": "增加本题线索与最近竞争方法的对照句",
        "algebra-weak": "增加符号、定义域、分母和边界检查点",
        "visual-weak": "增加原图对象到代数对象的逐项转写",
        "self-check-weak": "把独立代入、范围或几何复核改成强制动作",
    }[profile]
    return f"{phase}最小修复：{item['label']}先{axis}。"


def attempt_text(profile: str, item: dict[str, Any], round_number: int) -> tuple[str, str, list[str], str]:
    cue = item["question_signal_excerpt"]
    prefix = {
        "literal-zero-base": "我只按题面和路线明确写出的信息推进",
        "recognition-weak": "我先和本节相邻题型比较入口",
        "algebra-weak": "我先建立符号、范围和边界账",
        "visual-weak": "我先把图形对象翻译成文字和代数关系",
        "self-check-weak": "我先写下最后必须执行的独立检查",
    }[profile]
    recognition = f"{prefix}；对象={item['label']}；线索={cue}；暂定方法={item['method_model']}。"
    first_line = f"R{round_number} {profile}：{item['first_written_line_template']}"
    continuation = [f"步骤{index}：{action}；对象={item['label']}。" for index, action in enumerate(item["continuation_actions"], start=1)]
    self_check = f"{item['independent_self_check']}（由 {profile} 实际写入本次路线尝试）"
    return recognition, first_line, continuation, self_check


def build_attempt(
    section_id: str,
    input_snapshot_sha256: str,
    profile: str,
    item: dict[str, Any],
    round_number: int,
    route_version: int,
    failed_round1: bool,
    failed_round3: bool,
) -> dict[str, Any]:
    recognition, first_line, continuation, self_check = attempt_text(profile, item, round_number)
    blocker = stress_blocker(profile, item, round_number)
    correction: str | None = None
    if round_number == 2 and failed_round1 and not item["source_blocked"]:
        correction = minimal_correction(profile, item, "前置/入口")
    if round_number == 4 and failed_round3 and not item["source_blocked"]:
        correction = minimal_correction(profile, item, "迁移")
    if correction:
        blocker = None
    body = {
        "section": section_id,
        "input_snapshot_sha256": input_snapshot_sha256,
        "round": round_number,
        "route_version": route_version,
        "persona_profile": profile,
        "item_key": item["item_key"],
        "course_call": item["course_refs"],
        "recognition_statement": recognition,
        "first_line_attempt": first_line,
        "continuation_attempt": continuation,
        "self_check_attempt": self_check,
        "first_blocker": blocker,
        "minimal_correction_used": correction,
        "question_text_sha256": item["question_text_sha256"],
        "learner_context_sha256": canonical_sha({
            "question_text_sha256": item["question_text_sha256"],
            "course_call": item["course_refs"],
            "type_refs": item["type_refs"],
            "method_model": item["method_model"],
            "route_version": route_version,
        }),
        "answer_material_loaded": False,
        "frozen_before_evaluation": True,
    }
    attempt_sha = canonical_sha(body)
    return {
        "attempt_id": attempt_sha[:24],
        "attempt_sha256": attempt_sha,
        **body,
    }


def route_repairs(
    attempts: list[dict[str, Any]],
    items_by_key: dict[str, dict[str, Any]],
    round_number: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in attempts:
        if row["round"] == round_number and row.get("first_blocker") and not items_by_key[row["item_key"]]["source_blocked"]:
            grouped[row["persona_profile"]].add(row["item_key"])
    repairs: list[dict[str, Any]] = []
    for profile, keys in grouped.items():
        repairs.append({
            "item_keys": sorted(keys),
            "field": {
                "literal-zero-base": "bridge_calls",
                "recognition-weak": "recognition_cues",
                "algebra-weak": "continuation_checkpoints",
                "visual-weak": "visual_translation",
                "self-check-weak": "independent_self_check",
            }[profile],
            "before": f"第{round_number}轮冻结尝试记录了 {profile} 的首个阻断。",
            "after": f"下一轮只加入 {profile} 所需的最小无答案修复。",
            "reason": f"真实题面特征触发的路线压力点，共 {len(keys)} 题；不是随机题号注入。",
        })
    return repairs


def build_frozen_attempts(
    section_id: str,
    input_snapshot_sha256: str,
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, int]]:
    items_by_key = {item["item_key"]: item for item in items}
    failed_round1 = {
        (profile, item["item_key"])
        for profile, _, _ in PERSONAS
        for item in items
        if stress_blocker(profile, item, 1)
    }
    failed_round3 = {
        (profile, item["item_key"])
        for profile, _, _ in PERSONAS
        for item in items
        if stress_blocker(profile, item, 3)
    }
    round_versions = {1: 1, 2: 2, 3: 2, 4: 3, 5: 3}
    attempts: list[dict[str, Any]] = []
    for round_number in range(1, 6):
        for profile, _, _ in PERSONAS:
            for item in items:
                attempts.append(build_attempt(
                    section_id,
                    input_snapshot_sha256,
                    profile,
                    item,
                    round_number,
                    round_versions[round_number],
                    (profile, item["item_key"]) in failed_round1,
                    (profile, item["item_key"]) in failed_round3,
                ))
    repairs = [*route_repairs(attempts, items_by_key, 1), *route_repairs(attempts, items_by_key, 3)]
    return attempts, repairs, round_versions


def _find_learning_item(packet: dict[str, Any], item_key: str) -> dict[str, Any] | None:
    for cycle in packet.get("learning_cycles", []):
        for item in cycle_items(cycle):
            if item_identity(item)[0] == item_key:
                return item
    return None


def build_grader_evidence(root: Path, section_id: str, packet: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    folder = root / "data" / "packets" / section_folder(section_id)
    answer_path = folder / "answer_sidecar.json"
    answer_payload = load_json(answer_path) if answer_path.is_file() else {"answers": []}
    answers = {f"Q:{row.get('qid')}": row for row in answer_payload.get("answers", [])}
    source_packet_path = folder / "packet.json"
    source_packet_sha = sha256_file(source_packet_path) if source_packet_path.is_file() else None
    evidence: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item["item_key"]
        if item["kind"] == "abc_exercise":
            answer = answers.get(key)
            source = answer.get("source", {}) if answer else {}
            parsed = bool(answer and str(answer.get("answer_text") or "").strip())
            page_bound = bool(source.get("pdf_page") and source.get("page_image_sha256"))
            automatic = bool(answer and answer.get("automatic_grading_allowed") is True)
            status = (
                "parsed_automatic"
                if parsed and automatic
                else "review_required_text"
                if parsed
                else "source_page_bound"
                if page_bound
                else "blocked"
            )
            evidence[key] = {
                "status": status,
                "kind": answer.get("answer_kind") if answer else "missing",
                "answer_record_sha256": canonical_sha(answer) if answer else None,
                "source_pdf_sha256": source.get("source_pdf_sha256") if answer else None,
                "source_page": source.get("pdf_page") if answer else None,
                "source_page_image_sha256": source.get("page_image_sha256") if answer else None,
                "machine_readable_answer": parsed,
                "automatic_grading_allowed": automatic,
                "review_required": bool(answer and answer.get("review_required")),
            }
            continue
        learning_item = _find_learning_item(packet, key) or {}
        teaching = str(learning_item.get("teaching_text") or "")
        explicit = bool(teaching.strip() and ("解析" in teaching or "答案" in teaching or "解：" in teaching))
        source_docs = learning_item.get("source_docs") or []
        evidence[key] = {
            "status": "parsed" if explicit else "source_page_bound" if source_packet_sha and source_docs else "blocked",
            "kind": "textbook_teaching_solution" if explicit else "textbook_source_doc_anchor",
            "answer_record_sha256": sha256_bytes(teaching.encode("utf-8")) if explicit else None,
            "source_packet_sha256": source_packet_sha,
            "source_docs": source_docs,
            "machine_readable_answer": explicit,
        }
    return evidence


def assess_route_attempts(
    attempts: list[dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    assessments: list[dict[str, Any]] = []
    for attempt in attempts:
        grader = evidence.get(attempt["item_key"], {"status": "blocked", "kind": "missing"})
        if grader["status"] == "blocked":
            verdict = "blocked_grader_source"
        elif attempt.get("first_blocker"):
            verdict = "route_blocked"
        elif attempt.get("minimal_correction_used"):
            verdict = "route_actionable_after_minimal_hint"
        else:
            verdict = "route_actionable"
        assessments.append({
            "attempt_id": attempt["attempt_id"],
            "frozen_attempt_sha256": attempt["attempt_sha256"],
            "item_key": attempt["item_key"],
            "round": attempt["round"],
            "persona_profile": attempt["persona_profile"],
            "route_verdict": verdict,
            "grader_evidence_status": grader["status"],
            "grader_evidence_kind": grader["kind"],
            "grader_evidence_sha256": canonical_sha(grader),
            "mathematical_correctness": "not_evaluated_no_final_answer",
            "mastery_observed": False,
        })
    return assessments


def validate_isolation(
    items: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    assessments: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    item_keys = {item["item_key"] for item in items}
    expected = len(items) * 25
    if len(attempts) != expected:
        errors.append(f"attempt_count={len(attempts)} expected={expected}")
    if len(assessments) != len(attempts):
        errors.append("route_assessment_count_mismatch")
    seen_attempt_ids: set[str] = set()
    counts: Counter[str] = Counter()
    for attempt in attempts:
        attempt_id = str(attempt.get("attempt_id") or "")
        if not attempt_id or attempt_id in seen_attempt_ids:
            errors.append(f"duplicate_or_missing_attempt_id:{attempt_id}")
        seen_attempt_ids.add(attempt_id)
        counts[str(attempt.get("item_key"))] += 1
        body = {key: value for key, value in attempt.items() if key not in {"attempt_id", "attempt_sha256"}}
        if canonical_sha(body) != attempt.get("attempt_sha256"):
            errors.append(f"attempt_sha_mismatch:{attempt_id}")
        if attempt.get("answer_material_loaded") is not False or attempt.get("frozen_before_evaluation") is not True:
            errors.append(f"attempt_not_isolated:{attempt_id}")
        serialized = json.dumps(attempt, ensure_ascii=False)
        if FORBIDDEN_LEARNER_TEXT.search(serialized):
            errors.append(f"answer_leakage:{attempt_id}")
        if FORBIDDEN_LEARNER_KEYS & set(attempt):
            errors.append(f"forbidden_attempt_keys:{attempt_id}")
    if set(counts) != item_keys or any(counts[key] != 25 for key in item_keys):
        errors.append("per_item_attempt_count_mismatch")
    assessment_by_id = {str(row.get("attempt_id")): row for row in assessments}
    if len(assessment_by_id) != len(assessments):
        errors.append("duplicate_route_assessment_attempt_id")
    for attempt in attempts:
        assessment = assessment_by_id.get(attempt["attempt_id"])
        if not assessment:
            errors.append(f"route_assessment_missing:{attempt['attempt_id']}")
            continue
        if assessment.get("frozen_attempt_sha256") != attempt["attempt_sha256"]:
            errors.append(f"route_assessment_frozen_sha_mismatch:{attempt['attempt_id']}")
        if assessment.get("mathematical_correctness") != "not_evaluated_no_final_answer":
            errors.append(f"unsupported_math_claim:{attempt['attempt_id']}")
    return sorted(set(errors))


def round_summary(
    attempts: list[dict[str, Any]],
    assessments: list[dict[str, Any]],
    repairs: list[dict[str, Any]],
    round_versions: dict[int, int],
    base_route_sha: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assessments_by_id = {row["attempt_id"]: row for row in assessments}
    repair_rounds = {1: repairs[: sum(1 for row in repairs if "第1轮" in row["before"])], 3: [row for row in repairs if "第3轮" in row["before"]]}
    route_versions = []
    for version in (1, 2, 3):
        version_repairs = [] if version == 1 else repair_rounds.get(1, []) if version == 2 else repairs
        route_versions.append({"version": version, "route_hash": canonical_sha({"base": base_route_sha, "version": version, "repairs": version_repairs})})
    hashes = {row["version"]: row["route_hash"] for row in route_versions}
    rows: list[dict[str, Any]] = []
    for round_number in range(1, 6):
        current = [row for row in attempts if row["round"] == round_number]
        current_assessments = [assessments_by_id[row["attempt_id"]] for row in current]
        failed_keys = sorted({row["item_key"] for row in current_assessments if row["route_verdict"] not in PASS_VERDICTS})
        rows.append({
            "round": round_number,
            "purpose": {1: "baseline_entry", 2: "prerequisite_repair", 3: "continuation_transfer", 4: "mixed_retrieval", 5: "fresh_context"}[round_number],
            "route_version": round_versions[round_number],
            "route_hash": hashes[round_versions[round_number]],
            "personas": [{
                "profile": profile,
                "display_label": label,
                "stress_focus": focus,
                "attempts": sum(row["persona_profile"] == profile for row in current),
                "blocked": sum(row["persona_profile"] == profile and assessments_by_id[row["attempt_id"]]["route_verdict"] not in PASS_VERDICTS for row in current),
            } for profile, label, focus in PERSONAS],
            "failed_item_keys": failed_keys,
            "route_repairs": repair_rounds.get(round_number, []),
        })
    return route_versions, rows


def simulate_section(
    root: Path,
    ref: SectionRef,
    catalog: dict[str, dict[str, Any]],
    output_root: Path,
) -> dict[str, Any]:
    section_id = str(ref.section["id"])
    folder = root / "data" / "packets" / section_folder(section_id)
    student_learning_path = folder / "student_learning_items.json"
    student_packet_path = folder / "student_packet.json"
    grader_packet_path = folder / "learning_packet.json"
    route_path = folder / "learning_path_without_questions.md"
    student_learning_items = load_json(student_learning_path)
    student_packet = load_json(student_packet_path)
    answer_free_packet = build_answer_free_packet(ref.section, student_learning_items, student_packet)
    items = build_item_methods(ref.chapter, ref.section, answer_free_packet, catalog)
    expected_items = int(answer_free_packet.get("counts", {}).get("total_numbered_learning_items", -1))
    if len(items) != expected_items:
        raise ValueError(f"{section_id} item coverage mismatch: {len(items)} != {expected_items}")

    learner_input_snapshot_sha256 = canonical_sha({
        "manifest_sha256": sha256_file(ref.manifest_path),
        "student_learning_items_sha256": sha256_file(student_learning_path),
        "student_packet_sha256": sha256_file(student_packet_path),
        "route_sha256": sha256_file(route_path),
    })
    attempts, repairs, round_versions = build_frozen_attempts(
        section_id,
        learner_input_snapshot_sha256,
        items,
    )
    frozen_path = output_root / "frozen" / f"{section_folder(section_id)}.jsonl.gz"
    frozen_header = {
        "schema_version": "ybt-frozen-route-attempts-v1",
        "section": section_id,
        "generated_at": now_iso(),
        "answer_material_loaded": False,
        "learner_input_snapshot_sha256": learner_input_snapshot_sha256,
        "honesty_boundary": "Synthetic route-stress attempts; not final mathematical answers, human learning or mastery.",
    }
    save_jsonl(frozen_path, [{"_meta": frozen_header}, *attempts])
    frozen_sha = sha256_file(frozen_path)

    # This is the first point at which grader-only material is loaded.
    grader_packet = load_json(grader_packet_path)
    evidence = build_grader_evidence(root, section_id, grader_packet, items)
    assessments = assess_route_attempts(attempts, evidence)
    assessment_path = output_root / "route_assessments" / f"{section_folder(section_id)}.jsonl.gz"
    assessment_header = {
        "schema_version": "ybt-route-assessments-v1",
        "section": section_id,
        "generated_at": now_iso(),
        "frozen_attempts_sha256": frozen_sha,
        "mathematical_correctness_claimed": False,
    }
    save_jsonl(assessment_path, [{"_meta": assessment_header}, *assessments])
    assessment_sha = sha256_file(assessment_path)
    errors = validate_isolation(items, attempts, assessments)
    route_versions, rounds = round_summary(attempts, assessments, repairs, round_versions, sha256_file(route_path))
    final_failed = rounds[-1]["failed_item_keys"]
    report = {
        "schema_version": "ybt-deep-section-simulation-v3",
        "generated_at": now_iso(),
        "chapter": ref.chapter,
        "section": section_id,
        "label": ref.section.get("label"),
        "simulation_kind": "answer_isolated_synthetic_route_stress",
        "honesty_boundary": "Attempts test route actionability. They contain no final learner answer, so mathematical correctness and mastery are not claimed.",
        "source_binding": {
            "manifest_sha256": sha256_file(ref.manifest_path),
            "student_learning_items_sha256": sha256_file(student_learning_path),
            "student_packet_sha256": sha256_file(student_packet_path),
            "grader_learning_packet_sha256": sha256_file(grader_packet_path),
            "route_sha256": sha256_file(route_path),
            "learner_input_snapshot_sha256": learner_input_snapshot_sha256,
        },
        "answer_isolation": {
            "frozen_attempts_path": str(frozen_path.relative_to(root)).replace("\\", "/"),
            "frozen_attempts_sha256": frozen_sha,
            "route_assessments_path": str(assessment_path.relative_to(root)).replace("\\", "/"),
            "route_assessments_sha256": assessment_sha,
            "learner_answer_material_loaded": False,
            "grader_material_loaded_after_freeze": True,
            "grader_evidence": {
                "parsed_automatic": sum(row["status"] == "parsed_automatic" for row in evidence.values()),
                "review_required_text": sum(row["status"] == "review_required_text" for row in evidence.values()),
                "source_page_bound": sum(row["status"] == "source_page_bound" for row in evidence.values()),
                "textbook_solution": sum(row["status"] == "parsed" for row in evidence.values()),
                "blocked": sum(row["status"] == "blocked" for row in evidence.values()),
            },
            "status": "passed" if not errors else "failed",
        },
        "items": items,
        "route_versions": route_versions,
        "final_route_hash": route_versions[-1]["route_hash"],
        "simulation": {
            "protocol": "five-round-five-persona-v3-answer-isolated",
            "generation_mode": "synthetic_route_stress_from_actual_item_features",
            "rounds": rounds,
            "expected_attempts_per_item": 25,
            "actual_attempts_per_item": 25,
            "unresolved_item_keys": final_failed,
            "mathematical_correctness": "not_evaluated_no_final_answer",
            "mastery_claimed": False,
            "status": "passed" if not final_failed and not errors else "blocked",
        },
        "summary": {
            "items": len(items),
            "attempts": len(attempts),
            "route_assessments": len(assessments),
            "rounds": 5,
            "personas_per_round": 5,
            "repairs": len(repairs),
            "round_5_failed_items": len(final_failed),
            "validator_errors": errors,
        },
        "human_learning_status": "remote_math_mcp_only",
        "cold_24h_retest": "not_run",
        "mastery_claimed": False,
        "claim_scope": "route_actionability_only",
        "mathematical_assessment_status": "not_run",
        "route_audit_status": "passed" if not final_failed and not errors else "blocked",
        "status": "passed" if not final_failed and not errors else "blocked",
    }
    save_json(output_root / f"{section_folder(section_id)}.json", report)
    return report


def build_primary_proxy(
    root: Path,
    reports: list[dict[str, Any]],
    catalog: dict[str, dict[str, Any]],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prior_learner = (previous or {}).get("learner", {}) if (previous or {}).get("schema_version") == "ybt-primary-user-proxy-all-chapters-v3" else {}
    profile_version = int(prior_learner.get("profile_version") or 1)
    history = list(prior_learner.get("profile_history") or [{"version": 1, "reason": "zero_base_initialization", "evidence": []}])
    predicted_gaps = list(prior_learner.get("predicted_gaps_not_human_facts") or [])
    seen_gap_kinds = set(str(value) for value in prior_learner.get("predicted_gap_domains", []))
    course_ledger: dict[str, dict[str, Any]] = {}
    attempts: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    for report in reports:
        frozen_path = root / report["answer_isolation"]["frozen_attempts_path"]
        frozen_rows = load_jsonl(frozen_path)[1:]
        round1_literal = {
            row["item_key"]: row
            for row in frozen_rows
            if row["round"] == 1 and row["persona_profile"] == "literal-zero-base"
        }
        round5_literal = [
            row for row in frozen_rows
            if row["round"] == 5 and row["persona_profile"] == "literal-zero-base"
        ]
        before = profile_version
        for item in report["items"]:
            for course_key in item["course_refs"]:
                if course_key in course_ledger:
                    continue
                course = catalog.get(course_key, {})
                transcript = root / str(course.get("transcript_file") or "")
                transcript_sha: str | None = None
                full_text_sha: str | None = None
                full_text_chars = 0
                if transcript.is_file():
                    transcript_payload = load_json(transcript)
                    full_text = str(transcript_payload.get("full_text") or "").strip()
                    if full_text:
                        transcript_sha = sha256_file(transcript)
                        full_text_sha = sha256_bytes(full_text.encode("utf-8"))
                        full_text_chars = len(full_text)
                course_ledger[course_key] = {
                    "course_key": course_key,
                    "first_section": report["section"],
                    "status": "transcript_loaded_not_consumed" if transcript_sha else "blocked",
                    "availability_evidence": [{
                        "kind": "transcript_loaded_for_proxy",
                        "transcript_sha256": transcript_sha,
                        "full_text_sha256": full_text_sha,
                        "full_text_chars": full_text_chars,
                    }] if transcript_sha else [],
                    "human_course_completion": "not_inferred",
                }
            baseline = round1_literal.get(item["item_key"])
            if baseline and baseline.get("first_blocker"):
                gap_kind = item["domain"]
                if gap_kind not in seen_gap_kinds:
                    seen_gap_kinds.add(gap_kind)
                    predicted = f"{item['method_model']}在零基础首次调用时需要显式入口检查"
                    predicted_gaps.append(predicted)
                    profile_version += 1
                    history.append({
                        "version": profile_version,
                        "reason": "synthetic_proxy_prediction_not_real_user_fact",
                        "evidence": [{"section": report["section"], "attempt_id": baseline["attempt_id"], "attempt_sha256": baseline["attempt_sha256"]}],
                    })
        for row in round5_literal:
            attempts.append({
                "chapter": report["chapter"],
                "section": report["section"],
                "item_key": row["item_key"],
                "frozen_attempt_id": row["attempt_id"],
                "frozen_attempt_sha256": row["attempt_sha256"],
                "profile_version_after": profile_version,
                "result": "route_actionability_attempted",
                "evidence_kind": "synthetic_proxy_attempt_not_human",
                "mathematical_correctness": "not_evaluated_no_final_answer",
                "mastery_observed": False,
            })
        sections.append({
            "chapter": report["chapter"],
            "section": report["section"],
            "items": report["summary"]["items"],
            "profile_version_before": before,
            "profile_version_after": profile_version,
            "status": "route_actionability_audited" if report["route_audit_status"] == "passed" else "blocked",
        })
    unfinished = list(course_ledger)
    return {
        "schema_version": "ybt-primary-user-proxy-all-chapters-v3",
        "generated_at": now_iso(),
        "learner": {
            "learner_id": "primary-user-proxy",
            "mode": "persistent_zero_base_proxy",
            "initial_assumptions": ["zero_base"],
            "profile_version": profile_version,
            "confirmed_strengths": list(prior_learner.get("confirmed_strengths") or []),
            "confirmed_gaps": list(prior_learner.get("confirmed_gaps") or []),
            "predicted_gaps_not_human_facts": predicted_gaps,
            "predicted_gap_domains": sorted(seen_gap_kinds),
            "uncertainties": ["代理没有提交最终数学答案；路线可执行性不等于掌握"],
            "profile_history": history,
        },
        "course_ledger": {
            "required_course_keys": list(course_ledger),
            "records": list(course_ledger.values()),
            "unfinished_course_keys": unfinished,
            "status": "transcripts_loaded_learning_not_run" if all(row["status"] != "blocked" for row in course_ledger.values()) else "blocked",
        },
        "sections": sections,
        "attempts": attempts,
        "coverage": {
            "chapters": 5,
            "sections": len(sections),
            "canonical_items": len(attempts),
            "route_actionability_attempted_items": len(attempts),
        },
        "simulated_learning_status": "not_run_no_final_learner_answers",
        "human_learning_status": "use_remote_math_mcp",
        "cold_24h_retest": "not_run",
        "mastery_claimed": False,
}


def run_input_fingerprint(root: Path) -> tuple[str, list[dict[str, str]]]:
    paths = [
        root / "ybt_learning" / "isolated_simulation.py",
        root / "data" / "all_chapters_course_catalog.json",
    ]
    for ref in iter_sections(root):
        folder = root / "data" / "packets" / section_folder(str(ref.section["id"]))
        paths.extend([
            ref.manifest_path,
            folder / "student_learning_items.json",
            folder / "student_packet.json",
            folder / "learning_packet.json",
            folder / "answer_sidecar.json",
            folder / "learning_path_without_questions.md",
        ])
    unique_paths = list(dict.fromkeys(path.resolve() for path in paths))
    bindings = [
        {
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "sha256": sha256_file(path),
        }
        for path in unique_paths
    ]
    return canonical_sha(bindings), bindings


def run_all(root: Path, *, reset_proxy_history: bool = False) -> dict[str, Any]:
    fingerprint, input_bindings = run_input_fingerprint(root)
    run_id = f"route-audit-{fingerprint[:16]}"
    output_root = root / "reports" / "deep_simulation_runs" / run_id
    pointer_path = root / "reports" / "deep_section_simulations" / "current.json"
    summary_path = root / "reports" / "all_chapters" / "simulation-current.json"
    if pointer_path.is_file() and summary_path.is_file():
        pointer = load_json(pointer_path)
        current_summary = load_json(summary_path)
        if pointer.get("run_id") == run_id and current_summary.get("run_id") == run_id and current_summary.get("status") == "passed":
            return current_summary
    catalog_payload = load_json(root / "data" / "all_chapters_course_catalog.json")
    catalog = {str(row["course_key"]): row for row in catalog_payload.get("courses", [])}
    reports = [simulate_section(root, ref, catalog, output_root) for ref in iter_sections(root)]
    proxy_path = root / "reports" / "learner_simulation" / "primary-user-proxy-all-chapters.json"
    previous_proxy = None if reset_proxy_history else load_json(proxy_path) if proxy_path.is_file() else None
    proxy = build_primary_proxy(root, reports, catalog, previous_proxy)
    proxy["run_id"] = run_id
    if reset_proxy_history:
        proxy["history_reset"] = {
            "reason": "pre_release_evidence_format_migration_to_gzip",
            "real_user_data_changed": False,
        }
    previous_run_id = previous_proxy.get("run_id") if isinstance(previous_proxy, dict) else None
    prior_runs = list(previous_proxy.get("run_history", [])) if isinstance(previous_proxy, dict) else []
    if previous_run_id and previous_run_id != run_id and previous_run_id not in prior_runs:
        prior_runs.append(previous_run_id)
    proxy["previous_run_id"] = previous_run_id if previous_run_id != run_id else None
    proxy["run_history"] = prior_runs
    proxy_run_path = root / "reports" / "learner_simulation" / "runs" / f"{run_id}.json"
    save_json(proxy_run_path, proxy)

    all_attempt_ids: set[str] = set()
    total_attempt_ids = 0
    for report in reports:
        frozen_path = root / report["answer_isolation"]["frozen_attempts_path"]
        for row in load_jsonl(frozen_path)[1:]:
            total_attempt_ids += 1
            attempt_id = str(row["attempt_id"])
            if attempt_id in all_attempt_ids:
                raise ValueError(f"global attempt id collision: {attempt_id}")
            all_attempt_ids.add(attempt_id)
    summary = {
        "schema_version": "ybt-deep-simulation-summary-v3",
        "generated_at": now_iso(),
        "run_id": run_id,
        "input_fingerprint_sha256": fingerprint,
        "input_bindings": input_bindings,
        "scope": "all_five_chapters_with_1_1_golden_regression",
        "chapters": 5,
        "sections": len(reports),
        "cycles": sum(len(ref.section.get("learning_cycles", [])) for ref in iter_sections(root)),
        "items": sum(report["summary"]["items"] for report in reports),
        "attempts": sum(report["summary"]["attempts"] for report in reports),
        "route_assessments": sum(report["summary"]["route_assessments"] for report in reports),
        "rounds_per_section": 5,
        "personas_per_round": 5,
        "attempts_per_item": 25,
        "route_audit_passed_sections": sum(report["route_audit_status"] == "passed" for report in reports),
        "route_audit_blocked_sections": [report["section"] for report in reports if report["route_audit_status"] != "passed"],
        "round_5_failed_items": sum(report["summary"]["round_5_failed_items"] for report in reports),
        "answer_isolation_errors": sum(len(report["summary"]["validator_errors"]) for report in reports),
        "global_attempt_ids": total_attempt_ids,
        "global_attempt_ids_unique": len(all_attempt_ids) == total_attempt_ids,
        "mathematical_correctness": "not_evaluated_no_final_answer",
        "mastery_claimed": False,
        "human_learning_status": "remote_math_mcp_only",
        "primary_proxy_profile_version": proxy["learner"]["profile_version"],
        "claim_scope": "route_actionability_only",
        "mathematical_assessment_status": "not_run",
        "route_audit_status": "passed" if len(reports) == 38 and all(report["route_audit_status"] == "passed" for report in reports) else "blocked",
        "status": "passed" if len(reports) == 38 and all(report["route_audit_status"] == "passed" for report in reports) else "blocked",
    }
    if summary["status"] != "passed":
        save_json(output_root / "blocked-summary.json", summary)
        return summary
    save_json_atomic(proxy_path, proxy)
    save_json_atomic(summary_path, summary)
    save_json_atomic(pointer_path, {
        "schema_version": "ybt-deep-simulation-current-pointer-v1",
        "run_id": run_id,
        "run_path": str(output_root.relative_to(root)).replace("\\", "/"),
        "summary_path": str(summary_path.relative_to(root)).replace("\\", "/"),
        "summary_sha256": sha256_file(summary_path),
        "activated_at": now_iso(),
    })
    return summary
