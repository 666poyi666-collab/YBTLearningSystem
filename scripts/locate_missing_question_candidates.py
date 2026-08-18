#!/usr/bin/env python3
"""Locate OCR text intervals that contain questions with lost printed numbers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OCR_ROOTS = {
    2: ROOT / "data" / "ocr_live_current" / "second_chapter_109",
    3: ROOT / "data" / "ocr_live_current" / "third_chapter_180",
    4: ROOT / "data" / "ocr_live_current" / "chapter4_100",
    5: ROOT / "data" / "ocr_live_current" / "chapter5_95",
}
GROUP_RE = re.compile(r"^#{0,6}\s*([ABC])\s*组", re.I)
QNUM_RE = re.compile(r"^#{0,6}\s*(\d{1,3})\s*\\?\s*[.、．]\s*")
NOISE_RE = re.compile(r"^(?:答案|解析|解答|解[:：]|第\s*\d+\s*节|一\s*数|高中数学一本通|[ABCD][.．])")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def section_lines(ocr_root: Path, low: int, high: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current_group: str | None = None
    for doc in range(low, high + 1):
        path = ocr_root / f"doc_{doc}.md"
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            group_match = GROUP_RE.match(stripped)
            if group_match:
                current_group = group_match.group(1).upper()
            number = None
            number_match = QNUM_RE.match(stripped)
            if current_group and number_match and not NOISE_RE.match(stripped) and len(stripped) > len(number_match.group(0)):
                number = int(number_match.group(1))
            rows.append(
                {
                    "doc": doc,
                    "line": line_number,
                    "text": line,
                    "group": current_group,
                    "group_header": group_match.group(1).upper() if group_match else None,
                    "question_number": number,
                }
            )
    return rows


def locate_one(rows: list[dict[str, Any]], missing: dict[str, Any]) -> dict[str, Any]:
    number = int(missing["number"])
    numbered = [(index, row) for index, row in enumerate(rows) if row["question_number"] is not None]
    lower = [(index, row) for index, row in numbered if int(row["question_number"]) < number]
    upper = [(index, row) for index, row in numbered if int(row["question_number"]) > number]
    lower_index, lower_row = max(lower, key=lambda item: (int(item[1]["question_number"]), item[0])) if lower else (-1, None)
    upper_index, upper_row = min(upper, key=lambda item: (int(item[1]["question_number"]), item[0])) if upper else (len(rows), None)

    # Numbering restarts only once per section and increases through A/B/C.
    # Restrict the interval to nearest numeric neighbors in document order.
    if lower_row:
        same_lower = [item for item in numbered if item[0] < upper_index and int(item[1]["question_number"]) == int(lower_row["question_number"])]
        if same_lower:
            lower_index, lower_row = max(same_lower, key=lambda item: item[0])
    if upper_row:
        same_upper = [item for item in numbered if item[0] > lower_index and int(item[1]["question_number"]) == int(upper_row["question_number"])]
        if same_upper:
            upper_index, upper_row = min(same_upper, key=lambda item: item[0])

    interval = rows[lower_index + 1 : upper_index]
    nonempty = [row for row in interval if row["text"].strip()]
    headers = [row for row in interval if row["group_header"]]
    inferred_group = headers[-1]["group_header"] if headers else (
        nonempty[0]["group"] if nonempty else missing.get("group")
    )
    docs = sorted({row["doc"] for row in nonempty})
    preview = "\n".join(row["text"] for row in interval).strip()
    return {
        "number": number,
        "extractor_group": missing.get("group"),
        "position_inferred_group": inferred_group,
        "lower_neighbor": {
            "number": lower_row["question_number"],
            "group": lower_row["group"],
            "doc": lower_row["doc"],
            "line": lower_row["line"],
        } if lower_row else None,
        "upper_neighbor": {
            "number": upper_row["question_number"],
            "group": upper_row["group"],
            "doc": upper_row["doc"],
            "line": upper_row["line"],
        } if upper_row else None,
        "candidate_docs": docs,
        "candidate_text": preview,
        "status": "needs_manual_source_review",
    }


def main() -> int:
    output_rows: list[dict[str, Any]] = []
    for chapter, ocr_root in OCR_ROOTS.items():
        structure = load_json(ROOT / "reports" / "builds" / f"ch{chapter}-structure-current.json")
        for section in structure.get("sections") or []:
            missing_rows = section.get("missing_numbers") or []
            if not missing_rows:
                continue
            low, high = section["ocr_docs"]
            rows = section_lines(ocr_root, low, high)
            for missing in missing_rows:
                candidate = locate_one(rows, missing)
                output_rows.append(
                    {
                        "chapter": chapter,
                        "section": section["section"],
                        "label": section.get("label"),
                        **candidate,
                    }
                )
    payload = {
        "schema_version": 1,
        "artifact": "MISSING_PRINTED_QUESTION_CANDIDATES",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "needs_manual_source_review" if output_rows else "passed",
        "candidate_count": len(output_rows),
        "candidates": output_rows,
    }
    output = ROOT / "reports" / "builds" / "missing-question-candidates-current.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in output_rows:
        text = re.sub(r"\s+", " ", row["candidate_text"])[:180]
        print(
            f"{row['section']} #{row['number']} extractor={row['extractor_group']} "
            f"position={row['position_inferred_group']} docs={row['candidate_docs']} :: {text}"
        )
    print(f"saved {output} candidates={len(output_rows)}")
    return 1 if output_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
