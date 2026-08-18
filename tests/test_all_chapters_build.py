from __future__ import annotations

import unittest

from scripts.build_all_chapters import CHAPTERS, COURSE_DIRS, load_json, manifest_totals, section_folder


class AllChaptersBuildTests(unittest.TestCase):
    def test_current_manifest_totals_are_exact(self) -> None:
        manifests = {
            chapter: load_json(config["manifest"])
            for chapter, config in CHAPTERS.items()
        }
        self.assertEqual(
            manifest_totals(manifests),
            {
                "chapters": 5,
                "sections": 38,
                "worked_examples": 379,
                "direct_variants": 284,
                "abc_exercises": 546,
                "total_numbered_learning_items": 1209,
            },
        )

    def test_allowed_course_roots_exclude_pollution_sources(self) -> None:
        self.assertEqual(len(COURSE_DIRS), 8)
        joined = "\n".join(COURSE_DIRS)
        self.assertNotIn("老人", joined)
        self.assertNotIn("8.5g", joined)
        self.assertNotIn("数学摄像头", joined)

    def test_section_folder_is_stable_for_combined_section(self) -> None:
        self.assertEqual(section_folder("1.2+1.3"), "1.2_1.3")
        self.assertEqual(section_folder("ch3.s13"), "ch3.s13")


if __name__ == "__main__":
    unittest.main()
