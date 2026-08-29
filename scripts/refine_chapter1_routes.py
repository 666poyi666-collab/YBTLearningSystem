#!/usr/bin/env python3
"""Apply the reviewed chapter-one course and bridge routing corrections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "chapter1_manifest.json"

ROUTES: dict[str, dict[str, tuple[list[str], list[str]]]] = {
    "1.2+1.3": {
        "1.2_1.3-cycle-1": (["decomposition", "equal_surface"], ["space_vector_ops"]),
        "1.2_1.3-cycle-2": (["coordinate_system"], ["space_vector_ops", "decomposition"]),
        "1.2_1.3-cycle-3": (["coordinate_ops"], ["space_vector_ops", "coordinate_system"]),
        "1.2_1.3-cycle-4": ([], ["space_vector_ops", "decomposition", "equal_surface", "coordinate_ops"]),
        "1.2_1.3-cycle-5": ([], ["space_vector_ops", "coordinate_system", "coordinate_ops"]),
        "1.2_1.3-cycle-6": ([], ["coordinate_system", "coordinate_ops"]),
        "1.2_1.3-cycle-7": ([], ["coordinate_system", "coordinate_ops"]),
        "1.2_1.3-cycle-8": ([], ["coordinate_system", "coordinate_ops"]),
        "1.2_1.3-cycle-9": ([], ["decomposition", "equal_surface", "coordinate_ops"]),
        "1.2_1.3-cycle-10": ([], ["space_vector_ops", "coordinate_system", "coordinate_ops"]),
    },
    "1.4": {
        "1.4-cycle-1": (["direction_normal", "parallel_perpendicular", "coplanar"], ["coordinate_ops"]),
        "1.4-cycle-2": (["line_line_angle", "line_plane_angle", "plane_plane_angle", "plane_equation_upper", "plane_equation_lower", "distance"], ["coordinate_ops", "direction_normal", "parallel_perpendicular", "coplanar"]),
        "1.4-cycle-3": ([], ["coordinate_ops", "direction_normal", "parallel_perpendicular", "coplanar", "plane_plane_angle"]),
        "1.4-cycle-4": ([], ["coordinate_ops", "direction_normal", "parallel_perpendicular", "line_line_angle", "line_plane_angle", "plane_plane_angle", "distance"]),
        "1.4-cycle-5": ([], ["coordinate_ops", "direction_normal", "parallel_perpendicular", "line_plane_angle", "plane_plane_angle", "plane_equation_upper", "plane_equation_lower", "distance"]),
        "1.4-cycle-6": (["moving_point"], ["coordinate_ops", "direction_normal", "parallel_perpendicular", "coplanar", "line_plane_angle", "plane_plane_angle", "distance"]),
        "1.4-cycle-7": ([], ["coordinate_ops", "direction_normal", "parallel_perpendicular", "coplanar", "line_plane_angle", "plane_plane_angle", "distance", "moving_point"]),
    },
    "micro专题1": {
        "micro-cycle-1": ([], ["direction_normal", "line_plane_angle", "distance", "moving_point"]),
        "micro-cycle-2": ([], ["direction_normal", "parallel_perpendicular", "line_plane_angle", "plane_equation_upper"]),
        "micro-cycle-3": ([], ["direction_normal", "parallel_perpendicular", "line_line_angle", "line_plane_angle", "plane_plane_angle", "distance", "moving_point"]),
        "micro-cycle-4": ([], ["direction_normal", "parallel_perpendicular", "line_line_angle", "plane_plane_angle", "moving_point"]),
        "micro-cycle-5": ([], ["direction_normal", "plane_equation_upper", "distance", "moving_point"]),
        "micro-cycle-6": ([], ["direction_normal", "parallel_perpendicular", "line_plane_angle", "plane_plane_angle", "moving_point"]),
    },
}

BRIDGE_TARGETS = {
    "bridge-1.1-polarization": ["B8", "C15"],
    "bridge-1.2-apollonius": ["C16"],
    "bridge-1.2-single-variable": [],
    "bridge-1.4-folding": ["C10"],
    "bridge-1.4-dihedral-trig": ["C11"],
    "bridge-micro-existence": ["C6", "C12"],
    "bridge-micro-completion": ["C7", "C8"],
}

CYCLE_BRIDGES = {
    "1.2_1.3-cycle-4": [],
    "1.2_1.3-cycle-9": [],
    "1.2_1.3-cycle-10": ["bridge-1.1-polarization", "bridge-1.2-apollonius"],
    "1.4-cycle-5": [],
    "1.4-cycle-6": ["bridge-micro-completion"],
    "1.4-cycle-7": ["bridge-1.4-folding", "bridge-micro-existence"],
    "micro-cycle-1": ["bridge-1.2-single-variable"],
    "micro-cycle-4": ["bridge-1.4-folding", "bridge-1.4-dihedral-trig"],
    "micro-cycle-5": ["bridge-micro-sphere", "bridge-micro-existence"],
    "micro-cycle-6": ["bridge-micro-completion"],
}


def main() -> int:
    manifest: dict[str, Any] = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    seen_cycles: set[str] = set()
    seen_bridges: set[str] = set()
    for section in manifest.get("sections", []):
        section_id = str(section.get("id"))
        route = ROUTES.get(section_id)
        for cycle in section.get("learning_cycles", []):
            cycle_id = str(cycle.get("id"))
            if route and cycle_id in route:
                cycle["course_keys"], cycle["prerequisite_course_keys"] = route[cycle_id]
                cycle["course_mapping_status"] = "SEMANTIC_REVIEWED"
                seen_cycles.add(cycle_id)
            if cycle_id in CYCLE_BRIDGES:
                cycle["bridge_unit_ids"] = CYCLE_BRIDGES[cycle_id]
        for bridge in section.get("bridge_units", []):
            bridge_id = str(bridge.get("id"))
            if bridge_id in BRIDGE_TARGETS:
                bridge["target_questions"] = BRIDGE_TARGETS[bridge_id]
                seen_bridges.add(bridge_id)
    expected_cycles = {cycle for route in ROUTES.values() for cycle in route}
    if seen_cycles != expected_cycles:
        raise ValueError(f"chapter-one route cycle mismatch: {sorted(expected_cycles - seen_cycles)}")
    missing_bridges = set(BRIDGE_TARGETS) - seen_bridges
    if missing_bridges:
        raise ValueError(f"chapter-one bridge mismatch: {sorted(missing_bridges)}")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "cycles": len(seen_cycles), "bridges": len(seen_bridges)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
