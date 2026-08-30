from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.export_all_section_routes import all_sections, render_section


ROOT = Path(__file__).resolve().parents[1]


class AllSectionRouteTests(unittest.TestCase):
    def test_every_section_renders_all_items_without_answers(self) -> None:
        catalog_payload = json.loads((ROOT / "data/all_chapters_course_catalog.json").read_text(encoding="utf-8"))
        catalog = {str(row["course_key"]): row for row in catalog_payload["courses"]}
        total = 0
        for chapter, section in all_sections():
            section_id = str(section["id"])
            packet = json.loads((ROOT / "data/packets" / section_id.replace("+", "_") / "learning_packet.json").read_text(encoding="utf-8"))
            rendered = render_section(chapter, section, packet, catalog)
            self.assertIn("本节课程顺序", rendered)
            self.assertIn("卡住时怎么写", rendered)
            self.assertNotIn("正确答案", rendered)
            self.assertNotIn("answer_sidecar", rendered)
            total += int(packet["counts"]["total_numbered_learning_items"])
        self.assertEqual(total, 1209)


if __name__ == "__main__":
    unittest.main()
