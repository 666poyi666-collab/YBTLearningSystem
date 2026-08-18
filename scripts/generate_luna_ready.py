#!/usr/bin/env python3
"""Generate the fail-closed source snapshot consumed by Luna section tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ybt_learning.vision import GLM_VISION_MODEL, structured_answer_leaks  # noqa: E402


FORMULA_ANCHORS = (
    ("ch3.s1", 0),
    ("ch3.s5", 88),
    ("4.4", 53),
    ("4.5", 73),
    ("5.5", 67),
)
REQUIRED_ARRAY_FIELDS = (
    "objects",
    "relations",
    "coordinates",
    "ranges",
    "text",
    "uncertainties",
)
ANSWER_LEAK_RE = re.compile(
    r"答案\s*[：:]|解法\s*[一二两12]?\s*[：:]|解析\s*[：:]|解答\s*[：:]|"
    r"最终答案|故答案|故\s*[A-D]\s*项(?:正确|错误)|正确选项|故选\s*[A-D]",
    re.I,
)


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


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def _meaningful(structured: dict[str, Any]) -> bool:
    return any(
        structured.get(field) not in (None, "", [], {})
        for field in REQUIRED_ARRAY_FIELDS[:-1]
    )


def _validate_assignment_coverage(
    assignments: dict[str, Any],
    report_sections: set[str],
    errors: list[str],
) -> None:
    tasks = assignments.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 10:
        errors.append("assignment_task_count_not_10")
        return
    assigned: list[str] = []
    expected_item_sum = 0
    for task in tasks:
        if not isinstance(task, dict):
            errors.append("assignment_task_not_object")
            continue
        sections = task.get("sections")
        if not isinstance(sections, list) or not sections:
            errors.append(f"{task.get('task_id')}:sections_missing")
            continue
        assigned.extend(str(section) for section in sections)
        expected_item_sum += int(task.get("expected_items", 0))
    duplicates = sorted({section for section in assigned if assigned.count(section) > 1})
    if duplicates:
        errors.append(f"duplicate_assigned_sections:{duplicates}")
    if set(assigned) != report_sections:
        errors.append(
            "assignment_section_set_mismatch:"
            f"missing={sorted(report_sections - set(assigned))},"
            f"unexpected={sorted(set(assigned) - report_sections)}"
        )
    if expected_item_sum != 1209:
        errors.append(f"assignment_item_sum:{expected_item_sum}")


def _validate_course_catalog(catalog: dict[str, Any], errors: list[str]) -> None:
    if catalog.get("status") != "passed":
        errors.append("course_catalog_not_passed")
    allowed_root = (Path.home() / "Downloads" / "课程合集").resolve()
    for row in catalog.get("courses", []):
        if not isinstance(row, dict):
            errors.append("course_row_not_object")
            continue
        for field, hash_field in (
            ("video_file", "video_sha256"),
            ("transcript_file", "transcript_sha256"),
        ):
            path = Path(str(row.get(field) or ""))
            if not path.is_file():
                errors.append(f"course_source_missing:{path}")
                continue
            if field == "video_file" and not path.resolve().is_relative_to(allowed_root):
                errors.append(f"course_source_outside_allowed_root:{path}")
            if sha256_file(path) != row.get(hash_field):
                errors.append(f"course_source_hash_mismatch:{path}")


def _validate_visual_sidecar(
    sidecar: dict[str, Any],
    root: Path,
    source_inventory_path: Path,
    source_inventory_sha256: str,
    expected_target_count: int,
    errors: list[str],
) -> dict[str, Any]:
    target_count = int(sidecar.get("target_count", -1))
    passed_count = int(sidecar.get("passed_count", -1))
    results = sidecar.get("results")
    if sidecar.get("status") != "passed":
        errors.append("visual_sidecar_not_passed")
    if target_count != expected_target_count or passed_count != target_count:
        errors.append(
            f"visual_count_gate:{passed_count}/{target_count}:expected={expected_target_count}"
        )
    if not isinstance(results, list) or len(results) != target_count:
        errors.append("visual_result_count_mismatch")
        return {"target_count": target_count, "passed_count": passed_count}
    inventory_path = Path(str(sidecar.get("inventory_path") or ""))
    if not inventory_path.is_absolute():
        inventory_path = root / inventory_path
    if not inventory_path.is_file():
        errors.append(f"visual_source_inventory_missing:{inventory_path}")
    else:
        if inventory_path.resolve() != source_inventory_path.resolve():
            errors.append("visual_source_inventory_path_mismatch")
        if sha256_file(inventory_path) != sidecar.get("inventory_sha256"):
            errors.append("visual_source_inventory_hash_mismatch")
    if sidecar.get("inventory_sha256") != source_inventory_sha256:
        errors.append("visual_source_inventory_not_frozen_snapshot")
    keys: set[tuple[str, str]] = set()
    for index, row in enumerate(results):
        if not isinstance(row, dict):
            errors.append(f"visual_row_not_object:{index}")
            continue
        key = str(row.get("question_hint") or ""), str(row.get("image_sha256") or "")
        if key in keys:
            errors.append(f"visual_duplicate:{key}")
        keys.add(key)
        if row.get("status") != "passed":
            errors.append(f"visual_row_not_passed:{index}")
        if row.get("model") != GLM_VISION_MODEL:
            errors.append(f"visual_model_mismatch:{index}")
        if row.get("confidence") not in {"E1", "E2"}:
            errors.append(f"visual_confidence_not_release_grade:{index}")
        image = Path(str(row.get("image") or ""))
        if not image.is_file() or sha256_file(image) != row.get("image_sha256"):
            errors.append(f"visual_image_hash_mismatch:{index}")
        structured = row.get("structured")
        if not isinstance(structured, dict):
            errors.append(f"visual_structure_missing:{index}")
            continue
        if any(
            not isinstance(structured.get(field), list)
            or len(structured[field]) > 8
            for field in REQUIRED_ARRAY_FIELDS
        ):
            errors.append(f"visual_structure_shape_invalid:{index}")
        if not _meaningful(structured):
            errors.append(f"visual_structure_empty:{index}")
        if structured_answer_leaks(structured):
            errors.append(f"visual_answer_language:{index}")
    return {"target_count": target_count, "passed_count": passed_count}


def _validate_visual_source_inventory(
    inventory: dict[str, Any],
    errors: list[str],
) -> int:
    rows = inventory.get("items")
    if not isinstance(rows, list):
        errors.append("visual_source_inventory_items_missing")
        return -1
    item_count = int(inventory.get("item_image_count", -1))
    unique_count = int(inventory.get("unique_image_count", -1))
    missing_count = int(inventory.get("missing_image_count", -1))
    actual_unique = len({str(row.get("image") or "") for row in rows if isinstance(row, dict)})
    if item_count != len(rows):
        errors.append(f"visual_source_inventory_item_count:{item_count}/{len(rows)}")
    if unique_count != actual_unique or unique_count != item_count:
        errors.append(
            f"visual_source_inventory_unique_count:{unique_count}/{actual_unique}/{item_count}"
        )
    if missing_count != 0:
        errors.append(f"visual_source_inventory_missing_images:{missing_count}")
    if item_count <= 0:
        errors.append(f"visual_source_inventory_empty:{item_count}")
    return item_count


def _validate_formula_anchors(
    section_bindings: dict[str, dict[str, Any]],
    errors: list[str],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for section_id, ocr_doc in FORMULA_ANCHORS:
        binding = section_bindings.get(section_id)
        if binding is None:
            errors.append(f"formula_section_missing:{section_id}")
            continue
        packet = load_json(Path(binding["packet_path"]))
        page = next(
            (item for item in packet.get("pages", []) if item.get("ocr_doc") == ocr_doc),
            None,
        )
        if page is None:
            errors.append(f"formula_page_missing:{section_id}:doc_{ocr_doc}")
            continue
        math_errors = page.get("math_errors") or []
        if math_errors:
            errors.append(f"formula_errors_remain:{section_id}:doc_{ocr_doc}:{math_errors}")
        evidence.append(
            {
                "section": section_id,
                "ocr_doc": ocr_doc,
                "math_errors": math_errors,
            }
        )
    return evidence


def _validate_answer_isolation(
    section_id: str,
    folder: Path,
    learning: dict[str, Any],
    errors: list[str],
) -> None:
    learner_facing_learning = {
        "knowledge_and_type_pages": learning.get("knowledge_and_type_pages", []),
        "direct_variants": learning.get("direct_variants", []),
        "exercise_questions": learning.get("exercise_questions", []),
    }
    if ANSWER_LEAK_RE.search(json.dumps(learner_facing_learning, ensure_ascii=False)):
        errors.append(f"learning_packet_answer_leak:{section_id}")
    for filename in ("student_packet.json", "student_learning_items.json"):
        path = folder / filename
        if not path.is_file():
            errors.append(f"student_artifact_missing:{section_id}:{filename}")
            continue
        value = load_json(path)
        serialized = json.dumps(value, ensure_ascii=False)
        if ANSWER_LEAK_RE.search(serialized):
            errors.append(f"student_artifact_answer_leak:{section_id}:{filename}")
        if filename == "student_packet.json" and value.get("answer_sidecar") is not None:
            errors.append(f"student_packet_answer_sidecar_present:{section_id}")


def build_ready(root: Path) -> tuple[dict[str, Any], list[str]]:
    assignments_path = root / "reports" / "luna_dispatch" / "assignments.json"
    report_path = root / "reports" / "all_chapters" / "packet-build-current.json"
    catalog_path = root / "data" / "all_chapters_course_catalog.json"
    visual_path = root / "data" / "vision_sidecar_all_chapters.json"
    visual_source_inventory_path = (
        root
        / "reports"
        / "all_chapters"
        / "visual-inventory-source-question-only.json"
    )
    residual_inventory_path = root / "reports" / "all_chapters" / "visual-inventory-current.json"
    required_paths = (
        assignments_path,
        report_path,
        catalog_path,
        visual_path,
        visual_source_inventory_path,
        residual_inventory_path,
    )
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        return {}, [f"required_file_missing:{path}" for path in missing]

    assignments = load_json(assignments_path)
    report = load_json(report_path)
    catalog = load_json(catalog_path)
    visual = load_json(visual_path)
    visual_source_inventory = load_json(visual_source_inventory_path)
    residual = load_json(residual_inventory_path)
    errors: list[str] = []

    expected = assignments.get("expected") or {}
    if report.get("status") != "passed":
        errors.append(f"packet_build_status:{report.get('status')}")
    if report.get("expected") != expected or report.get("actual") != {
        key: expected.get(key)
        for key in (
            "worked_examples",
            "direct_variants",
            "abc_exercises",
            "total_numbered_learning_items",
        )
    }:
        errors.append("packet_build_totals_mismatch")
    report_rows = report.get("sections")
    if not isinstance(report_rows, list) or len(report_rows) != 38:
        errors.append("packet_build_section_count_not_38")
        report_rows = []
    report_section_ids = {str(row.get("section")) for row in report_rows if isinstance(row, dict)}
    _validate_assignment_coverage(assignments, report_section_ids, errors)
    _validate_course_catalog(catalog, errors)
    visual_source_inventory_sha256 = sha256_file(visual_source_inventory_path)
    visual_target_count = _validate_visual_source_inventory(visual_source_inventory, errors)
    visual_gate = _validate_visual_sidecar(
        visual,
        root,
        visual_source_inventory_path,
        visual_source_inventory_sha256,
        visual_target_count,
        errors,
    )
    if residual.get("status") != "passed" or any(
        int(residual.get(field, -1)) != 0
        for field in ("item_image_count", "unique_image_count", "missing_image_count")
    ):
        errors.append("post_build_visual_inventory_not_zero")

    section_bindings: dict[str, dict[str, Any]] = {}
    for row in report_rows:
        section_id = str(row.get("section") or "")
        folder = root / "data" / "packets" / section_folder(section_id)
        packet_path = folder / "packet.json"
        learning_path = folder / "learning_packet.json"
        if not packet_path.is_file() or not learning_path.is_file():
            errors.append(f"section_packet_missing:{section_id}")
            continue
        packet_sha = sha256_file(packet_path)
        learning_sha = sha256_file(learning_path)
        if row.get("packet_sha256") != packet_sha:
            errors.append(f"packet_hash_mismatch:{section_id}")
        if row.get("learning_packet_sha256") != learning_sha:
            errors.append(f"learning_packet_hash_mismatch:{section_id}")
        if row.get("packet_status") != "VERIFIED" or row.get("learning_status") != "VERIFIED":
            errors.append(f"section_not_verified:{section_id}")
        learning = load_json(learning_path)
        _validate_answer_isolation(section_id, folder, learning, errors)
        section_bindings[section_id] = {
            "chapter": row.get("chapter"),
            "packet_path": str(packet_path),
            "packet_sha256": packet_sha,
            "learning_packet_path": str(learning_path),
            "learning_packet_sha256": learning_sha,
            "counts": row.get("counts"),
        }
    formula_gate = _validate_formula_anchors(section_bindings, errors)

    payload = {
        "schema_version": "ybt-luna-ready-v1",
        "status": "ready" if not errors else "blocked",
        "requirement_id": assignments.get("requirement_id"),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "expected": expected,
        "source_binding": {
            "assignments_path": str(assignments_path),
            "assignments_sha256": None,
            "packet_build_path": str(report_path),
            "packet_build_sha256": sha256_file(report_path),
            "course_catalog_path": str(catalog_path),
            "course_catalog_sha256": sha256_file(catalog_path),
            "vision_sidecar_path": str(visual_path),
            "vision_sidecar_sha256": sha256_file(visual_path),
            "visual_source_inventory_path": str(visual_source_inventory_path),
            "visual_source_inventory_sha256": visual_source_inventory_sha256,
        },
        "visual_gate": {
            **visual_gate,
            "post_build_unbound_items": int(residual.get("item_image_count", -1)),
        },
        "formula_gate": formula_gate,
        "sections": [section_bindings[key] for key in sorted(section_bindings)],
        "simulation_status": "not_run",
        "human_acceptance": "not_run",
        "cold_24h_retest": "not_run",
        "errors": errors,
    }
    return payload, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument(
        "--out",
        default=str(ROOT / "reports" / "luna_dispatch" / "READY.json"),
    )
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    output = Path(args.out)
    payload, errors = build_ready(root)
    if errors:
        print(json.dumps({"status": "blocked", "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    assignments_path = root / "reports" / "luna_dispatch" / "assignments.json"
    assignments = load_json(assignments_path)
    assignments["status"] = "ready"
    assignments["ready_generated_at"] = payload["generated_at"]
    atomic_write_json(assignments_path, assignments)
    payload["source_binding"]["assignments_sha256"] = sha256_file(assignments_path)
    atomic_write_json(output, payload)
    persisted = load_json(output)
    if persisted.get("status") != "ready" or persisted.get("errors"):
        raise RuntimeError("persisted READY failed its final state check")
    print(
        json.dumps(
            {
                "status": "ready",
                "ready": str(output),
                "ready_sha256": sha256_file(output),
                "sections": len(persisted["sections"]),
                "items": persisted["expected"]["total_numbered_learning_items"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
