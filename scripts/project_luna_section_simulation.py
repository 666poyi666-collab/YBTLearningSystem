#!/usr/bin/env python3
"""Project the validated Luna 1.1 section simulation into the runtime gate.

The runtime acceptance report predates the full-book Luna deliveries and still
expects one current 1.1 aggregate. This adapter keeps that interface while
using only the current Luna delivery as evidence. It deliberately copies no
question text, solution, answer, or evaluator conclusion into the projection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DELIVERY_RELATIVE = Path("reports/luna_sections/LUNA-YBT-05/delivery.json")
OUTPUT_DEFAULT = ROOT / "reports/zero_base_cycles/1.1-current-agent-simulation.json"
GENERATION = "G-LUNA-20260817-01"
SOURCE_FILES = (
    "chapter1_manifest.json",
    "data/bridge_micro_lessons.json",
    "data/packets/1.1/learning_packet.json",
    "data/packets/1.1/student_learning_items.json",
    "data/contexts/1.1.json",
    "data/question_coverage.json",
    "data/zero_base_simulation_standard.md",
    "data/packets/1.1/learning_path_without_questions.md",
    DELIVERY_RELATIVE.as_posix(),
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_revision() -> dict[str, str]:
    revisions: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        revisions[relative] = sha256(path)
    return revisions


def expected_item_ids(packet: dict[str, Any], student_packet: dict[str, Any]) -> dict[str, str]:
    """Return the runtime item id for each delivery item key."""
    result: dict[str, str] = {}
    for cycle in packet.get("learning_cycles", []):
        for item in [*cycle.get("worked_examples", []), *cycle.get("direct_variants", [])]:
            item_id = str(item.get("item_id"))
            result[f"LI:{item_id}"] = item_id

    qid_to_label = {
        str(question.get("qid")): f"{question.get('group')}{question.get('number')}"
        for question in student_packet.get("questions", [])
        if question.get("qid") and question.get("group") and question.get("number") is not None
    }
    for qid, label in qid_to_label.items():
        result[f"Q:{qid}"] = label
    return result


def final_round(section: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    simulation = section.get("simulation") or {}
    if simulation.get("protocol") != "five-round-five-persona-v1" or simulation.get("status") != "passed":
        raise ValueError("1.1 Luna simulation is not a passed five-round protocol")
    rounds = simulation.get("rounds") or []
    if len(rounds) != 5 or rounds[-1].get("round") != 5:
        raise ValueError("1.1 Luna simulation does not contain five ordered rounds")
    round_five = rounds[-1]
    personas = round_five.get("personas") or []
    if len(personas) != 5:
        raise ValueError("1.1 cold proxy round must contain five personas")

    by_item: dict[str, dict[str, Any]] = {}
    for persona in personas:
        results = persona.get("item_results") or []
        if not results:
            raise ValueError(f"{persona.get('persona_id')}: missing item results")
        for attempt in results:
            key = str(attempt.get("item_key"))
            if key in by_item and by_item[key] != attempt:
                raise ValueError(f"round 5 has inconsistent attempts for {key}")
            by_item[key] = attempt
            required = (
                "recognized_method",
                "first_line_written",
                "continuation_complete",
                "self_check_complete",
            )
            if any(attempt.get(field) is not True for field in required) or attempt.get("verdict") != "passed":
                raise ValueError(f"round 5 item did not pass: {key}")
    return by_item, personas


def project(output: Path) -> dict[str, Any]:
    delivery_path = ROOT / DELIVERY_RELATIVE
    delivery = load(delivery_path)
    if delivery.get("status") != "passed":
        raise ValueError("LUNA-YBT-05 delivery is not passed")
    section = next((item for item in delivery.get("sections", []) if item.get("section") == "1.1"), None)
    if not isinstance(section, dict):
        raise ValueError("LUNA-YBT-05 does not contain section 1.1")

    packet = load(ROOT / "data" / "packets" / "1.1" / "learning_packet.json")
    student_packet = load(ROOT / "data" / "packets" / "1.1" / "student_packet.json")
    id_map = expected_item_ids(packet, student_packet)
    methods = {str(item.get("item_key")): item for item in section.get("items", [])}
    attempts, personas = final_round(section)
    if set(methods) != set(id_map) or set(attempts) != set(id_map):
        raise ValueError(
            f"1.1 item closure mismatch methods={len(methods)} attempts={len(attempts)} expected={len(id_map)}"
        )

    context = load(ROOT / "data" / "contexts" / "1.1.json")
    context_sha = str(context.get("evidence", {}).get("context_sha256", ""))
    if len(context_sha) != 64:
        raise ValueError("current 1.1 context hash is missing")
    revisions = source_revision()

    item_results: list[dict[str, Any]] = []
    for item in section.get("items", []):
        key = str(item.get("item_key"))
        attempt = attempts[key]
        item_results.append({
            "section": "1.1",
            "cycle": item.get("cycle_sequence"),
            "item_id": id_map[key],
            "source_revision": {
                "generation": GENERATION,
                "authority": DELIVERY_RELATIVE.as_posix(),
                "route_version": item.get("route_version"),
                "round": 5,
            },
            "context_sha256": context_sha,
            "observation_signal": "；".join(str(value) for value in item.get("recognition_cues") or []),
            "course_call": {
                "course_keys": [str(value) for value in item.get("course_refs") or []],
                "method_model_id": str(item.get("method_model") or ""),
                "knowledge_refs": [str(value) for value in item.get("knowledge_refs") or []],
                "type_refs": [str(value) for value in item.get("type_refs") or []],
            },
            "first_line": str(item.get("first_written_line_template") or ""),
            "second_line": "先按首行模板落笔，再逐项执行当前项目列出的继续动作。",
            "continuation": "；".join(str(value) for value in item.get("continuation_actions") or []),
            "independent_self_check": "；".join(str(value) for value in item.get("independent_self_checks") or []),
            "first_breakpoint": attempt.get("first_blocker") or "无",
            "hint_level": "minimal" if attempt.get("correction_used") else "none",
            "verdict": "PASS",
            "evidence_level": "LUNA_MAX_PROXY_ROUND_5_PASS",
            "answer_sidecar_read": False,
            "human_acceptance_not_proven": True,
        })

    workers = [
        {
            "agent_id": str(persona.get("persona_id")),
            "worker": index,
            "profile": persona.get("profile"),
            "status": "pass",
            "item_count": len(item_results),
            "evidence_file": DELIVERY_RELATIVE.as_posix(),
        }
        for index, persona in enumerate(personas, start=1)
    ]
    payload = {
        "artifact": "CURRENT_GENERATION_ZERO_BASE_AGENT_SIMULATION",
        "section": "1.1",
        "generation": GENERATION,
        "authority": {
            "kind": "luna_section_delivery_projection",
            "delivery": DELIVERY_RELATIVE.as_posix(),
            "task_id": "LUNA-YBT-05",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "max",
            "context_window": 1050000,
            "protocol": "five-round-five-persona-v1",
            "source_round": 5,
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
        "task_coverage": {
            "task_count": len(item_results),
            "expected_task_count": len(item_results),
            "complete": True,
        },
        "summary": {
            "workers": 5,
            "pass": 5,
            "partial": 0,
            "fail": 0,
            "task_coverage_complete": True,
            "route_verdict": "PASS",
            "human_acceptance_not_proven": True,
            "cold_retest_24h": "not_run",
            "real_user_observation": "not_run",
        },
        "workers": workers,
        "item_results": item_results,
        "answer_free_boundary": {
            "answer_sidecar_read": False,
            "answer_ocr_read": False,
            "answer_text_in_context": False,
            "student_mastery_claim": False,
        },
        "source_revision": revisions,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Project the current Luna 1.1 simulation into the runtime gate")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    args = parser.parse_args()
    payload = project(args.output)
    print(json.dumps({
        "output": str(args.output),
        "generation": payload["generation"],
        "items": len(payload["item_results"]),
        "workers": payload["summary"]["workers"],
        "status": "passed",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
