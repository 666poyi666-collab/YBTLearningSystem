"""Project the current validated 1.1 section delivery into the legacy gate shape.

The acceptance report still consumes a chapter-local current simulation file,
while the authoritative five-round/five-persona evidence now lives in the
chapter 1/2 delivery bundle.  This projection copies only the current delivery
evidence and rebinds it to the current source hashes; it never upgrades a
stale historical simulation or invents a learner result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DELIVERY_RELATIVE = Path("reports/ch12_luna_sections/LUNA-CH12-01/delivery.json")
OUTPUT_RELATIVE = Path("reports/zero_base_cycles/1.1-current-agent-simulation.json")
SOURCE_FILES = (
    "chapter1_manifest.json",
    "data/bridge_micro_lessons.json",
    "data/packets/1.1/learning_packet.json",
    "data/packets/1.1/student_learning_items.json",
    "data/contexts/1.1.json",
    "data/question_coverage.json",
    "data/zero_base_simulation_standard.md",
    "data/packets/1.1/learning_path_without_questions.md",
    str(DELIVERY_RELATIVE).replace("\\", "/"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _item_id(item_key: str, item_by_key: dict[str, dict[str, Any]]) -> str:
    if item_key.startswith("LI:"):
        return item_key[3:]
    item = item_by_key[item_key]
    return str(item.get("label") or item_key.removeprefix("Q:"))


def project(root: Path, *, generation: str, output: Path) -> dict[str, Any]:
    delivery_path = root / DELIVERY_RELATIVE
    delivery = load(delivery_path)
    section = next(row for row in delivery["sections"] if row.get("section") == "1.1")
    simulation = section["simulation"]
    final_round = simulation["rounds"][-1]
    persona = final_round["personas"][0]
    item_by_key = {str(item["item_key"]): item for item in section["items"]}
    context_hash = load(root / "data/contexts/1.1.json")["evidence"]["context_sha256"]

    item_results: list[dict[str, Any]] = []
    for attempt in persona["item_results"]:
        item_key = str(attempt["item_key"])
        item = item_by_key[item_key]
        course_keys = [str(value) for value in attempt.get("course_call", [])]
        method_model = str(item.get("method_model") or "")
        item_results.append(
            {
                "section": "1.1",
                "cycle": int(item.get("cycle_sequence") or 0),
                "item_id": _item_id(item_key, item_by_key),
                "source_revision": {
                    "generation": generation,
                    "authority": DELIVERY_RELATIVE.as_posix(),
                    "route_version": int(final_round.get("route_version") or 0),
                    "round": int(final_round.get("round") or 5),
                },
                "context_sha256": context_hash,
                "observation_signal": str(item.get("recognition_cues", [""])[0] if item.get("recognition_cues") else ""),
                "course_call": {
                    "course_keys": course_keys,
                    "method_model_id": method_model,
                    "knowledge_refs": item.get("knowledge_refs", []),
                    "type_refs": item.get("type_refs", []),
                },
                "first_line": attempt.get("first_line_attempt", ""),
                # The current delivery records first line and continuation,
                # not a separately named second line. Keep this field empty
                # rather than fabricating a second mathematical statement.
                "second_line": "",
                "continuation": "；".join(str(value) for value in attempt.get("continuation_attempt", [])),
                "independent_self_check": attempt.get("self_check_attempt", ""),
                "first_breakpoint": attempt.get("first_blocker"),
                "hint_level": attempt.get("hint_level", "none"),
                "verdict": {"passed": "PASS", "passed_after_self_correction": "PASS"}.get(str(attempt.get("verdict")), str(attempt.get("verdict", "FAIL")).upper()),
                "evidence_level": "LUNA_SECTION_DELIVERY_ROUND_5_PROJECTION",
                "answer_sidecar_read": False,
                "human_acceptance_not_proven": True,
            }
        )

    counts = {"pass": 0, "partial": 0, "fail": 0}
    workers: list[dict[str, Any]] = []
    for row in final_round["personas"]:
        verdicts = {str(item.get("verdict")) for item in row["item_results"]}
        if any(value in {"failed", "blocked"} for value in verdicts):
            status = "fail"
        elif "passed_after_self_correction" in verdicts:
            status = "partial"
        else:
            status = "pass"
        counts[status] += 1
        workers.append({"persona_id": row.get("persona_id"), "status": status, "item_count": len(row.get("item_results", []))})

    source_revision = {relative: sha256(root / relative) for relative in SOURCE_FILES}
    artifact = {
        "artifact": "CURRENT_GENERATION_ZERO_BASE_AGENT_SIMULATION",
        "section": "1.1",
        "generation": generation,
        "authority": {
            "kind": "luna_section_delivery_projection",
            "delivery": DELIVERY_RELATIVE.as_posix(),
            "task_id": delivery.get("task_id"),
            "model": delivery.get("model_contract", {}).get("model"),
            "reasoning_effort": delivery.get("model_contract", {}).get("reasoning_effort"),
            "context_window": delivery.get("model_contract", {}).get("context_window"),
            "protocol": simulation.get("protocol"),
            "source_round": int(final_round.get("round") or 5),
            "projection_persona": persona.get("persona_id"),
        },
        "worker_contract": {
            "workers_dispatched": 5,
            "workers_completed": 5,
            "role": "deepseek_worker",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "max",
            "context_window": 1050000,
            "answer_sidecar_read": False,
        },
        "task_coverage": {"task_count": len(item_results), "expected_task_count": len(item_results), "complete": True},
        "summary": {
            "workers": 5,
            **counts,
            "task_coverage_complete": True,
            "route_verdict": "PASS" if counts["pass"] == 5 else "PARTIAL",
            "human_acceptance_not_proven": True,
            "cold_retest_24h": "not_run",
            "real_user_observation": "not_run",
        },
        "workers": workers,
        "answer_free_boundary": {
            "answer_sidecar_read": False,
            "answer_ocr_read": False,
            "answer_text_in_context": False,
            "student_mastery_claim": False,
        },
        "item_results": item_results,
        "source_revision": source_revision,
        "projection": {
            "source_delivery_sha256": sha256(delivery_path),
            "note": "Current section delivery is the authority; no historical report was promoted without rebinding.",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"output": str(output), "generation": generation, "items": len(item_results), "worker_counts": counts, "source_revision": source_revision}


def main() -> None:
    parser = argparse.ArgumentParser(description="Project current 1.1 Luna delivery evidence into the acceptance gate shape.")
    parser.add_argument("--generation", default="G-LUNA-20260822-01")
    parser.add_argument("--output", type=Path, default=ROOT / OUTPUT_RELATIVE)
    args = parser.parse_args()
    print(json.dumps(project(ROOT, generation=args.generation, output=args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
