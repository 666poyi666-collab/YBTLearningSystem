#!/usr/bin/env python3
"""Build grader-only answer evidence from all 38 source answer PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/answer_evidence"
REPORT = ROOT / "reports/deep_simulation/answer-evidence.json"
GROUP_RE = re.compile(r"([ABC])\s*组", re.I)
NUMBER_RE = re.compile(r"^\s*(\d{1,2})\s*([.．、:：])\s*(.*)$")
BARE_NUMBER_RE = re.compile(r"^\s*(\d{1,2})\s*$")
QUESTION_SOURCE_RE = re.compile(
    r"20\d{2}|期中|期末|月考|模拟|联考|高考|开学|统考|一模|二模|三模|卷[）)]|考试[）)]"
)
ANSWER_START_RE = re.compile(r"^(?:答案|解析|解法\s*\d*|解|证明|[A-D](?:\s*$|\s*[.．、]))", re.I)
VISUAL_REVIEW_MARKER = "[SOURCE_PAGE_VISUAL_REVIEW_REQUIRED]"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", value).lower()


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def reusable_page_ocr(path: Path, source_pdf_sha256: str) -> list[dict[str, Any]] | None:
    """Reuse OCR only when the source PDF and every rendered page still match."""
    if not path.is_file():
        return None
    cached = load(path)
    if cached.get("source_pdf", {}).get("sha256") != source_pdf_sha256:
        return None
    pages = cached.get("pages")
    if not isinstance(pages, list) or not pages:
        return None
    required = {
        "pdf_page",
        "ocr_lines",
        "ocr_text_sha256",
        "page_image_sha256",
        "page_image_path",
    }
    for page in pages:
        if not isinstance(page, dict) or not required.issubset(page):
            return None
        image_path = ROOT / str(page["page_image_path"])
        if not image_path.is_file() or sha256_file(image_path) != page["page_image_sha256"]:
            return None
    return pages


def answer_pdfs(roots: list[Path]) -> list[Path]:
    return sorted(path for root in roots for path in root.rglob("*（习题册+答案册）.pdf"))


def match_pdf(chapter: int, label: str, paths: list[Path]) -> Path:
    title = re.sub(r"^第\d+节\s*", "", label)
    def source_title(path: Path) -> str:
        value = re.sub(r"（习题册\+答案册）$", "", path.stem)
        return re.sub(r"^第\d+节\s*", "", value)
    candidates = [
        path for path in paths
        if f"第{chapter}章" in str(path.parent.parent)
        and normalized(title) == normalized(source_title(path))
    ]
    if len(candidates) != 1:
        candidates = [path for path in paths if normalized(title) == normalized(source_title(path))]
    if len(candidates) != 1:
        raise ValueError(f"answer PDF resolution failed: chapter={chapter} label={label} candidates={candidates}")
    return candidates[0]


def ocr_rows(result: Any) -> list[dict[str, Any]]:
    rows = []
    for item in result or []:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        box, text, score = item[0], str(item[1]).strip(), item[2]
        if not text:
            continue
        try:
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            rows.append({
                "text": text,
                "confidence": round(float(score), 4),
                "bbox": [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)],
                "center_x": sum(xs) / len(xs),
                "center_y": sum(ys) / len(ys),
            })
        except (TypeError, ValueError, IndexError):
            continue
    return sorted(rows, key=lambda row: (row["center_y"], row["center_x"]))


def answer_like(value: str) -> bool:
    text = value.strip()
    if not text or len(text) > 240:
        return False
    if QUESTION_SOURCE_RE.search(text):
        return False
    return bool(
        ANSWER_START_RE.search(text)
        or re.search(r"[=<>±√]|\\|\d|无解|不存在|充分|必要|平行|垂直", text, re.I)
    )


def parse_numbered_row(value: str) -> tuple[int, str, str] | None:
    """Return number, remainder and marker kind for a numbered OCR row."""
    match = NUMBER_RE.match(value)
    if match:
        return int(match.group(1)), match.group(3).strip(), "punctuated"
    match = BARE_NUMBER_RE.match(value)
    if match:
        return int(match.group(1)), "", "bare"
    return None


def question_header_like(value: str) -> bool:
    return bool(QUESTION_SOURCE_RE.search(value))


def answer_header_strength(remainder: str, marker_kind: str) -> int:
    """Rank a repeated number as an answer header without solving the problem."""
    text = remainder.strip()
    if question_header_like(text):
        return -1
    if ANSWER_START_RE.search(text):
        return 4
    if answer_like(text):
        return 3
    if marker_kind == "punctuated":
        return 2
    return 1


def flattened_rows(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    group = "A"
    for page in pages:
        for local_index, row in enumerate(page["ocr_lines"]):
            group_match = GROUP_RE.search(row["text"])
            if group_match:
                group = group_match.group(1).upper()
            numbered = parse_numbered_row(row["text"])
            rows.append({
                **row,
                "pdf_page": page["pdf_page"],
                "page_image_sha256": page["page_image_sha256"],
                "page_image_path": page["page_image_path"],
                "ocr_text_sha256": page["ocr_text_sha256"],
                "local_index": local_index,
                "global_index": len(rows),
                "group": group,
                "numbered": numbered,
                "is_group_header": bool(group_match),
                "is_question_header": bool(numbered and question_header_like(numbered[1])),
            })
    return rows


def parse_candidates(
    pages: list[dict[str, Any]], expected_keys: set[tuple[str, int]]
) -> tuple[dict[tuple[str, int], dict[str, Any]], dict[tuple[str, int], dict[str, Any]]]:
    """Parse repeated numbered answer headers and locate source-page fallbacks."""
    rows = flattened_rows(pages)
    occurrences: dict[tuple[str, int], list[dict[str, Any]]] = {}
    all_occurrences_by_number: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        if not row["numbered"]:
            continue
        number, remainder, marker_kind = row["numbered"]
        key = (row["group"], number)
        occurrence = {
            **row,
            "remainder": remainder,
            "marker_kind": marker_kind,
            "strength": answer_header_strength(remainder, marker_kind),
        }
        all_occurrences_by_number.setdefault(number, []).append(occurrence)
        if key in expected_keys:
            occurrences.setdefault(key, []).append(occurrence)

    parsed: dict[tuple[str, int], dict[str, Any]] = {}
    anchors: dict[tuple[str, int], dict[str, Any]] = {}
    for key in expected_keys:
        values = occurrences.get(key, [])
        expected_number_is_unique = sum(number == key[1] for _, number in expected_keys) == 1
        if not values and expected_number_is_unique:
            # A few packet manifests retain a historical B/C boundary that
            # differs from the printed source heading. The section-wide number
            # is unique, so bind it while recording the actual source group.
            global_values = all_occurrences_by_number.get(key[1], [])
            global_question_headers = [row for row in global_values if row["is_question_header"]]
            if len(global_question_headers) == 1:
                values = global_values
        question_headers = [row for row in values if row["is_question_header"]]
        if question_headers:
            question_header = question_headers[0]
            anchors[key] = question_header
            next_question_index = next(
                (
                    row["global_index"]
                    for row in rows[question_header["global_index"] + 1 :]
                    if row["is_question_header"] or row["is_group_header"]
                ),
                len(rows),
            )
            candidates = [
                row
                for row in values
                if question_header["global_index"] < row["global_index"] < next_question_index
                and not row["is_question_header"]
            ]
        else:
            # Some scans lose the exam-source line. A later repeated number is
            # still usable when it has an explicit answer marker.
            if values:
                anchors[key] = values[0]
            candidates = [row for index, row in enumerate(values) if index > 0 and not row["is_question_header"]]
            next_question_index = len(rows)

        strong = [row for row in candidates if row["strength"] >= 2]
        if strong:
            chosen = sorted(strong, key=lambda row: (-row["strength"], row["global_index"]))[0]
        elif len(candidates) == 1 and candidates[0]["marker_kind"] == "bare":
            chosen = candidates[0]
        else:
            continue

        segment_end = next(
            (
                row["global_index"]
                for row in rows[chosen["global_index"] + 1 : next_question_index]
                if row["is_group_header"]
            ),
            next_question_index,
        )
        segment = [
            row["text"]
            for row in rows[chosen["global_index"] : segment_end]
            if not row["is_group_header"]
        ]
        answer_text = "\n".join(segment).strip()
        if not answer_text:
            continue
        review_required = chosen["strength"] < 3 or float(chosen["confidence"]) < 0.65
        parsed[key] = {
            "group": key[0],
            "source_group": chosen["group"],
            "number": key[1],
            "answer_text": answer_text,
            "answer_line": chosen["remainder"],
            "pdf_page": chosen["pdf_page"],
            "page_image_path": chosen["page_image_path"],
            "page_image_sha256": chosen["page_image_sha256"],
            "ocr_text_sha256": chosen["ocr_text_sha256"],
            "ocr_confidence": chosen["confidence"],
            "parse_status": (
                "parsed_repeated_numbered_answer"
                if chosen["strength"] >= 3
                else "parsed_repeated_blank_or_bare_header"
            ),
            "evidence_kind": "parsed_answer_text",
            "confidence": "medium" if review_required else "high",
            "review_required": review_required,
            "automatic_grading_allowed": not review_required,
        }
    return parsed, anchors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-root", type=Path, action="append", required=True)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--page-root", type=Path, default=ROOT / "tmp/answer-evidence-pages")
    parser.add_argument(
        "--reuse-page-ocr",
        action="store_true",
        help="Reuse cached OCR only when the source PDF and every page image SHA match.",
    )
    args = parser.parse_args()
    try:
        import pymupdf
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as error:
        raise SystemExit("pymupdf and rapidocr_onnxruntime are required") from error

    pdfs = answer_pdfs([path.resolve() for path in args.book_root])
    if len(pdfs) != 38:
        raise ValueError(f"expected 38 answer PDFs, found {len(pdfs)}")
    engine = RapidOCR()
    section_reports = []
    total_questions = 0
    parsed_questions = 0
    visual_fallback_questions = 0
    blocked_questions = 0
    review_required_questions = 0
    source_manifest = []

    for chapter in range(1, 6):
        manifest = load(ROOT / f"chapter{chapter}_manifest.json")
        for section in manifest.get("sections", []):
            section_id = str(section["id"])
            pdf = match_pdf(chapter, str(section["label"]), pdfs)
            pdf_hash = sha256_file(pdf)
            evidence_path = OUTPUT / f"{section_folder(section_id)}.json"
            page_dir = args.page_root / section_folder(section_id)
            page_dir.mkdir(parents=True, exist_ok=True)
            pages = reusable_page_ocr(evidence_path, pdf_hash) if args.reuse_page_ocr else None
            if pages is None:
                document = pymupdf.open(str(pdf))
                pages = []
                try:
                    for page_index in range(len(document)):
                        image_path = page_dir / f"page-{page_index + 1:03d}.jpg"
                        if image_path.is_file():
                            image_bytes = image_path.read_bytes()
                        else:
                            pixmap = document[page_index].get_pixmap(dpi=args.dpi, alpha=False)
                            image_bytes = pixmap.tobytes("jpg", jpg_quality=84)
                            image_path.write_bytes(image_bytes)
                        result, _ = engine(str(image_path))
                        rows = ocr_rows(result)
                        text = "\n".join(row["text"] for row in rows)
                        pages.append({
                            "pdf_page": page_index + 1,
                            "ocr_lines": [{key: row[key] for key in ("text", "confidence", "bbox")} for row in rows],
                            "ocr_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                            "page_image_sha256": hashlib.sha256(image_bytes).hexdigest(),
                            "page_image_path": f"tmp/answer-evidence-pages/{section_folder(section_id)}/{image_path.name}",
                        })
                finally:
                    document.close()
            student = load(ROOT / "data/packets" / section_folder(section_id) / "student_packet.json")
            expected_keys = {
                (str(question["group"]), int(question["number"]))
                for question in student.get("questions", [])
            }
            parsed, anchors = parse_candidates(pages, expected_keys)
            existing_sidecar_path = ROOT / "data/packets" / section_folder(section_id) / "answer_sidecar.json"
            answer_rows = []
            missing = []
            review_required = []
            section_parsed = 0
            section_visual_fallback = 0
            section_blocked = 0
            for question in student.get("questions", []):
                total_questions += 1
                key = (str(question["group"]), int(question["number"]))
                evidence = parsed.get(key)
                if evidence:
                    parsed_questions += 1
                    section_parsed += 1
                    if evidence["review_required"]:
                        review_required_questions += 1
                        review_required.append({
                            "qid": question["qid"],
                            "group": question["group"],
                            "number": question["number"],
                            "reason": "low_confidence_or_blank_answer_header",
                        })
                    answer_rows.append({
                        "qid": question["qid"],
                        "section": section_id,
                        "group": question["group"],
                        "number": question["number"],
                        "answer_text": evidence["answer_text"],
                        "answer_isolated": True,
                        "source": {
                            "file_name": pdf.name,
                            "source_pdf_sha256": pdf_hash,
                            "source_group": evidence["source_group"],
                            "pdf_page": evidence["pdf_page"],
                            "page_image_path": evidence["page_image_path"],
                            "page_image_sha256": evidence["page_image_sha256"],
                            "ocr_text_sha256": evidence["ocr_text_sha256"],
                        },
                        "answer_kind": "original_answer_book_ocr_with_source_page",
                        "answer_evidence": "E1",
                        "evidence_kind": evidence["evidence_kind"],
                        "confidence": evidence["confidence"],
                        "parse_status": evidence["parse_status"],
                        "review_required": evidence["review_required"],
                        "automatic_grading_allowed": evidence["automatic_grading_allowed"],
                        "answer_text_kind": "ocr_answer_text",
                        "grader_only": True,
                    })
                elif anchors.get(key):
                    anchor = anchors[key]
                    visual_fallback_questions += 1
                    review_required_questions += 1
                    section_visual_fallback += 1
                    review_required.append({
                        "qid": question["qid"],
                        "group": question["group"],
                        "number": question["number"],
                        "reason": "source_page_visual_review_required",
                    })
                    answer_rows.append({
                        "qid": question["qid"],
                        "section": section_id,
                        "group": question["group"],
                        "number": question["number"],
                        "answer_text": VISUAL_REVIEW_MARKER,
                        "answer_isolated": True,
                        "source": {
                            "file_name": pdf.name,
                            "source_pdf_sha256": pdf_hash,
                            "source_group": anchor["group"],
                            "pdf_page": anchor["pdf_page"],
                            "page_image_path": anchor["page_image_path"],
                            "page_image_sha256": anchor["page_image_sha256"],
                            "ocr_text_sha256": anchor["ocr_text_sha256"],
                        },
                        "answer_kind": "original_answer_book_source_page_visual",
                        "answer_evidence": "E1_VISUAL",
                        "evidence_kind": "source_page_visual",
                        "confidence": "source_bound_unparsed",
                        "parse_status": "source_page_visual_review_required",
                        "review_required": True,
                        "automatic_grading_allowed": False,
                        "answer_text_kind": "evidence_locator_not_answer",
                        "grader_only": True,
                    })
                else:
                    blocked_questions += 1
                    section_blocked += 1
                    missing.append({"qid": question["qid"], "group": question["group"], "number": question["number"]})
                    answer_rows.append({
                        "qid": question["qid"],
                        "section": section_id,
                        "group": question["group"],
                        "number": question["number"],
                        "answer_text": "",
                        "answer_isolated": True,
                        "source": {"file_name": pdf.name, "source_pdf_sha256": pdf_hash},
                        "answer_kind": "source_pdf_available_parse_pending",
                        "answer_evidence": "E0",
                        "evidence_kind": "blocked_no_stable_page_anchor",
                        "confidence": "none",
                        "parse_status": "not_parsed",
                        "review_required": True,
                        "automatic_grading_allowed": False,
                        "answer_text_kind": "missing",
                        "grader_only": True,
                    })
            sidecar = {
                "schema_version": "ybt-answer-sidecar-v3",
                "section": section_id,
                "consumer_guard": "GRADER_ONLY_NEVER_PASS_TO_STUDENT_OR_PERSONA",
                "source_pdf": {"file_name": pdf.name, "sha256": pdf_hash, "page_count": len(pages)},
                "answers": answer_rows,
                "parsed_answers": section_parsed,
                "visual_fallback_answers": section_visual_fallback,
                "evidenced_answers": section_parsed + section_visual_fallback,
                "blocked_answers": section_blocked,
                "review_required_answers": review_required,
                "missing_answers": missing,
                "status": "VERIFIED" if not missing else "PARTIAL",
            }
            save(existing_sidecar_path, sidecar)
            save(evidence_path, {
                "schema_version": "ybt-answer-source-pages-v2",
                "section": section_id,
                "source_pdf": sidecar["source_pdf"],
                "pages": pages,
                "parsed": list(parsed.values()),
                "source_page_anchors": [
                    {
                        "group": key[0],
                        "source_group": anchor["group"],
                        "number": key[1],
                        "pdf_page": anchor["pdf_page"],
                        "page_image_path": anchor["page_image_path"],
                        "page_image_sha256": anchor["page_image_sha256"],
                        "ocr_text_sha256": anchor["ocr_text_sha256"],
                    }
                    for key, anchor in sorted(anchors.items())
                ],
                "consumer_guard": sidecar["consumer_guard"],
            })
            source_manifest.append({"chapter": chapter, "section": section_id, "file_name": pdf.name, "sha256": pdf_hash, "pages": len(pages)})
            section_reports.append({
                "chapter": chapter,
                "section": section_id,
                "questions": len(answer_rows),
                "parsed": section_parsed,
                "visual_fallback": section_visual_fallback,
                "evidenced": section_parsed + section_visual_fallback,
                "review_required": len(review_required),
                "blocked": section_blocked,
                "missing": section_blocked,
                "status": sidecar["status"],
            })
            print(
                f"answer evidence: {len(section_reports)}/38 {section_id} "
                f"parsed={section_parsed} visual={section_visual_fallback} "
                f"blocked={section_blocked} total={len(answer_rows)}",
                flush=True,
            )

    report = {
        "schema_version": "ybt-all-answer-evidence-report-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_pdfs": len(source_manifest),
        "source_manifest": source_manifest,
        "questions": total_questions,
        "parsed_questions": parsed_questions,
        "visual_fallback_questions": visual_fallback_questions,
        "evidenced_questions": parsed_questions + visual_fallback_questions,
        "review_required_questions": review_required_questions,
        "blocked_questions": blocked_questions,
        "missing_questions": blocked_questions,
        "sections": section_reports,
        "status": "passed" if blocked_questions == 0 else "partial",
        "automatic_grading_status": (
            "passed"
            if review_required_questions == 0 and blocked_questions == 0
            else "requires_visual_review"
        ),
        "student_context_answer_leakage": False,
    }
    save(REPORT, report)
    print(json.dumps({
        key: report[key]
        for key in (
            "source_pdfs",
            "questions",
            "parsed_questions",
            "visual_fallback_questions",
            "review_required_questions",
            "blocked_questions",
            "status",
        )
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
