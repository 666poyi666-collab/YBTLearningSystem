#!/usr/bin/env python3
"""Build a hash-bound, scoped Luna assignment from current 一本通 packets."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(value for value in root.rglob("*") if value.is_file() and "__pycache__" not in value.parts):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def section_folder(section: str) -> str:
    return section.replace("+", "_")


def item_count(project_root: Path, section: str) -> int:
    packet = load_json(project_root / "data" / "packets" / section_folder(section) / "learning_packet.json")
    if packet.get("section") != section:
        raise ValueError(f"section mismatch: {section}")
    return sum(len(packet.get(key, [])) for key in ("worked_examples", "direct_variants", "exercise_questions"))


def parse_task(value: str) -> tuple[str, list[str]]:
    task_id, separator, sections = value.partition("=")
    parsed = [section.strip() for section in sections.split(",") if section.strip()]
    if not separator or not task_id.strip() or not parsed:
        raise argparse.ArgumentTypeError("task must be TASK_ID=section[,section]")
    return task_id.strip(), parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--requirement-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--task", action="append", required=True, type=parse_task)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    skill_root = Path(args.skill_root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = project_root / output

    ready_path = project_root / "reports" / "luna_dispatch" / "READY.json"
    packet_build_path = project_root / "reports" / "all_chapters" / "packet-build-current.json"
    course_catalog_path = project_root / "data" / "all_chapters_course_catalog.json"
    vision_sidecar_path = project_root / "data" / "vision_sidecar_all_chapters.json"
    ready = load_json(ready_path)
    packet_build = load_json(packet_build_path)
    if ready.get("status") != "ready" or packet_build.get("status") != "passed":
        raise SystemExit("current source snapshot is not ready")

    known_sections = {str(row.get("section")) for row in packet_build.get("sections", [])}
    seen: set[str] = set()
    tasks = []
    for task_id, sections in args.task:
        overlap = seen.intersection(sections)
        if overlap:
            raise SystemExit(f"duplicate section assignment: {sorted(overlap)}")
        unknown = set(sections) - known_sections
        if unknown:
            raise SystemExit(f"unknown sections: {sorted(unknown)}")
        seen.update(sections)
        tasks.append(
            {
                "task_id": task_id,
                "sections": sections,
                "expected_items": sum(item_count(project_root, section) for section in sections),
                "output_dir": f"{args.output_root.rstrip('/')}/{task_id}",
            }
        )

    assignment = {
        "schema_version": "ybt-luna-assignment-v2",
        "status": "ready",
        "requirement_id": args.requirement_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_contract": {
            "agent_type": "luna_worker",
            "model": "combo/protect-luna",
            "reasoning_effort": "max",
        },
        "target_sections": [section for _, sections in args.task for section in sections],
        "source_binding": {
            "ready_sha256": sha256_file(ready_path),
            "packet_build_sha256": sha256_file(packet_build_path),
            "course_catalog_sha256": sha256_file(course_catalog_path),
            "vision_sidecar_sha256": sha256_file(vision_sidecar_path),
            "skill_contract_sha256": sha256_tree(skill_root),
        },
        "tasks": tasks,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(assignment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(assignment, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
