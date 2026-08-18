from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ybt_learning.packet import (
    PacketBuilder,
    PacketError,
    _extract_learning_items,
    _extract_knowledge_blocks,
    _usable_vision_sidecar,
)


def section(question_range: list[int]) -> dict:
    return {
        "id": "test",
        "label": "派生题号纠正测试",
        "ocr_docs": [0, 0],
        "question_groups": {"B": question_range},
        "knowledge_points": [],
        "learning_cycles": [],
    }


class DerivedQuestionCorrectionTests(unittest.TestCase):
    def build(self, text: str, question_range: list[int], corrections: list[dict]) -> dict:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ocr = root / "ocr"
            out = root / "packets"
            ocr.mkdir()
            (ocr / "doc_0.md").write_text(text, encoding="utf-8")
            packet = PacketBuilder(ocr_root=ocr, output_root=out).build_section(
                section(question_range),
                visual_sidecar={"derived_question_corrections": corrections},
            )
            student = json.loads((out / "test" / "student_packet.json").read_text(encoding="utf-8"))
            return {"packet": packet, "student": student}

    def test_misread_b13_does_not_replace_real_b15(self) -> None:
        result = self.build(
            "## B组 强化能力\n15.（2023·黑龙江答案模拟）\n误读的第13题题面足够长。\n"
            "14. 真正的第14题题面。\n15. 真正的第15题题面。\n",
            [13, 15],
            [
                {
                    "id": "fix-b13",
                    "section": "test",
                    "source_doc": 0,
                    "action": "replace_line",
                    "match_text": "15.（2023·黑龙江答案模拟）",
                    "replacement": "13.（2025·黑龙江哈尔滨模拟）",
                    "expected_matches": 1,
                    "evidence": "source-page",
                }
            ],
        )
        questions = {(item["group"], item["number"]): item for item in result["packet"]["questions"]}
        self.assertEqual(set(questions), {("B", 13), ("B", 14), ("B", 15)})
        self.assertIn("误读的第13题题面", questions[("B", 13)]["question_text"])
        self.assertIn("真正的第15题题面", questions[("B", 15)]["question_text"])
        self.assertEqual(result["packet"]["manifest"]["derived_question_correction_count"], 1)

    def test_result_line_is_removed_from_question_and_student_page(self) -> None:
        result = self.build(
            "## B组 强化能力\n16. 数列的通项公式已知，求参数范围。\n"
            "16. $\\left(-\\infty, \\frac{3}{2}\\right)$\n",
            [16, 16],
            [
                {
                    "id": "drop-answer-line",
                    "section": "test",
                    "source_doc": 0,
                    "action": "remove_line",
                    "match_text": r"16. \(\left(-\infty, \frac{3}{2}\right)\)",
                    "expected_matches": 1,
                    "evidence": "primary-ocr",
                }
            ],
        )
        self.assertEqual(len(result["packet"]["questions"]), 1)
        self.assertNotIn("infty", result["packet"]["questions"][0]["question_text"])
        self.assertNotIn("infty", result["student"]["pages"][0]["text"])

    def test_correction_is_fail_closed_when_anchor_does_not_match(self) -> None:
        with self.assertRaises(PacketError):
            self.build(
                "## B组\n16. 实际题面。\n",
                [16, 16],
                [
                    {
                        "id": "missing-anchor",
                        "section": "test",
                        "source_doc": 0,
                        "action": "remove_line",
                        "match_text": "16. 不存在的答案行",
                        "expected_matches": 1,
                    }
                ],
            )

    def test_prefix_correction_repairs_long_corrupted_option_line(self) -> None:
        result = self.build(
            "## B组 强化能力\n"
            "1. 选择符合条件的方程。\n"
            "A. $x=1$ \\quad \\quad $\n",
            [1, 1],
            [
                {
                    "id": "repair-long-option",
                    "section": "test",
                    "source_doc": 0,
                    "action": "replace_line",
                    "match_prefix": r"A. \(x=1\)",
                    "replacement": r"A. \(x=1\)",
                    "expected_matches": 1,
                    "evidence": "source-page",
                }
            ],
        )
        self.assertEqual(result["packet"]["status"], "VERIFIED")
        self.assertNotIn("unbalanced_dollar", result["packet"]["unresolved"])

    def test_visual_sidecar_rejects_answer_book_payload(self) -> None:
        self.assertFalse(
            _usable_vision_sidecar(
                {
                    "status": "passed",
                    "confidence": "E1",
                    "structured": {"text": "答案册解析", "objects": ["triangle"]},
                }
            )
        )

    def test_learning_item_visual_blocks_learning_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ocr = root / "ocr"
            out = root / "packets"
            images = ocr / "imgs"
            images.mkdir(parents=True)
            (images / "example.png").write_bytes(b"not-a-real-png-but-content-bound")
            (ocr / "doc_0.md").write_text(
                "## 知识点 1：图形关系\n"
                "先识别图中对象及其位置关系。\n"
                "【例1】观察下图并判断关系。\n"
                '<img src="imgs/example.png" />\n'
                "## B组 强化能力\n"
                "1. 不依赖图片的独立习题。\n",
                encoding="utf-8",
            )
            packet = PacketBuilder(ocr_root=ocr, output_root=out).build_section(
                {
                    **section([1, 1]),
                    "knowledge_points": [{"id": "K1", "examples": ["例1"]}],
                }
            )
            learning = json.loads(
                (out / "test" / "learning_packet.json").read_text(encoding="utf-8")
            )
            student_items = json.loads(
                (out / "test" / "student_learning_items.json").read_text(encoding="utf-8")
            )
            self.assertEqual(packet["status"], "VERIFIED")
            self.assertEqual(learning["status"], "UNVERIFIED")
            self.assertEqual(student_items["status"], "UNVERIFIED")
            self.assertTrue(any("NEEDS_VISION_SIDECAR" in item for item in learning["unresolved"]))

    def test_inline_example_marker_starts_a_new_item(self) -> None:
        items = _extract_learning_items(
            [
                {
                    "ocr_doc": 0,
                    "source_path": "doc_0.md",
                    "text": "【例 10】上一题。\n解析：上一题过程。答案：1【例 11】下一题题面。",
                }
            ],
            {
                "id": "test",
                "knowledge_points": [
                    {"id": "K1", "examples": ["例10", "例11"]},
                ],
                "type_training": [],
            },
        )
        self.assertEqual(
            [item["example_number"] for item in items["worked_examples"]],
            [10, 11],
        )
        self.assertIn("下一题题面", items["worked_examples"][1]["question_text"])

    def test_duplicate_direct_variant_is_collapsed_by_parent_and_text(self) -> None:
        items = _extract_learning_items(
            [
                {
                    "ocr_doc": 0,
                    "source_path": "doc_0.md",
                    "text": (
                        "【例6】基础题。\n"
                        "【变式1】同一道变式题。\n"
                        "【变式 1】同一道变式题。\n"
                    ),
                }
            ],
            {
                "id": "test",
                "knowledge_points": [{"id": "K1", "examples": ["例6"]}],
                "type_training": [],
            },
        )
        self.assertEqual(len(items["direct_variants"]), 1)
        self.assertEqual(len(items["deduplicated_items"]), 1)

    def test_inline_knowledge_heading_is_split_from_previous_paragraph(self) -> None:
        blocks = _extract_knowledge_blocks(
            [
                {
                    "text": (
                        "## 知识点 1：定义\n第一块内容。\n"
                        "上一段结尾。知识点 2：通项公式\n第二块内容。"
                    )
                }
            ],
            {
                "id": "test",
                "knowledge_points": [
                    {"id": "K1", "label": "定义", "examples": []},
                    {"id": "K2", "label": "通项公式", "examples": []},
                ],
            },
        )
        self.assertEqual([item["id"] for item in blocks], ["K1", "K2"])
        self.assertIn("第二块内容", blocks[1]["text"])


if __name__ == "__main__":
    unittest.main()
