#!/usr/bin/env python3
"""Build a fail-closed source and artifact coverage report for chapters 1-5."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "reports" / "all_chapters"
TRANSCRIPT_ROOT = ROOT / "data" / "course_transcripts"

CHAPTERS: dict[int, dict[str, Any]] = {
    1: {
        "book_directory": "第1章 空间向量与立体几何",
        "ocr": ROOT / "data" / "ocr_live_current" / "first_chapter_69",
        "pages": 69,
        "courses": ("3.1 空间向量与立体几何",),
    },
    2: {
        "book_directory": "第2章 直线和圆的方程",
        "ocr": ROOT / "data" / "ocr_live_current" / "second_chapter_109",
        "pages": 109,
        "courses": ("3.2 直线与圆的方程",),
    },
    3: {
        "book_directory": "第3章 圆锥曲线的方程",
        "ocr": ROOT / "data" / "ocr_live_current" / "third_chapter_180",
        "pages": 180,
        "courses": ("3.3 圆锥曲线的方程", "3.4 圆锥曲线方程的综合提升"),
    },
    4: {
        "pdf": ROOT / "data" / "ocr_sources" / "第4章 数列（无答案册）.pdf",
        "ocr": ROOT / "data" / "ocr_live_current" / "chapter4_100",
        "pages": 100,
        "courses": ("4.3 数列", "4.4 数列的综合提升"),
    },
    5: {
        "pdf": ROOT / "data" / "ocr_sources" / "第5章 一元函数的导数及其应用（无答案册）.pdf",
        "ocr": ROOT / "data" / "ocr_live_current" / "chapter5_95",
        "pages": 95,
        "courses": ("4.1 一元函数的导数及其应用", "4.2 一元函数的导数及其应用的综合提升"),
    },
}

IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
DOC_RE = re.compile(r"^doc_(\d+)\.md$")
POLLUTION_RE = re.compile(r"老人版|8\.5g|数学摄像头", re.I)
ANSWER_RE = re.compile(r"(?im)^\s*(?:答案|解析|解答)\s*[：:]")


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path) or "0" * 64))
    return digest.hexdigest()


def pdf_page_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:
        try:
            import subprocess

            result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True)
            match = re.search(r"(?m)^Pages:\s*(\d+)\s*$", result.stdout)
            return int(match.group(1)) if match else None
        except Exception:
            return None


def scan_pdf_source(config: dict[str, Any], book_root: Path | None) -> dict[str, Any]:
    expected = int(config["pages"])
    if config.get("pdf"):
        paths = [Path(config["pdf"])]
    elif book_root is not None:
        directory = book_root / str(config["book_directory"])
        paths = sorted(
            path for path in directory.glob("*.pdf")
            if "（方法册+习题册）" in path.name and "答案册" not in path.name
        ) if directory.is_dir() else []
    else:
        paths = []
    counts = [pdf_page_count(path) for path in paths]
    actual = sum(value for value in counts if value is not None)
    complete = bool(paths) and all(value is not None for value in counts) and actual == expected
    return {
        "status": "passed" if complete else "blocked",
        "path": str(paths[0]) if len(paths) == 1 else None,
        "paths": [str(path) for path in paths],
        "file_count": len(paths),
        "exists": bool(paths) and all(path.is_file() for path in paths),
        "expected_pages": expected,
        "actual_pages": actual,
        "sha256": sha256_file(paths[0]) if len(paths) == 1 else (aggregate_hash(paths) if paths else None),
        "source_mode": "single_chapter_pdf" if len(paths) == 1 else "section_pdfs",
    }


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def range_count(groups: Any) -> int | None:
    if not isinstance(groups, dict) or not groups:
        return None
    total = 0
    for value in groups.values():
        if not isinstance(value, list) or len(value) != 2:
            return None
        start, end = value
        if not isinstance(start, int) or not isinstance(end, int) or end < start:
            return None
        total += end - start + 1
    return total


def scan_ocr(directory: Path, expected_pages: int) -> dict[str, Any]:
    numbered: dict[int, Path] = {}
    if directory.is_dir():
        for path in directory.glob("doc_*.md"):
            match = DOC_RE.match(path.name)
            if match:
                numbered[int(match.group(1))] = path
    expected = set(range(expected_pages))
    actual = set(numbered)
    empty = sorted(number for number, path in numbered.items() if path.stat().st_size == 0)
    decode_errors: list[int] = []
    broken_images: list[dict[str, Any]] = []
    pollution: list[int] = []
    for number, path in sorted(numbered.items()):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            decode_errors.append(number)
            text = path.read_text(encoding="utf-8", errors="replace")
        if POLLUTION_RE.search(text):
            pollution.append(number)
        for match in IMAGE_RE.finditer(text):
            raw = next(value for value in match.groups() if value)
            if re.match(r"^(?:https?:|data:)", raw, re.I):
                continue
            resolved = (path.parent / raw).resolve()
            if not resolved.is_file():
                broken_images.append({"doc": number, "ref": raw, "resolved": str(resolved)})
    ordered = [numbered[number] for number in sorted(numbered)]
    missing = sorted(expected - actual)
    extras = sorted(actual - expected)
    status = "passed" if not (missing or extras or empty or decode_errors or broken_images or pollution) else "blocked"
    return {
        "status": status,
        "directory": str(directory),
        "expected_pages": expected_pages,
        "document_count": len(numbered),
        "missing_docs": missing,
        "extra_docs": extras,
        "empty_docs": empty,
        "decode_error_docs": decode_errors,
        "broken_image_refs": broken_images,
        "pollution_docs": pollution,
        "aggregate_sha256": aggregate_hash(ordered) if ordered else None,
    }


def manifest_course_keys(manifest: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for section in manifest.get("sections", []):
        keys.update(str(value) for value in section.get("required_course_keys", []))
        keys.update(str(value) for value in section.get("support_course_keys", []))
        for cycle in section.get("learning_cycles", []):
            for field in ("course_keys", "prerequisite_course_keys", "optional_course_keys"):
                keys.update(str(value) for value in cycle.get(field, []))
    return keys


def scan_frozen_courses(manifest: dict[str, Any]) -> dict[str, Any]:
    catalog_path = ROOT / "data" / "all_chapters_course_catalog.json"
    catalog_payload = load_json(catalog_path)
    catalog = {str(row.get("course_key")): row for row in catalog_payload.get("courses", [])}
    required = manifest_course_keys(manifest)
    missing = sorted(required - set(catalog))
    invalid: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    for key in sorted(required):
        course = catalog.get(key, {})
        transcript = ROOT / str(course.get("transcript_file") or "")
        value = load_json(transcript)
        full_text = str(value.get("full_text") or "")
        recorded_video_sha = str(value.get("source_video_sha256") or "")
        if not transcript.is_file() or len(full_text) < 100:
            invalid.append({"course_key": key, "reason": "transcript_missing_or_short"})
        elif recorded_video_sha != str(course.get("video_sha256") or ""):
            invalid.append({"course_key": key, "reason": "frozen_video_hash_binding_mismatch"})
        rows.append({
            "course_key": key,
            "course_id": course.get("course_id"),
            "title": course.get("title"),
            "video_file": course.get("video_file"),
            "recorded_video_sha256": course.get("video_sha256"),
            "transcript": str(transcript),
            "transcript_present": transcript.is_file(),
            "transcript_chars": len(full_text),
            "sentence_count": len(value.get("sentences") or []),
            "source_mode": "frozen_video_hash_plus_repository_transcript",
        })
    blockers = [
        *(["frozen_course_keys_missing"] if missing else []),
        *(["frozen_transcripts_invalid"] if invalid else []),
    ]
    return {
        "status": "passed" if not blockers else "blocked",
        "source_mode": "frozen_catalog",
        "course_directories": [],
        "missing_directories": [],
        "video_count": len(rows),
        "transcript_count": sum(row["transcript_present"] for row in rows),
        "missing_course_keys": missing,
        "invalid_transcripts": invalid,
        "video_hash_mismatches": [],
        "pollution_transcripts": [],
        "blockers": blockers,
        "rows": rows,
    }


def scan_courses(course_dirs: tuple[str, ...], validate_hashes: bool, course_root: Path | None, manifest: dict[str, Any]) -> dict[str, Any]:
    if course_root is None:
        return scan_frozen_courses(manifest)
    videos: list[Path] = []
    missing_dirs: list[str] = []
    for dirname in course_dirs:
        directory = course_root / dirname
        if not directory.is_dir():
            missing_dirs.append(str(directory))
            continue
        videos.extend(sorted(directory.glob("*.mp4"), key=lambda path: path.name))

    rows: list[dict[str, Any]] = []
    missing_transcripts: list[str] = []
    invalid_transcripts: list[dict[str, str]] = []
    hash_mismatches: list[str] = []
    pollution_transcripts: list[str] = []
    for video in videos:
        transcript_path = TRANSCRIPT_ROOT / f"{video.stem}.json"
        transcript = load_json(transcript_path)
        full_text = str(transcript.get("full_text") or "")
        sentences = transcript.get("sentences") or []
        if not transcript_path.is_file():
            missing_transcripts.append(video.name)
        elif len(full_text) < 100 or not isinstance(sentences, list) or not sentences:
            invalid_transcripts.append({"video": video.name, "reason": "empty_or_too_short"})
        if POLLUTION_RE.search(full_text):
            pollution_transcripts.append(video.name)
        actual_hash = sha256_file(video) if validate_hashes else None
        recorded_hash = transcript.get("source_video_sha256")
        if validate_hashes and actual_hash != recorded_hash:
            hash_mismatches.append(video.name)
        rows.append(
            {
                "video": str(video),
                "video_size": video.stat().st_size,
                "video_sha256": actual_hash,
                "transcript": str(transcript_path),
                "transcript_present": transcript_path.is_file(),
                "transcript_chars": len(full_text),
                "sentence_count": len(sentences) if isinstance(sentences, list) else 0,
                "recorded_video_sha256": recorded_hash,
                "hash_validated": validate_hashes,
                "hash_match": actual_hash == recorded_hash if validate_hashes else None,
            }
        )
    blockers = [
        *(["course_directories_missing"] if missing_dirs else []),
        *(["transcripts_missing"] if missing_transcripts else []),
        *(["transcripts_invalid"] if invalid_transcripts else []),
        *(["video_hash_mismatch"] if hash_mismatches else []),
        *(["pollution_detected"] if pollution_transcripts else []),
        *(["video_hashes_not_validated"] if videos and not validate_hashes else []),
    ]
    return {
        "status": "passed" if not blockers else ("unknown" if blockers == ["video_hashes_not_validated"] else "blocked"),
        "course_directories": list(course_dirs),
        "missing_directories": missing_dirs,
        "video_count": len(videos),
        "transcript_count": sum(row["transcript_present"] for row in rows),
        "missing_transcripts": missing_transcripts,
        "invalid_transcripts": invalid_transcripts,
        "video_hash_mismatches": hash_mismatches,
        "pollution_transcripts": pollution_transcripts,
        "blockers": blockers,
        "rows": rows,
    }


def scan_packet(section: dict[str, Any]) -> dict[str, Any]:
    section_id = str(section.get("id") or "")
    directory = ROOT / "data" / "packets" / section_folder(section_id)
    required = (
        "learning_packet.json",
        "student_learning_items.json",
        "student_packet.json",
        "learning_path_without_questions.md",
        "learning_path_without_questions.html",
    )
    missing = [name for name in required if not (directory / name).is_file()]
    learning = load_json(directory / "learning_packet.json")
    student = load_json(directory / "student_packet.json")
    answer_leaks: list[str] = []
    if student:
        for question in student.get("questions") or []:
            if ANSWER_RE.search(str(question.get("question_text") or "")):
                answer_leaks.append(str(question.get("qid") or "unknown"))
    packet_counts = learning.get("counts") if isinstance(learning.get("counts"), dict) else None
    status = "passed" if not missing and learning.get("status") == "VERIFIED" and not answer_leaks else "blocked"
    return {
        "status": status,
        "directory": str(directory),
        "missing_files": missing,
        "learning_packet_status": learning.get("status"),
        "counts": packet_counts,
        "student_answer_leaks": answer_leaks,
    }


def simulation_status(section_id: str) -> dict[str, Any]:
    candidates = [
        ROOT / "reports" / "all_section_simulations" / f"{section_id}-route-contract-simulation.json",
        ROOT / "reports" / "all_section_simulations" / f"{section_folder(section_id)}-route-contract-simulation.json",
        ROOT / "reports" / "zero_base_cycles" / f"{section_id}-current-agent-simulation.json",
        ROOT / "reports" / "zero_base_cycles" / f"{section_folder(section_id)}-current-agent-simulation.json",
    ]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        return {"status": "not_run", "path": None, "generation": None, "source_revision_match": None}
    payload = load_json(path)
    current = payload.get("source_revision_match") is True
    return {
        "status": "passed" if current else "blocked",
        "path": str(path),
        "generation": payload.get("generation"),
        "source_revision_match": payload.get("source_revision_match"),
    }


def scan_chapter(
    number: int,
    config: dict[str, Any],
    validate_hashes: bool,
    book_root: Path | None,
    course_root: Path | None,
) -> dict[str, Any]:
    manifest_path = ROOT / f"chapter{number}_manifest.json"
    manifest = load_json(manifest_path)
    pdf_record = scan_pdf_source(config, book_root)
    ocr = scan_ocr(Path(config["ocr"]), config["pages"])
    courses = scan_courses(config["courses"], validate_hashes, course_root, manifest)
    sections: list[dict[str, Any]] = []
    for section in manifest.get("sections") or []:
        section_id = str(section.get("id") or "")
        ocr_docs = section.get("ocr_docs")
        section_ocr_ready = (
            isinstance(ocr_docs, list)
            and len(ocr_docs) == 2
            and all(isinstance(value, int) for value in ocr_docs)
            and ocr_docs[0] <= ocr_docs[1]
            and not set(range(ocr_docs[0], ocr_docs[1] + 1)).intersection(ocr["missing_docs"])
        )
        expected_questions = range_count(section.get("question_groups"))
        verified_questions = section.get("verified_question_count")
        question_manifest_status = "passed" if expected_questions and verified_questions == expected_questions else "blocked"
        packet = scan_packet(section)
        simulation = simulation_status(section_id)
        sections.append(
            {
                "id": section_id,
                "label": section.get("label"),
                "pdf_pages": section.get("pdf_pages"),
                "ocr_docs": ocr_docs,
                "ocr_section_status": "passed" if section_ocr_ready else "blocked",
                "question_manifest_status": question_manifest_status,
                "expected_question_count": expected_questions,
                "verified_question_count": verified_questions,
                "learning_item_counts": section.get("learning_item_counts"),
                "packet": packet,
                "simulation": simulation,
            }
        )
    manifest_pollution = POLLUTION_RE.findall(manifest_path.read_text(encoding="utf-8-sig")) if manifest_path.is_file() else []
    section_ids = [row["id"] for row in sections]
    chapter_status = "passed" if (
        pdf_record["status"] == "passed"
        and ocr["status"] == "passed"
        and courses["status"] == "passed"
        and sections
        and all(row["ocr_section_status"] == "passed" for row in sections)
        and all(row["question_manifest_status"] == "passed" for row in sections)
        and all(row["packet"]["status"] == "passed" for row in sections)
        and all(row["simulation"]["status"] == "passed" for row in sections)
        and not manifest_pollution
    ) else "blocked"
    return {
        "chapter": number,
        "status": chapter_status,
        "manifest": str(manifest_path),
        "manifest_schema": manifest.get("schema_version"),
        "manifest_pollution_hits": manifest_pollution,
        "section_count": len(sections),
        "section_ids": section_ids,
        "pdf": pdf_record,
        "ocr": ocr,
        "courses": courses,
        "sections": sections,
    }


def markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# 一本通第1-5章当前覆盖审计",
        "",
        f"生成时间：`{payload['generated_at']}`",
        f"整体状态：`{payload['overall_status']}`",
        "",
        "## 章节总览",
        "",
        "| 章 | 状态 | PDF | OCR | 视频/转写 | 小节 | 题包通过 | 当前模拟通过 |",
        "|---:|---|---|---|---|---:|---:|---:|",
    ]
    for chapter in payload["chapters"]:
        sections = chapter["sections"]
        lines.append(
            f"| {chapter['chapter']} | {chapter['status']} | {chapter['pdf']['actual_pages']}/{chapter['pdf']['expected_pages']} | "
            f"{chapter['ocr']['document_count']}/{chapter['ocr']['expected_pages']} | "
            f"{chapter['courses']['video_count']}/{chapter['courses']['transcript_count']} | "
            f"{chapter['section_count']} | {sum(row['packet']['status'] == 'passed' for row in sections)}/{len(sections)} | "
            f"{sum(row['simulation']['status'] == 'passed' for row in sections)}/{len(sections)} |"
        )
    lines.extend(
        [
            "",
            "## 小节矩阵",
            "",
            "| 小节 | OCR | 题号清单 | 学习包/路径 | 当前代模拟 | 教材习题数 | 学习题项数 |",
            "|---|---|---|---|---|---:|---:|",
        ]
    )
    for chapter in payload["chapters"]:
        for section in chapter["sections"]:
            counts = section.get("learning_item_counts") or {}
            total = counts.get("total") or counts.get("total_numbered_learning_items") or "?"
            lines.append(
                f"| {section['id']} {section.get('label') or ''} | {section['ocr_section_status']} | "
                f"{section['question_manifest_status']} | {section['packet']['status']} | "
                f"{section['simulation']['status']} | {section.get('verified_question_count') or '?'} | {total} |"
            )
    lines.extend(["", "## 当前硬缺口", ""])
    for blocker in payload["blockers"]:
        lines.append(f"- {blocker}")
    if not payload["blockers"]:
        lines.append("- 无")
    return "\n".join(lines) + "\n"


def build_report(validate_hashes: bool, book_root: Path | None = None, course_root: Path | None = None) -> dict[str, Any]:
    chapters = [scan_chapter(number, config, validate_hashes, book_root, course_root) for number, config in CHAPTERS.items()]
    blockers: list[str] = []
    for chapter in chapters:
        number = chapter["chapter"]
        if chapter["pdf"]["status"] != "passed":
            blockers.append(f"chapter{number}:pdf_incomplete")
        if chapter["ocr"]["status"] != "passed":
            blockers.append(f"chapter{number}:ocr_incomplete")
        if chapter["courses"]["status"] != "passed":
            blockers.extend(f"chapter{number}:courses:{item}" for item in chapter["courses"]["blockers"])
        for section in chapter["sections"]:
            if section["question_manifest_status"] != "passed":
                blockers.append(f"{section['id']}:question_manifest_incomplete")
            if section["packet"]["status"] != "passed":
                blockers.append(f"{section['id']}:learning_packet_or_route_incomplete")
            if section["simulation"]["status"] != "passed":
                blockers.append(f"{section['id']}:current_simulation_{section['simulation']['status']}")
    return {
        "schema_version": 1,
        "artifact": "ALL_CHAPTER_SOURCE_AND_ROUTE_COVERAGE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "passed" if not blockers else "blocked",
        "video_hashes_validated": validate_hashes,
        "chapter_count": len(chapters),
        "section_count": sum(chapter["section_count"] for chapter in chapters),
        "chapters": chapters,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-video-hashes", action="store_true")
    parser.add_argument("--book-root", type=Path, default=Path(os.environ["YBT_BOOK_ROOT"]) if os.environ.get("YBT_BOOK_ROOT") else None)
    parser.add_argument("--course-root", type=Path, default=Path(os.environ["YBT_COURSE_ROOT"]) if os.environ.get("YBT_COURSE_ROOT") else None)
    parser.add_argument("--json", type=Path, default=REPORT_ROOT / "source-coverage-current.json")
    parser.add_argument("--markdown", type=Path, default=REPORT_ROOT / "source-coverage-current.md")
    args = parser.parse_args()
    payload = build_report(args.validate_video_hashes, args.book_root, args.course_root)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown_report(payload), encoding="utf-8-sig")
    print(json.dumps({
        "status": payload["overall_status"],
        "chapters": payload["chapter_count"],
        "sections": payload["section_count"],
        "blockers": len(payload["blockers"]),
        "json": str(args.json),
        "markdown": str(args.markdown),
    }, ensure_ascii=False))
    return 0 if payload["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
