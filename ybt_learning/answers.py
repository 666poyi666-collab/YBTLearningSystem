from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import clean_text, normalize_math


GROUP_RE = re.compile(r"(?i)(?:^|\n)\s*(?:#{1,6}\s*)?(?P<group>[ABC])\s*组")
QUESTION_LINE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?P<number>\d{1,2})\s*(?:\\?[.．、]|(?=（)|(?=\())\s*(?P<rest>.*)$"
)


def _is_question_header(line: str) -> re.Match[str] | None:
    match = QUESTION_LINE_RE.match(line)
    if not match:
        return None
    rest = match.group("rest").strip()
    # 答案页常有“1. B/2. C”，不能把它们误识别成下一道题。
    if re.fullmatch(r"[A-D](?:\s*[,，、/]\s*[A-D])*", rest, flags=re.I):
        return None
    if re.fullmatch(r"(?:解|答案)?\s*[A-D]{1,4}", rest, flags=re.I):
        return None
    if re.match(r"^(?:答案|解析|解答|解法|证明)\b", rest):
        return None
    # 题目标题通常有日期、括号、汉字、数学符号或较长题干；裸数字/字母不是题头。
    if not rest or len(rest) >= 4 or re.search(r"[（(）)·。？?，,；;中文A-Za-z$\\]", rest):
        return match
    return None


def build_answer_index(root: str | Path, expected_groups: dict[str, list[int]]) -> dict[tuple[str, int], dict[str, Any]]:
    """从独立答案册 OCR 构建 (组别, 印刷题号) -> 答案块索引。

    只读答案 OCR；答案永远写入 answer_sidecar，不进入 student_packet。
    """
    root = Path(root)
    if not root.exists():
        return {}
    expected = {(group, n) for group, bounds in expected_groups.items() for n in range(bounds[0], bounds[1] + 1)}
    candidates: dict[tuple[str, int], list[dict[str, Any]]] = {}
    current_group: str | None = None
    fixed_group_by_number = {
        "section-01": {1: "A", 2: "A", 3: "A", 4: "B", 5: "B", 6: "B", 7: "B", 8: "B", 9: "B", 10: "B", 11: "B", 12: "B", 13: "C", 14: "C"},
        "section-02": {1: "A", 2: "A", 3: "A", 4: "A", 5: "B", 6: "B", 7: "B", 8: "B", 9: "B", 10: "B", 11: "B", 12: "B", 13: "B", 14: "C", 15: "C", 16: "C"},
        "section-03": {1: "A", 2: "A", 3: "B", 4: "B", 5: "B", 6: "B", 7: "B", 8: "B", 9: "C", 10: "C", 11: "C", 12: "C"},
        "section-04": {1: "B", 2: "B", 3: "B", 4: "B", 5: "C", 6: "C", 7: "C", 8: "C"},
    }.get(root.name, {})
    for page in sorted(root.glob("doc_*.md"), key=lambda p: int(p.stem.split("_")[-1])):
        raw = normalize_math(clean_text(page.read_text(encoding="utf-8", errors="replace")))
        groups = list(GROUP_RE.finditer(raw))
        if groups:
            current_group = groups[-1].group("group").upper()
        lines = raw.splitlines()
        active: tuple[str, int, int] | None = None
        blocks: list[tuple[str, int, int, int]] = []
        answer_line_re = re.compile(r"^\s*(?:答案|解答)\s*[：:]?\s*(?P<value>.+)$", flags=re.I)
        for line_index, line in enumerate(lines):
            group_match = GROUP_RE.search(line)
            if group_match:
                current_group = group_match.group("group").upper()
            # 在答案 OCR 中，裸的“5. C”是答案，不是新题；为已知题号直接记录答案行，
            # 但不把它作为题干块起点。
            answer_line = re.match(r"^\s*(?P<number>\d{1,2})\s*[.．、]\s*(?P<value>[A-D](?:\s*[,，、/]\s*[A-D])*)\s*$", line, flags=re.I)
            if answer_line:
                number = int(answer_line.group("number"))
                key = (fixed_group_by_number.get(number) or current_group or "?", number)
                if key in expected:
                    candidates.setdefault(key, []).append({"text": answer_line.group("value").strip(), "source": {"file": str(page), "ocr_doc": int(page.stem.split("_")[-1])}, "kind": "answer_marker"})
                continue
            header = _is_question_header(line)
            if not header:
                continue
            number = int(header.group("number"))
            key = (fixed_group_by_number.get(number) or current_group or "?", number)
            if key not in expected:
                continue
            if active is not None:
                blocks.append((active[0], active[1], active[2], line_index))
            active = (key[0], number, line_index)
        if active is not None:
            blocks.append((active[0], active[1], active[2], len(lines)))
        for group, number, start, end in blocks:
            text = "\n".join(lines[start:end]).strip()
            if not text:
                continue
            # 题干块里若只是“解/解析”而没有新题，保留它作为答案证据；
            # 这类 OCR 目录本身是答案册，不会进入 student_packet。
            candidates.setdefault((group, number), []).append({
                "text": text,
                "source": {"file": str(page), "ocr_doc": int(page.stem.split("_")[-1])},
                "kind": "solution_block",
            })
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for key, values in candidates.items():
        # 同一题可能跨页或 OCR 重复；标准答案标记优先，解题块作为可选的独立答案证据。
        result[key] = max(values, key=lambda item: (item.get("kind") == "answer_marker", len(item["text"])))
    return result


def merge_answer_indexes(primary: dict[tuple[str, int], dict[str, Any]], fallback: dict[tuple[str, int], dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    """答案 OCR 有时把答案行放在前一页/下一页；合并时优先保留更明确的答案标记。

    当前 OCR 结果若只有解题过程而没有标准答案字母/数值，仍记为 E1/E0，
    不把它误称为官方判分答案。
    """
    result = dict(fallback)
    for key, value in primary.items():
        if key not in result or value.get("kind") == "answer_marker" or len(value.get("text", "")) > len(result[key].get("text", "")):
            result[key] = value
    return result
