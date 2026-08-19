#!/usr/bin/env python3
"""Build a hash-bound, answer-free audit package for ChatGPT."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from chapter_learning_progress import chapter_facts, load_json, sha256_file


def _section_folder(section: str) -> str:
    return section.replace("+", "_")


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _course_rows(project_root: Path, catalog: dict[str, dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in keys:
        course = catalog[key]
        video_stem = Path(str(course.get("video_file") or "")).stem
        transcript_path = project_root / "data" / "course_transcripts" / f"{video_stem}.json"
        transcript: dict[str, Any] = {}
        if transcript_path.is_file():
            transcript = load_json(transcript_path)
        full_text = str(transcript.get("full_text") or "").strip()
        rows.append({
            "course_key": key,
            "course_number": video_stem.split(" ", 1)[0],
            "title": str(course.get("title") or key),
            "transcript_path": _relative(transcript_path, project_root),
            "transcript_exists": transcript_path.is_file(),
            "transcript_nonempty": bool(full_text),
            "transcript_chars": len(full_text),
            "transcript_sha256": sha256_file(transcript_path) if transcript_path.is_file() else None,
        })
    return rows


def build_audit(project_root: Path) -> dict[str, Any]:
    catalog_document = load_json(project_root / "data" / "all_chapters_course_catalog.json")
    catalog = {str(row["course_key"]): row for row in catalog_document.get("courses", [])}
    transcript_paths = list((project_root / "data" / "course_transcripts").glob("*.json"))
    sections: list[dict[str, Any]] = []
    chapter_rows: list[dict[str, Any]] = []

    for chapter in (1, 2):
        manifest_path = project_root / f"chapter{chapter}_manifest.json"
        manifest = load_json(manifest_path)
        facts = chapter_facts(project_root, chapter)
        progress_path = project_root / "data" / "learner_progress" / f"chapter{chapter}.json"
        progress = load_json(progress_path)
        progress_by_section = {str(row["section"]): row for row in progress.get("sections", [])}
        manifest_by_section = {str(row["id"]): row for row in manifest.get("sections", [])}

        for section_id in facts["manifest_sections"]:
            manifest_section = manifest_by_section[section_id]
            delivery = facts["section_deliveries"][section_id]
            packet_root = project_root / "data" / "packets" / _section_folder(section_id)
            packet_path = packet_root / "learning_packet.json"
            student_path = packet_root / "student_learning_items.json"
            student_packet_path = packet_root / "student_packet.json"
            packet_manifest_path = packet_root / "manifest.json"
            packet = load_json(packet_path)
            student = load_json(student_path)
            student_packet = load_json(student_packet_path)
            delivery_items = sorted(delivery.get("items", []), key=lambda row: int(row.get("ordinal") or 0))

            course_keys: list[str] = []
            for item in delivery_items:
                for key in item.get("course_refs", []):
                    value = str(key)
                    if value not in course_keys:
                        course_keys.append(value)
            courses = _course_rows(project_root, catalog, course_keys)

            counts = {
                "worked_examples": len(packet.get("worked_examples", [])),
                "direct_variants": len(packet.get("direct_variants", [])),
                "abc_exercises": len(packet.get("exercise_questions", [])),
            }
            counts["total"] = sum(counts.values())
            student_counts = {
                "worked_examples": len(student.get("worked_examples", [])),
                "direct_variants": len(student.get("direct_variants", [])),
                "abc_exercises": len(student_packet.get("questions", [])),
            }
            student_counts["total"] = sum(student_counts.values())
            question_rows = [
                *student.get("worked_examples", []),
                *student.get("direct_variants", []),
                *student_packet.get("questions", []),
            ]
            progress_section = progress_by_section[section_id]
            missing: list[str] = []
            for path in (packet_manifest_path, packet_path, student_path, student_packet_path):
                if not path.is_file():
                    missing.append(_relative(path, project_root))
            if counts["total"] != len(delivery_items) or student_counts["total"] != len(delivery_items):
                missing.append("canonical_item_count_mismatch")
            if any(not str(row.get("question_text") or "").strip() for row in question_rows):
                missing.append("empty_student_question_text")
            missing.extend(row["transcript_path"] for row in courses if not row["transcript_nonempty"])

            sections.append({
                "chapter": chapter,
                "section": section_id,
                "title": str(manifest_section.get("label") or section_id),
                "manifest_path": _relative(manifest_path, project_root),
                "packet_manifest_path": _relative(packet_manifest_path, project_root),
                "learning_packet_path": _relative(packet_path, project_root),
                "student_learning_items_path": _relative(student_path, project_root),
                "student_packet_path": _relative(student_packet_path, project_root),
                "knowledge_points": [str(row.get("label") or "") for row in manifest_section.get("knowledge_points", [])],
                "type_labels": [str(value) for value in manifest_section.get("type_labels", [])],
                "learning_cycles": [
                    {"id": str(row.get("id") or ""), "title": str(row.get("title") or "")}
                    for row in manifest_section.get("learning_cycles", [])
                ],
                "item_counts": counts,
                "student_item_counts": student_counts,
                "first_item_label": str(delivery_items[0].get("label") or "") if delivery_items else None,
                "last_item_label": str(delivery_items[-1].get("label") or "") if delivery_items else None,
                "question_content_complete": len(question_rows) == len(delivery_items) and all(
                    str(row.get("question_text") or "").strip() for row in question_rows
                ),
                "courses": courses,
                "teacher_transcripts_ready": all(row["transcript_nonempty"] for row in courses),
                "progress": {
                    "path": _relative(progress_path, project_root),
                    "chapter_status": str(progress.get("status") or ""),
                    "human_learning_status": str(progress.get("human_learning_status") or ""),
                    "section_status": str(progress_section.get("status") or ""),
                    "attempted_items": len(progress_section.get("attempted_item_keys", [])),
                    "passed_items": len(progress_section.get("passed_item_keys", [])),
                },
                "hashes": {
                    "chapter_manifest_sha256": sha256_file(manifest_path),
                    "learning_packet_sha256": sha256_file(packet_path),
                    "student_learning_items_sha256": sha256_file(student_path),
                    "student_packet_sha256": sha256_file(student_packet_path),
                    "progress_sha256": sha256_file(progress_path),
                },
                "missing": sorted(set(missing)),
                "status": "complete" if not missing else "partial",
            })

        chapter_rows.append({
            "chapter": chapter,
            "sections": len(facts["manifest_sections"]),
            "canonical_items": facts["canonical_item_count"],
            "required_courses": len(facts["required_course_keys"]),
            "progress_path": _relative(progress_path, project_root),
            "progress_status": str(progress.get("status") or ""),
        })

    catalog_transcripts = {
        Path(str(row.get("video_file") or "")).stem
        for row in catalog.values()
        if str(row.get("video_file") or "")
    }
    existing_transcripts = {path.stem for path in transcript_paths}
    return {
        "schema_version": "ybt-chatgpt-context-audit-v1",
        "scope": "chapters_1_and_2",
        "teacher_behavior_contract": {
            "item_source": "Read the current item from student_learning_items.json.",
            "route_source": "Read the current cycle and course references from the chapter manifest and learning delivery.",
            "teaching_source": "Read every referenced course transcript full_text before explaining the item.",
            "teaching_style": "Use the teacher's definitions, method order, recognition cues, and terminology from the transcript.",
            "answer_policy": "Do not read or expose answer sidecars before the learner freezes an attempt.",
            "progress_policy": "Repository progress and browser local progress are separate. Use an explicit browser progress snapshot for current user state.",
        },
        "library": {
            "catalog_courses": len(catalog_transcripts),
            "transcript_files": len(existing_transcripts),
            "catalog_transcripts_present": len(catalog_transcripts & existing_transcripts),
            "missing_catalog_transcripts": sorted(catalog_transcripts - existing_transcripts),
        },
        "chapters": chapter_rows,
        "sections": sections,
        "summary": {
            "sections": len(sections),
            "canonical_items": sum(row["item_counts"]["total"] for row in sections),
            "complete_sections": sum(row["status"] == "complete" for row in sections),
            "partial_sections": sum(row["status"] == "partial" for row in sections),
            "all_question_content_complete": all(row["question_content_complete"] for row in sections),
            "all_teacher_transcripts_ready": all(row["teacher_transcripts_ready"] for row in sections),
        },
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# 第一、二章 ChatGPT 上下文完整性审计",
        "",
        f"- 节次：{audit['summary']['sections']}",
        f"- 教材项目：{audit['summary']['canonical_items']}",
        f"- 完整节次：{audit['summary']['complete_sections']}",
        f"- 课程目录/转写：{audit['library']['catalog_transcripts_present']}/{audit['library']['catalog_courses']}",
        "",
        "| 节次 | 知识点 | 循环 | 例题 | 变式 | A/B/C | 总数 | 转写 | 进度 | 状态 |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in audit["sections"]:
        counts = row["item_counts"]
        progress = row["progress"]
        lines.append(
            f"| {row['section']} {row['title']} | {len(row['knowledge_points'])} | {len(row['learning_cycles'])} | "
            f"{counts['worked_examples']} | {counts['direct_variants']} | {counts['abc_exercises']} | {counts['total']} | "
            f"{'就绪' if row['teacher_transcripts_ready'] else '缺失'} | "
            f"{progress['attempted_items']}/{progress['passed_items']} | {row['status']} |"
        )
    lines.extend([
        "",
        "## 讲题协议",
        "",
        "ChatGPT 必须先读取当前题目的无答案题面，再读取该题绑定的课程转写正文，并采用网课老师的定义、识别方式、方法顺序和术语辅助用户。浏览器实时进度不在 GitHub 中，必须由网页复制进度快照传入。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-root", default="data/chatgpt_context")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    output_root = project_root / args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    audit = build_audit(project_root)
    json_path = output_root / "chapter12_complete_audit.json"
    markdown_path = output_root / "chapter12_complete_audit.md"
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps(audit["summary"] | {"json": str(json_path), "markdown": str(markdown_path)}, ensure_ascii=False))
    return 0 if audit["summary"]["partial_sections"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
