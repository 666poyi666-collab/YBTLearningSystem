#!/usr/bin/env python3
"""Focused semantic tests for the v2 learner-simulation validator."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate_section_delivery.py")
SPEC = importlib.util.spec_from_file_location("ybt_validator", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def build_section() -> tuple[dict, dict[str, dict]]:
    items = {
        f"LI:item-{index}": {
            "item_key": f"LI:item-{index}",
            "course_refs": ["course-a"],
        }
        for index in range(1, 7)
    }
    route_versions = [
        {"version": round_number, "route_hash": f"route-{round_number}"}
        for round_number in range(1, 6)
    ]
    rounds = []
    profiles = sorted(VALIDATOR.PERSONAS)
    for round_number in range(1, 6):
        personas = []
        for persona_index, profile in enumerate(profiles, start=1):
            results = []
            for item_index, item_key in enumerate(items, start=1):
                results.append(
                    {
                        "item_key": item_key,
                        "course_call": ["course-a"],
                        "recognition_statement": f"R{round_number} P{persona_index} item {item_index} cue",
                        "first_line_attempt": f"R{round_number} P{persona_index} item {item_index} first line",
                        "continuation_attempt": [f"item {item_index} action", f"persona {persona_index} check"],
                        "self_check_attempt": f"R{round_number} P{persona_index} item {item_index} self check",
                        "recognized_method": True,
                        "first_line_written": True,
                        "continuation_complete": True,
                        "self_check_complete": True,
                        "first_blocker": None,
                        "correction_used": None,
                        "verdict": "passed",
                    }
                )
            personas.append(
                {
                    "persona_id": f"R{round_number}-P{persona_index}",
                    "profile": profile,
                    "item_results": results,
                }
            )
        rounds.append(
            {
                "round": round_number,
                "route_version": round_number,
                "route_hash": f"route-{round_number}",
                "personas": personas,
                "failed_item_keys": [],
                "route_repairs": [],
            }
        )
    section = {
        "section": "test",
        "route_versions": route_versions,
        "final_route_hash": "route-5",
        "simulation": {
            "protocol": "five-round-five-persona-v2",
            "rounds": rounds,
            "actual_attempts_per_item": {key: 25 for key in items},
            "unresolved_item_keys": [],
            "status": "passed",
        },
    }
    return section, items


class SimulationValidatorTests(unittest.TestCase):
    def test_valid_v2_simulation_passes(self) -> None:
        section, items = build_section()
        self.assertEqual([], VALIDATOR.validate_simulation(section, items))

    def test_failed_list_cannot_contradict_passed_attempts(self) -> None:
        section, items = build_section()
        section["simulation"]["rounds"][3]["failed_item_keys"] = list(items)
        errors = VALIDATOR.validate_simulation(section, items)
        self.assertTrue(any("failed_item_keys mismatch" in error for error in errors))

    def test_boolean_only_attempts_fail(self) -> None:
        section, items = build_section()
        result = section["simulation"]["rounds"][0]["personas"][0]["item_results"][0]
        for field in (
            "course_call",
            "recognition_statement",
            "first_line_attempt",
            "continuation_attempt",
            "self_check_attempt",
        ):
            result.pop(field)
        errors = VALIDATOR.validate_simulation(section, items)
        self.assertTrue(any("missing attempt fields" in error for error in errors))

    def test_bulk_copied_attempts_fail(self) -> None:
        section, items = build_section()
        for persona in section["simulation"]["rounds"][0]["personas"]:
            template = copy.deepcopy(persona["item_results"][0])
            for result in persona["item_results"]:
                item_key = result["item_key"]
                result.update(copy.deepcopy(template))
                result["item_key"] = item_key
        errors = VALIDATOR.validate_simulation(section, items)
        self.assertTrue(any("excessively generic" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
