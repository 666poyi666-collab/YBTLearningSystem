#!/usr/bin/env python3
"""Validate optional exam routes against current chapter cycle identities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/exam_papers/manifest.json"))
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    cycle_ids = {
        str(cycle["id"])
        for chapter in range(1, 6)
        for section in json.loads(Path(f"chapter{chapter}_manifest.json").read_text(encoding="utf-8-sig"))["sections"]
        for cycle in section.get("learning_cycles", [])
    }
    section_ids = {
        str(section["id"])
        for chapter in range(1, 6)
        for section in json.loads(Path(f"chapter{chapter}_manifest.json").read_text(encoding="utf-8-sig"))["sections"]
    }
    errors = []
    for route in payload.get("routes", []):
        route_id = str(route.get("route_id") or "missing-route-id")
        if route.get("optional") is not True or route.get("blocks_ybt_progress") is not False:
            errors.append(f"{route_id}:exam_route_must_be_optional_non_blocking")
        if route.get("mapping_status") not in {"candidate", "visually_verified", "semantically_verified"}:
            errors.append(f"{route_id}:invalid_mapping_status")
        errors.extend(f"{route_id}:unknown_cycle:{value}" for value in route.get("required_cycle_ids", []) if value not in cycle_ids)
        errors.extend(f"{route_id}:unknown_section:{value}" for value in route.get("required_section_ids", []) if value not in section_ids)
        if not route.get("question_ref"):
            errors.append(f"{route_id}:missing_question_ref")
    print(json.dumps({"status": "passed" if not errors else "failed", "routes": len(payload.get("routes", [])), "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
