from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "chapter1_manifest.json",
    "data/bridge_micro_lessons.json",
    "data/packets/1.1/learning_packet.json",
    "data/packets/1.1/student_learning_items.json",
    "data/contexts/1.1.json",
    "data/question_coverage.json",
    "data/zero_base_simulation_standard.md",
    "data/packets/1.1/learning_path_without_questions.md",
)
WORKER_AGENT_IDS = {
    "1": "01a00a58-1d1f-7f33-82c6-e00110e00e06",
    "2": "01a00a58-1f0c-7210-9f90-d32ecce2133b",
    "3": "01a00a58-1f93-7890-b485-ed27bb45ad31",
    "4": "01a00a58-2017-73d3-9c5d-1cad47fb4388",
    "5": "01a00a58-20a0-7fb3-9fdc-7b8018bb57ff",
}
WORKER_SCOPES = {
    "1": ("1-2", "01-14"),
    "2": ("3-4", "15-17"),
    "3": ("5-6", "18-26"),
    "4": ("7-8", "27-35"),
    "5": ("9-10", "36-38"),
}
WORKER_TASK_COUNTS = {"1": 14, "2": 3, "3": 9, "4": 9, "5": 3}
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


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_item_ids(packet: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for cycle in packet.get("learning_cycles", []):
        result.update(str(item.get("item_id")) for item in cycle.get("worked_examples", []))
        result.update(str(item.get("item_id")) for item in cycle.get("direct_variants", []))
        result.update(
            f"{item.get('group')}{item.get('number')}"
            for item in cycle.get("exercise_questions", [])
        )
    return result


def validate_worker(
    worker: dict[str, Any],
    generation: str,
    expected_ids: set[str],
    expected_context_hash: str,
) -> None:
    if worker.get("section") != "1.1" or worker.get("generation") != generation:
        raise ValueError(f"worker {worker.get('worker')} has wrong section or generation")
    if worker.get("answer_sidecar_read") is not False or worker.get("human_acceptance_not_proven") is not True:
        raise ValueError(f"worker {worker.get('worker')} violates top-level answer boundary")
    if worker.get("worker_status") not in {"PASS", "PARTIAL", "BLOCKED", "FAIL"}:
        raise ValueError(f"worker {worker.get('worker')} has invalid worker_status")
    for item in worker.get("item_results", []):
        missing = REQUIRED_ITEM_FIELDS - set(item)
        if missing:
            raise ValueError(f"{worker.get('worker')}:{item.get('item_id')} missing {sorted(missing)}")
        if item.get("section") != "1.1" or item.get("answer_sidecar_read") is not False or item.get("human_acceptance_not_proven") is not True:
            raise ValueError(f"{worker.get('worker')}:{item.get('item_id')} violates answer boundary")
        if item.get("source_revision", {}).get("generation") != generation:
            raise ValueError(f"{worker.get('worker')}:{item.get('item_id')} source generation mismatch")
        if item.get("context_sha256") != expected_context_hash:
            raise ValueError(f"{worker.get('worker')}:{item.get('item_id')} context hash invalid")
        if not isinstance(item.get("course_call"), dict) or not item["course_call"].get("method_model_id"):
            raise ValueError(f"{worker.get('worker')}:{item.get('item_id')} course model missing")
        if item.get("hint_level") not in {"none", "minimal", "full"}:
            raise ValueError(f"{worker.get('worker')}:{item.get('item_id')} hint level invalid")
        if item.get("verdict") not in {"PASS", "PARTIAL", "BLOCKED", "FAIL"}:
            raise ValueError(f"{worker.get('worker')}:{item.get('item_id')} verdict invalid")


def build_snapshot(
    root: Path,
    generation: str,
    *,
    worker_suffix: str = "",
    worker_agent_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
    worker_agent_ids = worker_agent_ids or WORKER_AGENT_IDS
    if set(worker_agent_ids) != set(WORKER_AGENT_IDS):
        raise ValueError("worker agent id map must cover workers 1-5")
    packet = load(root / "data" / "packets" / "1.1" / "learning_packet.json")
    student_items_path = root / "data" / "packets" / "1.1" / "student_learning_items.json"
    student_items = load(student_items_path)
    packet_learning_ids = {
        str(item.get("item_id"))
        for cycle in packet.get("learning_cycles", [])
        for item in [*cycle.get("worked_examples", []), *cycle.get("direct_variants", [])]
    }
    student_learning_ids = {
        str(item.get("item_id"))
        for item in [*student_items.get("worked_examples", []), *student_items.get("direct_variants", [])]
    }
    if student_items.get("packet_type") != "DEEPSEEK_STUDENT_LEARNING_ITEMS":
        raise ValueError("student learning item packet type mismatch")
    if packet_learning_ids != student_learning_ids:
        raise ValueError(
            "student learning item closure mismatch: "
            f"missing={sorted(packet_learning_ids - student_learning_ids)}, "
            f"extra={sorted(student_learning_ids - packet_learning_ids)}"
        )
    if student_items.get("counts", {}).get("total") != len(student_learning_ids):
        raise ValueError("student learning item count mismatch")
    expected = expected_item_ids(packet)
    context = load(root / "data" / "contexts" / "1.1.json")
    expected_context_hash = str(context.get("evidence", {}).get("context_sha256", ""))
    if len(expected_context_hash) != 64:
        raise ValueError("current context hash missing")
    workers: list[dict[str, Any]] = []
    item_results: list[dict[str, Any]] = []
    method_check_results: list[dict[str, Any]] = []
    for worker_number in sorted(WORKER_AGENT_IDS, key=int):
        path = root / "reports" / "zero_base_cycles" / f"1.1-structured-worker-{worker_number}{worker_suffix}.json"
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = load(path)
        validate_worker(payload, generation, expected, expected_context_hash)
        item_results.extend(payload.get("item_results", []))
        method_check_results.extend(payload.get("method_check_results", []))
        cycles, tasks = WORKER_SCOPES[worker_number]
        worker_status = str(payload["worker_status"]).lower()
        # The aggregate acceptance schema has only pass/partial/fail rows;
        # preserve item-level BLOCKED while treating a blocked worker as fail.
        normalized_status = "fail" if worker_status == "blocked" else worker_status
        workers.append({
            "agent_id": worker_agent_ids[worker_number],
            "worker": int(worker_number),
            "cycles": cycles,
            "tasks": tasks,
            "status": normalized_status,
            "item_count": len(payload.get("item_results", [])),
            "method_check_count": len(payload.get("method_check_results", [])),
            "first_breakpoints": payload.get("first_breakpoints", []),
            "evidence_file": path.relative_to(root).as_posix(),
        })

    observed = [str(item.get("item_id")) for item in item_results]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        missing = sorted(expected - set(observed))
        extra = sorted(set(observed) - expected)
        raise ValueError(f"item closure mismatch: missing={missing}, extra={extra}")

    source_revision = {relative: sha256(root / relative) for relative in SOURCE_FILES}
    status_counts = Counter(worker["status"] for worker in workers)
    return {
        "schema_version": "1.1",
        "artifact": "CURRENT_GENERATION_ZERO_BASE_AGENT_SIMULATION",
        "generation": generation,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "section": "1.1",
        "worker_contract": {
            "workers_dispatched": 5,
            "workers_completed": 5,
            "role": "deepseek_worker",
            "model": "opencode-go/deepseek-v4-flash",
            "reasoning_effort": "max",
            "context_window": 1000000,
            "answer_sidecar_read": False,
        },
        "source_revision": source_revision,
        "task_coverage": {
            "ranges": [
                {"workers": [worker_agent_ids[number]], "cycles": WORKER_SCOPES[number][0], "tasks": WORKER_SCOPES[number][1], "task_count": WORKER_TASK_COUNTS[number]}
                for number in sorted(WORKER_AGENT_IDS, key=int)
            ],
            "task_count": len(item_results),
            "expected_task_count": len(expected),
            "complete": len(item_results) == len(expected),
        },
        "workers": workers,
        "item_results": item_results,
        "method_check_results": method_check_results,
        "summary": {
            "workers": len(workers),
            "pass": status_counts.get("pass", 0),
            "partial": status_counts.get("partial", 0),
            "fail": status_counts.get("fail", 0),
            "task_coverage_complete": len(item_results) == len(expected),
            "route_verdict": "PASS" if status_counts.get("pass", 0) == 5 else "PARTIAL_NEEDS_RETEST",
            "human_acceptance_not_proven": True,
            "cold_retest_24h": "not_run",
            "real_user_observation": "not_run",
        },
        "material_blockers": [
            f"{item.get('item_id')}: {item.get('first_breakpoint')}"
            for item in item_results
            if item.get("verdict") in {"PARTIAL", "BLOCKED"} and item.get("first_breakpoint")
        ],
        "answer_free_boundary": {
            "answer_sidecar_read": False,
            "answer_ocr_read": False,
            "answer_text_in_context": False,
            "student_mastery_claim": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge validated per-item zero-base worker results")
    parser.add_argument("--generation", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker-suffix", default="")
    parser.add_argument(
        "--worker-ids",
        default="",
        help="Comma-separated worker IDs in worker 1..5 order; defaults to the historical group.",
    )
    args = parser.parse_args()
    worker_ids = None
    if args.worker_ids:
        values = [item.strip() for item in args.worker_ids.split(",") if item.strip()]
        if len(values) != 5:
            raise SystemExit("--worker-ids must contain exactly five comma-separated IDs")
        worker_ids = {str(index): value for index, value in enumerate(values, start=1)}
    payload = build_snapshot(
        ROOT,
        args.generation,
        worker_suffix=args.worker_suffix,
        worker_agent_ids=worker_ids,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "generation": args.generation,
        "items": len(payload["item_results"]),
        "methods": len(payload["method_check_results"]),
        "summary": payload["summary"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
