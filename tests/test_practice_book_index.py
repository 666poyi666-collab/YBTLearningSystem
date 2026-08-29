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

    def test_page_and_item_routes_are_consistent_and_cycles_exist(self) -> None:
        manifests = {
            chapter: json.loads((ROOT / f"chapter{chapter}_manifest.json").read_text(encoding="utf-8"))
            for chapter in (1, 2, 3)
        }
        valid_cycles = {
            str(cycle["id"])
            for manifest in manifests.values()
            for section in manifest["sections"]
            for cycle in section.get("learning_cycles", [])
        }
        by_page = {page["pdf_page"]: page for page in self.payload["pages"]}
        for item in self.payload["items"]:
            page = by_page[item["pdf_page"]]
            self.assertEqual(item["section"], page["section"])
            self.assertEqual(item["unit"], page["unit"])
            self.assertEqual(item["course_keys"], page["course_keys"])
            self.assertTrue(set(item["cycle_ids"]).issubset(page["cycle_ids"]))
            self.assertFalse(set(item["cycle_ids"]) - valid_cycles)

    def test_combined_review_pages_do_not_claim_single_section_cycles(self) -> None:
        pages = {page["printed_page"]: page for page in self.payload["pages"] if page["printed_page"]}
        self.assertEqual(pages[48]["section"], "2.6+2.7-review")
        self.assertEqual(pages[48]["cycle_ids"], [])
        self.assertEqual(pages[78]["section"], "ch3.s3+ch3.s6-review")
        self.assertEqual(pages[78]["cycle_ids"], [])
        self.assertEqual(pages[79]["section"], "ch3.s9")
        self.assertFalse(any(cycle.startswith("ch3.s10-") for cycle in pages[79]["cycle_ids"]))
        self.assertEqual(pages[80]["section"], "chapter-3")
        self.assertEqual(pages[80]["cycle_ids"], [])

    def test_source_anchored_page_repairs_and_level_inheritance(self) -> None:
        by_page: dict[int, list[dict]] = {}
        for item in self.payload["items"]:
            by_page.setdefault(item["printed_page"], []).append(item)
        self.assertEqual([item["question_number"] for item in by_page[78]], list(range(1, 10)))
        self.assertEqual([item["question_number"] for item in by_page[80]], list(range(1, 6)))
        self.assertTrue(all(item["cadence"] == "after_section" for item in by_page[15]))
        self.assertTrue(all(item["cadence"] == "after_section" for item in by_page[18]))
        self.assertTrue(all(item["cadence"] == "after_section" for item in by_page[22]))


if __name__ == "__main__":
    unittest.main()
