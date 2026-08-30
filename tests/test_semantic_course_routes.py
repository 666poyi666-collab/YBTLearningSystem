from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def manifest(chapter: int) -> dict:
    return json.loads((ROOT / f"chapter{chapter}_manifest.json").read_text(encoding="utf-8-sig"))


def section(chapter: int, section_id: str) -> dict:
    return next(row for row in manifest(chapter)["sections"] if row["id"] == section_id)


class SemanticCourseRouteTests(unittest.TestCase):
    def test_chapter2_courses_are_bound_to_reviewed_examples(self) -> None:
        expected = {
            "2.1": {"slope_angle_relation": 1, "moving_line_region": 13},
            "2.3": {"point_line_distance": 4},
            "2.6": {
                "line_circle_position": 1,
                "tangent": 2,
                "chord_length": 6,
                "longest_shortest_chord": 7,
                "line_circle_extreme": 10,
            },
        }
        for section_id, course_targets in expected.items():
            row = section(2, section_id)
            for course_key, example_number in course_targets.items():
                cycle = next(cycle for cycle in row["learning_cycles"] if course_key in cycle["course_keys"])
                self.assertIn(example_number, cycle["example_numbers"])

    def test_type_examples_and_variants_keep_the_explicit_type_role(self) -> None:
        packet = json.loads((ROOT / "data" / "packets" / "2.6" / "learning_packet.json").read_text(encoding="utf-8"))
        type_examples = [item for item in packet["worked_examples"] if item["example_number"] >= 5]
        self.assertTrue(type_examples)
        self.assertTrue(all(item["role"] == "type_example" and item["role_ref"] for item in type_examples))
        self.assertTrue(all(item["role_ref"] for item in packet["direct_variants"]))

    def test_reviewed_courses_are_placed_with_transcript_bound_evidence(self) -> None:
        row = section(5, "5.5")
        self.assertEqual(row["course_mapping_status"], "SEMANTIC_TARGETS_REVIEWED_AND_PLACED")
        self.assertEqual(row["unplaced_course_keys"], [])
        self.assertFalse(any(gap.get("kind") == "unplaced_course" for gap in row["coverage_gaps"]))
        cycles = {cycle["id"]: cycle for cycle in row["learning_cycles"]}
        for placement in row["course_mapping_review"]["placements"]:
            self.assertEqual(len(placement["transcript_sha256"]), 64)
            self.assertIn(placement["course_key"], cycles[placement["cycle_id"]][placement["field"]])

    def test_review_section_does_not_introduce_misbound_courses(self) -> None:
        row = section(5, "5.6")
        self.assertTrue(all(not cycle["course_keys"] for cycle in row["learning_cycles"]))
        self.assertEqual(row["unplaced_course_keys"], [])


if __name__ == "__main__":
    unittest.main()
