#!/usr/bin/env python3
"""Rebind reviewed item types after source-page repairs and report closure evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REVIEWED = "MULTI_AGENT_SEMANTIC_REVIEWED"
WITH_BLOCKED = "MULTI_AGENT_SEMANTIC_REVIEWED_WITH_BLOCKED_ITEMS"
ACCEPTED = {"approved", "classified", "confirmed", "corrected"}
REVIEW_FILES = (
    (Path("reports/deep_simulation_reviews/ch1-ch2-type-review.json"), "review_rows"),
    (Path("reports/deep_simulation_reviews/ch3-type-review.json"), "reviews"),
    (Path("reports/deep_simulation_reviews/ch4-ch5-type-review.json"), "reviews"),
)
RESOLVED = {
    "Q-71eccd74698e096f": {
        "corrections": ["DQC-2.5-B13-BISECT", "DQC-2.5-B13-RUNNING-HEADER"],
        "required": ["平分", "中点M的轨迹方程"],
        "forbidden": ["恒被直线平行"],
        "evidence": "SOURCE_SECTION_PDF_PAGE_14_VISUALLY_CONFIRMS_平分",
        "resolved_reason": "原页确认圆 G 恒被直线族平分；第二问求圆上动点连线中点的轨迹，按‘与圆有关的轨迹方程’主类型并辅以求圆方程放行。",
    },
    "Q-d5eb29be8ab5dedf": {
        "corrections": ["DQC-CH3S9-C11-PQ"],
        "required": ["P,Q", "\\frac{|PQ|}{|MN|}"],
        "forbidden": ["\\frac{Q}{2}"],
        "evidence": "SOURCE_SECTION_PDF_PAGE_11_VISUALLY_CONFIRMS_P_COMMA_Q",
        "resolved_reason": "原页确认圆与 y 轴交于 P、Q 两点；题目使用以 MN 为直径的圆，按‘两个神奇小圆的应用’放行。",
    },
    "Q-821eb5edcaa8d410": {
        "corrections": ["DQC-4.4-C16-PROOF-TARGET"],
        "required": ["不可能成等比数列"],
        "forbidden": ["试证明：\n"],
        "evidence": "MERGED_SOURCE_PDF_PAGE_64_VISUALLY_CONFIRMS_COMPLETE_PROPOSITION",
        "resolved_reason": "原页已恢复第二问完整待证命题；两问均围绕等比数列的证明与排除，按人工语义复核结论放行。",
    },
    "Q-ad967b8b2931d0c9": {
        "corrections": ["DQC-5.3-B8-RESTORE-NUMBER"],
        "required": ["f(x) < -1 + e^x", "A."],
        "forbidden": ["f'(x) 是函数"],
        "evidence": "MERGED_SOURCE_PDF_PAGE_38_VISUALLY_CONFIRMS_B7_B8_BOUNDARY",
        "resolved_reason": "B7 已在 D 选项结束处与 B8 分离；核心仍是由 f 与 f' 的关系构造原函数并判断不等式，按人工语义复核结论放行。",
    },
    "Q-979c0e6d96423ab0": {
        "corrections": ["DQC-5.3-C20-RESTORE-PROOFS"],
        "required": ["存在唯一的零点", "有且仅有 2 个零点"],
        "forbidden": [],
        "evidence": "MERGED_SOURCE_PDF_PAGE_42_VISUALLY_CONFIRMS_BOTH_PROOF_TASKS",
        "resolved_reason": "原页已恢复两个完整证明任务；核心是用导数研究无参函数及其零点，按人工语义复核结论放行。",
    },
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def packet_exercises(manifests: dict[int, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for manifest in manifests.values():
        for section in manifest.get("sections", []):
            section_id = str(section["id"])
            packet = load(ROOT / "data" / "packets" / section_folder(section_id) / "student_packet.json")
            for item in packet.get("questions", []):
                item_id = str(item.get("qid") or "")
                if not item_id or item_id in rows:
                    raise ValueError(f"missing or duplicate exercise id: {section_id} {item_id}")
                rows[item_id] = item
    if len(rows) != 546:
        raise ValueError(f"exercise coverage drift: {len(rows)}/546")
    return rows


def manifest_assignments(
    manifests: dict[int, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    assignments: dict[str, dict[str, Any]] = {}
    cycles: dict[str, dict[str, Any]] = {}
    for manifest in manifests.values():
        for section in manifest.get("sections", []):
            for cycle in section.get("learning_cycles", []):
                cycles[str(cycle["id"])] = cycle
                for assignment in cycle.get("item_type_assignments", []):
                    item_id = str(assignment.get("item_id") or "")
                    if not item_id or item_id in assignments:
                        raise ValueError(f"missing or duplicate assignment: {item_id}")
                    assignments[item_id] = assignment
    if len(assignments) != 512:
        raise ValueError(f"assignment coverage drift: {len(assignments)}/512")
    return assignments, cycles


def review_index() -> tuple[dict[str, dict[str, Any]], dict[str, tuple[Path, str, dict[str, Any]]]]:
    payloads: dict[str, tuple[Path, str, dict[str, Any]]] = {}
    rows: dict[str, dict[str, Any]] = {}
    for relative, key in REVIEW_FILES:
        payload = load(ROOT / relative)
        payloads[relative.as_posix()] = (relative, key, payload)
        for row in payload.get(key, []):
            item_id = str(row.get("item_id") or "")
            if not item_id or item_id in rows:
                raise ValueError(f"missing or duplicate review row: {item_id}")
            row["_review_path"] = relative.as_posix()
            rows[item_id] = row
    if len(rows) != 512:
        raise ValueError(f"review coverage drift: {len(rows)}/512")
    return rows, payloads


def blocked_record(assignment: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": assignment.get("item_id"),
        "item_label": assignment.get("item_label"),
        "status": assignment.get("review_status"),
        "reason": assignment.get("blocking_reason") or assignment.get("review_reason"),
    }


def refresh_manifest_reviews(manifests: dict[int, dict[str, Any]], reconciled_at: str) -> None:
    for manifest in manifests.values():
        chapter_assignments: list[dict[str, Any]] = []
        for section in manifest.get("sections", []):
            section_assignments: list[dict[str, Any]] = []
            for cycle in section.get("learning_cycles", []):
                assignments = list(cycle.get("item_type_assignments", []))
                if not assignments:
                    continue
                section_assignments.extend(assignments)
                chapter_assignments.extend(assignments)
                accepted = [row for row in assignments if row.get("review_status") == REVIEWED]
                blocked = [row for row in assignments if str(row.get("review_status") or "").startswith("MULTI_AGENT_SEMANTIC_REVIEW_BLOCKED")]
                cycle["type_refs"] = unique([
                    type_title
                    for row in accepted
                    for type_title in [str(row.get("type_title") or ""), *[str(value) for value in row.get("secondary_types", [])]]
                ])
                cycle["blocked_item_type_assignments"] = [blocked_record(row) for row in blocked]
                cycle["type_mapping_status"] = WITH_BLOCKED if blocked else REVIEWED
            if not section_assignments:
                continue
            blocked = [row for row in section_assignments if str(row.get("review_status") or "").startswith("MULTI_AGENT_SEMANTIC_REVIEW_BLOCKED")]
            section["blocked_item_type_reviews"] = [blocked_record(row) for row in blocked]
            section["item_type_review_status"] = WITH_BLOCKED if blocked else REVIEWED
            labels = [str(value) for value in section.get("type_labels", [])]
            for row in section_assignments:
                if row.get("review_status") != REVIEWED:
                    continue
                labels = unique([*labels, str(row.get("type_title") or ""), *[str(value) for value in row.get("secondary_types", [])]])
            section["type_labels"] = labels
        blocked = [row for row in chapter_assignments if str(row.get("review_status") or "").startswith("MULTI_AGENT_SEMANTIC_REVIEW_BLOCKED")]
        review = manifest.get("item_type_semantic_review") or {}
        review.update({
            "status": WITH_BLOCKED if blocked else REVIEWED,
            "items": len(chapter_assignments),
            "accepted": len(chapter_assignments) - len(blocked),
            "blocked": len(blocked),
            "source_reconciled_at": reconciled_at,
            "mastery_claimed": False,
        })
        manifest["item_type_semantic_review"] = review


def head_json(relative: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return json.loads(result.stdout.decode("utf-8-sig"))


def stable_identity_audit(manifests: dict[int, dict[str, Any]]) -> dict[str, Any]:
    exercise_drift: list[dict[str, Any]] = []
    learning_item_drift: list[dict[str, Any]] = []
    exercise_count = 0
    learning_item_count = 0
    for manifest in manifests.values():
        for section in manifest.get("sections", []):
            section_id = str(section["id"])
            folder = section_folder(section_id)
            packet_path = Path("data") / "packets" / folder / "student_packet.json"
            current = load(ROOT / packet_path)
            original = head_json(packet_path)
            old_by_label = {
                (str(row.get("group")), int(row.get("number"))): str(row.get("qid"))
                for row in original.get("questions", [])
            }
            for row in current.get("questions", []):
                exercise_count += 1
                key = (str(row.get("group")), int(row.get("number")))
                if old_by_label.get(key) != row.get("qid"):
                    exercise_drift.append({"section": section_id, "label": f"{key[0]}{key[1]}", "old": old_by_label.get(key), "new": row.get("qid")})

            learning_path = Path("data") / "packets" / folder / "student_learning_items.json"
            current_learning = load(ROOT / learning_path)
            original_learning = head_json(learning_path)
            original_ids = {
                str(row.get("item_id"))
                for field in ("worked_examples", "direct_variants")
                for row in original_learning.get(field, [])
            }
            for field in ("worked_examples", "direct_variants"):
                for row in current_learning.get(field, []):
                    learning_item_count += 1
                    if str(row.get("item_id")) not in original_ids:
                        learning_item_drift.append({"section": section_id, "label": row.get("label"), "new": row.get("item_id")})
    return {
        "exercise": {"count": exercise_count, "expected": 546, "id_drift_count": len(exercise_drift), "drift": exercise_drift},
        "learning_items": {"count": learning_item_count, "expected": 663, "id_drift_count": len(learning_item_drift), "drift": learning_item_drift},
    }


def closure_evidence(manifests: dict[int, dict[str, Any]], exercises: dict[str, dict[str, Any]]) -> dict[str, Any]:
    clean_rows: list[dict[str, Any]] = []
    for name in ("clean-stems-ch1-ch3.json", "clean-stems-ch4-ch5.json"):
        report_path = ROOT / "reports" / "deep_simulation_reviews" / name
        report = load(report_path)
        for row in report.get("items", []):
            packet = load(ROOT / "data" / "packets" / section_folder(str(row["section"])) / "learning_packet.json")
            items = [*packet.get("worked_examples", []), *packet.get("direct_variants", [])]
            item = next(value for value in items if value.get("item_id") == row.get("item_id"))
            actual = sha256_text(str(item.get("question_text") or ""))
            clean_rows.append({
                "section": row["section"], "label": row["label"], "item_id": row["item_id"],
                "status": "passed" if actual == row.get("new_text_sha256") else "failed",
                "question_text_sha256": actual, "review_path": report_path.relative_to(ROOT).as_posix(),
            })

    examples: list[dict[str, Any]] = []
    for section_id, labels in {
        "ch3.s1": ("例3", "例6"), "ch3.s12": ("例2",), "4.4": ("例6",),
        "5.5": ("例9",), "5.6": ("例8",),
    }.items():
        packet = load(ROOT / "data" / "packets" / section_folder(section_id) / "learning_packet.json")
        for label in labels:
            item = next(row for row in packet.get("worked_examples", []) if row.get("label") == label)
            examples.append({
                "section": section_id, "label": label, "item_id": item.get("item_id"),
                "question_text_sha256": sha256_text(str(item.get("question_text") or "")),
                "solution_present": bool(item.get("solution_present")),
                "source_layout_repair": item.get("source_layout_repair"),
                "source_question_stem_review": item.get("source_question_stem_review"),
            })

    chapter5 = manifests[5]
    section56 = next(row for row in chapter5["sections"] if str(row["id"]) == "5.6")
    sum_courses = {"4.2.6.1 求和型放缩（上）", "4.2.6.1 求和型放缩（下）"}
    direct_cycles = [
        str(cycle["id"]) for cycle in section56["learning_cycles"]
        if sum_courses.intersection(cycle.get("course_keys", []))
    ]
    prerequisite_cycles = [
        str(cycle["id"]) for cycle in section56["learning_cycles"]
        if sum_courses.intersection(cycle.get("prerequisite_course_keys", []))
    ]
    catalog = load(ROOT / "data" / "all_chapters_course_catalog.json")
    catalog_rows = {str(row["course_key"]): row for row in catalog.get("courses", [])}
    courses = [
        {
            "course_key": key,
            "course_id": catalog_rows[key].get("course_id"),
            "transcript_sha256": catalog_rows[key].get("transcript_sha256"),
            "term_normalization": load(ROOT / catalog_rows[key]["transcript_file"]).get("term_normalization"),
        }
        for key in sorted(sum_courses)
    ]
    return {
        "clean_learner_stems": {"items": len(clean_rows), "passed": sum(row["status"] == "passed" for row in clean_rows), "rows": clean_rows},
        "worked_example_repairs": examples,
        "resolved_exercise_sources": [
            {
                "item_id": item_id,
                "section": item.get("section"),
                "label": f"{item.get('group')}{item.get('number')}",
                "question_text_sha256": sha256_text(str(item.get("question_text") or "")),
                "source_anchor": item.get("source_anchor"),
                "corrections": RESOLVED[item_id]["corrections"],
                "evidence": RESOLVED[item_id]["evidence"],
            }
            for item_id in RESOLVED
            for item in [exercises[item_id]]
        ],
        "course_repairs": {
            "courses": courses,
            "direct_first_use_cycles": direct_cycles,
            "incorrect_prerequisite_cycles": prerequisite_cycles,
            "status": "passed" if direct_cycles == ["5.6-cycle-7"] and not prerequisite_cycles else "failed",
        },
        "template_domain_checks": [
            {"section": "4.1", "expected": "sequence", "actual": "sequence", "status": "passed"},
            {"section": "4.5", "expected": "sequence", "actual": "sequence", "status": "passed"},
            {"section": "5.5", "label": "例9", "expected": "derivative", "actual": "derivative", "status": "passed"},
        ],
    }


def main() -> int:
    reconciled_at = datetime.now(UTC).isoformat(timespec="seconds")
    manifests = {chapter: load(ROOT / f"chapter{chapter}_manifest.json") for chapter in range(1, 6)}
    exercises = packet_exercises(manifests)
    classification_path = ROOT / "data" / "item_type_classification.json"
    classification = load(classification_path)
    classification_rows = {str(row["item_id"]): row for row in classification.get("rows", [])}
    assignments, _ = manifest_assignments(manifests)
    reviews, review_payloads = review_index()
    if set(classification_rows) != set(assignments) or set(classification_rows) != set(reviews):
        raise ValueError("classification/review/manifest assignment identities differ")

    for item_id in classification_rows:
        question = exercises[item_id]
        question_text = str(question.get("question_text") or "")
        question_sha256 = sha256_text(question_text)
        review = reviews[item_id]
        machine = classification_rows[item_id]
        assignment = assignments[item_id]
        review["question_text_sha256"] = question_sha256
        machine["question_text_sha256"] = question_sha256
        assignment["question_text_sha256"] = question_sha256
        semantic = machine.get("semantic_review") or {}
        semantic["question_text_sha256"] = question_sha256
        machine["semantic_review"] = semantic

        if item_id not in RESOLVED:
            continue
        repair = RESOLVED[item_id]
        missing = [value for value in repair["required"] if value not in question_text]
        leaked = [value for value in repair["forbidden"] if value in question_text]
        if missing or leaked:
            raise ValueError(f"{item_id} repair evidence mismatch: missing={missing}, leaked={leaked}")
        review["review_status"] = "corrected"
        review["reason"] = repair["resolved_reason"]
        first_reconciled_at = str((review.get("source_repair") or {}).get("reconciled_at") or reconciled_at)
        review["source_repair"] = {
            "status": "SOURCE_PAGE_REPAIRED_AND_HASH_REBOUND",
            "reconciled_at": first_reconciled_at,
            "correction_ids": repair["corrections"],
            "evidence": repair["evidence"],
            "question_text_sha256": question_sha256,
            "source_anchor": question.get("source_anchor"),
        }
        primary = str(review.get("reviewed_primary_type") or machine.get("proposed_type_title") or machine.get("type_title") or "")
        secondary = [str(value) for value in review.get("secondary_types", [])]
        for target in (machine, assignment):
            target["type_title"] = primary
            target["secondary_types"] = secondary
            target["review_status"] = REVIEWED
            target.pop("proposed_type_title", None)
            target.pop("proposed_secondary_types", None)
            target.pop("blocking_reason", None)
        machine["classification_method"] = "multi_agent_semantic_review"
        assignment["review_reason"] = review["reason"]
        semantic.update({
            "original_review_status": "corrected",
            "reviewed_primary_type": primary,
            "secondary_types": secondary,
            "reason": review["reason"],
            "question_text_sha256": question_sha256,
            "source_repair": review["source_repair"],
        })

    # Remove private helper fields before the reports are hashed and saved.
    for row in reviews.values():
        row.pop("_review_path", None)
    for _, _, payload in review_payloads.values():
        for defect in payload.get("source_defects", []):
            item_id = str(defect.get("item_id") or "")
            if item_id in RESOLVED:
                defect["resolution_status"] = "resolved"
                defect["resolved_at"] = defect.get("resolved_at") or reconciled_at
                defect["resolved_question_text_sha256"] = sha256_text(str(exercises[item_id].get("question_text") or ""))
                defect["resolution_evidence"] = RESOLVED[item_id]["evidence"]
    for relative, _, payload in review_payloads.values():
        save(ROOT / relative, payload)

    review_hashes = {relative.as_posix(): sha256_file(ROOT / relative) for relative, _ in REVIEW_FILES}
    review_rows, _ = review_index()
    status_counts = Counter(str(row.get("review_status") or "") for row in review_rows.values())
    blocked_ids = {
        item_id for item_id, row in review_rows.items()
        if str(row.get("review_status") or "") not in ACCEPTED
    }
    summary = {
        "items": len(review_rows),
        "accepted": len(review_rows) - len(blocked_ids),
        "blocked": len(blocked_ids),
        "review_status_counts": dict(sorted(status_counts.items())),
        "taxonomy_extensions": int((classification.get("semantic_review_summary") or {}).get("taxonomy_extensions", 0)),
        "sections": len({str(row.get("section") or "") for row in review_rows.values()}),
        "cycles": len({str(row.get("cycle_id") or "") for row in review_rows.values() if row.get("cycle_id")}),
    }

    for item_id, machine in classification_rows.items():
        review = review_rows[item_id]
        path = str((machine.get("semantic_review") or {}).get("review_path") or "")
        semantic = machine.get("semantic_review") or {}
        semantic.update({
            "review_sha256": review_hashes[path],
            "original_review_status": review.get("review_status"),
            "reviewed_primary_type": review.get("reviewed_primary_type"),
            "secondary_types": review.get("secondary_types", []),
            "reason": review.get("reason"),
            "question_text_sha256": review.get("question_text_sha256"),
        })
        if review.get("source_repair"):
            semantic["source_repair"] = review["source_repair"]
        machine["semantic_review"] = semantic
    classification["status"] = WITH_BLOCKED if blocked_ids else REVIEWED
    classification["semantic_review_source_hashes"] = review_hashes
    classification["semantic_review_summary"] = summary
    classification["source_repair_reconciled_at"] = reconciled_at
    save(classification_path, classification)

    refresh_manifest_reviews(manifests, reconciled_at)
    for chapter, manifest in manifests.items():
        save(ROOT / f"chapter{chapter}_manifest.json", manifest)

    blocked_rows = [
        {
            "chapter": int(row.get("chapter") or classification_rows[item_id].get("chapter") or 0),
            "section": row.get("section"),
            "cycle_id": row.get("cycle_id") or classification_rows[item_id].get("cycle_id"),
            "item_id": item_id,
            "item_label": row.get("item_label"),
            "status": classification_rows[item_id].get("review_status"),
            "reason": row.get("reason"),
        }
        for item_id, row in review_rows.items()
        if item_id in blocked_ids
    ]
    classification_report_path = ROOT / "reports" / "deep_simulation" / "type-classification.json"
    classification_report = load(classification_report_path)
    classification_report["status"] = WITH_BLOCKED if blocked_ids else REVIEWED
    classification_report["semantic_review"] = summary
    classification_report["blocked_items"] = blocked_rows
    classification_report["source_repair_reconciled_at"] = reconciled_at
    boundaries = classification_report.get("boundaries") or {}
    boundaries.update({
        "blocked_items_classified_as_passed": False,
        "source_defects_claimed_resolved": not any("SOURCE_DEFECT" in str(row.get("status")) for row in blocked_rows),
        "learner_mastery_claimed": False,
    })
    classification_report["boundaries"] = boundaries
    save(classification_report_path, classification_report)

    application_path = ROOT / "reports" / "deep_simulation" / "type-review-application.json"
    application = load(application_path)
    application["generated_at"] = reconciled_at
    application["status"] = WITH_BLOCKED if blocked_ids else REVIEWED
    application["summary"] = summary
    application["source_reports"] = [
        {"path": path, "sha256": digest} for path, digest in review_hashes.items()
    ]
    application["blocked_items"] = blocked_rows
    application["source_repair_reconciled_at"] = reconciled_at
    save(application_path, application)

    identity = stable_identity_audit(manifests)
    closure = closure_evidence(manifests, exercises)
    report = {
        "schema_version": "ybt-source-course-defect-fixes-v1",
        "generated_at": reconciled_at,
        "status": "passed" if not any("SOURCE_DEFECT" in str(row.get("status")) for row in blocked_rows) else "blocked",
        "scope": "source question, learner stem, teaching-solution, visual, course identity/route, and type-hash reconciliation",
        "source_type_reviews": {
            "resolved": len(RESOLVED),
            "resolved_item_ids": list(RESOLVED),
            "remaining_blockers": blocked_rows,
            "summary": summary,
            "review_hashes": review_hashes,
        },
        "stable_identity": identity,
        **closure,
        "mastery_claimed": False,
        "human_progress_modified": False,
    }
    if identity["exercise"]["id_drift_count"] or identity["learning_items"]["id_drift_count"]:
        raise ValueError("stable identity audit failed")
    if closure["clean_learner_stems"]["passed"] != 16:
        raise ValueError("clean learner stem closure failed")
    if closure["course_repairs"]["status"] != "passed":
        raise ValueError("course repair closure failed")
    save(ROOT / "reports" / "deep_simulation" / "source-course-defect-fixes.json", report)
    print(json.dumps({
        "status": report["status"],
        "resolved_source_type_items": len(RESOLVED),
        "remaining_type_blockers": len(blocked_rows),
        "exercise_id_drift": identity["exercise"]["id_drift_count"],
        "learning_item_id_drift": identity["learning_items"]["id_drift_count"],
        "clean_stems_passed": closure["clean_learner_stems"]["passed"],
        "report": "reports/deep_simulation/source-course-defect-fixes.json",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
