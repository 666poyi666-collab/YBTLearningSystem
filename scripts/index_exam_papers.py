#!/usr/bin/env python3
"""Index user-provided exam paper files without treating answer pages as stems."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_role(name: str) -> str:
    compact = re.sub(r"\s+", "", name)
    has_answer = "答案" in compact or "解析" in compact
    has_original = "原卷" in compact or "试卷" in compact or "月考" in compact or "期中" in compact or "期末" in compact
    if has_answer and not ("原卷版" in compact or "含答案" in compact):
        return "answer_only"
    return "question_paper" if has_original else "unclassified"


def pdf_metadata(path: Path) -> dict[str, Any]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        text_pages = sum(bool((page.extract_text() or "").strip()) for page in reader.pages)
        return {"page_count": len(reader.pages), "text_layer_pages": text_pages}
    except Exception as error:
        return {"page_count": None, "text_layer_pages": None, "metadata_error": type(error).__name__}


def docx_metadata(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            return {
                "has_document_xml": "word/document.xml" in names,
                "embedded_media_count": sum(name.startswith("word/media/") for name in names),
            }
    except (OSError, zipfile.BadZipFile) as error:
        return {"metadata_error": type(error).__name__}


def image_metadata(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return {"width": image.width, "height": image.height, "image_format": image.format}
    except Exception as error:
        return {"metadata_error": type(error).__name__}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/exam_papers/source_inventory.json"))
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not root.is_dir():
        raise SystemExit(f"source root is missing: {root}")

    rows = []
    for path in sorted((item for item in root.rglob("*") if item.is_file() and item.suffix.lower() in SUPPORTED), key=lambda item: item.as_posix()):
        source_hash = sha256_file(path)
        metadata = pdf_metadata(path) if path.suffix.lower() == ".pdf" else docx_metadata(path) if path.suffix.lower() == ".docx" else image_metadata(path)
        rows.append({
            "source_id": f"exam-{source_hash[:16]}",
            "relative_path": path.relative_to(root).as_posix(),
            "file_name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "sha256": source_hash,
            "source_role": source_role(path.name),
            "question_authority": source_role(path.name) == "question_paper",
            **metadata,
        })

    payload = {
        "schema_version": "math-exam-source-inventory-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root_label": root.name,
        "source_count": len(rows),
        "question_paper_count": sum(row["source_role"] == "question_paper" for row in rows),
        "answer_only_count": sum(row["source_role"] == "answer_only" for row in rows),
        "sources": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("source_count", "question_paper_count", "answer_only_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
