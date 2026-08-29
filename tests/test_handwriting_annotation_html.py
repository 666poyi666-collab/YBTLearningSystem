from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_handwriting_annotation_html.py"


class HandwritingAnnotationHtmlTests(unittest.TestCase):
    def test_transparent_overlay_marks_first_error_without_covering_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "handwriting.png"
            analysis = root / "analysis.json"
            output = root / "review.html"
            Image.new("RGB", (400, 300), "white").save(image)
            analysis.write_text(json.dumps({
                "schema_version": "math-handwriting-annotation-v1",
                "source": {"image_evidence_id": "test-image"},
                "question": {"item_ref": "例15"},
                "summary": {"first_wrong_line": 2, "analysis_status": "proposed"},
                "lines": [
                    {"line": 1, "status": "correct", "bbox": [0.1, 0.1, 0.4, 0.1], "explanation": "首行建模正确。", "latex": "x+y=1"},
                    {"line": 2, "status": "first_wrong", "bbox": [0.1, 0.25, 0.5, 0.1], "explanation": "此处把方向向量写反。", "latex": "\\overrightarrow{AB}=-\\overrightarrow{BA}"},
                    {"line": 3, "status": "downstream_contaminated", "bbox": [0.1, 0.4, 0.6, 0.1], "explanation": "该行沿用上一行错误，不重复归因。"},
                ],
            }, ensure_ascii=False), encoding="utf-8")
            subprocess.run([sys.executable, str(SCRIPT), "--image", str(image), "--analysis", str(analysis), "--out", str(output)], check=True, capture_output=True, text=True)
            html = output.read_text(encoding="utf-8")
            self.assertIn('class="overlay overlay-first_wrong"', html)
            self.assertIn('class="overlay overlay-downstream_contaminated"', html)
            self.assertIn("fill:none", html)
            self.assertIn("MathJax", html)
            self.assertIn("file:///", html)
            self.assertIn("data-image-sha256", html)
            self.assertNotRegex(html, r"<rect[^>]+style=\"[^\"]*fill:")

    def test_missing_first_error_is_rejected_for_proposed_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "handwriting.png"
            analysis = root / "analysis.json"
            output = root / "review.html"
            Image.new("RGB", (20, 20), "white").save(image)
            analysis.write_text(json.dumps({
                "schema_version": "math-handwriting-annotation-v1",
                "source": {"image_evidence_id": "test-image"},
                "summary": {"analysis_status": "proposed"},
                "lines": [{"line": 1, "status": "correct", "explanation": "该行可读且正确。"}],
            }, ensure_ascii=False), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(SCRIPT), "--image", str(image), "--analysis", str(analysis), "--out", str(output)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("exactly one first_wrong", proc.stderr)

    def test_uncertain_review_must_disclose_what_is_unclear(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "handwriting.png"
            analysis = root / "analysis.json"
            output = root / "review.html"
            Image.new("RGB", (20, 20), "white").save(image)
            analysis.write_text(json.dumps({
                "schema_version": "math-handwriting-annotation-v1",
                "source": {"image_evidence_id": "test-image"},
                "summary": {"analysis_status": "needs_clarification"},
                "lines": [{"line": 1, "status": "uncertain", "explanation": "符号看不清。"}],
            }, ensure_ascii=False), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(SCRIPT), "--image", str(image), "--analysis", str(analysis), "--out", str(output)], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("disclose uncertainties", proc.stderr)

    def test_saved_mcp_annotation_spec_is_directly_renderable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "handwriting.png"
            analysis = root / "mcp-response.json"
            output = root / "review.html"
            Image.new("RGB", (100, 100), "white").save(image)
            analysis.write_text(json.dumps({
                "analysis": {"itemRef": "B10", "analysisStatus": "proposed"},
                "annotationSpec": {
                    "schemaVersion": "math-handwriting-annotation-v1",
                    "imageEvidenceId": "mcp-image",
                    "uncertainties": [],
                    "clarificationRequest": None,
                    "overlays": [{"line": 2, "status": "first_wrong", "bbox": [0.1, 0.2, 0.6, 0.1], "explanation": "负号遗漏", "latex": "-\\frac12"}],
                },
            }, ensure_ascii=False), encoding="utf-8")
            subprocess.run([sys.executable, str(SCRIPT), "--image", str(image), "--analysis", str(analysis), "--out", str(output)], check=True, capture_output=True, text=True)
            html = output.read_text(encoding="utf-8")
            self.assertIn("B10", html)
            self.assertIn("overlay-first_wrong", html)


if __name__ == "__main__":
    unittest.main()
