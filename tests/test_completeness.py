from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ybt_learning.completeness import audit_chapter1, expected_question_keys, ocr_question_scan


ROOT = Path(__file__).resolve().parents[1]


class CompletenessAuditTests(unittest.TestCase):
    def test_current_chapter1_inventory_is_closed(self) -> None:
        result = audit_chapter1(ROOT)
        self.assertEqual(result["status"], "passed", result["findings"])
        self.assertEqual(result["packet_totals"]["total_numbered_learning_items"], 124)
        self.assertEqual(result["coverage_question_count"], 50)

    def test_expected_question_ranges_are_inclusive(self) -> None:
        self.assertEqual(expected_question_keys({"A": [1, 2], "B": [3, 4]}), {"A1", "A2", "B3", "B4"})

    def test_method_bridge_entries_always_name_a_bridge_unit(self) -> None:
        coverage = json.loads((ROOT / "data" / "question_coverage.json").read_text(encoding="utf-8"))
        for question in coverage["questions"]:
            if question.get("section") == "1.1" and question.get("unlock_class") == "METHOD_BRIDGE":
                self.assertTrue(
                    question.get("bridge_units"),
                    f"{question.get('section')}/{question.get('question_key')} has METHOD_BRIDGE without a bridge unit",
                )

    def test_ocr_scan_accepts_spacing_before_escaped_period_and_reports_out_of_range(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ocr_root = Path(temporary)
            (ocr_root / "doc_0.md").write_text(
                "# A组\n1 \\. （2025·测试）题干\n3. （2025·越界）题干\n",
                encoding="utf-8",
            )
            found, out_of_range = ocr_question_scan(ocr_root, [0, 0], {"A": [1, 2]})
        self.assertEqual(found, {"A1"})
        self.assertEqual(out_of_range, {"A3"})

    def test_missing_question_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in ("chapter1_manifest.json", "data/question_coverage.json"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
            manifest = json.loads((root / "chapter1_manifest.json").read_text(encoding="utf-8"))
            manifest["sections"] = [manifest["sections"][0]]
            manifest["source_evidence"]["learning_item_counts"] = manifest["sections"][0]["learning_item_counts"] | {
                "total_numbered_learning_items": manifest["sections"][0]["learning_item_counts"]["total"]
            }
            (root / "chapter1_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            result = audit_chapter1(root)
            self.assertEqual(result["status"], "blocked")
            self.assertTrue(any(item["code"] == "packet_missing" for item in result["findings"]))

    def test_raw_ocr_packet_catches_manifest_omission(self) -> None:
        """The generated raw OCR packet must not be allowed to outvote the manifest silently."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = json.loads((ROOT / "chapter1_manifest.json").read_text(encoding="utf-8"))
            section = next(item for item in manifest["sections"] if item["id"] == "1.1")
            section["question_groups"]["B"] = [4, 11]
            manifest["sections"] = [section]
            manifest["source_evidence"]["learning_item_counts"] = {
                "worked_examples": section["learning_item_counts"]["worked_examples"],
                "direct_variants": section["learning_item_counts"]["direct_variants"],
                "abc_exercises": section["learning_item_counts"]["abc_exercises"],
                "total_numbered_learning_items": section["learning_item_counts"]["total"],
            }
            (root / "chapter1_manifest.json").parent.mkdir(parents=True, exist_ok=True)
            (root / "chapter1_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
            )

            packet_dir = root / "data" / "packets" / "1.1"
            packet_dir.mkdir(parents=True, exist_ok=True)
            for name in ("packet.json", "learning_packet.json"):
                shutil.copy2(ROOT / "data" / "packets" / "1.1" / name, packet_dir / name)

            coverage = json.loads((ROOT / "data" / "question_coverage.json").read_text(encoding="utf-8"))
            coverage["questions"] = [item for item in coverage["questions"] if item.get("section") == "1.1"]
            coverage["question_count"] = len(coverage["questions"])
            coverage_dir = root / "data"
            coverage_dir.mkdir(parents=True, exist_ok=True)
            (coverage_dir / "question_coverage.json").write_text(
                json.dumps(coverage, ensure_ascii=False), encoding="utf-8"
            )

            result = audit_chapter1(root)
            self.assertEqual(result["status"], "blocked")
            self.assertTrue(
                any(item["code"] == "raw_ocr_packet_manifest_mismatch" for item in result["findings"]),
                result["findings"],
            )


if __name__ == "__main__":
    unittest.main()
