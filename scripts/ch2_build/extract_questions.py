# -*- coding: utf-8 -*-
"""第 2 章题号清单提取（v2，行序扫描）。

从 data/ocr_live_current/second_chapter_109/doc_N.md 按节提取：
  - 知识点头（知识点 N：标题）及其所在页
  - 例题【例 N】、直接变式【变式N】及其父例题（按页顺序最近例）
  - 类型头（类型Ⅰ..）及其包含的例号
  - A/B/C 分组头与组内题号（含 OCR 转义/标题化变体）
  - 题号缺口检测（跨组连续性）→ needs_manual / recovery 候选

输出: tmp/ch2_question_list.json + 控制台汇总
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(r"C:\开发\小工具\一本通学习系统_v7")
OCR_ROOT = ROOT / "data" / "ocr_live_current" / "second_chapter_109"
MANIFEST = json.loads((ROOT / "chapter2_manifest.json").read_text(encoding="utf-8"))

EXAMPLE_RE = re.compile(r"【\s*例\s*(\d+)\s*】")
VARIANT_RE = re.compile(r"【\s*变式\s*(\d*)\s*】")
GROUP_RE = re.compile(r"^#{0,4}\s*(A|B|C)\s*组", re.M)
TYPE_RE = re.compile(r"^#{0,4}\s*类型\s*([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|[IVX]+)\s*[：:、．.]\s*(.*)$", re.M)
KNOWLEDGE_RE = re.compile(r"^#{0,4}\s*知识点\s*(\d+)\s*[：:、.]?\s*(.*)$", re.M)
# 题号行：可选 markdown 标题前缀、可选反斜杠转义点
QNUM_RE = re.compile(r"^#{0,6}\s*(\d+)\s*\\?\s*[.、．]\s*")
# 不计题号的行首
NOISE_STARTS = ("<table", "<div", "![](", "（", "(", "答案", "解析", "解：", "解:", "【", "注", "①", "②", "③", "④", "⑤", "A.", "B.", "C.", "D.", "A．", "B．", "C．", "D．", "一 数", "第", "## 一")


def load_doc(index: int) -> str:
    p = OCR_ROOT / f"doc_{index}.md"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def section_scan(section: dict) -> dict:
    lo, hi = section["ocr_docs"]
    docs = {i: load_doc(i) for i in range(lo, hi + 1)}

    examples: list[dict] = []
    variants: list[dict] = []
    types: list[dict] = []
    knowledge_points: list[dict] = []
    group_numbers: dict[str, list[int]] = {}
    page_hits: dict[int, list[str]] = {}

    def note(page: int, tag: str) -> None:
        page_hits.setdefault(page, [])
        if tag not in page_hits[page]:
            page_hits[page].append(tag)

    current_group: str | None = None
    current_type: dict | None = None
    current_knowledge: dict | None = None
    last_example: int | None = None

    for page in range(lo, hi + 1):
        text = docs.get(page, "")
        if not text:
            page_hits.setdefault(page, []).append("NO_OCR")
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # 1) 组头
            m = GROUP_RE.match(stripped)
            if m:
                current_group = m.group(1)
                group_numbers.setdefault(current_group, [])
                note(page, f"{current_group}组头")
                current_type = None
                continue
            # 2) 类型头
            m = TYPE_RE.match(stripped)
            if m and current_group is None:
                current_type = {"type": m.group(1), "title": m.group(2).strip(), "example_numbers": [], "pages": [page]}
                types.append(current_type)
                note(page, f"类型{m.group(1)}")
                continue
            # 3) 知识点头
            m = KNOWLEDGE_RE.match(stripped)
            if m and current_group is None:
                current_knowledge = {"id": f"{section['id']}-k{m.group(1)}", "label": m.group(2).strip() or f"知识点{m.group(1)}", "pages": [page]}
                knowledge_points.append(current_knowledge)
                note(page, f"知识点{m.group(1)}")
                continue
            # 4) 例题
            m = EXAMPLE_RE.search(stripped)
            if m:
                num = int(m.group(1))
                last_example = num
                if not any(e["number"] == num for e in examples):
                    examples.append({"number": num, "label": f"例{num}", "pages": []})
                e = next(e for e in examples if e["number"] == num)
                if page not in e["pages"]:
                    e["pages"].append(page)
                note(page, f"例{num}")
                if current_type is not None and num not in current_type["example_numbers"]:
                    current_type["example_numbers"].append(num)
                if current_knowledge is not None:
                    ref = f"例{num}"
                    if ref not in current_knowledge.setdefault("examples", []):
                        current_knowledge["examples"].append(ref)
                continue
            # 5) 变式
            m = VARIANT_RE.search(stripped)
            if m:
                suffix = m.group(1)
                label = f"变式{suffix}" if suffix else "变式"
                variants.append({"label": label, "parent_example": last_example, "pages": [page]})
                note(page, label)
                continue
            # 6) 组内题号
            if current_group is not None:
                m = QNUM_RE.match(stripped)
                if m and not stripped.startswith(NOISE_STARTS) and len(stripped) > 3:
                    num = int(m.group(1))
                    if num not in group_numbers[current_group]:
                        group_numbers[current_group].append(num)
                        note(page, f"{current_group}{num}")
                    continue

    # 分组区间（含缺口标记）
    question_groups: dict[str, list[int]] = {}
    gaps: dict[str, list[int]] = {}
    all_nums: list[int] = []
    for g in ("A", "B", "C"):
        nums = sorted(group_numbers.get(g, []))
        all_nums.extend(nums)
        if not nums:
            continue
        first, last = nums[0], nums[-1]
        question_groups[g] = [first, last]
        missing = [n for n in range(first, last + 1) if n not in nums]
        if missing:
            gaps[f"{g}_gaps"] = missing
    all_nums = sorted(set(all_nums))
    # 跨组连续性
    continuity = {}
    order = [g for g in ("A", "B", "C") if g in question_groups]
    for a, b in zip(order, order[1:]):
        continuity[f"{a}->{b}"] = {"ok": question_groups[a][1] + 1 == question_groups[b][0],
                                   "a_last": question_groups[a][1], "b_first": question_groups[b][0]}
    # 全节题号缺口（恢复候选）
    recovery_candidates = []
    if all_nums:
        for n in range(all_nums[0], all_nums[-1] + 1):
            if n not in all_nums:
                recovery_candidates.append({
                    "number": n,
                    "group": next((g for g in ("A", "B", "C") if question_groups.get(g) and question_groups[g][0] <= n <= question_groups[g][1]), None),
                    "reason": "question_number_lost_in_ocr", "needs_manual": True,
                })

    # 逐页对账
    needs_manual_pages: list[dict] = []
    for page in range(lo, hi + 1):
        hits = page_hits.get(page, [])
        if not hits or hits == ["NO_OCR"]:
            needs_manual_pages.append({"page": page + 1, "reason": "no_ocr_or_no_markers"})
            continue
        if not any(h.startswith(("例", "变式", "A", "B", "C", "知识点", "类型")) for h in hits):
            needs_manual_pages.append({"page": page + 1, "reason": f"markers={hits}"})

    return {
        "section": section["id"],
        "label": section["label"],
        "pdf_pages": section["pdf_pages"],
        "ocr_docs": [lo, hi],
        "knowledge_points": knowledge_points,
        "examples": examples,
        "variants": variants,
        "types": types,
        "question_groups": question_groups,
        "group_gaps": gaps,
        "continuity": continuity,
        "all_question_numbers": all_nums,
        "recovery_candidates": recovery_candidates,
        "page_hits": {str(k + 1): v for k, v in page_hits.items()},
        "needs_manual_pages": needs_manual_pages,
    }


def main() -> None:
    if not OCR_ROOT.is_dir():
        raise SystemExit(f"OCR 目录不存在: {OCR_ROOT}")
    out = []
    for section in MANIFEST["sections"]:
        scan = section_scan(section)
        out.append(scan)
        print(json.dumps({
            "section": scan["section"],
            "knowledge_points": len(scan["knowledge_points"]),
            "examples": [e["number"] for e in scan["examples"]],
            "variants": len(scan["variants"]),
            "types": [(t["type"], t["example_numbers"]) for t in scan["types"]],
            "groups": {k: v for k, v in scan["question_groups"].items()},
            "gaps": scan["group_gaps"],
            "continuity": scan["continuity"],
            "recovery": scan["recovery_candidates"],
            "needs_manual_pages": len(scan["needs_manual_pages"]),
        }, ensure_ascii=False))
    (ROOT / "tmp" / "ch2_question_list.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved tmp/ch2_question_list.json")


if __name__ == "__main__":
    main()
