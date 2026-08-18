#!/usr/bin/env python3
"""Write a fail-closed status ledger for chapter-level learner simulations."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.merge_chapter_zero_base_simulations import (
    ROOT,
    SECTION_CONFIG,
    expected_item_ids,
    load,
    sha256,
    source_revision,
)


OUTPUT = ROOT / "reports" / "zero_base_cycles" / "chapter1-current-simulation-status.json"


def historical_metadata(section: str, current_context_sha: str) -> dict[str, Any]:
    config = SECTION_CONFIG[section]
    paths = sorted(
        path
        for path in (ROOT / "reports" / "zero_base_cycles").glob(f"{section}-structured-worker-*.json")
        if path.name != Path(config["worker"]).name
    )
    generations: set[str] = set()
    context_hashes: set[str] = set()
    statuses: set[str] = set()
    for path in paths:
        try:
            payload = load(path)
        except (OSError, json.JSONDecodeError):
            statuses.add("UNREADABLE")
            continue
        if payload.get("generation"):
            generations.add(str(payload["generation"]))
        context = payload.get("context_binding", {}).get("context_sha256")
        if not context:
            items = payload.get("item_results") or []
            if items:
                context = items[0].get("context_sha256")
        if context:
            context_hashes.add(str(context))
        if payload.get("worker_status"):
            statuses.add(str(payload["worker_status"]))
    return {
        "file_count": len(paths),
        "files": [str(path.relative_to(ROOT)).replace("\\", "/") for path in paths],
        "generations": sorted(generations),
        "context_hashes": sorted(context_hashes),
        "worker_statuses": sorted(statuses),
        "current_context_hash": current_context_sha,
        "historical_context_stale": bool(context_hashes) and context_hashes != {current_context_sha},
    }


def build_status() -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    for section, config in SECTION_CONFIG.items():
        packet = load(ROOT / config["packet"])
        context = load(ROOT / config["context"])
        current_context_sha = str(context.get("evidence", {}).get("context_sha256", ""))
        expected_count = len(expected_item_ids(packet))
        worker_path = ROOT / config["worker"]
        sections.append({
            "section": section,
            "current_worker_file": config["worker"],
            "current_worker_present": worker_path.is_file(),
            "expected_item_count": expected_count,
            "current_item_count": None,
            "current_status": "NOT_RUN" if not worker_path.is_file() else "PENDING_MERGE",
            "context_sha256": current_context_sha,
            "source_revision": source_revision(section),
            "historical_shards": historical_metadata(section, current_context_sha),
        })
    aggregate_path = ROOT / "reports" / "zero_base_cycles" / "chapter1-current-agent-simulation.json"
    aggregate_error = None
    if aggregate_path.is_file():
        try:
            aggregate = load(aggregate_path)
            if aggregate.get("artifact") != "CURRENT_CHAPTER_ZERO_BASE_AGENT_SIMULATION":
                aggregate_error = "current_chapter_simulation_artifact_mismatch"
            else:
                aggregate_sections = {
                    item.get("section"): item for item in aggregate.get("sections", [])
                }
                for item in sections:
                    record = aggregate_sections.get(item["section"])
                    if record and record.get("item_count") == record.get("expected_item_count"):
                        item["current_status"] = "VERIFIED"
                        item["current_item_count"] = record.get("item_count")
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            aggregate_error = f"current_chapter_simulation_unreadable:{type(exc).__name__}"
    current_ready = sum(1 for item in sections if item["current_status"] == "VERIFIED")
    expected = sum(item["expected_item_count"] for item in sections)
    return {
        "schema_version": "1.0",
        "artifact": "CHAPTER_ZERO_BASE_SIMULATION_STATUS",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "第一章 1.2+1.3、1.4、micro专题1 当前代逐题零基础模拟证据状态",
        "sections": sections,
        "summary": {
            "section_count": len(sections),
            "current_sections_verified": current_ready,
            "required_sections": len(sections),
            "current_items_verified": 0,
            "required_items": expected,
            "all_current_section_simulations_ready": current_ready == len(sections),
            "human_acceptance_not_proven": True,
            "cold_retest_24h": "not_run",
            "real_user_observation": "not_run",
        },
        "release_boundary": {
            "old_shards_can_prove_current_generation": False,
            "chapter_probe_is_student_mastery": False,
            "answer_sidecar_read": False,
            "student_mastery_claim": False,
        },
        "blockers": [
            *([] if current_ready == len(sections) else ["current_section_worker_outputs_missing_or_not_merged"]),
            *([aggregate_error] if aggregate_error else []),
            "historical_shards_are_not_current_generation_evidence",
        ],
    }


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = build_status()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "summary": payload["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
