from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_luna_ready import (
    FORMULA_ANCHORS,
    _validate_answer_isolation,
    _validate_visual_sidecar,
    sha256_file,
)
from ybt_learning.vision import GLM_VISION_MODEL


class LunaReadyTests(unittest.TestCase):
    def test_formula_gate_includes_ch3_s5_doc_88(self) -> None:
        self.assertIn(("ch3.s5", 88), FORMULA_ANCHORS)

    def test_visual_gate_uses_frozen_inventory_count(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "diagram.jpg"
            image.write_bytes(b"diagram")
            inventory = root / "visual-inventory-source-question-only.json"
            inventory.write_text("{}", encoding="utf-8")
            digest = sha256_file(image)
            errors: list[str] = []
            result = _validate_visual_sidecar(
                {
                    "status": "passed",
                    "target_count": 1,
                    "passed_count": 1,
                    "inventory_path": str(inventory),
                    "inventory_sha256": sha256_file(inventory),
                    "results": [
                        {
                            "status": "passed",
                            "question_hint": "1.1-A1",
                            "image": str(image),
                            "image_sha256": digest,
                            "model": GLM_VISION_MODEL,
                            "confidence": "E2",
                            "structured": {
                                "objects": ["点A"],
                                "relations": [],
                                "coordinates": [],
                                "ranges": [],
                                "text": ["A"],
                                "uncertainties": [],
                            },
                        }
                    ],
                },
                root,
                inventory,
                sha256_file(inventory),
                1,
                errors,
            )
            self.assertEqual(result, {"target_count": 1, "passed_count": 1})
            self.assertEqual(errors, [])

    def test_answer_isolation_rejects_unmarked_option_judgement(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "student_packet.json").write_text(
                json.dumps({"answer_sidecar": None, "questions": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            (root / "student_learning_items.json").write_text(
                json.dumps({"direct_variants": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            errors: list[str] = []
            _validate_answer_isolation(
                "4.3",
                root,
                {
                    "knowledge_and_type_pages": [],
                    "direct_variants": [{"question_text": "推导后，故 A 项错误"}],
                    "exercise_questions": [],
                },
                errors,
            )
            self.assertIn("learning_packet_answer_leak:4.3", errors)

    def test_answer_isolation_accepts_clean_question_only_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "student_packet.json").write_text(
                json.dumps(
                    {"answer_sidecar": None, "questions": [{"question_text": "题干"}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "student_learning_items.json").write_text(
                json.dumps({"direct_variants": [{"question_text": "题干"}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            errors: list[str] = []
            _validate_answer_isolation(
                "4.3",
                root,
                {
                    "knowledge_and_type_pages": [],
                    "direct_variants": [{"question_text": "题干"}],
                    "exercise_questions": [],
                },
                errors,
            )
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
