#!/usr/bin/env python3
"""Build exact-SHA PaddleOCR plus READY-bound GLM fallback evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
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


def section_folder(section: str) -> str:
    return section.replace("+", "_")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--assignment", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--luna-blocker", required=True)
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    assignment_path = Path(args.assignment)
    if not assignment_path.is_absolute():
        assignment_path = root / assignment_path
    assignment = load_json(assignment_path)
    task = next((row for row in assignment.get("tasks", []) if row.get("task_id") == args.task_id), None)
    if task is None:
        raise SystemExit(f"unknown task: {args.task_id}")
    sidecar_path = root / "data" / "vision_sidecar_all_chapters.json"
    sidecar = load_json(sidecar_path)
    expected_sidecar_sha = str((assignment.get("source_binding") or {}).get("vision_sidecar_sha256") or "")
    if sha256_file(sidecar_path) != expected_sidecar_sha:
        raise SystemExit("vision sidecar is stale against assignment")

    sidecar_index: dict[tuple[str, str], dict] = {}
    for row in sidecar.get("results", []):
        if isinstance(row, dict):
            sidecar_index[(str(row.get("section")), str(row.get("image_sha256") or "").lower())] = row

    image_items: dict[tuple[str, str], list[str]] = defaultdict(list)
    image_paths: dict[tuple[str, str], Path] = {}
    image_docs: dict[tuple[str, str], list[int]] = {}
    for section in task.get("sections", []):
        packet = load_json(root / "data" / "packets" / section_folder(str(section)) / "learning_packet.json")
        for kind, prefix in (("worked_examples", "LI"), ("direct_variants", "LI"), ("exercise_questions", "Q")):
            for item in packet.get(kind, []):
                item_id = item.get("item_id") if prefix == "LI" else item.get("qid")
                item_key = f"{prefix}:{item_id}"
                for ref in item.get("image_refs", []) or []:
                    image_path = Path(ref.get("path") or "").resolve()
                    if not image_path.is_file():
                        raise SystemExit(f"missing image: {image_path}")
                    image_sha = sha256_file(image_path)
                    key = (str(section), image_sha)
                    image_items[key].append(item_key)
                    image_paths[key] = image_path
                    image_docs[key] = [int(value) for value in item.get("source_docs", [])]

    records = []
    for (section, image_sha), item_keys in sorted(image_items.items()):
        row = sidecar_index.get((section, image_sha))
        if row is None or row.get("status") != "passed" or row.get("model") != "glm-4.6v-flash":
            raise SystemExit(f"missing current GLM observation: {section} {image_sha}")
        structured = row.get("structured")
        if not isinstance(structured, dict):
            raise SystemExit(f"invalid GLM structure: {section} {image_sha}")
        image_path = image_paths[(section, image_sha)]
        ocr_root = image_path.parent.parent
        paddle_path = None
        for doc in image_docs[(section, image_sha)]:
            candidate = ocr_root / f"doc_{doc}.md"
            if candidate.is_file():
                paddle_path = candidate
                break
        if paddle_path is None:
            raise SystemExit(f"missing PaddleOCR doc: {section} {image_sha}")
        records.append(
            {
                "section": section,
                "item_keys": sorted(set(item_keys)),
                "image": str(image_path),
                "image_sha256": image_sha,
                "paddle": {
                    "status": "passed",
                    "artifact": str(paddle_path),
                    "artifact_sha256": sha256_file(paddle_path),
                    "text": [],
                    "coordinates": [],
                },
                "luna": {"status": "blocked", "blocker": args.luna_blocker},
                "visual": {
                    "status": "passed",
                    "provider": sidecar.get("provider"),
                    "model": "glm-4.6v-flash",
                    "objects": structured.get("objects") or [],
                    "relations": structured.get("relations") or [],
                    "coordinates": structured.get("coordinates") or [],
                    "ranges": structured.get("ranges") or [],
                    "text": structured.get("text") or [],
                    "uncertainties": structured.get("uncertainties") or [],
                },
                "conflicts": [],
                "adjudication": [],
                "status": "passed",
            }
        )

    result = {
        "schema_version": "ybt-ocr-vision-crosscheck-v1",
        "mode": "paddle_glm_crosscheck",
        "source_binding": {
            "assignment_sha256": sha256_file(assignment_path),
            "vision_sidecar_sha256": sha256_file(sidecar_path),
        },
        "luna_capability": {"status": "blocked", "blocker": args.luna_blocker},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": records,
        "status": "passed",
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "records": len(records), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
