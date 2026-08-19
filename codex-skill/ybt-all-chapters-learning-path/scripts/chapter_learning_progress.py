#!/usr/bin/env python3
"""Shared project-derived facts for growing-learner chapter progress."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ACTIVE_CHAPTERS = {1, 2}
PROGRESS_SCHEMA = "ybt-growing-learner-chapter-v1"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def section_folder(section: str) -> str:
    return section.replace("+", "_")


def item_key(item: dict[str, Any], kind: str) -> str:
    if kind == "exercise_questions":
        return f"Q:{item['qid']}"
    return f"LI:{item['item_id']}"


def canonical_item_keys(project_root: Path, section: str) -> list[str]:
    packet_path = project_root / "data" / "packets" / section_folder(section) / "learning_packet.json"
    packet = load_json(packet_path)
    if str(packet.get("section")) != section:
        raise ValueError(f"section mismatch in {packet_path}")
    keys: list[str] = []
    for kind in ("worked_examples", "direct_variants", "exercise_questions"):
        keys.extend(item_key(item, kind) for item in packet.get(kind, []))
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate canonical item keys in {section}")
    return keys


def chapter_facts(project_root: Path, chapter: int) -> dict[str, Any]:
    if chapter not in ACTIVE_CHAPTERS:
        raise ValueError(f"chapter {chapter} is outside the active scope {sorted(ACTIVE_CHAPTERS)}")

    manifest_path = project_root / f"chapter{chapter}_manifest.json"
    catalog_path = project_root / "data" / "all_chapters_course_catalog.json"
    assignment_path = project_root / "reports" / "ch12_luna_dispatch" / "assignments.json"
    requirements_path = project_root / "docs" / "PRODUCT-REQUIREMENTS.md"
    manifest = load_json(manifest_path)
    catalog = load_json(catalog_path)
    assignment = load_json(assignment_path)
    catalog_keys = {str(row.get("course_key")) for row in catalog.get("courses", [])}

    manifest_sections = [str(row["id"]) for row in manifest.get("sections", [])]
    section_delivery: dict[str, dict[str, Any]] = {}
    delivery_hashes: dict[str, str] = {}
    for task in assignment.get("tasks", []):
        task_id = str(task.get("task_id") or "")
        output_dir = Path(str(task.get("output_dir") or ""))
        delivery_path = output_dir / "delivery.json"
        if not delivery_path.is_absolute():
            delivery_path = project_root / delivery_path
        delivery = load_json(delivery_path)
        contains_chapter_section = False
        for row in delivery.get("sections", []):
            section = str(row.get("section") or "")
            if section not in manifest_sections:
                continue
            contains_chapter_section = True
            if section in section_delivery:
                raise ValueError(f"duplicate section delivery: {section}")
            section_delivery[section] = row
        if contains_chapter_section:
            delivery_hashes[task_id] = sha256_file(delivery_path)

    missing_sections = [section for section in manifest_sections if section not in section_delivery]
    if missing_sections:
        raise ValueError(f"missing chapter section deliveries: {missing_sections}")

    required_course_keys: list[str] = []
    first_section: dict[str, str] = {}
    item_courses: dict[str, list[str]] = {}
    section_items: dict[str, list[str]] = {}
    for section in manifest_sections:
        canonical = canonical_item_keys(project_root, section)
        section_items[section] = canonical
        delivered = section_delivery[section]
        delivered_items = {
            str(item.get("item_key") or ""): item
            for item in delivered.get("items", [])
            if isinstance(item, dict)
        }
        if set(delivered_items) != set(canonical):
            raise ValueError(f"delivery item coverage mismatch: {section}")
        for key in canonical:
            course_refs = [str(value) for value in delivered_items[key].get("course_refs", [])]
            if not course_refs:
                raise ValueError(f"item has no course coverage: {section} {key}")
            unknown = sorted(set(course_refs) - catalog_keys)
            if unknown:
                raise ValueError(f"item references unknown courses: {section} {key} {unknown}")
            item_courses[key] = course_refs
            for course_key in course_refs:
                if course_key not in first_section:
                    first_section[course_key] = section
                    required_course_keys.append(course_key)

    return {
        "chapter": chapter,
        "manifest_sections": manifest_sections,
        "section_deliveries": {section: section_delivery[section] for section in manifest_sections},
        "section_items": section_items,
        "item_courses": item_courses,
        "required_course_keys": required_course_keys,
        "first_section": first_section,
        "canonical_item_count": sum(len(values) for values in section_items.values()),
        "source_binding": {
            "manifest_sha256": sha256_file(manifest_path),
            "course_catalog_sha256": sha256_file(catalog_path),
            "assignment_sha256": sha256_file(assignment_path),
            "requirements_sha256": sha256_file(requirements_path),
            "delivery_sha256": delivery_hashes,
        },
    }
