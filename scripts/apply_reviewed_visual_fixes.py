#!/usr/bin/env python3
"""Merge independently reviewed visual rows into the shared semantic override layer."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ybt_learning.packet import _usable_vision_sidecar


TARGET = ROOT / "data/vision_semantic_overrides.json"
REPORT = ROOT / "reports/deep_simulation/visual-fix-application.json"
SOURCES = (
    ROOT / "reports/deep_simulation_reviews/visual-fixes-ch1.json",
    ROOT / "reports/deep_simulation_reviews/visual-fixes-ch23.json",
    ROOT / "reports/deep_simulation_reviews/visual-fixes-ch45.json",
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dropped_hashes() -> set[str]:
    payload = load(ROOT / "data/item_image_attachment_overrides.json")
    return {
        str(row.get("drop", {}).get("image_sha256") or "")
        for row in payload.get("overrides", [])
    }


def normalize_row(raw: dict[str, Any], source: Path) -> dict[str, Any]:
    row = dict(raw)
    image = Path(str(row.get("image") or ""))
    if not image.is_absolute():
        image = ROOT / image
    if not image.is_file():
        raise ValueError(f"visual image missing: {source} {image}")
    actual_hash = sha256_file(image)
    if actual_hash != row.get("image_sha256"):
        raise ValueError(f"visual image SHA mismatch: {source} {row.get('question_hint')}")
    row["image"] = image.relative_to(ROOT).as_posix()
    provenance = dict(row.get("source_provenance") or {})
    provenance["review_report"] = source.relative_to(ROOT).as_posix()
    provenance["review_report_sha256"] = sha256_file(source)
    provenance["original_image_sha256"] = actual_hash
    row["source_provenance"] = provenance
    if not _usable_vision_sidecar(row):
        raise ValueError(f"visual row is not release-grade: {source} {row.get('question_hint')}")
    return row


def merged_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    existing = load(TARGET) if TARGET.is_file() else {"results": []}
    dropped = dropped_hashes()
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in existing.get("results", []):
        key = (str(row.get("question_hint") or ""), str(row.get("image_sha256") or ""))
        if key[0] and key[1] and key[1] not in dropped:
            by_key[key] = row

    applied = 0
    skipped_dropped = 0
    source_rows = 0
    source_bindings = []
    for source in SOURCES:
        payload = load(source)
        rows = payload.get("results") or payload.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"review report has no result list: {source}")
        source_bindings.append({"path": source.relative_to(ROOT).as_posix(), "sha256": sha256_file(source)})
        for raw in rows:
            if not isinstance(raw, dict):
                raise ValueError(f"review row is not an object: {source}")
            source_rows += 1
            if str(raw.get("image_sha256") or "") in dropped:
                skipped_dropped += 1
                continue
            row = normalize_row(raw, source)
            key = (str(row["question_hint"]), str(row["image_sha256"]))
            by_key[key] = row
            applied += 1

    results = sorted(by_key.values(), key=lambda row: (str(row.get("section")), str(row.get("question_hint")), str(row.get("image_sha256"))))
    payload = {
        "schema_version": "ybt-visual-semantic-overrides-v2",
        "status": "source_page_reviewed",
        "consumer_guard": "Only source-page-reviewed, answer-free visible facts. Never solve or infer a correct option.",
        "results": results,
    }
    report = {
        "schema_version": "ybt-reviewed-visual-fix-application-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_bindings": source_bindings,
        "source_rows": source_rows,
        "applied_rows": applied,
        "skipped_dropped_attachments": skipped_dropped,
        "shared_rows": len(results),
        "status": "passed",
    }
    return payload, report


def validate_current() -> dict[str, Any]:
    payload = load(TARGET)
    dropped = dropped_hashes()
    errors = []
    seen: set[tuple[str, str]] = set()
    for row in payload.get("results", []):
        key = (str(row.get("question_hint") or ""), str(row.get("image_sha256") or ""))
        if key in seen:
            errors.append(f"duplicate:{key}")
        seen.add(key)
        if key[1] in dropped:
            errors.append(f"dropped_attachment_present:{key}")
        image = ROOT / str(row.get("image") or "")
        if not image.is_file() or sha256_file(image) != key[1]:
            errors.append(f"image_binding:{key}")
        if not _usable_vision_sidecar(row):
            errors.append(f"unusable:{key}")
    if errors:
        raise ValueError(f"visual override validation failed: {errors[:20]}")
    return {"status": "passed", "rows": len(seen), "dropped_attachments": len(dropped)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(validate_current(), ensure_ascii=False))
        return 0
    payload, report = merged_payload()
    save(TARGET, payload)
    save(REPORT, report)
    result = validate_current()
    result.update({"applied_rows": report["applied_rows"], "skipped_dropped_attachments": report["skipped_dropped_attachments"]})
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
