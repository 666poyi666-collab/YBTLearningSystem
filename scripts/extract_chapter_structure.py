#!/usr/bin/env python3
"""Extract textbook layout markers for chapters 2-5 from current OCR.

This script creates evidence inventories only. Missing printed numbers remain
explicit recovery candidates and are never silently treated as verified.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    2: {"manifest": ROOT / "chapter2_manifest.json", "ocr": ROOT / "data" / "ocr_live_current" / "second_chapter_109"},
    3: {"manifest": ROOT / "chapter3_manifest.json", "ocr": ROOT / "data" / "ocr_live_current" / "third_chapter_180"},
    4: {"manifest": ROOT / "chapter4_manifest.json", "ocr": ROOT / "data" / "ocr_live_current" / "chapter4_100"},
    5: {"manifest": ROOT / "chapter5_manifest.json", "ocr": ROOT / "data" / "ocr_live_current" / "chapter5_95"},
}

EXAMPLE_RE = re.compile(r"【\s*例\s*(\d+)\s*】")
VARIANT_RE = re.compile(r"【\s*变式\s*(\d*)\s*】")
GROUP_RE = re.compile(r"^#{0,6}\s*([ABC])\s*组", re.I)
TYPE_RE = re.compile(r"^#{0,6}\s*类型\s*([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|[IVX]+)\s*[：:、．.]?\s*(.*)$", re.I)
KNOWLEDGE_RE = re.compile(r"^#{0,6}\s*知识点\s*(\d+)\s*[：:、．.]?\s*(.*)$")
INLINE_KNOWLEDGE_RE = re.compile(r"(?=知识点\s*\d+\s*[：:])")
QNUM_RE = re.compile(r"^#{0,6}\s*(\d{1,3})\s*\\?\s*[.、．]\s*")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
NOISE_RE = re.compile(r"^(?:答案|解析|解答|解[:：]|第\s*\d+\s*节|一\s*数|高中数学一本通|[ABCD][.．])")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def chapter_sections(chapter: int, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sections = [dict(section) for section in manifest.get("sections") or []]
    if chapter == 3:
        evidence_path = ROOT / "reports" / "builds" / "ch3-ocr-question-list.json"
        evidence = load_json(evidence_path)
        by_id = {row["id"]: row for row in evidence.get("sections") or []}
        for section in sections:
            row = by_id.get(section.get("id"), {})
            section["pdf_pages"] = row.get("pdf_pages")
            section["ocr_docs"] = row.get("ocr_docs")
    for section in sections:
        if not section.get("ocr_docs") and section.get("pdf_pages"):
            start, end = section["pdf_pages"]
            section["ocr_docs"] = [start - 1, end - 1]
    return sections


def compact_label(value: str, fallback: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip(" ：:、.．")
    return value if value and not re.fullmatch(r"知识点\s*\d+", value) else fallback


def merge_knowledge(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in rows:
        key = row["id"]
        if key not in merged:
            merged[key] = dict(row)
            merged[key]["pages"] = list(row.get("pages") or [])
            merged[key]["examples"] = list(row.get("examples") or [])
            order.append(key)
            continue
        target = merged[key]
        if target["label"].startswith("知识点") and not row["label"].startswith("知识点"):
            target["label"] = row["label"]
        target["pages"] = sorted(set([*target["pages"], *row.get("pages", [])]))
        target["examples"] = list(dict.fromkeys([*target["examples"], *row.get("examples", [])]))
    return [merged[key] for key in order]


def infer_expected_groups(observed: dict[str, list[int]]) -> tuple[dict[str, list[int]], list[str]]:
    ordered = [group for group in ("A", "B", "C") if observed.get(group)]
    if not ordered:
        return {}, []
    expected: dict[str, list[int]] = {}
    assumptions: list[str] = []
    for index, group in enumerate(ordered):
        numbers = sorted(set(observed[group]))
        if index == 0:
            start = 1
            if numbers[0] != 1:
                assumptions.append(f"{group}_start_inferred:1:first_observed={numbers[0]}")
        else:
            previous = ordered[index - 1]
            start = expected[previous][1] + 1
            if start != numbers[0]:
                assumptions.append(f"{group}_start_inferred:{start}:first_observed={numbers[0]}")
        if index + 1 < len(ordered):
            next_numbers = sorted(set(observed[ordered[index + 1]]))
            end = next_numbers[0] - 1
            if end != numbers[-1]:
                assumptions.append(f"{group}_end_inferred:{end}:last_observed={numbers[-1]}")
        else:
            end = numbers[-1]
        expected[group] = [start, end]
    return expected, assumptions


def scan_section(section: dict[str, Any], ocr_root: Path) -> dict[str, Any]:
    section_id = str(section.get("id") or "")
    docs_range = section.get("ocr_docs")
    if not isinstance(docs_range, list) or len(docs_range) != 2:
        return {
            "section": section_id,
            "label": section.get("label"),
            "status": "blocked",
            "errors": ["ocr_docs_missing"],
        }
    low, high = docs_range
    docs: dict[int, str] = {}
    missing_docs: list[int] = []
    for page in range(low, high + 1):
        path = ocr_root / f"doc_{page}.md"
        if not path.is_file():
            missing_docs.append(page)
            docs[page] = ""
        else:
            docs[page] = path.read_text(encoding="utf-8", errors="replace")

    examples: dict[int, dict[str, Any]] = {}
    variants: list[dict[str, Any]] = []
    duplicate_variants: list[dict[str, Any]] = []
    variant_seen: dict[tuple[int | None, str], dict[str, Any]] = {}
    types: list[dict[str, Any]] = []
    knowledge_rows: list[dict[str, Any]] = []
    observed_groups: dict[str, list[int]] = {}
    question_occurrences: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    page_hits: dict[int, list[str]] = {}
    group_headers: dict[str, int] = {}
    current_group: str | None = None
    current_type: dict[str, Any] | None = None
    current_knowledge: dict[str, Any] | None = None
    last_example: int | None = None

    def note(page: int, marker: str) -> None:
        bucket = page_hits.setdefault(page, [])
        if marker not in bucket:
            bucket.append(marker)

    for page in range(low, high + 1):
        source_lines = [
            (line_number, fragment if index == 0 else f"## {fragment}")
            for line_number, line in enumerate(docs[page].splitlines(), start=1)
            for index, fragment in enumerate(INLINE_KNOWLEDGE_RE.split(line))
            if fragment
        ]
        for line_number, line in source_lines:
            stripped = line.strip()
            if not stripped:
                continue
            group_match = GROUP_RE.match(stripped)
            if group_match:
                current_group = group_match.group(1).upper()
                observed_groups.setdefault(current_group, [])
                group_headers.setdefault(current_group, page)
                current_type = None
                current_knowledge = None
                note(page, f"{current_group}组头")
                continue

            type_match = TYPE_RE.match(stripped)
            if type_match and current_group is None:
                current_type = {
                    "type": type_match.group(1),
                    "title": compact_label(type_match.group(2), f"类型{type_match.group(1)}"),
                    "example_numbers": [],
                    "pages": [page],
                }
                types.append(current_type)
                note(page, f"类型{current_type['type']}")
                continue

            knowledge_match = KNOWLEDGE_RE.match(stripped)
            if knowledge_match and current_group is None:
                number = int(knowledge_match.group(1))
                current_knowledge = {
                    "id": f"{section_id}-k{number}",
                    "label": compact_label(knowledge_match.group(2), f"知识点{number}"),
                    "pages": [page],
                    "examples": [],
                }
                knowledge_rows.append(current_knowledge)
                note(page, f"知识点{number}")
                continue

            example_match = EXAMPLE_RE.search(stripped)
            if example_match and current_group is None:
                number = int(example_match.group(1))
                last_example = number
                item = examples.setdefault(number, {"number": number, "label": f"例{number}", "pages": []})
                if page not in item["pages"]:
                    item["pages"].append(page)
                if current_type is not None and number not in current_type["example_numbers"]:
                    current_type["example_numbers"].append(number)
                if current_knowledge is not None:
                    ref = f"例{number}"
                    if ref not in current_knowledge["examples"]:
                        current_knowledge["examples"].append(ref)
                note(page, f"例{number}")
                continue

            variant_match = VARIANT_RE.search(stripped)
            if variant_match and current_group is None:
                suffix = variant_match.group(1)
                label = f"变式{suffix}" if suffix else "变式"
                current_variant = {
                    "label": label,
                    "parent_example": last_example,
                    "pages": [page],
                    "line": line_number,
                }
                normalized_variant = re.sub(r"\s+", "", stripped).replace("。", ".").rstrip(".")
                variant_key = (last_example, normalized_variant)
                previous_variant = variant_seen.get(variant_key)
                if previous_variant is None:
                    variant_seen[variant_key] = current_variant
                    variants.append(current_variant)
                else:
                    duplicate_variants.append(
                        {
                            "parent_example": last_example,
                            "kept": previous_variant,
                            "removed": current_variant,
                            "reason": "same_parent_and_normalized_question_line",
                        }
                    )
                note(page, label)
                continue

            if current_group:
                number_match = QNUM_RE.match(stripped)
                if number_match and not NOISE_RE.match(stripped) and len(stripped) > len(number_match.group(0)):
                    number = int(number_match.group(1))
                    question_occurrences[(current_group, number)].append(
                        {"doc": page, "line": line_number, "header": stripped}
                    )
                    if number not in observed_groups[current_group]:
                        observed_groups[current_group].append(number)
                    note(page, f"{current_group}{number}")

    expected_groups, inference_notes = infer_expected_groups(observed_groups)
    missing_numbers: list[dict[str, Any]] = []
    for group, bounds in expected_groups.items():
        observed = set(observed_groups.get(group) or [])
        for number in range(bounds[0], bounds[1] + 1):
            if number not in observed:
                missing_numbers.append(
                    {
                        "group": group,
                        "number": number,
                        "reason": "printed_number_missing_from_ocr",
                        "status": "needs_source_anchor",
                    }
                )

    broken_variant_parents = [row for row in variants if row.get("parent_example") is None]
    duplicate_numbers = []
    for (group, number), occurrences in sorted(question_occurrences.items()):
        if len(occurrences) < 2:
            continue
        normalized_headers = {
            re.sub(r"\s+", "", re.sub(r"^#+", "", row["header"]))
            for row in occurrences
        }
        duplicate_numbers.append(
            {
                "group": group,
                "number": number,
                "occurrences": occurrences,
                "same_normalized_header": len(normalized_headers) == 1,
            }
        )
    knowledge = merge_knowledge(knowledge_rows)
    example_rows = [examples[number] for number in sorted(examples)]
    unresolved = []
    unresolved.extend(f"missing_ocr_doc:{number}" for number in missing_docs)
    unresolved.extend(f"missing_question:{row['group']}{row['number']}" for row in missing_numbers)
    unresolved.extend(f"variant_without_parent:doc_{row['pages'][0]}:line_{row['line']}" for row in broken_variant_parents)
    unresolved.extend(
        f"conflicting_duplicate_question_number:{row['group']}{row['number']}"
        for row in duplicate_numbers
        if not row["same_normalized_header"]
    )
    status = "passed" if not unresolved and expected_groups else "blocked"
    return {
        "section": section_id,
        "label": section.get("label"),
        "status": status,
        "pdf_pages": section.get("pdf_pages"),
        "ocr_docs": docs_range,
        "knowledge_points": knowledge,
        "examples": example_rows,
        "variants": variants,
        "duplicate_learning_items_removed": duplicate_variants,
        "types": types,
        "observed_question_numbers": {group: sorted(set(values)) for group, values in observed_groups.items()},
        "question_groups": expected_groups,
        "question_group_inference": inference_notes,
        "question_count": sum(end - start + 1 for start, end in expected_groups.values()),
        "missing_numbers": missing_numbers,
        "duplicate_question_numbers": duplicate_numbers,
        "group_header_docs": group_headers,
        "page_hits": {str(page): markers for page, markers in sorted(page_hits.items())},
        "image_ref_count": sum(len(IMAGE_RE.findall(text)) for text in docs.values()),
        "unresolved": unresolved,
    }


def scan_chapter(chapter: int) -> dict[str, Any]:
    config = CONFIG[chapter]
    manifest = load_json(config["manifest"])
    sections = chapter_sections(chapter, manifest)
    rows = [scan_section(section, config["ocr"]) for section in sections]
    return {
        "schema_version": 1,
        "artifact": "TEXTBOOK_STRUCTURE_EXTRACTION",
        "chapter": chapter,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(config["manifest"]),
        "ocr_root": str(config["ocr"]),
        "status": "passed" if rows and all(row["status"] == "passed" for row in rows) else "blocked",
        "sections": rows,
        "summary": {
            "section_count": len(rows),
            "knowledge_points": sum(len(row.get("knowledge_points") or []) for row in rows),
            "worked_examples": sum(len(row.get("examples") or []) for row in rows),
            "direct_variants": sum(len(row.get("variants") or []) for row in rows),
            "abc_exercises": sum(int(row.get("question_count") or 0) for row in rows),
            "missing_printed_numbers": sum(len(row.get("missing_numbers") or []) for row in rows),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", choices=["2", "3", "4", "5", "all"], default="all")
    args = parser.parse_args()
    chapters = list(CONFIG) if args.chapter == "all" else [int(args.chapter)]
    results = []
    for chapter in chapters:
        payload = scan_chapter(chapter)
        output = ROOT / "reports" / "builds" / f"ch{chapter}-structure-current.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results.append({"chapter": chapter, "status": payload["status"], **payload["summary"], "output": str(output)})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(row["status"] == "passed" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
