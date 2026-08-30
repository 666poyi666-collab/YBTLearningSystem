from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExamPaperWorkflowTests(unittest.TestCase):
    def test_manifest_is_optional_and_answer_pages_are_not_authority(self) -> None:
        payload = json.loads((ROOT / "data" / "exam_papers" / "manifest.json").read_text(encoding="utf-8"))
        policy = payload["route_policy"]
        self.assertTrue(policy["optional"])
        self.assertFalse(policy["blocks_ybt_progress"])
        self.assertTrue(policy["answer_page_is_not_question_authority"])

    def test_empty_route_manifest_is_valid_until_question_papers_arrive(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_exam_routes.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
