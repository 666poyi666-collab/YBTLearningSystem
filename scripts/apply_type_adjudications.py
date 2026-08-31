#!/usr/bin/env python3
"""Apply two hash-bound controller adjudications over semantic type reviews."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ADJUDICATION_PATH = Path("data/type_review_controller_adjudications.json")
CLASSIFICATION_PATH = Path("data/item_type_classification.json")
MANIFEST_PATH = Path("chapter2_manifest.json")
CLASSIFICATION_REPORT_PATH = Path("reports/deep_simulation/type-classification.json")
APPLICATION_REPORT_PATH = Path("reports/deep_simulation/type-review-application.json")

EXPECTED_ITEM_IDS = {
    "Q-097281f5844ed6cf",
    "Q-3235c438f136521a",
}
NON_TARGET_MANUAL_ITEM_ID = "Q-71eccd74698e096f"  # 2.5 B13 is owned by source reconciliation.
REVIEWED_STATUS = "MULTI_AGENT_SEMANTIC_REVIEWED"
ADJUDICATED_STATUS = "MULTI_AGENT_SEMANTIC_REVIEWED_CONTROLLER_ADJUDICATED"
BLOCKED_PREFIX = "MULTI_AGENT_SEMANTIC_REVIEW_BLOCKED_"
OVERALL_BLOCKED_STATUS = "MULTI_AGENT_SEMANTIC_REVIEWED_WITH_BLOCKED_ITEMS"


class ContractError(ValueError):
    """Raised before writes if source evidence or the target state has drifted."""


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


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def require_equal(actual: Any, expected: Any, context: str) -> None:
    if actual != expected:
        raise ContractError(f"{context}: expected {expected!r}, got {actual!r}")


def require(condition: bool, context: str) -> None:
    if not condition:
        raise ContractError(context)


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def is_blocked(status: Any) -> bool:
    return str(status or "").startswith(BLOCKED_PREFIX)


def is_accepted(status: Any) -> bool:
    return status in {REVIEWED_STATUS, ADJUDICATED_STATUS}


def expected_overall_status(blocked: int) -> str:
    return OVERALL_BLOCKED_STATUS if blocked else REVIEWED_STATUS


def load_contract(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    path = root / ADJUDICATION_PATH
    payload = load_json(path)
    require_equal(
        payload.get("schema_version"),
        "ybt-type-review-controller-adjudications-v1",
        "adjudication schema",
    )
    rows = payload.get("adjudications")
    require(isinstance(rows, list), "adjudications must be a list")
    ids = [str(row.get("item_id") or "") for row in rows if isinstance(row, dict)]
    require_equal(len(rows), 2, "adjudication row count")
    require_equal(len(ids), len(set(ids)), "duplicate adjudication item ids")
    require_equal(set(ids), EXPECTED_ITEM_IDS, "adjudication item scope")
    require_equal((payload.get("scope") or {}).get("item_count"), 2, "scope item count")
    require_equal(set((payload.get("scope") or {}).get("item_ids", [])), EXPECTED_ITEM_IDS, "scope ids")
    boundaries = payload.get("boundaries") or {}
    require_equal(boundaries.get("adjudicates_source_defects"), False, "source-defect boundary")
    require_equal(boundaries.get("touches_2_5_B13"), False, "2.5 B13 boundary")
    require_equal(boundaries.get("learner_mastery_claimed"), False, "mastery boundary")
    require_equal(boundaries.get("answer_text_exposed_to_learner"), False, "answer exposure boundary")
    for row in rows:
        require(isinstance(row, dict), "adjudication row must be an object")
        require_equal(int(row.get("chapter") or 0), 2, f"{row.get('item_id')} chapter")
        require(str(row.get("reviewed_primary_type") or "").strip() != "", f"{row.get('item_id')} empty primary type")
        secondary = [str(value).strip() for value in row.get("secondary_types", [])]
        require_equal(len(secondary), len(set(secondary)), f"{row.get('item_id')} duplicate secondary types")
        require(str(row["reviewed_primary_type"]) not in secondary, f"{row.get('item_id')} primary repeated as secondary")
        evidence = row.get("answer_evidence") or {}
        require(len(str(evidence.get("page_image_sha256") or "")) == 64, f"{row.get('item_id')} page-image SHA")
    return payload, rows, sha256_file(path)


def classification_index(classification: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = classification.get("rows")
    require(isinstance(rows, list), "classification rows must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = str(row.get("item_id") or "")
        require(item_id and item_id not in result, f"missing or duplicate classification id: {item_id!r}")
        result[item_id] = row
    return result


def manifest_indexes(
    manifest: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, tuple[dict[str, Any], dict[str, Any]]]]:
    sections: dict[str, dict[str, Any]] = {}
    cycles: dict[str, dict[str, Any]] = {}
    assignments: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for section in manifest.get("sections", []):
        section_id = str(section.get("id") or "")
        require(section_id and section_id not in sections, f"missing or duplicate manifest section: {section_id!r}")
        sections[section_id] = section
        for cycle in section.get("learning_cycles", []):
            cycle_id = str(cycle.get("id") or "")
            require(cycle_id and cycle_id not in cycles, f"missing or duplicate manifest cycle: {cycle_id!r}")
            cycles[cycle_id] = cycle
            for assignment in cycle.get("item_type_assignments", []):
                item_id = str(assignment.get("item_id") or "")
                require(item_id and item_id not in assignments, f"missing or duplicate manifest assignment: {item_id!r}")
                assignments[item_id] = (cycle, assignment)
    return sections, cycles, assignments


def packet_item(root: Path, adjudication: dict[str, Any]) -> dict[str, Any]:
    section_id = str(adjudication["section"])
    packet = load_json(root / "data" / "packets" / section_folder(section_id) / "learning_packet.json")
    require_equal(str(packet.get("section") or ""), section_id, f"{section_id} packet section")
    matches: list[tuple[str, dict[str, Any]]] = []
    for cycle in packet.get("learning_cycles", []):
        for item in cycle.get("exercise_questions", []):
            if item.get("qid") == adjudication["item_id"]:
                matches.append((str(cycle.get("cycle_id") or ""), item))
    require_equal(len(matches), 1, f"{adjudication['item_id']} packet occurrence count")
    cycle_id, item = matches[0]
    require_equal(cycle_id, adjudication["cycle_id"], f"{adjudication['item_id']} packet cycle")
    require_equal(str(item.get("section") or ""), section_id, f"{adjudication['item_id']} packet item section")
    require_equal(f"{item.get('group')}{item.get('number')}", adjudication["item_label"], f"{adjudication['item_id']} packet label")
    require_equal(
        sha256_text(str(item.get("question_text") or "")),
        adjudication["question_text_sha256"],
        f"{adjudication['item_id']} packet question SHA-256",
    )
    return item


def validate_answer_evidence(root: Path, adjudication: dict[str, Any]) -> dict[str, Any]:
    expected = adjudication["answer_evidence"]
    sidecar = load_json(root / expected["sidecar_path"])
    require_equal(sidecar.get("schema_version"), "ybt-answer-sidecar-v3", f"{adjudication['item_id']} sidecar schema")
    require_equal(sidecar.get("section"), adjudication["section"], f"{adjudication['item_id']} sidecar section")
    require_equal(sidecar.get("status"), "VERIFIED", f"{adjudication['item_id']} sidecar status")
    require_equal((sidecar.get("source_pdf") or {}).get("sha256"), expected["source_pdf_sha256"], f"{adjudication['item_id']} sidecar PDF SHA-256")
    matches = [answer for answer in sidecar.get("answers", []) if answer.get("qid") == adjudication["item_id"]]
    require_equal(len(matches), 1, f"{adjudication['item_id']} answer evidence count")
    answer = matches[0]
    source = answer.get("source") or {}
    require_equal(answer.get("section"), adjudication["section"], f"{adjudication['item_id']} answer section")
    require_equal(f"{answer.get('group')}{answer.get('number')}", adjudication["item_label"], f"{adjudication['item_id']} answer label")
    require_equal(answer.get("answer_isolated"), True, f"{adjudication['item_id']} answer isolation")
    require_equal(answer.get("review_required"), False, f"{adjudication['item_id']} answer review flag")
    require_equal(answer.get("automatic_grading_allowed"), True, f"{adjudication['item_id']} grading flag")
    require(str(answer.get("answer_text") or "").strip() != "", f"{adjudication['item_id']} answer text is empty")
    require_equal(answer.get("parse_status"), expected["parse_status"], f"{adjudication['item_id']} parse status")
    require_equal(source.get("source_pdf_sha256"), expected["source_pdf_sha256"], f"{adjudication['item_id']} answer PDF SHA-256")
    require_equal(source.get("pdf_page"), expected["pdf_page"], f"{adjudication['item_id']} answer PDF page")
    require_equal(source.get("page_image_path"), expected["page_image_path"], f"{adjudication['item_id']} page-image path")
    require_equal(source.get("page_image_sha256"), expected["page_image_sha256"], f"{adjudication['item_id']} sidecar page-image SHA-256")
    image_path = root / expected["page_image_path"]
    require(image_path.is_file(), f"{adjudication['item_id']} source page image is missing: {image_path}")
    require_equal(sha256_file(image_path), expected["page_image_sha256"], f"{adjudication['item_id']} actual page-image SHA-256")
    return answer


def relevant_review_rows(
    root: Path,
    payload: dict[str, Any],
    *,
    strict_current_hashes: bool,
) -> dict[str, dict[str, Any]]:
    source_binding = payload.get("source_binding") or {}
    report_specs = source_binding.get("semantic_review_report_snapshots") or []
    require_equal(len(report_specs), 3, "semantic-review report binding count")
    relevant: dict[str, dict[str, Any]] = {}
    for spec in report_specs:
        path = root / str(spec.get("path") or "")
        require(path.is_file(), f"semantic-review report is missing: {path}")
        if strict_current_hashes:
            require_equal(
                sha256_file(path),
                str(spec.get("sha256") or ""),
                f"{spec.get('path')} evidence-snapshot SHA-256",
            )
        report = load_json(path)
        rows = report.get("review_rows")
        if rows is None:
            rows = report.get("reviews")
        require(isinstance(rows, list), f"semantic-review rows missing: {path}")
        for row in rows:
            item_id = str(row.get("item_id") or "")
            if item_id in EXPECTED_ITEM_IDS:
                require(item_id not in relevant, f"duplicate target semantic-review row: {item_id}")
                relevant[item_id] = row
    require_equal(set(relevant), EXPECTED_ITEM_IDS, "target semantic-review report coverage")
    return relevant


def all_targets_applied(classification_by_id: dict[str, dict[str, Any]]) -> bool:
    return all(
        classification_by_id[item_id].get("review_status") == ADJUDICATED_STATUS
        and isinstance(classification_by_id[item_id].get("controller_adjudication"), dict)
        for item_id in EXPECTED_ITEM_IDS
    )


def validate_row_bindings(
    root: Path,
    adjudications: list[dict[str, Any]],
    classification_by_id: dict[str, dict[str, Any]],
    sections: dict[str, dict[str, Any]],
    assignments: dict[str, tuple[dict[str, Any], dict[str, Any]]],
    review_rows: dict[str, dict[str, Any]],
    applied: bool,
    adjudication_path_sha256: str,
) -> None:
    for adjudication in adjudications:
        item_id = adjudication["item_id"]
        require(item_id in classification_by_id, f"classification target missing: {item_id}")
        require(item_id in assignments, f"manifest target assignment missing: {item_id}")
        machine = classification_by_id[item_id]
        cycle, assignment = assignments[item_id]
        require_equal(machine.get("chapter"), adjudication["chapter"], f"{item_id} classification chapter")
        require_equal(machine.get("section"), adjudication["section"], f"{item_id} classification section")
        require_equal(machine.get("cycle_id"), adjudication["cycle_id"], f"{item_id} classification cycle")
        require_equal(machine.get("item_label"), adjudication["item_label"], f"{item_id} classification label")
        require_equal(machine.get("question_text_sha256"), adjudication["question_text_sha256"], f"{item_id} classification question SHA-256")
        require_equal(cycle.get("id"), adjudication["cycle_id"], f"{item_id} manifest cycle")
        require_equal(assignment.get("item_label"), adjudication["item_label"], f"{item_id} manifest label")
        require_equal(assignment.get("question_text_sha256"), adjudication["question_text_sha256"], f"{item_id} manifest question SHA-256")
        require(adjudication["section"] in sections, f"manifest section missing: {adjudication['section']}")
        packet_item(root, adjudication)
        validate_answer_evidence(root, adjudication)

        semantic = machine.get("semantic_review") or {}
        require_equal(semantic.get("review_path"), adjudication["expected_semantic_review_path"], f"{item_id} semantic-review path")
        require_equal(semantic.get("original_review_status"), adjudication["expected_original_review_status"], f"{item_id} original review status")
        require_equal(semantic.get("reviewed_primary_type"), adjudication["reviewed_primary_type"], f"{item_id} semantic-review primary type")
        require_equal(list(semantic.get("secondary_types", [])), adjudication["secondary_types"], f"{item_id} semantic-review secondary types")
        require_equal(semantic.get("question_text_sha256"), adjudication["question_text_sha256"], f"{item_id} semantic-review question SHA-256")

        report_row = review_rows[item_id]
        require_equal(report_row.get("section"), adjudication["section"], f"{item_id} review-report section")
        require_equal(report_row.get("item_label"), adjudication["item_label"], f"{item_id} review-report label")
        require_equal(report_row.get("review_status"), adjudication["expected_original_review_status"], f"{item_id} review-report status")
        require_equal(report_row.get("reviewed_primary_type"), adjudication["reviewed_primary_type"], f"{item_id} review-report primary type")
        require_equal(list(report_row.get("secondary_types", [])), adjudication["secondary_types"], f"{item_id} review-report secondary types")

        if not applied:
            require_equal(machine.get("review_status"), adjudication["expected_original_blocked_status"], f"{item_id} original classification block")
            require_equal(assignment.get("review_status"), adjudication["expected_original_blocked_status"], f"{item_id} original manifest block")
            require_equal(machine.get("proposed_type_title"), adjudication["reviewed_primary_type"], f"{item_id} classification proposal")
            require_equal(list(machine.get("proposed_secondary_types", [])), adjudication["secondary_types"], f"{item_id} classification secondary proposals")
            require_equal(assignment.get("proposed_type_title"), adjudication["reviewed_primary_type"], f"{item_id} manifest proposal")
            require_equal(list(assignment.get("proposed_secondary_types", [])), adjudication["secondary_types"], f"{item_id} manifest secondary proposals")
        else:
            require_equal(machine.get("review_status"), ADJUDICATED_STATUS, f"{item_id} adjudicated classification status")
            require_equal(assignment.get("review_status"), ADJUDICATED_STATUS, f"{item_id} adjudicated manifest status")
            require_equal(machine.get("type_title"), adjudication["reviewed_primary_type"], f"{item_id} adjudicated classification primary")
            require_equal(list(machine.get("secondary_types", [])), adjudication["secondary_types"], f"{item_id} adjudicated classification secondary")
            require_equal(assignment.get("type_title"), adjudication["reviewed_primary_type"], f"{item_id} adjudicated manifest primary")
            require_equal(list(assignment.get("secondary_types", [])), adjudication["secondary_types"], f"{item_id} adjudicated manifest secondary")
            overlay = machine.get("controller_adjudication") or {}
            require_equal(overlay.get("adjudication_id"), adjudication["adjudication_id"], f"{item_id} adjudication id")
            require_equal(overlay.get("source_path"), ADJUDICATION_PATH.as_posix(), f"{item_id} adjudication source")
            require_equal(overlay.get("source_sha256"), adjudication_path_sha256, f"{item_id} adjudication source SHA-256")
            require_equal(overlay.get("prior_review_status"), adjudication["expected_original_blocked_status"], f"{item_id} prior status audit")
            require_equal((overlay.get("answer_evidence") or {}).get("page_image_sha256"), adjudication["answer_evidence"]["page_image_sha256"], f"{item_id} page-image audit SHA-256")
            require("proposed_type_title" not in machine and "blocking_reason" not in machine, f"{item_id} stale classification block fields")
            require("proposed_type_title" not in assignment and "blocking_reason" not in assignment, f"{item_id} stale manifest block fields")


def assignment_type_refs(cycle: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for assignment in cycle.get("item_type_assignments", []):
        if not is_accepted(assignment.get("review_status")):
            continue
        refs.extend([str(assignment.get("type_title") or "")])
        refs.extend(str(value) for value in assignment.get("secondary_types", []))
    return unique(refs)


def blocked_assignment_records(cycle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "item_id": assignment["item_id"],
            "item_label": assignment["item_label"],
            "status": assignment["review_status"],
            "reason": assignment.get("blocking_reason") or assignment.get("review_reason") or "",
        }
        for assignment in cycle.get("item_type_assignments", [])
        if is_blocked(assignment.get("review_status"))
    ]


def refresh_section(section: dict[str, Any]) -> None:
    blocked: list[dict[str, Any]] = []
    for cycle in section.get("learning_cycles", []):
        if not cycle.get("item_type_assignments"):
            continue
        cycle_blocked = blocked_assignment_records(cycle)
        cycle["type_refs"] = assignment_type_refs(cycle)
        cycle["type_mapping_status"] = expected_overall_status(len(cycle_blocked))
        if cycle_blocked:
            cycle["blocked_item_type_assignments"] = cycle_blocked
            blocked.extend(cycle_blocked)
        else:
            cycle.pop("blocked_item_type_assignments", None)
    section["item_type_review_status"] = expected_overall_status(len(blocked))
    section["blocked_item_type_reviews"] = blocked


def current_counts(classification: dict[str, Any]) -> tuple[int, int, Counter[str]]:
    statuses = Counter(str(row.get("review_status") or "") for row in classification.get("rows", []))
    accepted = sum(count for status, count in statuses.items() if is_accepted(status))
    blocked = sum(count for status, count in statuses.items() if is_blocked(status))
    return accepted, blocked, statuses


def adjust_historical_summary(summary: dict[str, Any], extension_delta: int) -> None:
    counts = dict(summary.get("review_status_counts") or {})
    needs_manual = int(counts.get("needs_manual_review") or 0)
    require(needs_manual >= 2, "semantic-review summary has fewer than two manual blocks")
    counts["needs_manual_review"] = needs_manual - 2
    if counts["needs_manual_review"] == 0:
        counts.pop("needs_manual_review")
    counts["controller_adjudicated"] = int(counts.get("controller_adjudicated") or 0) + 2
    summary["review_status_counts"] = dict(sorted(counts.items()))
    summary["accepted"] = int(summary.get("accepted") or 0) + 2
    summary["blocked"] = int(summary.get("blocked") or 0) - 2
    summary["taxonomy_extensions"] = int(summary.get("taxonomy_extensions") or 0) + extension_delta
    summary["controller_adjudicated"] = 2


def refresh_coverage_summary(summary: dict[str, Any], classification: dict[str, Any]) -> None:
    rows = classification.get("rows", [])
    summary["items"] = len(rows)
    summary["sections"] = len({str(row.get("section") or "") for row in rows})
    summary["cycles"] = len({str(row.get("cycle_id") or "") for row in rows})


def apply_adjudications(
    classification: dict[str, Any],
    manifest: dict[str, Any],
    classification_report: dict[str, Any],
    application_report: dict[str, Any],
    payload: dict[str, Any],
    adjudications: list[dict[str, Any]],
    adjudication_path_sha256: str,
) -> None:
    applied_at = datetime.now(timezone.utc).isoformat()
    classification_by_id = classification_index(classification)
    sections, _, assignments = manifest_indexes(manifest)
    non_target_rows_before = {
        item_id: canonical(row)
        for item_id, row in classification_by_id.items()
        if item_id not in EXPECTED_ITEM_IDS
    }
    non_target_assignments_before = {
        item_id: canonical(assignment)
        for item_id, (_, assignment) in assignments.items()
        if item_id not in EXPECTED_ITEM_IDS
    }
    other_blocked_before = [
        copy.deepcopy(item)
        for item in application_report.get("blocked_items", [])
        if item.get("item_id") not in EXPECTED_ITEM_IDS
    ]
    extension_delta = 0
    extension_records: list[dict[str, Any]] = []

    for adjudication in adjudications:
        item_id = adjudication["item_id"]
        machine = classification_by_id[item_id]
        _, assignment = assignments[item_id]
        section = sections[adjudication["section"]]
        evidence = adjudication["answer_evidence"]
        overlay = {
            "adjudication_id": adjudication["adjudication_id"],
            "source_path": ADJUDICATION_PATH.as_posix(),
            "source_sha256": adjudication_path_sha256,
            "applied_at": applied_at,
            "prior_review_status": adjudication["expected_original_blocked_status"],
            "prior_type_title": machine.get("type_title"),
            "prior_blocking_reason": machine.get("blocking_reason"),
            "semantic_review_path": (machine.get("semantic_review") or {}).get("review_path"),
            "semantic_review_sha256": (machine.get("semantic_review") or {}).get("review_sha256"),
            "question_text_sha256": adjudication["question_text_sha256"],
            "answer_evidence": {
                "sidecar_path": evidence["sidecar_path"],
                "source_pdf_sha256": evidence["source_pdf_sha256"],
                "pdf_page": evidence["pdf_page"],
                "page_image_sha256": evidence["page_image_sha256"],
            },
            "reason": adjudication["reason"],
        }
        machine["type_title"] = adjudication["reviewed_primary_type"]
        machine["secondary_types"] = adjudication["secondary_types"]
        machine["classification_method"] = "controller_adjudication_after_multi_agent_semantic_review"
        machine["review_status"] = ADJUDICATED_STATUS
        machine["controller_adjudication"] = copy.deepcopy(overlay)
        for field in ("proposed_type_title", "proposed_secondary_types", "blocking_reason"):
            machine.pop(field, None)

        assignment["type_title"] = adjudication["reviewed_primary_type"]
        assignment["secondary_types"] = adjudication["secondary_types"]
        assignment["review_status"] = ADJUDICATED_STATUS
        assignment["adjudication_ref"] = f"{ADJUDICATION_PATH.as_posix()}#{adjudication['adjudication_id']}"
        assignment["adjudication_reason"] = adjudication["reason"]
        assignment["answer_page_image_sha256"] = evidence["page_image_sha256"]
        for field in ("proposed_type_title", "proposed_secondary_types", "blocking_reason"):
            assignment.pop(field, None)

        type_labels = list(section.get("type_labels", []))
        for position, type_title in enumerate([adjudication["reviewed_primary_type"], *adjudication["secondary_types"]]):
            if type_title in type_labels:
                continue
            type_labels.append(type_title)
            extension = {
                "chapter": adjudication["chapter"],
                "section": adjudication["section"],
                "type_title": type_title,
                "introduced_by_item_id": item_id,
                "introduced_by_item_label": adjudication["item_label"],
                "role": "primary" if position == 0 else "secondary",
                "adjudication_ref": f"{ADJUDICATION_PATH.as_posix()}#{adjudication['adjudication_id']}",
            }
            section.setdefault("semantic_type_taxonomy_extensions", []).append(copy.deepcopy(extension))
            extension_records.append(extension)
            extension_delta += 1
        section["type_labels"] = type_labels

    for section_id in {row["section"] for row in adjudications}:
        refresh_section(sections[section_id])

    accepted, blocked, _ = current_counts(classification)
    classification["status"] = expected_overall_status(blocked)
    adjust_historical_summary(classification["semantic_review_summary"], extension_delta)
    refresh_coverage_summary(classification["semantic_review_summary"], classification)
    require_equal(classification["semantic_review_summary"]["accepted"], accepted, "classification accepted summary after adjudication")
    require_equal(classification["semantic_review_summary"]["blocked"], blocked, "classification blocked summary after adjudication")
    classification["controller_adjudication_applied_at"] = applied_at
    classification["controller_adjudication_sources"] = [{"path": ADJUDICATION_PATH.as_posix(), "sha256": adjudication_path_sha256}]
    classification["controller_adjudication_summary"] = {
        "adjudicated": 2,
        "remaining_blocked": blocked,
        "source_defects_resolved": 0,
        "mastery_claimed": False,
    }

    classification_report["status"] = expected_overall_status(blocked)
    adjust_historical_summary(classification_report["semantic_review"], extension_delta)
    refresh_coverage_summary(classification_report["semantic_review"], classification)
    classification_report["blocked_items"] = [
        item for item in classification_report.get("blocked_items", [])
        if item.get("item_id") not in EXPECTED_ITEM_IDS
    ]
    classification_report["controller_adjudication_applied_at"] = applied_at
    classification_report["controller_adjudication"] = classification["controller_adjudication_summary"]
    classification_report["controller_adjudication_source"] = {
        "path": ADJUDICATION_PATH.as_posix(),
        "sha256": adjudication_path_sha256,
    }

    application_report["status"] = expected_overall_status(blocked)
    adjust_historical_summary(application_report["summary"], extension_delta)
    refresh_coverage_summary(application_report["summary"], classification)
    application_report["blocked_items"] = [
        item for item in application_report.get("blocked_items", [])
        if item.get("item_id") not in EXPECTED_ITEM_IDS
    ]
    application_report.setdefault("taxonomy_extensions", []).extend(copy.deepcopy(extension_records))
    application_report["controller_adjudication_applied_at"] = applied_at
    application_report["controller_adjudication_source"] = {
        "path": ADJUDICATION_PATH.as_posix(),
        "sha256": adjudication_path_sha256,
    }
    application_report["controller_adjudications"] = [
        {
            "adjudication_id": row["adjudication_id"],
            "chapter": row["chapter"],
            "section": row["section"],
            "cycle_id": row["cycle_id"],
            "item_id": row["item_id"],
            "item_label": row["item_label"],
            "status": ADJUDICATED_STATUS,
            "reviewed_primary_type": row["reviewed_primary_type"],
            "secondary_types": row["secondary_types"],
            "question_text_sha256": row["question_text_sha256"],
            "answer_page_image_sha256": row["answer_evidence"]["page_image_sha256"],
        }
        for row in adjudications
    ]
    application_report.setdefault("boundaries", {})["source_defects_resolved_by_controller"] = 0
    application_report["boundaries"]["learner_mastery_claimed"] = False

    chapter_rows = [row for row in classification.get("rows", []) if row.get("chapter") == 2]
    chapter_blocked = [row for row in chapter_rows if is_blocked(row.get("review_status"))]
    chapter_summary = manifest.get("item_type_semantic_review") or {}
    chapter_summary.update({
        "status": expected_overall_status(len(chapter_blocked)),
        "items": len(chapter_rows),
        "accepted": len(chapter_rows) - len(chapter_blocked),
        "blocked": len(chapter_blocked),
        "controller_adjudicated": 2,
        "controller_adjudication_applied_at": applied_at,
        "controller_adjudication_source": {
            "path": ADJUDICATION_PATH.as_posix(),
            "sha256": adjudication_path_sha256,
        },
        "mastery_claimed": False,
    })
    manifest["item_type_semantic_review"] = chapter_summary

    non_target_rows_after = {
        item_id: canonical(row)
        for item_id, row in classification_by_id.items()
        if item_id not in EXPECTED_ITEM_IDS
    }
    non_target_assignments_after = {
        item_id: canonical(assignment)
        for item_id, (_, assignment) in assignments.items()
        if item_id not in EXPECTED_ITEM_IDS
    }
    require_equal(non_target_rows_after, non_target_rows_before, "non-target classification rows changed")
    require_equal(non_target_assignments_after, non_target_assignments_before, "non-target manifest assignments changed")
    require_equal(
        [item for item in application_report.get("blocked_items", [])],
        other_blocked_before,
        "non-target application blocked records changed",
    )


def validate_summaries(
    classification: dict[str, Any],
    manifest: dict[str, Any],
    classification_report: dict[str, Any],
    application_report: dict[str, Any],
    adjudication_path_sha256: str,
) -> dict[str, Any]:
    classification_by_id = classification_index(classification)
    sections, cycles, assignments = manifest_indexes(manifest)
    accepted, blocked, statuses = current_counts(classification)
    expected_items = len(classification.get("rows", []))
    expected_sections = len({str(row.get("section") or "") for row in classification.get("rows", [])})
    expected_cycles = len({str(row.get("cycle_id") or "") for row in classification.get("rows", [])})
    require_equal(sum(statuses.values()), int(classification.get("items") or 0), "classification status coverage")
    require_equal(statuses.get(ADJUDICATED_STATUS, 0), 2, "controller-adjudicated item count")
    require_equal(classification.get("status"), expected_overall_status(blocked), "classification top status")
    require_equal((classification.get("semantic_review_summary") or {}).get("accepted"), accepted, "classification accepted summary")
    require_equal((classification.get("semantic_review_summary") or {}).get("blocked"), blocked, "classification blocked summary")
    require_equal((classification.get("semantic_review_summary") or {}).get("controller_adjudicated"), 2, "classification adjudication summary")
    require_equal((classification.get("semantic_review_summary") or {}).get("items"), expected_items, "classification item coverage")
    require_equal((classification.get("semantic_review_summary") or {}).get("sections"), expected_sections, "classification section coverage")
    require_equal((classification.get("semantic_review_summary") or {}).get("cycles"), expected_cycles, "classification cycle coverage")
    require_equal((classification.get("controller_adjudication_summary") or {}).get("adjudicated"), 2, "classification controller count")
    require_equal((classification.get("controller_adjudication_summary") or {}).get("remaining_blocked"), blocked, "classification remaining blocked")
    require_equal((classification.get("controller_adjudication_summary") or {}).get("mastery_claimed"), False, "classification mastery boundary")
    source = (classification.get("controller_adjudication_sources") or [{}])[0]
    require_equal(source.get("path"), ADJUDICATION_PATH.as_posix(), "classification adjudication source")
    require_equal(source.get("sha256"), adjudication_path_sha256, "classification adjudication source SHA-256")

    for report_name, report, summary_key in (
        ("classification report", classification_report, "semantic_review"),
        ("application report", application_report, "summary"),
    ):
        summary = report.get(summary_key) or {}
        require_equal(report.get("status"), expected_overall_status(blocked), f"{report_name} status")
        require_equal(summary.get("accepted"), accepted, f"{report_name} accepted")
        require_equal(summary.get("blocked"), blocked, f"{report_name} blocked")
        require_equal(summary.get("controller_adjudicated"), 2, f"{report_name} adjudicated")
        require_equal(summary.get("items"), expected_items, f"{report_name} item coverage")
        require_equal(summary.get("sections"), expected_sections, f"{report_name} section coverage")
        require_equal(summary.get("cycles"), expected_cycles, f"{report_name} cycle coverage")
        blocked_ids = {str(row.get("item_id") or "") for row in report.get("blocked_items", [])}
        require_equal(blocked_ids, {item_id for item_id, row in classification_by_id.items() if is_blocked(row.get("review_status"))}, f"{report_name} blocked ids")
        require(EXPECTED_ITEM_IDS.isdisjoint(blocked_ids), f"{report_name} still declares adjudicated targets blocked")
        require(NON_TARGET_MANUAL_ITEM_ID not in EXPECTED_ITEM_IDS, "2.5 B13 leaked into adjudication scope")

    chapter_rows = [row for row in classification.get("rows", []) if row.get("chapter") == 2]
    chapter_blocked = sum(is_blocked(row.get("review_status")) for row in chapter_rows)
    chapter_summary = manifest.get("item_type_semantic_review") or {}
    require_equal(chapter_summary.get("items"), len(chapter_rows), "chapter2 summary items")
    require_equal(chapter_summary.get("accepted"), len(chapter_rows) - chapter_blocked, "chapter2 summary accepted")
    require_equal(chapter_summary.get("blocked"), chapter_blocked, "chapter2 summary blocked")
    require_equal(chapter_summary.get("status"), expected_overall_status(chapter_blocked), "chapter2 summary status")
    require_equal(chapter_summary.get("controller_adjudicated"), 2, "chapter2 adjudicated summary")
    require_equal(chapter_summary.get("mastery_claimed"), False, "chapter2 mastery boundary")

    for section_id in {"2.1", "2.6"}:
        section = sections[section_id]
        section_blocked = [
            assignment
            for cycle in section.get("learning_cycles", [])
            for assignment in cycle.get("item_type_assignments", [])
            if is_blocked(assignment.get("review_status"))
        ]
        require_equal(section.get("item_type_review_status"), expected_overall_status(len(section_blocked)), f"{section_id} section status")
        declared = {str(row.get("item_id") or "") for row in section.get("blocked_item_type_reviews", [])}
        require_equal(declared, {str(row.get("item_id") or "") for row in section_blocked}, f"{section_id} section blocked ids")

    for cycle_id in {"2.1-cycle-11", "2.6-cycle-11"}:
        cycle = cycles[cycle_id]
        blocked_in_cycle = blocked_assignment_records(cycle)
        require_equal(cycle.get("type_refs"), assignment_type_refs(cycle), f"{cycle_id} type refs")
        require_equal(cycle.get("type_mapping_status"), expected_overall_status(len(blocked_in_cycle)), f"{cycle_id} status")
        declared = {str(row.get("item_id") or "") for row in cycle.get("blocked_item_type_assignments", [])}
        require_equal(declared, {str(row.get("item_id") or "") for row in blocked_in_cycle}, f"{cycle_id} blocked ids")

    for item_id in EXPECTED_ITEM_IDS:
        _, assignment = assignments[item_id]
        section = sections[classification_by_id[item_id]["section"]]
        for type_title in [assignment["type_title"], *assignment.get("secondary_types", [])]:
            require(type_title in section.get("type_labels", []), f"{item_id} adjudicated type absent from section taxonomy: {type_title}")
    app_ids = {str(row.get("item_id") or "") for row in application_report.get("controller_adjudications", [])}
    require_equal(app_ids, EXPECTED_ITEM_IDS, "application controller-adjudication ids")
    require_equal((application_report.get("boundaries") or {}).get("source_defects_resolved_by_controller"), 0, "source-defect resolution boundary")
    require_equal((application_report.get("boundaries") or {}).get("learner_mastery_claimed"), False, "application mastery boundary")
    non_target_manual = classification_by_id.get(NON_TARGET_MANUAL_ITEM_ID) or {}
    non_target_overlay = non_target_manual.get("controller_adjudication") or {}
    require(
        non_target_overlay.get("source_path") != ADJUDICATION_PATH.as_posix(),
        "2.5 B13 was modified by the controller-adjudication overlay",
    )
    return {
        "status": "passed",
        "adjudicated": 2,
        "accepted": accepted,
        "remaining_blocked": blocked,
        "touched_2_5_B13": False,
        "source_defects_resolved": 0,
        "mastery_claimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--check", action="store_true", help="validate the applied adjudication overlay")
    parser.add_argument("--dry-run", action="store_true", help="validate the prior state without writing")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    payload, adjudications, adjudication_path_sha256 = load_contract(root)
    classification = load_json(root / CLASSIFICATION_PATH)
    manifest = load_json(root / MANIFEST_PATH)
    classification_report = load_json(root / CLASSIFICATION_REPORT_PATH)
    application_report = load_json(root / APPLICATION_REPORT_PATH)
    classification_by_id = classification_index(classification)
    sections, _, assignments = manifest_indexes(manifest)
    applied = all_targets_applied(classification_by_id)

    if not applied:
        require(not args.check, "controller adjudications have not been applied")
    review_rows = relevant_review_rows(root, payload, strict_current_hashes=not applied)
    validate_row_bindings(
        root,
        adjudications,
        classification_by_id,
        sections,
        assignments,
        review_rows,
        applied,
        adjudication_path_sha256,
    )

    if applied:
        result = validate_summaries(
            classification,
            manifest,
            classification_report,
            application_report,
            adjudication_path_sha256,
        )
        result["mode"] = "check"
        result["already_applied"] = True
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.dry_run:
        print(json.dumps({
            "status": "passed",
            "mode": "dry-run",
            "adjudications": 2,
            "writes": 0,
            "answer_page_images_verified": 2,
        }, ensure_ascii=False))
        return 0

    apply_adjudications(
        classification,
        manifest,
        classification_report,
        application_report,
        payload,
        adjudications,
        adjudication_path_sha256,
    )
    # Validate all derived summaries before the first write.
    result = validate_summaries(
        classification,
        manifest,
        classification_report,
        application_report,
        adjudication_path_sha256,
    )
    save_json(root / CLASSIFICATION_PATH, classification)
    save_json(root / MANIFEST_PATH, manifest)
    save_json(root / CLASSIFICATION_REPORT_PATH, classification_report)
    save_json(root / APPLICATION_REPORT_PATH, application_report)
    result["mode"] = "apply"
    result["report"] = APPLICATION_REPORT_PATH.as_posix()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as error:
        print(json.dumps({"status": "contract_error", "error": str(error)}, ensure_ascii=False))
        raise SystemExit(1)
