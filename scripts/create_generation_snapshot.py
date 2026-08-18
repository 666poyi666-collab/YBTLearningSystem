from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ybt_learning.completeness import audit_chapter1
from scripts.generate_acceptance_report import load_current_simulation


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_tree(paths: list[Path], root: Path) -> tuple[str, dict[str, str]]:
    files: dict[str, str] = {}
    for path in sorted({item.resolve() for item in paths if item.is_file()}):
        relative = path.relative_to(root.resolve()).as_posix()
        files[relative] = sha256_file(path)
    digest = hashlib.sha256()
    for relative, value in files.items():
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), files


def _load(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.is_file():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _input_groups(root: Path) -> dict[str, list[Path]]:
    return {
        "route": [
            root / "chapter1_manifest.json",
            root / "data" / "chapter1_learning_plan.json",
            root / "data" / "question_coverage.json",
            root / "data" / "bridge_micro_lessons.json",
            *sorted((root / "data" / "packets").glob("*/learning_path_without_questions.md")),
        ],
        "packets": list((root / "data" / "packets").glob("*/learning_packet.json")),
        "student_inputs": list((root / "data" / "packets").glob("*/student_learning_items.json")),
        "contexts": list((root / "data" / "contexts").glob("*.json")),
        "tests": list((root / "tests").glob("*.py")),
        "standards": [root / "data" / "zero_base_simulation_standard.md"],
        "student_evidence": [
            root / "reports" / "zero_base_cycles" / "1.1-current-agent-simulation.json",
            root / "reports" / "zero_base_cycles" / "chapter1-current-simulation-status.json",
            root / "reports" / "zero_base_cycles" / "chapter1-current-agent-simulation.json",
            root / "reports" / "luna_sections" / "LUNA-YBT-05" / "delivery.json",
            root / "scripts" / "merge_chapter_zero_base_simulations.py",
            root / "scripts" / "generate_chapter_simulation_status.py",
            *sorted((root / "reports" / "zero_base_cycles").glob("1.2_1.3-structured-worker-g11.json")),
            *sorted((root / "reports" / "zero_base_cycles").glob("1.4-structured-worker-g11.json")),
            *sorted((root / "reports" / "zero_base_cycles").glob("micro专题1-structured-worker-g11.json")),
            *sorted((root / "reports" / "zero_base_cycles").glob("1.1-structured-worker-*.json")),
            root / "scripts" / "merge_structured_zero_base_simulation.py",
            root / "reports" / "final-teacher-judge-current.json",
        ],
    }


def create_snapshot(root: Path, generation: str, previous: Path | None = None) -> dict[str, Any]:
    groups = _input_groups(root)
    revisions: dict[str, dict[str, Any]] = {}
    for name, paths in groups.items():
        revision, files = hash_tree(paths, root)
        revisions[name] = {"sha256": revision, "files": files}

    completeness = audit_chapter1(root)
    final_acceptance = _load(root / "reports" / "final-acceptance.json")
    coverage = _load(root / "data" / "question_coverage.json")
    simulation_meta, simulation = load_current_simulation(root)
    chapter_status = _load(root / "reports" / "zero_base_cycles" / "chapter1-current-simulation-status.json")
    previous_data = _load(previous) if previous else {}
    previous_revisions = previous_data.get("revisions", {})
    changed_groups = [
        name
        for name, value in revisions.items()
        if previous_revisions.get(name, {}).get("sha256") != value["sha256"]
    ]

    all_questions_release = (
        coverage.get("summary", {}).get("attempt_ready_gate") is True
        and coverage.get("summary", {}).get("full_every_question_release_gate") is True
    )
    simulation_mastery_passed = simulation_meta.get("mastery_status") == "passed"
    chapter_simulation_ready = chapter_status.get("summary", {}).get("all_current_section_simulations_ready") is True
    simulation_generation_matches = simulation_meta.get("generation") == generation
    snapshot_files = {
        relative: digest
        for group in revisions.values()
        for relative, digest in group.get("files", {}).items()
    }
    simulation_source_matches_snapshot = bool(simulation_meta.get("source_revision")) and all(
        snapshot_files.get(relative) == digest
        for relative, digest in simulation_meta.get("source_revision", {}).items()
    )
    route_status = (
        "ROUTE_COMPLETE"
        if completeness["status"] == "passed"
        and all_questions_release
        and simulation_mastery_passed
        and chapter_simulation_ready
        and simulation_generation_matches
        and simulation_source_matches_snapshot
        else "IN_PROGRESS_NOT_PUBLISHABLE"
    )
    return {
        "schema_version": 1,
        "artifact": "LEARNING_ROUTE_GENERATION_SNAPSHOT",
        "generation": generation,
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "scope": "第一章当前路线；扩展章节必须另建章节级快照",
        "revisions": revisions,
        "changed_groups_from_previous": changed_groups,
        "completeness": completeness,
        "release_gates": {
            "all_questions_release": all_questions_release,
            "attempt_ready_gate": coverage.get("summary", {}).get("attempt_ready_gate"),
            "full_every_question_release_gate": coverage.get("summary", {}).get("full_every_question_release_gate"),
            "final_acceptance_status": final_acceptance.get("overall_status", "unknown"),
            "current_zero_base_simulation_evidence": simulation_meta.get("status"),
            "current_zero_base_simulation_generation": simulation_meta.get("generation"),
            "current_zero_base_simulation_generation_matches_snapshot": simulation_generation_matches,
            "current_zero_base_simulation_source_revision_match": simulation_meta.get("source_revision_match"),
            "current_zero_base_simulation_source_matches_snapshot": simulation_source_matches_snapshot,
            "current_zero_base_simulation_mastery_gate": simulation_mastery_passed,
            "current_zero_base_simulation_summary": simulation.get("summary", {}),
            "chapter_zero_base_simulation_ready": chapter_simulation_ready,
            "chapter_zero_base_simulation_summary": chapter_status.get("summary", {}),
        },
        "simulation_boundary": {
            "proxy_results_can_be_recorded": True,
            "human_acceptance_not_proven": True,
            "cold_retest_24h": "not_run",
            "real_user_observation": "not_run",
            "simulation_source": simulation_meta,
            "chapter_simulation_status": chapter_status,
        },
        "verdict": route_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze a hash-bound learning route generation")
    parser.add_argument("--generation", required=True, help="For example G-20260816-01")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()

    snapshot = create_snapshot(ROOT, args.generation, args.previous)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "generation": args.generation, "verdict": snapshot["verdict"], "changed_groups": snapshot["changed_groups_from_previous"]}, ensure_ascii=False))
    return 0 if snapshot["verdict"] == "ROUTE_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
