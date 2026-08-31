#!/usr/bin/env python3
"""Safely merge item-level semantic type reviews into canonical manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION_PATH = Path("data/item_type_classification.json")
CLASSIFICATION_REPORT_PATH = Path("reports/deep_simulation/type-classification.json")
APPLICATION_REPORT_PATH = Path("reports/deep_simulation/type-review-application.json")
CONTROLLER_ADJUDICATION_PATH = "data/type_review_controller_adjudications.json"

ACCEPTED_REVIEW_STATUSES = {"approved", "classified", "confirmed", "corrected"}
BLOCKED_REVIEW_STATUSES = {
    "needs_manual_review": "MULTI_AGENT_SEMANTIC_REVIEW_BLOCKED_MANUAL",
    "blocked_source_defect": "MULTI_AGENT_SEMANTIC_REVIEW_BLOCKED_SOURCE_DEFECT",
}
REVIEWED_STATUS = "MULTI_AGENT_SEMANTIC_REVIEWED"
CONTROLLER_ADJUDICATED_STATUS = "MULTI_AGENT_SEMANTIC_REVIEWED_CONTROLLER_ADJUDICATED"
OVERALL_STATUS = "MULTI_AGENT_SEMANTIC_REVIEWED_WITH_BLOCKED_ITEMS"

REVIEW_SPECS = (
    {
        "path": Path("reports/deep_simulation_reviews/ch1-ch2-type-review.json"),
        "rows_key": "review_rows",
        "schemas": {"ybt-semantic-type-review-v1"},
        "classification_hash": ("source_binding", "item_type_classification_sha256"),
        "manifest_hashes": {
            1: ("source_binding", "chapter1_manifest_sha256"),
            2: ("source_binding", "chapter2_manifest_sha256"),
        },
        "packet_hashes": ("source_binding", "chapter1_packet_sha256"),
    },
    {
        "path": Path("reports/deep_simulation_reviews/ch3-type-review.json"),
        "rows_key": "reviews",
        "schemas": {"ybt-ch3-type-semantic-review-v1"},
        "classification_hash": ("source_revisions", "classification_sha256"),
        "manifest_hashes": {3: ("source_revisions", "chapter3_manifest_sha256")},
        "packet_hashes": ("source_revisions", "learning_packet_sha256"),
    },
    {
        "path": Path("reports/deep_simulation_reviews/ch4-ch5-type-review.json"),
        "rows_key": "reviews",
        "schemas": {"ybt-semantic-type-review-v1"},
        "classification_hash": ("source_revisions", "classification_sha256"),
        "manifest_hashes": {
            4: ("source_revisions", "chapter4_manifest_sha256"),
            5: ("source_revisions", "chapter5_manifest_sha256"),
        },
        "packet_hashes": ("source_revisions", "learning_packet_sha256"),
    },
)


class ContractError(ValueError):
    """Raised before any write when a review can no longer bind to its source."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ContractError(f"expected JSON object: {path}")
    return value


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def nested(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise ContractError(f"missing review binding: {'.'.join(keys)}")
        value = value[key]
    return value


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def item_label(item: dict[str, Any]) -> str:
    return f"{item.get('group')}{item.get('number')}"


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def require_equal(actual: Any, expected: Any, context: str) -> None:
    if actual != expected:
        raise ContractError(f"{context}: expected {expected!r}, got {actual!r}")


def require_subset(actual: set[str], available: set[str], context: str) -> None:
    missing = sorted(actual - available)
    if missing:
        preview = ", ".join(missing[:20])
        suffix = f" ... and {len(missing) - 20} more" if len(missing) > 20 else ""
        raise ContractError(f"{context}: {len(missing)} missing item ids: {preview}{suffix}")


def review_rows_and_payloads(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []
    for spec in REVIEW_SPECS:
        path = root / spec["path"]
        payload = load_json(path)
        schema = str(payload.get("schema_version") or "")
        if schema not in spec["schemas"]:
            raise ContractError(f"unsupported review schema {schema!r}: {path}")
        raw_rows = payload.get(spec["rows_key"])
        if not isinstance(raw_rows, list):
            raise ContractError(f"missing review rows {spec['rows_key']!r}: {path}")
        report_hash = sha256_file(path)
        for raw in raw_rows:
            if not isinstance(raw, dict):
                raise ContractError(f"review row must be an object: {path}")
            row = dict(raw)
            row["_review_path"] = spec["path"].as_posix()
            row["_review_sha256"] = report_hash
            rows.append(row)
        payloads.append({"spec": spec, "payload": payload, "sha256": report_hash})
    return rows, payloads


def validate_baseline_hashes(
    root: Path,
    payloads: list[dict[str, Any]],
    classification_hash: str,
) -> None:
    checked_manifests: dict[int, str] = {}
    checked_packets: dict[str, str] = {}
    for source in payloads:
        spec = source["spec"]
        payload = source["payload"]
        expected_classification_hash = str(nested(payload, spec["classification_hash"])).lower()
        require_equal(
            classification_hash,
            expected_classification_hash,
            f"{spec['path']} classification SHA-256",
        )
        for chapter, keys in spec["manifest_hashes"].items():
            expected = str(nested(payload, keys)).lower()
            actual = sha256_file(root / f"chapter{chapter}_manifest.json")
            require_equal(actual, expected, f"chapter{chapter} manifest SHA-256")
            previous = checked_manifests.setdefault(chapter, expected)
            require_equal(previous, expected, f"chapter{chapter} conflicting review bindings")
        packet_hashes = nested(payload, spec["packet_hashes"])
        if not isinstance(packet_hashes, dict):
            raise ContractError(f"packet hash binding must be an object: {spec['path']}")
        for section_id, expected_value in packet_hashes.items():
            expected = str(expected_value).lower()
            packet_path = root / "data" / "packets" / section_folder(str(section_id)) / "learning_packet.json"
            actual = sha256_file(packet_path)
            require_equal(actual, expected, f"{section_id} learning packet SHA-256")
            previous = checked_packets.setdefault(str(section_id), expected)
            require_equal(previous, expected, f"{section_id} conflicting packet bindings")


def load_manifests(root: Path) -> tuple[dict[int, dict[str, Any]], dict[str, tuple[int, dict[str, Any]]]]:
    manifests: dict[int, dict[str, Any]] = {}
    sections: dict[str, tuple[int, dict[str, Any]]] = {}
    for chapter in range(1, 6):
        manifest = load_json(root / f"chapter{chapter}_manifest.json")
        manifests[chapter] = manifest
        for section in manifest.get("sections", []):
            section_id = str(section.get("id") or "")
            if not section_id or section_id in sections:
                raise ContractError(f"missing or duplicate canonical section id: {section_id!r}")
            sections[section_id] = (chapter, section)
    return manifests, sections


def load_packet_items(
    root: Path,
    section_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    items: dict[str, dict[str, Any]] = {}
    item_cycles: dict[str, str] = {}
    for section_id in sorted(section_ids):
        packet_path = root / "data" / "packets" / section_folder(section_id) / "learning_packet.json"
        packet = load_json(packet_path)
        require_equal(str(packet.get("section") or ""), section_id, f"{section_id} packet section")
        for cycle in packet.get("learning_cycles", []):
            cycle_id = str(cycle.get("cycle_id") or "")
            for item in cycle.get("exercise_questions", []):
                item_id = str(item.get("qid") or "")
                if not item_id or item_id in items:
                    raise ContractError(f"missing or duplicate packet item id: {section_id} {cycle_id} {item_id!r}")
                require_equal(str(item.get("section") or ""), section_id, f"{item_id} packet item section")
                items[item_id] = item
                item_cycles[item_id] = cycle_id
    return items, item_cycles


def assignment_index(
    sections: dict[str, tuple[int, dict[str, Any]]],
) -> tuple[dict[str, tuple[dict[str, Any], dict[str, Any]]], dict[str, dict[str, Any]]]:
    assignments: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    cycles: dict[str, dict[str, Any]] = {}
    for section_id, (_, section) in sections.items():
        for cycle in section.get("learning_cycles", []):
            cycle_id = str(cycle.get("id") or "")
            if not cycle_id or cycle_id in cycles:
                raise ContractError(f"missing or duplicate manifest cycle id: {section_id} {cycle_id!r}")
            cycles[cycle_id] = cycle
            for assignment in cycle.get("item_type_assignments", []):
                item_id = str(assignment.get("item_id") or "")
                if not item_id or item_id in assignments:
                    raise ContractError(f"missing or duplicate manifest type assignment: {item_id!r}")
                assignments[item_id] = (cycle, assignment)
    return assignments, cycles


def normalize_and_validate(
    root: Path,
    classification: dict[str, Any],
    review_rows: list[dict[str, Any]],
    sections: dict[str, tuple[int, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    classification_rows = classification.get("rows")
    if not isinstance(classification_rows, list):
        raise ContractError("classification rows must be a list")
    classification_by_id: dict[str, dict[str, Any]] = {}
    for row in classification_rows:
        item_id = str(row.get("item_id") or "")
        if not item_id or item_id in classification_by_id:
            raise ContractError(f"missing or duplicate classification item id: {item_id!r}")
        classification_by_id[item_id] = row

    review_by_id: dict[str, dict[str, Any]] = {}
    for raw in review_rows:
        item_id = str(raw.get("item_id") or "")
        if not item_id or item_id in review_by_id:
            raise ContractError(f"missing or duplicate review item id: {item_id!r}")
        if item_id not in classification_by_id:
            raise ContractError(f"review item absent from classification: {item_id}")
        review_by_id[item_id] = raw
    require_equal(set(review_by_id), set(classification_by_id), "review/classification item coverage")

    packet_items, packet_cycles = load_packet_items(
        root,
        {str(row.get("section") or "") for row in classification_rows},
    )
    manifest_assignments, manifest_cycles = assignment_index(sections)
    require_subset(set(classification_by_id), set(packet_items), "packet/classification item coverage")
    require_subset(set(classification_by_id), set(manifest_assignments), "manifest/classification assignment coverage")

    normalized: list[dict[str, Any]] = []
    for item_id, machine in classification_by_id.items():
        review = review_by_id[item_id]
        section_id = str(machine.get("section") or "")
        cycle_id = str(machine.get("cycle_id") or "")
        label = str(machine.get("item_label") or "")
        chapter = int(machine.get("chapter") or 0)
        if section_id not in sections:
            raise ContractError(f"classification references unknown section: {item_id} {section_id}")
        canonical_chapter, _ = sections[section_id]
        require_equal(chapter, canonical_chapter, f"{item_id} classification chapter")
        require_equal(str(review.get("section") or ""), section_id, f"{item_id} review section")
        require_equal(str(review.get("item_label") or ""), label, f"{item_id} review label")
        if review.get("chapter") is not None:
            require_equal(int(review["chapter"]), chapter, f"{item_id} review chapter")
        if review.get("cycle_id") is not None:
            require_equal(str(review["cycle_id"]), cycle_id, f"{item_id} review cycle")

        packet_item = packet_items[item_id]
        require_equal(packet_cycles[item_id], cycle_id, f"{item_id} packet cycle")
        require_equal(item_label(packet_item), label, f"{item_id} packet label")
        question_hash = sha256_text(str(packet_item.get("question_text") or ""))
        require_equal(
            str(machine.get("question_text_sha256") or "").lower(),
            question_hash,
            f"{item_id} classification question SHA-256",
        )
        review_question_hash = review.get("question_text_sha256")
        if review_question_hash is not None:
            require_equal(str(review_question_hash).lower(), question_hash, f"{item_id} review question SHA-256")

        manifest_cycle, assignment = manifest_assignments[item_id]
        require_equal(str(manifest_cycle.get("id") or ""), cycle_id, f"{item_id} manifest cycle")
        require_equal(str(assignment.get("item_label") or ""), label, f"{item_id} manifest assignment label")
        require_equal(
            str(assignment.get("type_title") or ""),
            str(machine.get("type_title") or ""),
            f"{item_id} machine type binding",
        )

        primary = str(review.get("reviewed_primary_type") or "").strip()
        secondary = [str(value).strip() for value in review.get("secondary_types", []) if str(value).strip()]
        if not primary:
            raise ContractError(f"reviewed primary type is empty: {item_id}")
        require_equal(len(secondary), len(set(secondary)), f"{item_id} duplicate secondary types")
        if primary in secondary:
            raise ContractError(f"primary type repeated as secondary: {item_id} {primary}")
        review_status = str(review.get("review_status") or "")
        if review_status not in ACCEPTED_REVIEW_STATUSES | set(BLOCKED_REVIEW_STATUSES):
            raise ContractError(f"unsupported semantic review status: {item_id} {review_status!r}")
        normalized.append({
            "chapter": chapter,
            "section": section_id,
            "cycle_id": cycle_id,
            "item_id": item_id,
            "item_label": label,
            "question_text_sha256": question_hash,
            "reviewed_primary_type": primary,
            "secondary_types": secondary,
            "review_status": review_status,
            "reason": str(review.get("reason") or "").strip(),
            "source_anchor": review.get("source_anchor"),
            "review_path": str(review["_review_path"]),
            "review_sha256": str(review["_review_sha256"]),
        })
    return normalized, classification_by_id, manifest_cycles


def is_applied(classification: dict[str, Any]) -> bool:
    rows = classification.get("rows", [])
    return bool(rows) and all(
        str(row.get("review_status") or "").startswith("MULTI_AGENT_SEMANTIC_")
        for row in rows
    )


def apply_reviews(
    classification: dict[str, Any],
    classification_report: dict[str, Any],
    manifests: dict[int, dict[str, Any]],
    sections: dict[str, tuple[int, dict[str, Any]]],
    normalized: list[dict[str, Any]],
    classification_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    applied_at = datetime.now(timezone.utc).isoformat()
    assignments, _ = assignment_index(sections)
    rows_by_cycle: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows_by_section: dict[str, list[dict[str, Any]]] = defaultdict(list)
    extensions: list[dict[str, Any]] = []

    for row in normalized:
        rows_by_cycle[row["cycle_id"]].append(row)
        rows_by_section[row["section"]].append(row)
        if row["review_status"] not in ACCEPTED_REVIEW_STATUSES:
            continue
        _, section = sections[row["section"]]
        labels = [str(value) for value in section.get("type_labels", [])]
        for position, type_title in enumerate([row["reviewed_primary_type"], *row["secondary_types"]]):
            if type_title in labels:
                continue
            labels.append(type_title)
            extensions.append({
                "chapter": row["chapter"],
                "section": row["section"],
                "type_title": type_title,
                "introduced_by_item_id": row["item_id"],
                "introduced_by_item_label": row["item_label"],
                "role": "primary" if position == 0 else "secondary",
            })
        section["type_labels"] = labels

    for row in normalized:
        machine = classification_by_id[row["item_id"]]
        _, assignment = assignments[row["item_id"]]
        machine_type = str(machine.get("type_title") or "")
        machine_method = str(machine.get("classification_method") or "")
        semantic = {
            "review_path": row["review_path"],
            "review_sha256": row["review_sha256"],
            "original_review_status": row["review_status"],
            "reviewed_primary_type": row["reviewed_primary_type"],
            "secondary_types": row["secondary_types"],
            "reason": row["reason"],
            "question_text_sha256": row["question_text_sha256"],
        }
        if row["source_anchor"] is not None:
            semantic["source_anchor"] = row["source_anchor"]

        machine["machine_type_title"] = machine_type
        machine["machine_classification_method"] = machine_method
        machine["semantic_review"] = semantic
        assignment["machine_type_title"] = str(assignment.get("type_title") or "")
        assignment["question_text_sha256"] = row["question_text_sha256"]
        assignment["review_ref"] = f"{row['review_path']}#{row['item_id']}"
        assignment["review_reason"] = row["reason"]

        if row["review_status"] in ACCEPTED_REVIEW_STATUSES:
            machine["type_title"] = row["reviewed_primary_type"]
            machine["secondary_types"] = row["secondary_types"]
            machine["classification_method"] = "multi_agent_semantic_review"
            machine["review_status"] = REVIEWED_STATUS
            assignment["type_title"] = row["reviewed_primary_type"]
            assignment["secondary_types"] = row["secondary_types"]
            assignment["review_status"] = REVIEWED_STATUS
            assignment.pop("proposed_type_title", None)
            assignment.pop("proposed_secondary_types", None)
            assignment.pop("blocking_reason", None)
        else:
            blocked_status = BLOCKED_REVIEW_STATUSES[row["review_status"]]
            machine["secondary_types"] = []
            machine["classification_method"] = "machine_semantic_classification_with_blocked_review"
            machine["review_status"] = blocked_status
            machine["proposed_type_title"] = row["reviewed_primary_type"]
            machine["proposed_secondary_types"] = row["secondary_types"]
            machine["blocking_reason"] = row["reason"]
            assignment["secondary_types"] = []
            assignment["review_status"] = blocked_status
            assignment["proposed_type_title"] = row["reviewed_primary_type"]
            assignment["proposed_secondary_types"] = row["secondary_types"]
            assignment["blocking_reason"] = row["reason"]

    for _, section in sections.values():
        section_id = str(section["id"])
        section_rows = rows_by_section.get(section_id, [])
        if not section_rows:
            continue
        section_blocked = [row for row in section_rows if row["review_status"] in BLOCKED_REVIEW_STATUSES]
        section["item_type_review_status"] = OVERALL_STATUS if section_blocked else REVIEWED_STATUS
        section["blocked_item_type_reviews"] = [
            {
                "item_id": row["item_id"],
                "item_label": row["item_label"],
                "status": BLOCKED_REVIEW_STATUSES[row["review_status"]],
                "reason": row["reason"],
            }
            for row in section_blocked
        ]
        section["semantic_type_taxonomy_extensions"] = [
            extension for extension in extensions if extension["section"] == section_id
        ]
        for cycle in section.get("learning_cycles", []):
            cycle_id = str(cycle.get("id") or "")
            cycle_rows = rows_by_cycle.get(cycle_id, [])
            if not cycle_rows:
                continue
            accepted = [row for row in cycle_rows if row["review_status"] in ACCEPTED_REVIEW_STATUSES]
            blocked = [row for row in cycle_rows if row["review_status"] in BLOCKED_REVIEW_STATUSES]
            cycle["type_refs"] = unique([
                type_title
                for row in accepted
                for type_title in [row["reviewed_primary_type"], *row["secondary_types"]]
            ])
            cycle["type_mapping_status"] = OVERALL_STATUS if blocked else REVIEWED_STATUS
            if blocked:
                cycle["blocked_item_type_assignments"] = [
                    {
                        "item_id": row["item_id"],
                        "item_label": row["item_label"],
                        "status": BLOCKED_REVIEW_STATUSES[row["review_status"]],
                        "reason": row["reason"],
                    }
                    for row in blocked
                ]
            else:
                cycle.pop("blocked_item_type_assignments", None)

    status_counts = Counter(row["review_status"] for row in normalized)
    accepted_count = sum(status_counts[status] for status in ACCEPTED_REVIEW_STATUSES)
    blocked_count = sum(status_counts[status] for status in BLOCKED_REVIEW_STATUSES)
    blocked_rows = [row for row in normalized if row["review_status"] in BLOCKED_REVIEW_STATUSES]
    review_sources = unique([row["review_path"] for row in normalized])
    review_hashes = {
        row["review_path"]: row["review_sha256"]
        for row in normalized
    }
    summary = {
        "items": len(normalized),
        "accepted": accepted_count,
        "blocked": blocked_count,
        "review_status_counts": dict(sorted(status_counts.items())),
        "taxonomy_extensions": len(extensions),
        "sections": len(rows_by_section),
        "cycles": len(rows_by_cycle),
    }
    classification["status"] = OVERALL_STATUS
    classification["semantic_review_applied_at"] = applied_at
    classification["semantic_review_sources"] = review_sources
    classification["semantic_review_source_hashes"] = review_hashes
    classification["semantic_review_summary"] = summary

    classification_report["status"] = OVERALL_STATUS
    classification_report["semantic_review_applied_at"] = applied_at
    classification_report["semantic_review"] = summary
    classification_report["blocked_items"] = [
        {
            "chapter": row["chapter"],
            "section": row["section"],
            "cycle_id": row["cycle_id"],
            "item_id": row["item_id"],
            "item_label": row["item_label"],
            "status": BLOCKED_REVIEW_STATUSES[row["review_status"]],
            "reason": row["reason"],
        }
        for row in blocked_rows
    ]

    for chapter, manifest in manifests.items():
        chapter_rows = [row for row in normalized if row["chapter"] == chapter]
        chapter_blocked = [row for row in chapter_rows if row["review_status"] in BLOCKED_REVIEW_STATUSES]
        manifest["item_type_semantic_review"] = {
            "status": OVERALL_STATUS if chapter_blocked else REVIEWED_STATUS,
            "applied_at": applied_at,
            "items": len(chapter_rows),
            "accepted": len(chapter_rows) - len(chapter_blocked),
            "blocked": len(chapter_blocked),
            "source_reports": unique([row["review_path"] for row in chapter_rows]),
            "mastery_claimed": False,
        }

    return {
        "schema_version": "ybt-item-type-review-application-v1",
        "generated_at": applied_at,
        "status": OVERALL_STATUS,
        "summary": summary,
        "source_reports": [
            {"path": path, "sha256": review_hashes[path]}
            for path in review_sources
        ],
        "taxonomy_extensions": extensions,
        "blocked_items": classification_report["blocked_items"],
        "boundaries": {
            "blocked_items_classified_as_passed": False,
            "source_defects_claimed_resolved": False,
            "learner_mastery_claimed": False,
        },
    }


def validate_applied_state(
    classification: dict[str, Any],
    manifests: dict[int, dict[str, Any]],
    sections: dict[str, tuple[int, dict[str, Any]]],
    normalized: list[dict[str, Any]],
    classification_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    assignments, _ = assignment_index(sections)
    errors: list[str] = []
    accepted = 0
    blocked = 0
    effectively_accepted_ids: set[str] = set()
    effectively_blocked_ids: set[str] = set()
    rows_by_cycle: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in normalized:
        rows_by_cycle[row["cycle_id"]].append(row)
        machine = classification_by_id[row["item_id"]]
        cycle, assignment = assignments[row["item_id"]]
        _, section = sections[row["section"]]
        controller_overlay = machine.get("controller_adjudication") or {}
        controller_override = (
            row["review_status"] in BLOCKED_REVIEW_STATUSES
            and machine.get("review_status") == CONTROLLER_ADJUDICATED_STATUS
            and assignment.get("review_status") == CONTROLLER_ADJUDICATED_STATUS
        )
        if controller_override:
            expected_prior_status = BLOCKED_REVIEW_STATUSES[row["review_status"]]
            source_sha = str(controller_overlay.get("source_sha256") or "")
            adjudication_id = str(controller_overlay.get("adjudication_id") or "")
            expected_ref = f"{CONTROLLER_ADJUDICATION_PATH}#{adjudication_id}"
            top_sources = classification.get("controller_adjudication_sources") or []
            if controller_overlay.get("source_path") != CONTROLLER_ADJUDICATION_PATH:
                errors.append(f"{row['item_id']}: controller-adjudication source path differs")
            if len(source_sha) != 64:
                errors.append(f"{row['item_id']}: controller-adjudication source SHA-256 is invalid")
            if not any(
                source.get("path") == CONTROLLER_ADJUDICATION_PATH
                and source.get("sha256") == source_sha
                for source in top_sources
                if isinstance(source, dict)
            ):
                errors.append(f"{row['item_id']}: controller-adjudication top-level source binding differs")
            if controller_overlay.get("prior_review_status") != expected_prior_status:
                errors.append(f"{row['item_id']}: controller-adjudication prior status differs")
            if controller_overlay.get("question_text_sha256") != row["question_text_sha256"]:
                errors.append(f"{row['item_id']}: controller-adjudication question SHA-256 differs")
            if assignment.get("adjudication_ref") != expected_ref:
                errors.append(f"{row['item_id']}: manifest controller-adjudication reference differs")
            answer_page_sha = str((controller_overlay.get("answer_evidence") or {}).get("page_image_sha256") or "")
            if len(answer_page_sha) != 64 or assignment.get("answer_page_image_sha256") != answer_page_sha:
                errors.append(f"{row['item_id']}: controller-adjudication answer-page SHA-256 differs")
            if machine.get("classification_method") != "controller_adjudication_after_multi_agent_semantic_review":
                errors.append(f"{row['item_id']}: controller-adjudication classification method differs")
            if any(field in machine for field in ("proposed_type_title", "proposed_secondary_types", "blocking_reason")):
                errors.append(f"{row['item_id']}: stale classification block fields remain after adjudication")
            if any(field in assignment for field in ("proposed_type_title", "proposed_secondary_types", "blocking_reason")):
                errors.append(f"{row['item_id']}: stale manifest block fields remain after adjudication")

        effectively_accepted = row["review_status"] in ACCEPTED_REVIEW_STATUSES or controller_override
        if effectively_accepted:
            accepted += 1
            effectively_accepted_ids.add(row["item_id"])
            expected_status = CONTROLLER_ADJUDICATED_STATUS if controller_override else REVIEWED_STATUS
            if machine.get("type_title") != row["reviewed_primary_type"]:
                errors.append(f"{row['item_id']}: classification primary type differs from review")
            if list(machine.get("secondary_types", [])) != row["secondary_types"]:
                errors.append(f"{row['item_id']}: classification secondary types differ from review")
            if assignment.get("type_title") != row["reviewed_primary_type"]:
                errors.append(f"{row['item_id']}: manifest primary type differs from review")
            if list(assignment.get("secondary_types", [])) != row["secondary_types"]:
                errors.append(f"{row['item_id']}: manifest secondary types differ from review")
            for type_title in [row["reviewed_primary_type"], *row["secondary_types"]]:
                if type_title not in section.get("type_labels", []):
                    errors.append(f"{row['item_id']}: reviewed type absent from section type_labels: {type_title}")
        else:
            blocked += 1
            effectively_blocked_ids.add(row["item_id"])
            expected_status = BLOCKED_REVIEW_STATUSES[row["review_status"]]
            if machine.get("type_title") == row["reviewed_primary_type"] and machine.get("machine_type_title") != row["reviewed_primary_type"]:
                errors.append(f"{row['item_id']}: blocked proposed type was applied as confirmed")
            if machine.get("proposed_type_title") != row["reviewed_primary_type"]:
                errors.append(f"{row['item_id']}: blocked classification proposal missing")
            if assignment.get("proposed_type_title") != row["reviewed_primary_type"]:
                errors.append(f"{row['item_id']}: blocked manifest proposal missing")
            if cycle.get("type_mapping_status") != OVERALL_STATUS:
                errors.append(f"{row['item_id']}: blocked cycle lacks explicit blocked status")
        if machine.get("review_status") != expected_status:
            errors.append(f"{row['item_id']}: classification review status differs")
        if assignment.get("review_status") != expected_status:
            errors.append(f"{row['item_id']}: manifest review status differs")
        if assignment.get("question_text_sha256") != row["question_text_sha256"]:
            errors.append(f"{row['item_id']}: manifest question hash differs")
        semantic = machine.get("semantic_review") or {}
        expected_review_ref = f"{row['review_path']}#{row['item_id']}"
        if semantic.get("review_path") != row["review_path"]:
            errors.append(f"{row['item_id']}: classification review path differs")
        if semantic.get("review_sha256") != row["review_sha256"]:
            errors.append(f"{row['item_id']}: classification review SHA-256 differs")
        if semantic.get("question_text_sha256") != row["question_text_sha256"]:
            errors.append(f"{row['item_id']}: classification semantic-review question hash differs")
        if semantic.get("reviewed_primary_type") != row["reviewed_primary_type"]:
            errors.append(f"{row['item_id']}: classification semantic-review primary type differs")
        if list(semantic.get("secondary_types", [])) != row["secondary_types"]:
            errors.append(f"{row['item_id']}: classification semantic-review secondary types differ")
        if assignment.get("review_ref") != expected_review_ref:
            errors.append(f"{row['item_id']}: manifest review reference differs")

    for _, section in sections.values():
        for cycle in section.get("learning_cycles", []):
            cycle_id = str(cycle.get("id") or "")
            cycle_rows = rows_by_cycle.get(cycle_id, [])
            if not cycle_rows:
                continue
            accepted_rows = [row for row in cycle_rows if row["item_id"] in effectively_accepted_ids]
            blocked_rows = [row for row in cycle_rows if row["item_id"] in effectively_blocked_ids]
            expected_type_refs = unique([
                type_title
                for row in accepted_rows
                for type_title in [row["reviewed_primary_type"], *row["secondary_types"]]
            ])
            if list(cycle.get("type_refs", [])) != expected_type_refs:
                errors.append(f"{cycle_id}: type_refs are not the exact accepted-review type union")
            expected_cycle_status = OVERALL_STATUS if blocked_rows else REVIEWED_STATUS
            if cycle.get("type_mapping_status") != expected_cycle_status:
                errors.append(f"{cycle_id}: cycle type mapping status differs")
            declared_blocked = {
                str(item.get("item_id") or "")
                for item in cycle.get("blocked_item_type_assignments", [])
                if isinstance(item, dict)
            }
            expected_blocked = {row["item_id"] for row in blocked_rows}
            if declared_blocked != expected_blocked:
                errors.append(f"{cycle_id}: blocked item set differs")

    expected_top_status = OVERALL_STATUS if blocked else REVIEWED_STATUS
    if classification.get("status") != expected_top_status:
        errors.append("classification top-level status differs from effective semantic-review state")
    summary = classification.get("semantic_review_summary") or {}
    if summary.get("items") != len(normalized):
        errors.append("classification semantic-review item count differs")
    if summary.get("accepted") != accepted:
        errors.append("classification semantic-review accepted count differs")
    if summary.get("blocked") != blocked:
        errors.append("classification semantic-review blocked count differs")
    for chapter, manifest in manifests.items():
        chapter_rows = [row for row in normalized if row["chapter"] == chapter]
        chapter_blocked = [row for row in chapter_rows if row["item_id"] in effectively_blocked_ids]
        expected = OVERALL_STATUS if chapter_blocked else REVIEWED_STATUS
        if (manifest.get("item_type_semantic_review") or {}).get("status") != expected:
            errors.append(f"chapter{chapter}: manifest semantic-review status differs")
    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:40])
        suffix = f"\n... and {len(errors) - 40} more" if len(errors) > 40 else ""
        raise ContractError(f"applied semantic review validation failed ({len(errors)}):\n{preview}{suffix}")
    return {
        "status": expected_top_status,
        "items": len(normalized),
        "accepted": accepted,
        "blocked": blocked,
        "sections": len({row["section"] for row in normalized}),
        "cycles": len({row["cycle_id"] for row in normalized}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--check", action="store_true", help="validate an already-applied semantic review")
    parser.add_argument("--dry-run", action="store_true", help="validate and report without writing")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    classification_path = root / CLASSIFICATION_PATH
    classification_report_path = root / CLASSIFICATION_REPORT_PATH
    classification = load_json(classification_path)
    classification_report = load_json(classification_report_path)
    review_rows, payloads = review_rows_and_payloads(root)
    manifests, sections = load_manifests(root)

    already_applied = is_applied(classification)
    if already_applied:
        normalized, classification_by_id, _ = normalize_and_validate(
            root,
            classification,
            review_rows,
            sections,
        )
        result = validate_applied_state(
            classification,
            manifests,
            sections,
            normalized,
            classification_by_id,
        )
        result["mode"] = "check"
        result["already_applied"] = True
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.check:
        raise ContractError("semantic reviews have not been applied")
    validate_baseline_hashes(root, payloads, sha256_file(classification_path))
    normalized, classification_by_id, _ = normalize_and_validate(
        root,
        classification,
        review_rows,
        sections,
    )
    if args.dry_run:
        counts = Counter(row["review_status"] for row in normalized)
        print(json.dumps({
            "mode": "dry-run",
            "items": len(normalized),
            "accepted": sum(counts[status] for status in ACCEPTED_REVIEW_STATUSES),
            "blocked": sum(counts[status] for status in BLOCKED_REVIEW_STATUSES),
            "status_counts": dict(sorted(counts.items())),
        }, ensure_ascii=False))
        return 0

    application_report = apply_reviews(
        classification,
        classification_report,
        manifests,
        sections,
        normalized,
        classification_by_id,
    )
    save_json(classification_path, classification)
    save_json(classification_report_path, classification_report)
    for chapter, manifest in manifests.items():
        save_json(root / f"chapter{chapter}_manifest.json", manifest)
    save_json(root / APPLICATION_REPORT_PATH, application_report)

    normalized_after, classification_by_id_after, _ = normalize_and_validate(
        root,
        classification,
        review_rows,
        sections,
    )
    result = validate_applied_state(
        classification,
        manifests,
        sections,
        normalized_after,
        classification_by_id_after,
    )
    result["mode"] = "apply"
    result["report"] = APPLICATION_REPORT_PATH.as_posix()
    result["taxonomy_extensions"] = len(application_report["taxonomy_extensions"])
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as error:
        print(json.dumps({"status": "contract_error", "error": str(error)}, ensure_ascii=False))
        raise SystemExit(1)
