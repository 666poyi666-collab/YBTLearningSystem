#!/usr/bin/env python3
"""Build a page-level, fail-closed index for the user-provided math handouts.

The PDFs are scanned/vector-first documents.  The index therefore keeps the
original page image and OCR as separate evidence.  OCR is a search aid, not
an authoritative replacement for formulas or diagrams; every page remains
``needs_visual_review`` until a visual check is recorded.

Example:
    python scripts/build_handout_index.py \
      --upper "C:/baidunetdiskdownload/高二数学精讲精练（上）.pdf" \
      --lower "C:/baidunetdiskdownload/高二数学精讲精练（下）.pdf" \
      --out tmp/handout-index
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz


COURSE_KEY_RE = re.compile(r"(?<![\d.])([345]\.\d+(?:\.\d+){1,3})(?![\d.])")
PRINTED_PAGE_RE = re.compile(r"^\d{1,3}$")
WATERMARK_RE = re.compile(r"加密|联系微信|gaokao|资料")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value or "").lower()


def load_catalog(project_root: Path) -> list[dict[str, Any]]:
    path = project_root / "data" / "all_chapters_course_catalog.json"
    if not path.is_file():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    return [course for course in value.get("courses", []) if isinstance(course, dict)]


def ordered_ocr(result: Any) -> tuple[str, list[float]]:
    rows: list[tuple[float, float, str, float]] = []
    for item in result or []:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        box, text, score = item[0], item[1], item[2]
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            rows.append((min(ys), min(xs), text.strip(), float(score)))
        except (TypeError, ValueError, IndexError):
            continue
    rows.sort(key=lambda row: (round(row[0] / 12) * 12, row[1]))
    return "\n".join(row[2] for row in rows), [row[3] for row in rows]


def printed_page_candidate(result: Any, image_width: int, image_height: int) -> int | None:
    candidates: list[tuple[float, int]] = []
    for item in result or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        box, text = item[0], str(item[1]).strip()
        if not PRINTED_PAGE_RE.fullmatch(text) or len(text) > 3:
            continue
        try:
            x = sum(float(point[0]) for point in box) / len(box)
            y = min(float(point[1]) for point in box)
            number = int(text)
        except (TypeError, ValueError, IndexError):
            continue
        in_outer_margin = x < image_width * 0.22 or x > image_width * 0.78
        if 0 < number <= 999 and y < image_height * 0.22 and in_outer_margin:
            candidates.append((y, number))
    return sorted(candidates)[0][1] if candidates else None


def course_candidates(text: str, headings: list[str], catalog: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized_headings = normalize("\n".join(headings))
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    numeric_keys = set(COURSE_KEY_RE.findall(text))
    for course in catalog:
        key = str(course.get("course_key", ""))
        title = str(course.get("title", ""))
        number = str(course.get("course_id", ""))
        match_type = None
        if key in numeric_keys or number in numeric_keys:
            match_type = "course_number"
        elif title and normalize(title) in normalized_headings:
            match_type = "title_exact"
        if match_type and key not in seen:
            found.append({"course_key": key, "title": title, "match_type": match_type})
            seen.add(key)
    return found


def heading_candidates(text: str) -> list[str]:
    values = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean or WATERMARK_RE.search(clean):
            continue
        if any(token in clean for token in ("模块", "专题", "知识梳理", "考点", "例题", "变式", "类型题")):
            values.append(clean)
    return values[:12]


def render_page(page: fitz.Page, destination: Path, dpi: int) -> tuple[bytes, int, int]:
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    data = pixmap.tobytes("jpg", jpg_quality=84)
    destination.write_bytes(data)
    return data, pixmap.width, pixmap.height


def build_book(
    pdf_path: Path,
    book_key: str,
    pages_root: Path,
    ocr: Any,
    catalog: list[dict[str, Any]],
    dpi: int,
) -> dict[str, Any]:
    source_sha = sha256_file(pdf_path)
    document = fitz.open(str(pdf_path))
    pages: list[dict[str, Any]] = []
    book_pages_root = pages_root / book_key
    book_pages_root.mkdir(parents=True, exist_ok=True)
    try:
        for index in range(len(document)):
            pdf_page = index + 1
            image_path = book_pages_root / f"page-{pdf_page:04d}.jpg"
            if image_path.is_file():
                image_bytes = image_path.read_bytes()
                rendered = fitz.Pixmap(image_bytes)
                image_width = rendered.width
                image_height = rendered.height
            else:
                image_bytes, image_width, image_height = render_page(document[index], image_path, dpi)
            result, _ = ocr(str(image_path))
            text, scores = ordered_ocr(result)
            headings = heading_candidates(text)
            candidates = course_candidates(text, headings, catalog)
            toc_page = sum("考点" in heading for heading in headings) >= 3
            page_record = {
                "book": book_key,
                "pdf_page": pdf_page,
                "printed_page": printed_page_candidate(result, int(image_width), int(image_height)),
                "heading_candidates": headings,
                "page_role": "table_of_contents" if toc_page else "content",
                "course_candidates": candidates,
                "mapping_status": "toc_reference" if toc_page and candidates else "candidate" if candidates else "unmapped",
                "ocr_text": text,
                "ocr_text_sha256": sha256_bytes(text.encode("utf-8")),
                "ocr_provider": "rapidocr_onnxruntime",
                "ocr_confidence": round(statistics.mean(scores), 4) if scores else 0,
                "ocr_status": "passed" if text else "empty",
                "needs_visual_review": True,
                "visual_status": "NEEDS_VISION_REVIEW",
                "source_pdf_sha256": source_sha,
                "page_image_sha256": sha256_bytes(image_bytes),
                "page_image_path": f"pages/{book_key}/page-{pdf_page:04d}.jpg",
                "image_width": int(image_width),
                "image_height": int(image_height),
            }
            pages.append(page_record)
            if pdf_page == 1 or pdf_page % 25 == 0 or pdf_page == len(document):
                print(f"{book_key}: {pdf_page}/{len(document)}", flush=True)
    finally:
        document.close()
    return {
        "book": book_key,
        "file_name": pdf_path.name,
        "source_pdf_sha256": source_sha,
        "page_count": len(pages),
        "ocr_provider": "rapidocr_onnxruntime",
        "mapping_policy": "course candidates are search hints; exact page/course binding requires visual review",
        "pages": pages,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upper", type=Path, required=True)
    parser.add_argument("--lower", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--remap-only", action="store_true")
    args = parser.parse_args()
    for path in (args.upper, args.lower):
        if not path.is_file():
            raise SystemExit(f"missing PDF: {path}")
    project_root = Path(__file__).resolve().parents[1]
    catalog = load_catalog(project_root)
    if args.remap_only:
        target = args.out / "index.json"
        index = json.loads(target.read_text(encoding="utf-8"))
        for book in index.get("books", []):
            for page in book.get("pages", []):
                headings = heading_candidates(str(page.get("ocr_text", "")))
                candidates = course_candidates(str(page.get("ocr_text", "")), headings, catalog)
                toc_page = sum("考点" in heading for heading in headings) >= 3
                page["heading_candidates"] = headings
                page["page_role"] = "table_of_contents" if toc_page else "content"
                page["course_candidates"] = candidates
                page["mapping_status"] = "toc_reference" if toc_page and candidates else "candidate" if candidates else "unmapped"
        target.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "remapped", "index": str(target)}, ensure_ascii=False))
        return 0
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as error:
        raise SystemExit("rapidocr_onnxruntime is required for local indexing") from error
    ocr = RapidOCR()
    pages_root = args.out / "pages"
    args.out.mkdir(parents=True, exist_ok=True)
    books = [
        build_book(args.upper, "upper", pages_root, ocr, catalog, args.dpi),
        build_book(args.lower, "lower", pages_root, ocr, catalog, args.dpi),
    ]
    index = {
        "schema_version": "math-course-handout-index-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_boundary": "user_provided_download",
        "text_is_search_aid_only": True,
        "visual_review_required": True,
        "books": books,
    }
    (args.out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"books": [(book["book"], book["page_count"]) for book in books], "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
