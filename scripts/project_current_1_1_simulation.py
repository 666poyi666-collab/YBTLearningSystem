"""Project current answer-isolated route-audit evidence into the legacy gate shape."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POINTER_RELATIVE = Path("reports/deep_section_simulations/current.json")
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
    POINTER_RELATIVE.as_posix(),
)
PASS_ROUTE_VERDICTS = {"route_actionable", "route_actionable_after_minimal_hint"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _item_id(item_key: str, item: dict[str, Any]) -> str:
    if item_key.startswith("LI:"):
        return item_key[3:]
    return str(item.get("label") or item_key.removeprefix("Q:"))


def project(root: Path, *, generation: str, output: Path) -> dict[str, Any]:
    pointer_path = root / POINTER_RELATIVE
    pointer = load(pointer_path)
    run_root = root / str(pointer["run_path"])
    report_path = run_root / "1.1.json"
    report = load(report_path)
    if report.get("schema_version") != "ybt-deep-section-simulation-v3":
        raise ValueError("current 1.1 route audit is not v3")
    if report.get("route_audit_status") != "passed" or report.get("mastery_claimed") is not False:
        raise ValueError("current 1.1 route audit is not a passed, non-mastery artifact")

    frozen_path = root / report["answer_isolation"]["frozen_attempts_path"]
    assessment_path = root / report["answer_isolation"]["route_assessments_path"]
    frozen_rows = load_jsonl(frozen_path)
    assessment_rows = load_jsonl(assessment_path)
    if frozen_rows[0]["_meta"].get("answer_material_loaded") is not False:
        raise ValueError("frozen attempt artifact is not answer-isolated")
    assessments = {row["attempt_id"]: row for row in assessment_rows[1:]}
    items = {str(row["item_key"]): row for row in report["items"]}
    round_five = [row for row in frozen_rows[1:] if row.get("round") == 5]
    by_profile: dict[str, list[dict[str, Any]]] = {}
    for row in round_five:
        by_profile.setdefault(str(row["persona_profile"]), []).append(row)
    if len(by_profile) != 5 or any(len(rows) != len(items) for rows in by_profile.values()):
        raise ValueError("current 1.1 route audit does not contain 5 x all-item round-five attempts")

    projection_profile = "literal-zero-base"
    projected_attempts = by_profile[projection_profile]
    context_hash = load(root / "data/contexts/1.1.json")["evidence"]["context_sha256"]
    item_results: list[dict[str, Any]] = []
    for attempt in projected_attempts:
        item_key = str(attempt["item_key"])
        item = items[item_key]
        assessment = assessments[attempt["attempt_id"]]
        if assessment.get("frozen_attempt_sha256") != attempt.get("attempt_sha256"):
            raise ValueError(f"assessment/frozen hash mismatch: {attempt['attempt_id']}")
        route_verdict = str(assessment.get("route_verdict") or "")
        item_results.append({
            "section": "1.1",
            "cycle": int(item.get("cycle_sequence") or 0),
            "item_id": _item_id(item_key, item),
            "source_revision": {
                "generation": generation,
                "authority": POINTER_RELATIVE.as_posix(),
                "run_id": pointer["run_id"],
                "round": 5,
            },
            "context_sha256": context_hash,
            "observation_signal": str(item.get("recognition_cues", [""])[0] if item.get("recognition_cues") else ""),
            "course_call": {
                "course_keys": list(attempt.get("course_call", [])),
                "method_model_id": item.get("method_model"),
                "knowledge_refs": item.get("knowledge_refs", []),
                "type_refs": item.get("type_refs", []),
            },
            "first_line": attempt.get("first_line_attempt", ""),
            "second_line": "",
            "continuation": "；".join(str(value) for value in attempt.get("continuation_attempt", [])),
            "independent_self_check": attempt.get("self_check_attempt", ""),
            "first_breakpoint": attempt.get("first_blocker"),
            "hint_level": "minimal" if attempt.get("minimal_correction_used") else "none",
            "verdict": "PASS" if route_verdict in PASS_ROUTE_VERDICTS else "FAIL",
            "evidence_level": "ANSWER_ISOLATED_ROUTE_AUDIT_ROUND_5_PROJECTION",
            "answer_sidecar_read": False,
            "mathematical_correctness": "not_evaluated_no_final_answer",
            "human_acceptance_not_proven": True,
        })

    counts = {"pass": 0, "partial": 0, "fail": 0}
    workers: list[dict[str, Any]] = []
    for profile, attempts in sorted(by_profile.items()):
        verdicts = [assessments[row["attempt_id"]].get("route_verdict") for row in attempts]
        status = "pass" if all(value in PASS_ROUTE_VERDICTS for value in verdicts) else "fail"
        counts[status] += 1
        workers.append({"persona_id": profile, "status": status, "item_count": len(attempts)})

    source_revision = {relative: sha256(root / relative) for relative in SOURCE_FILES}
    artifact = {
        "artifact": "CURRENT_GENERATION_ZERO_BASE_AGENT_SIMULATION",
        "section": "1.1",
        "generation": generation,
        "authority": {
            "kind": "answer_isolated_route_audit_projection",
            "current_pointer": POINTER_RELATIVE.as_posix(),
            "run_id": pointer["run_id"],
            "protocol": report["simulation"]["protocol"],
            "source_round": 5,
            "projection_persona": projection_profile,
            "claim_scope": "route_actionability_only",
        },
        "worker_contract": {
            "workers_dispatched": 5,
            "workers_completed": 5,
            "role": "synthetic_route_stress_persona",
            "model": "deterministic-route-audit",
            "reasoning_effort": "not_applicable",
            "context_window": None,
            "answer_sidecar_read": False,
        },
        "task_coverage": {"task_count": len(item_results), "expected_task_count": len(items), "complete": len(item_results) == len(items)},
        "summary": {
            "workers": 5,
            **counts,
            "task_coverage_complete": len(item_results) == len(items),
            "route_verdict": "PASS" if counts["pass"] == 5 else "FAIL",
            "mathematical_correctness": "not_evaluated_no_final_answer",
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
            "source_report_sha256": sha256(report_path),
            "frozen_attempts_sha256": sha256(frozen_path),
            "route_assessments_sha256": sha256(assessment_path),
            "note": "Compatibility projection only; route actionability is not mathematical correctness or mastery.",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "output": str(output),
        "generation": generation,
        "run_id": pointer["run_id"],
        "items": len(item_results),
        "worker_counts": counts,
        "source_revision": source_revision,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Project current answer-isolated 1.1 route audit into the legacy gate shape.")
    parser.add_argument("--generation", default="G-ROUTE-AUDIT-CURRENT")
    parser.add_argument("--output", type=Path, default=ROOT / OUTPUT_RELATIVE)
    args = parser.parse_args()
    print(json.dumps(project(ROOT, generation=args.generation, output=args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
