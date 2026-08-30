from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReviewedCoursePlacementTests(unittest.TestCase):
    def test_all_required_and_support_courses_are_placed_in_a_cycle(self) -> None:
        report = json.loads((ROOT / "reports/all_chapters/reviewed-course-placements.json").read_text(encoding="utf-8"))
        reviewed_sections = {row["section"] for row in report["rows"]}
        for chapter in range(1, 6):
            manifest = json.loads((ROOT / f"chapter{chapter}_manifest.json").read_text(encoding="utf-8"))
            for section in manifest["sections"]:
                if section["id"] not in reviewed_sections:
                    continue
                placed = {
                    str(course)
                    for cycle in section.get("learning_cycles", [])
                    for field in ("course_keys", "prerequisite_course_keys", "optional_course_keys")
                    for course in cycle.get(field, [])
                }
                expected = {str(course) for course in [*section.get("required_course_keys", []), *section.get("support_course_keys", [])]}
                self.assertFalse(section.get("unplaced_course_keys"), section["id"])
                self.assertTrue(expected.issubset(placed), f"{section['id']}: {sorted(expected - placed)}")

    def test_review_report_binds_every_new_placement_to_a_transcript_hash(self) -> None:
        report = json.loads((ROOT / "reports/all_chapters/reviewed-course-placements.json").read_text(encoding="utf-8"))
        self.assertEqual(report["sections"], 12)
        self.assertGreater(report["placements"], 30)
        self.assertTrue(all(len(row["transcript_sha256"]) == 64 for row in report["rows"]))


if __name__ == "__main__":
    unittest.main()
