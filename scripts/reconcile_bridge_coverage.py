#!/usr/bin/env python3
"""Bind answer-free bridge lessons to the first chapter's advanced cycles."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "chapter1_manifest.json"
BRIDGES = ROOT / "data/bridge_micro_lessons.json"
SUPPLEMENTS = ROOT / "data/bridge_supplement_lessons.json"
REPORT = ROOT / "reports/deep_simulation/bridge-coverage.json"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_question(section_id: str, value: str) -> str | None:
    prefix = f"{section_id}-"
    return value[len(prefix):] if value.startswith(prefix) else None


def main() -> int:
    manifest = load(MANIFEST)
    bridge_payload = load(BRIDGES)
    supplement_payload = load(SUPPLEMENTS)
    supplement_hash = sha256(SUPPLEMENTS)
    supplement_by_id = {str(row["id"]): row for row in supplement_payload.get("lessons", [])}
    bridge_by_id = {str(row["id"]): row for row in bridge_payload.get("units", [])}
    rows: list[dict[str, Any]] = []

    for section in manifest.get("sections", []):
        section_id = str(section.get("id") or "")
        if section_id == "1.1":
            continue
        cycles = section.get("learning_cycles", [])
        cycle_by_question: dict[str, dict[str, Any]] = {}
        for cycle in cycles:
            for question in cycle.get("exercise_keys", []):
                cycle_by_question[str(question)] = cycle

        expected_bridge_ids: set[str] = set()
        for bridge_id, bridge in bridge_by_id.items():
            if section_id not in [str(value) for value in bridge.get("sections", [])]:
                continue
            targets = [
                local_question(section_id, str(value))
                for value in bridge.get("target_questions", [])
            ]
            targets = [value for value in targets if value]
            matched_cycles: set[str] = set()
            for target in targets:
                cycle = cycle_by_question.get(target)
                if cycle is None:
                    continue
                bridge_ids = [str(value) for value in cycle.get("bridge_unit_ids", [])]
                if bridge_id not in bridge_ids:
                    bridge_ids.append(bridge_id)
                cycle["bridge_unit_ids"] = bridge_ids
                matched_cycles.add(str(cycle["id"]))
            if matched_cycles:
                expected_bridge_ids.add(bridge_id)
                rows.append({
                    "section": section_id,
                    "bridge_id": bridge_id,
                    "target_questions": targets,
                    "cycle_ids": sorted(matched_cycles),
                    "status": "SUPPLEMENT_READY",
                    "supplement_sha256": supplement_hash,
                })

        declared = {str(row.get("id")): row for row in section.get("bridge_units", []) if isinstance(row, dict) and row.get("id")}
        for bridge_id in sorted(expected_bridge_ids):
            canonical = bridge_by_id[bridge_id]
            supplement = supplement_by_id.get(bridge_id)
            row = declared.get(bridge_id)
            if row is None:
                row = {"id": bridge_id, "title": canonical.get("title")}
                section.setdefault("bridge_units", []).append(row)
            row.update({
                "title": canonical.get("title"),
                "target_questions": [
                    local_question(section_id, str(value))
                    for value in canonical.get("target_questions", [])
                    if local_question(section_id, str(value))
                ],
                "release_status": "SUPPLEMENT_READY",
                "source_status": "REPOSITORY_ANSWER_FREE_SUPPLEMENT_HASH_BOUND",
                "supplement_path": "data/bridge_supplement_lessons.json",
                "supplement_sha256": supplement_hash,
                "independent_checks": (supplement or {}).get("independent_check", canonical.get("method_check", [])),
                "mastery_boundary": "Route supplement is available; real completion and delayed retention remain unproven.",
            })

        old_gaps = [str(value) for value in section.get("coverage_gaps", [])]
        section["coverage_exceptions"] = [
            {
                "kind": "no_dedicated_video",
                "detail": value,
                "resolved_for_route_by": sorted(expected_bridge_ids),
                "course_coverage_claimed": False,
            }
            for value in old_gaps
        ]
        section["coverage_gaps"] = []
        section["coverage_status"] = "ROUTE_READY_WITH_ANSWER_FREE_SUPPLEMENTS"
        section["coverage_gate"] = "课程直接覆盖与无答案桥接分开记录；桥接已可执行，但代理掌握、真人掌握和24小时复测仍需独立证据。"

    save(MANIFEST, manifest)
    report = {
        "schema_version": "ybt-bridge-coverage-reconciliation-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "supplement_sha256": supplement_hash,
        "placements": len(rows),
        "sections": sorted({row["section"] for row in rows}),
        "rows": rows,
        "course_coverage_claimed": False,
        "human_mastery_claimed": False,
    }
    save(REPORT, report)
    print(json.dumps({"placements": len(rows), "sections": report["sections"], "report": str(REPORT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
