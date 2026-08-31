#!/usr/bin/env python3
"""Normalize source-verified ASR homophones in the two summation-bounding courses."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS = (
    ROOT / "data" / "course_transcripts" / "4.2.6.1 求和型放缩（上）.json",
    ROOT / "data" / "course_transcripts" / "4.2.6.1 求和型放缩（下）.json",
)
REPLACEMENTS = (
    ("复值放缩", "赋值放缩"),
    ("负值放缩", "赋值放缩"),
    ("复制放缩", "赋值放缩"),
    ("复值", "赋值"),
    ("放松", "放缩"),
    ("放错", "放缩"),
    ("防措", "放缩"),
    ("方错", "放缩"),
    ("放合", "放缩"),
    ("放坡", "放缩"),
    ("黄缩", "放缩"),
    ("数直型放缩", "数值型放缩"),
    ("竖直型放缩", "数值型放缩"),
    ("竖直性放缩", "数值型放缩"),
    ("通向性放缩", "通项型放缩"),
    ("求和性放缩", "求和型放缩"),
)


def normalize(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    updated = text
    for source, target in REPLACEMENTS:
        count = updated.count(source)
        if count:
            updated = updated.replace(source, target)
            counts[f"{source}->{target}"] = count
    return updated, counts


def merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + value


def update(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    original_full_text = str(payload.get("full_text") or "")
    full_text, full_counts = normalize(original_full_text)
    sentence_counts: dict[str, int] = {}
    sentences = payload.get("sentences")
    if isinstance(sentences, list):
        for sentence in sentences:
            if not isinstance(sentence, dict) or not isinstance(sentence.get("text"), str):
                continue
            sentence["text"], counts = normalize(sentence["text"])
            merge_counts(sentence_counts, counts)
    payload["full_text"] = full_text
    payload["term_normalization"] = {
        "schema_version": "ybt-course-term-normalization-v1",
        "status": "SOURCE_CONTEXT_REVIEWED",
        "normalized_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "original_full_text_sha256": hashlib.sha256(original_full_text.encode("utf-8")).hexdigest(),
        "normalized_full_text_sha256": hashlib.sha256(full_text.encode("utf-8")).hexdigest(),
        "full_text_replacements": full_counts,
        "sentence_replacements": sentence_counts,
        "timestamp_fields_preserved": True,
        "rule": "Only high-confidence homophones of 赋值/放缩/数值型/通项型 in the named mathematics courses are normalized.",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "file": path.relative_to(ROOT).as_posix(),
        "full_text_replacements": sum(full_counts.values()),
        "sentence_replacements": sum(sentence_counts.values()),
    }


def main() -> int:
    rows = [update(path) for path in TRANSCRIPTS]
    print(json.dumps({"status": "updated", "rows": rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
