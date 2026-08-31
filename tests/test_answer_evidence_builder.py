from __future__ import annotations

import importlib.util
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_all_answer_evidence", ROOT / "scripts" / "build_all_answer_evidence.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def page(number: int, lines: list[str]) -> dict:
    return {
        "pdf_page": number,
        "ocr_lines": [
            {"text": text, "confidence": 0.98, "bbox": [0, index, 10, index + 1]}
            for index, text in enumerate(lines)
        ],
        "ocr_text_sha256": f"ocr-{number}",
        "page_image_sha256": f"image-{number}",
        "page_image_path": f"tmp/pages/page-{number:03d}.jpg",
    }


class AnswerEvidenceParserTests(unittest.TestCase):
    def test_repeated_blank_header_and_solution_cues_are_retained(self) -> None:
        pages = [
            page(
                1,
                [
                    "B组 强化能力",
                    "12.（2025·重庆模拟）",
                    "题面",
                    "12.",
                    "8√5/5",
                    "解析1：已知直线，若参数成立，则距离为上述值",
                    "13.（2025·江苏模拟）",
                    "题面",
                    "13.解：（1）若a=0，则先分类讨论",
                    "所以结论成立",
                ],
            )
        ]

        parsed, anchors = MODULE.parse_candidates(pages, {("B", 12), ("B", 13)})

        self.assertEqual(set(parsed), {("B", 12), ("B", 13)})
        self.assertIn("8√5/5", parsed[("B", 12)]["answer_text"])
        self.assertTrue(parsed[("B", 12)]["review_required"])
        self.assertIn("若a=0", parsed[("B", 13)]["answer_text"])
        self.assertTrue(parsed[("B", 13)]["automatic_grading_allowed"])
        self.assertEqual(anchors[("B", 12)]["pdf_page"], 1)

    def test_bare_repeated_number_is_supported(self) -> None:
        pages = [
            page(
                2,
                [
                    "C组 拓展提升",
                    "16.（2025·河南模拟）",
                    "题面",
                    "16",
                    "答案的分式 OCR 行",
                ],
            )
        ]

        parsed, _ = MODULE.parse_candidates(pages, {("C", 16)})

        self.assertEqual(parsed[("C", 16)]["parse_status"], "parsed_repeated_blank_or_bare_header")
        self.assertIn("答案的分式 OCR 行", parsed[("C", 16)]["answer_text"])
        self.assertFalse(parsed[("C", 16)]["automatic_grading_allowed"])

    def test_question_page_is_preserved_when_text_answer_is_unparsed(self) -> None:
        pages = [
            page(
                3,
                [
                    "C组 拓展提升",
                    "14.（2025·江苏模拟）",
                    "题面但答案编号未被 OCR 识别",
                ],
            )
        ]

        parsed, anchors = MODULE.parse_candidates(pages, {("C", 14)})

        self.assertNotIn(("C", 14), parsed)
        self.assertEqual(anchors[("C", 14)]["page_image_sha256"], "image-3")

    def test_unique_number_can_bind_across_printed_group_boundary(self) -> None:
        pages = [
            page(
                4,
                [
                    "C组 拓展提升",
                    "9.（2025·全国模拟）",
                    "题面",
                    "9.解：（1）按原书解答",
                ],
            )
        ]

        parsed, anchors = MODULE.parse_candidates(pages, {("B", 9)})

        self.assertEqual(parsed[("B", 9)]["source_group"], "C")
        self.assertEqual(anchors[("B", 9)]["group"], "C")


class GeneratedAnswerEvidenceTests(unittest.TestCase):
    def test_all_generated_grader_evidence_is_nonempty_and_source_bound(self) -> None:
        report = json.loads(
            (ROOT / "reports" / "deep_simulation" / "answer-evidence.json").read_text(
                encoding="utf-8-sig"
            )
        )
        sidecars = sorted((ROOT / "data" / "packets").glob("*/answer_sidecar.json"))
        self.assertEqual(len(sidecars), 38)
        answers = []
        for path in sidecars:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            self.assertEqual(payload["status"], "VERIFIED", path)
            self.assertEqual(payload["blocked_answers"], 0, path)
            answers.extend(payload["answers"])

        self.assertEqual(len(answers), 546)
        self.assertEqual(len({row["qid"] for row in answers}), 546)
        checked_images: set[Path] = set()
        for row in answers:
            self.assertTrue(row["grader_only"], row["qid"])
            self.assertTrue(str(row["answer_text"]).strip(), row["qid"])
            source = row["source"]
            self.assertRegex(source["source_pdf_sha256"], r"^[0-9a-f]{64}$")
            self.assertGreaterEqual(int(source["pdf_page"]), 1)
            self.assertRegex(source["page_image_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(source["ocr_text_sha256"], r"^[0-9a-f]{64}$")
            relative_image_path = Path(source["page_image_path"])
            self.assertFalse(relative_image_path.is_absolute(), relative_image_path)
            image_path = ROOT / relative_image_path
            if image_path.is_file() and image_path not in checked_images:
                digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
                self.assertEqual(digest, source["page_image_sha256"], image_path)
                checked_images.add(image_path)
            if row["evidence_kind"] == "source_page_visual":
                self.assertEqual(row["answer_text"], MODULE.VISUAL_REVIEW_MARKER)
                self.assertTrue(row["review_required"])
                self.assertFalse(row["automatic_grading_allowed"])
                self.assertEqual(row["answer_text_kind"], "evidence_locator_not_answer")
            else:
                self.assertEqual(row["evidence_kind"], "parsed_answer_text")
                self.assertNotEqual(row["answer_text"], MODULE.VISUAL_REVIEW_MARKER)

        self.assertEqual(report["questions"], 546)
        self.assertEqual(report["parsed_questions"], 524)
        self.assertEqual(report["visual_fallback_questions"], 22)
        self.assertEqual(report["evidenced_questions"], 546)
        self.assertEqual(report["blocked_questions"], 0)
        self.assertEqual(report["status"], "passed")


if __name__ == "__main__":
    unittest.main()
