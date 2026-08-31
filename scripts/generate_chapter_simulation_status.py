#!/usr/bin/env python3
"""Project current v3 route-audit status for Chapter 1 sections after 1.1."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/zero_base_cycles/chapter1-current-simulation-status.json"
POINTER = ROOT / "reports/deep_section_simulations/current.json"
SECTIONS = ("1.2+1.3", "1.4", "micro专题1")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def folder(section: str) -> str:
    return section.replace("+", "_")


def build_status() -> dict[str, Any]:
    pointer = load(POINTER)
    run_root = ROOT / str(pointer["run_path"])
    rows = []
    blockers = []
    for section in SECTIONS:
        report_path = run_root / f"{folder(section)}.json"
        report = load(report_path)
        packet_path = ROOT / "data/packets" / folder(section) / "learning_packet.json"
        route_path = ROOT / "data/packets" / folder(section) / "learning_path_without_questions.md"
        expected = int(load(packet_path)["counts"]["total_numbered_learning_items"])
        errors = []
        if report.get("schema_version") != "ybt-deep-section-simulation-v3":
            errors.append("schema")
        if report.get("route_audit_status") != "passed":
            errors.append("route_audit")
        if report.get("mastery_claimed") is not False:
            errors.append("mastery_boundary")
        if report.get("summary", {}).get("items") != expected:
            errors.append("item_count")
        source = report.get("source_binding", {})
        if source.get("learning_packet_sha256") is not None:
            errors.append("legacy_learning_packet_binding")
        if source.get("grader_learning_packet_sha256") != sha256(packet_path):
            errors.append("learning_packet_sha")
        if source.get("route_sha256") != sha256(route_path):
            errors.append("route_sha")
        if report.get("answer_isolation", {}).get("status") != "passed":
            errors.append("answer_isolation")
        current_status = "VERIFIED" if not errors else "BLOCKED"
        if errors:
            blockers.append(f"{section}:{','.join(errors)}")
        rows.append({
            "section": section,
            "current_worker_file": str(report_path.relative_to(ROOT)).replace("\\", "/"),
            "current_worker_present": True,
            "expected_item_count": expected,
            "current_item_count": expected if not errors else None,
            "current_status": current_status,
            "run_id": pointer["run_id"],
            "source_revision": report.get("source_binding", {}),
            "mathematical_correctness": "not_evaluated_no_final_answer",
            "errors": errors,
        })
    current_ready = sum(row["current_status"] == "VERIFIED" for row in rows)
    current_items = sum(int(row["current_item_count"] or 0) for row in rows)
    required_items = sum(int(row["expected_item_count"]) for row in rows)
    return {
        "schema_version": "2.0",
        "artifact": "CHAPTER_ZERO_BASE_SIMULATION_STATUS",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "第一章 1.2+1.3、1.4、micro专题1 当前答案隔离路线审计状态",
        "authority": {
            "kind": "answer_isolated_route_audit_current_pointer",
            "pointer": str(POINTER.relative_to(ROOT)).replace("\\", "/"),
            "run_id": pointer["run_id"],
        },
        "sections": rows,
        "summary": {
            "section_count": len(rows),
            "current_sections_verified": current_ready,
            "required_sections": len(rows),
            "current_items_verified": current_items,
            "required_items": required_items,
            "all_current_section_simulations_ready": current_ready == len(rows),
            "route_actionability_only": True,
            "mathematical_correctness": "not_evaluated_no_final_answer",
            "human_acceptance_not_proven": True,
            "cold_retest_24h": "not_run",
            "real_user_observation": "not_run",
        },
        "release_boundary": {
            "route_audit_is_student_mastery": False,
            "answer_sidecar_in_persona_context": False,
            "student_mastery_claim": False,
        },
        "blockers": blockers,
    }


def main() -> int:
    payload = build_status()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "summary": payload["summary"]}, ensure_ascii=False))
    return 0 if payload["summary"]["all_current_section_simulations_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
