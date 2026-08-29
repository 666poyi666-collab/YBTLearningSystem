#!/usr/bin/env python3
"""Shared project-derived facts for growing-learner chapter progress."""

from __future__ import annotations

import hashlib
import json
import re
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


def current_route_items(project_root: Path, section: str) -> list[dict[str, Any]]:
    packet_path = project_root / "data" / "packets" / section_folder(section) / "learning_packet.json"
    packet = load_json(packet_path)
    knowledge_labels = {
        str(row.get("id")): str(row.get("label") or row.get("id"))
        for row in packet.get("knowledge_blocks", [])
    }
    rows: list[dict[str, Any]] = []
    ordinal = 0
    for cycle in sorted(packet.get("learning_cycles", []), key=lambda row: int(row.get("sequence") or 0)):
        sequence = int(cycle.get("sequence") or 0)
        course_refs = list(dict.fromkeys([
            *[str(key) for key in cycle.get("prerequisite_course_keys", [])],
            *[str(key) for key in cycle.get("course_keys", [])],
        ]))
        for field, kind, position in (
            ("worked_examples", "worked_example", "教材例题"),
            ("direct_variants", "direct_variant", "直属变式"),
            ("exercise_questions", "abc_exercise", "强化训练"),
        ):
            for item in cycle.get(field, []):
                ordinal += 1
                role = str(item.get("role") or "")
                role_ref = str(item.get("role_ref") or "")
                knowledge_refs = (
                    [knowledge_labels.get(role_ref, role_ref)] if role == "knowledge_example" and role_ref
                    else [] if role == "type_example"
                    else [knowledge_labels.get(str(value), str(value)) for value in cycle.get("knowledge_refs", [])]
                )
                type_refs = (
                    [role_ref] if role == "type_example" and role_ref
                    else [] if role == "knowledge_example"
                    else list(cycle.get("type_refs", []))
                )
                rows.append({
                    "item_key": item_key(item, field),
                    "label": str(item.get("label") or f"{item.get('group', '')}{item.get('number', '')}"),
                    "kind": kind,
                    "cycle_sequence": sequence,
                    "position": "类型题" if role == "type_example" else "知识点右侧例题" if role == "knowledge_example" else position,
                    "course_refs": course_refs,
                    "knowledge_refs": knowledge_refs,
                    "type_refs": type_refs,
                    "ordinal": ordinal,
                })
    return rows


def delivery_signature(item: dict[str, Any]) -> tuple[str, str]:
    kind = str(item.get("kind") or "")
    label = str(item.get("label") or "").replace("组", "")
    if kind == "direct_variant":
        label = label.replace("直属变式", "变式")
        label = re.sub(r"^例\d+·", "", label)
        label = re.sub(r"（.*）$", "", label)
    elif kind == "abc_exercise":
        label = label.replace("-", "")
    return kind, label


def project_delivery_to_current_routes(delivery: dict[str, Any], current: list[dict[str, Any]]) -> dict[str, Any]:
    old_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in delivery.get("items", []):
        signature = delivery_signature(item)
        old_groups.setdefault(signature, []).append(item)
    current_counts: dict[tuple[str, str], int] = {}
    for item in current:
        signature = delivery_signature(item)
        current_counts[signature] = current_counts.get(signature, 0) + 1
    if {key: len(value) for key, value in old_groups.items()} != current_counts:
        raise ValueError(f"delivery labels no longer match current packet: {delivery.get('section')}")
    projected = []
    offsets: dict[tuple[str, str], int] = {}
    for route in current:
        signature = delivery_signature(route)
        index = offsets.get(signature, 0)
        old = old_groups[signature][index]
        offsets[signature] = index + 1
        projected.append({
            **old,
            **route,
            "route_projection_status": "stale_delivery_content_rebound_to_current_route",
        })
    cycles = []
    by_sequence = {int(row.get("sequence") or 0): row for row in delivery.get("cycles", [])}
    for sequence in sorted({item["cycle_sequence"] for item in current}):
        old_cycle = by_sequence.get(sequence, {})
        cycle_items = [item for item in current if item["cycle_sequence"] == sequence]
        cycles.append({
            **old_cycle,
            "sequence": sequence,
            "course_keys": list(dict.fromkeys(key for item in cycle_items for key in item["course_refs"])),
            "route_projection_status": "current_manifest_route",
        })
    return {
        **delivery,
        "items": projected,
        "cycles": cycles,
        "route_projection_status": "stale_delivery_methods_rebound_by_kind_label_occurrence",
        "coverage": {**delivery.get("coverage", {}), "delivered_items": len(projected)},
    }


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
            delivered = project_delivery_to_current_routes(delivered, current_route_items(project_root, section))
            section_delivery[section] = delivered
            delivered_items = {
                str(item.get("item_key") or ""): item
                for item in delivered.get("items", [])
                if isinstance(item, dict)
            }
            if set(delivered_items) != set(canonical):
                raise ValueError(f"delivery item coverage mismatch after route projection: {section}")
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
