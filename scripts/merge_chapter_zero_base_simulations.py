#!/usr/bin/env python3
"""Merge current-generation zero-base simulations for the non-1.1 chapter sections.

This is deliberately fail-closed. A section is not accepted from an old shard,
an unbound context, an incomplete packet item set, or a worker that used the
answer sidecar. The controller owns the merge; workers only provide section
records in the explicitly assigned files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DEFAULT = ROOT / "reports" / "zero_base_cycles" / "chapter1-current-agent-simulation.json"

SECTION_CONFIG: dict[str, dict[str, str]] = {
    "1.2_1.3": {
        "packet": "data/packets/1.2_1.3/learning_packet.json",
        "student": "data/packets/1.2_1.3/student_learning_items.json",
        "context": "data/contexts/1.2_1.3.json",
        "route": "data/packets/1.2_1.3/learning_path_without_questions.md",
        "worker": "reports/zero_base_cycles/1.2_1.3-structured-worker-g11.json",
    },
    "1.4": {
        "packet": "data/packets/1.4/learning_packet.json",
        "student": "data/packets/1.4/student_learning_items.json",
        "context": "data/contexts/1.4.json",
        "route": "data/packets/1.4/learning_path_without_questions.md",
        "worker": "reports/zero_base_cycles/1.4-structured-worker-g11.json",
    },
    "micro专题1": {
        "packet": "data/packets/micro专题1/learning_packet.json",
        "student": "data/packets/micro专题1/student_learning_items.json",
        "context": "data/contexts/micro专题1.json",
        "route": "data/packets/micro专题1/learning_path_without_questions.md",
        "worker": "reports/zero_base_cycles/micro专题1-structured-worker-g11.json",
    },
}

COMMON_SOURCES = (
    "chapter1_manifest.json",
    "data/bridge_micro_lessons.json",
    "data/question_coverage.json",
    "data/zero_base_simulation_standard.md",
)

REQUIRED_ITEM_FIELDS = {
    "section",
    "cycle",
    "item_id",
    "source_revision",
    "context_sha256",
    "observation_signal",
    "course_call",
    "first_line",
    "second_line",
    "continuation",
    "independent_self_check",
    "first_breakpoint",
    "hint_level",
    "verdict",
    "answer_sidecar_read",
    "human_acceptance_not_proven",
}
EXPECTED_CONTRACT = {
    "role": "deepseek_worker",
    "model": "opencode-go/deepseek-v4-flash",
    "reasoning_effort": "max",
    "context_window": 1_000_000,
    "answer_sidecar_read": False,
}
ALLOWED_VERDICTS = {"PASS", "PARTIAL", "BLOCKED", "FAIL"}
ALLOWED_HINTS = {"none", "minimal", "full"}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_item_ids(packet: dict[str, Any]) -> set[str]:
    item_ids: set[str] = set()
    for cycle in packet.get("learning_cycles", []):
        item_ids.update(str(item.get("item_id")) for item in cycle.get("worked_examples", []))
        item_ids.update(str(item.get("item_id")) for item in cycle.get("direct_variants", []))
        item_ids.update(
            f"{item.get('group')}{item.get('number')}"
            for item in cycle.get("exercise_questions", [])
        )
    return item_ids


def source_revision(section: str) -> dict[str, str]:
    config = SECTION_CONFIG[section]
    paths = [
        *COMMON_SOURCES,
        config["packet"],
        config["student"],
        config["context"],
        config["route"],
    ]
    return {relative: sha256(ROOT / relative) for relative in paths}


def validate_item(item: dict[str, Any], section: str, generation: str, context_sha: str, expected_ids: set[str]) -> None:
    missing = sorted(REQUIRED_ITEM_FIELDS - set(item))
    if missing:
        raise ValueError(f"{section}:{item.get('item_id')} missing {missing}")
    if item.get("section") != section:
        raise ValueError(f"{section}:{item.get('item_id')} section mismatch")
    if str(item.get("item_id")) not in expected_ids:
        raise ValueError(f"{section}:{item.get('item_id')} is not in current packet")
    if item.get("source_revision", {}).get("generation") != generation:
        raise ValueError(f"{section}:{item.get('item_id')} generation mismatch")
    if item.get("context_sha256") != context_sha:
        raise ValueError(f"{section}:{item.get('item_id')} context hash mismatch")
    if item.get("answer_sidecar_read") is not False or item.get("human_acceptance_not_proven") is not True:
        raise ValueError(f"{section}:{item.get('item_id')} answer boundary violation")
    if not isinstance(item.get("course_call"), dict) or not item["course_call"].get("method_model_id"):
        raise ValueError(f"{section}:{item.get('item_id')} course method missing")
    if item.get("hint_level") not in ALLOWED_HINTS:
        raise ValueError(f"{section}:{item.get('item_id')} hint level invalid")
    if item.get("verdict") not in ALLOWED_VERDICTS:
        raise ValueError(f"{section}:{item.get('item_id')} verdict invalid")


def validate_section(section: str) -> dict[str, Any]:
    config = SECTION_CONFIG[section]
    worker_path = ROOT / config["worker"]
    if not worker_path.is_file():
        raise FileNotFoundError(f"missing current worker output: {config['worker']}")
    packet = load(ROOT / config["packet"])
    context = load(ROOT / config["context"])
    worker = load(worker_path)
    expected_ids = expected_item_ids(packet)
    context_sha = str(context.get("evidence", {}).get("context_sha256", ""))
    if len(context_sha) != 64:
        raise ValueError(f"{section}: current context hash missing")
    if worker.get("section") != section:
        raise ValueError(f"{section}: worker section mismatch")
    if worker.get("artifact") != "CURRENT_SECTION_ZERO_BASE_AGENT_SIMULATION":
        raise ValueError(f"{section}: worker artifact mismatch")
    generation = worker.get("generation")
    if not isinstance(generation, str) or not generation:
        raise ValueError(f"{section}: worker generation missing")
    if worker.get("context_sha256") != context_sha:
        raise ValueError(f"{section}: worker context hash mismatch")
    if worker.get("answer_sidecar_read") is not False or worker.get("human_acceptance_not_proven") is not True:
        raise ValueError(f"{section}: worker answer boundary violation")
    contract = worker.get("worker_contract", {})
    for key, expected in EXPECTED_CONTRACT.items():
        if contract.get(key) != expected:
            raise ValueError(f"{section}: worker contract mismatch {key}")
    current_sources = source_revision(section)
    if worker.get("source_revision") != current_sources:
        raise ValueError(f"{section}: source revision mismatch")
    items = worker.get("item_results")
    if not isinstance(items, list):
        raise ValueError(f"{section}: item_results missing")
    observed = [str(item.get("item_id")) for item in items]
    if len(observed) != len(set(observed)) or set(observed) != expected_ids:
        raise ValueError(
            f"{section}: item closure mismatch missing={sorted(expected_ids - set(observed))} "
            f"extra={sorted(set(observed) - expected_ids)}"
        )
    for item in items:
        validate_item(item, section, generation, context_sha, expected_ids)
    method_checks = worker.get("method_check_results", [])
    if not isinstance(method_checks, list):
        raise ValueError(f"{section}: method_check_results must be a list")
    for check in method_checks:
        if check.get("answer_sidecar_read") is not False or check.get("human_acceptance_not_proven") is not True:
            raise ValueError(f"{section}: method check answer boundary violation")
        if check.get("verdict") not in ALLOWED_VERDICTS:
            raise ValueError(f"{section}: method check verdict invalid")
    verdicts = Counter(str(item["verdict"]) for item in items)
    status = "PASS" if verdicts.get("PASS", 0) == len(items) else "PARTIAL_NEEDS_RETEST"
    return {
        "section": section,
        "worker_file": config["worker"],
        "generation": generation,
        "context_sha256": context_sha,
        "item_count": len(items),
        "expected_item_count": len(expected_ids),
        "method_check_count": len(method_checks),
        "verdict_counts": dict(sorted(verdicts.items())),
        "status": status,
        "source_revision": current_sources,
    }


def build_snapshot() -> dict[str, Any]:
    sections = [validate_section(section) for section in SECTION_CONFIG]
    total_counts = Counter()
    for section in sections:
        total_counts.update(section["verdict_counts"])
    return {
        "schema_version": "1.0",
        "artifact": "CURRENT_CHAPTER_ZERO_BASE_AGENT_SIMULATION",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": "第一章 1.2+1.3、1.4、micro专题1 当前代逐题零基础代理模拟",
        "worker_contract": dict(EXPECTED_CONTRACT),
        "sections": sections,
        "summary": {
            "section_count": len(sections),
            "item_count": sum(item["item_count"] for item in sections),
            "expected_item_count": sum(item["expected_item_count"] for item in sections),
            "item_coverage_complete": all(item["item_count"] == item["expected_item_count"] for item in sections),
            "method_check_count": sum(item["method_check_count"] for item in sections),
            "verdict_counts": dict(sorted(total_counts.items())),
            "proxy_mastery_status": "PASS" if total_counts.get("PASS", 0) == sum(item["item_count"] for item in sections) else "BLOCKED",
            "human_acceptance_not_proven": True,
            "cold_retest_24h": "not_run",
            "real_user_observation": "not_run",
        },
        "answer_free_boundary": {
            "answer_sidecar_read": False,
            "answer_ocr_read": False,
            "answer_text_in_context": False,
            "student_mastery_claim": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge current chapter section zero-base simulations")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    args = parser.parse_args()
    snapshot = build_snapshot()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": snapshot["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
