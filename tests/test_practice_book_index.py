from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "tmp" / "practice-book-index" / "index.json"


class PracticeBookIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not INDEX.is_file():
            raise unittest.SkipTest("practice-book OCR index has not been generated")
        cls.payload = json.loads(INDEX.read_text(encoding="utf-8"))

    def test_index_is_source_bound_and_unique(self) -> None:
        payload = self.payload
        self.assertEqual(payload["schema_version"], "math-practice-book-index-v1")
        self.assertEqual(payload["page_count"], 106)
        self.assertEqual(payload["source_pdf_sha256"], "d08ef016908977cd52872ce604daa4fd83991c51268b42638155c194a078d928")
        ids = [item["item_id"] for item in payload["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 727)

    def test_first_chapter_items_have_page_and_route_evidence(self) -> None:
        items = [item for item in self.payload["items"] if item["chapter"] == "1"]
        self.assertEqual(len(items), 194)
        self.assertTrue(all(item["pdf_page"] == item["printed_page"] + 8 for item in items))
        self.assertTrue(all(item["section"] and item["unit"] and item["cadence"] for item in items))
        self.assertTrue(all(item["visual_status"] == "NEEDS_SOURCE_PAGE_REVIEW" for item in items))
        self.assertTrue(all(item["answer_status"] == "not_in_source_pdf" for item in items))

    def test_course_mapping_is_not_invented_for_unmapped_units(self) -> None:
        for item in self.payload["items"]:
            if item["chapter"] == "1" and item["section"] in {"chapter-1", "micro专题1"}:
                self.assertEqual(item["course_keys"], [] if item["section"] == "chapter-1" else ["moving_point"])


if __name__ == "__main__":
    unittest.main()
