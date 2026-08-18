from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


def load_collector():
    path = Path(__file__).resolve().parents[1] / "scripts" / "browser_collect.py"
    spec = importlib.util.spec_from_file_location("ybt_browser_collect_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class BrowserCollectorTests(unittest.TestCase):
    def test_history_collection_keeps_85_and_85_course_independent(self) -> None:
        collector = load_collector()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "History"
            conn = sqlite3.connect(history)
            conn.execute("CREATE TABLE urls (url TEXT, title TEXT, visit_count INTEGER, last_visit_time INTEGER)")
            conn.executemany("INSERT INTO urls VALUES (?, ?, ?, ?)", [
                ("https://chatgpt.com/g/" + collector.PROJECT_URL_PART + "/c/a", "数学 - 8.5课程", 7, 13300000000000000),
                ("https://chatgpt.com/g/" + collector.PROJECT_URL_PART + "/c/b", "数学 - 8.5", 3, 13300000000000000),
                ("https://chatgpt.com/g/" + collector.PROJECT_URL_PART + "/c/c", "数学 - 8.5g", 1, 13300000000000000),
                ("https://chatgpt.com/g/another-gpt/c/cam", "Camera capture", 2, 13300000000000000),
                ("https://example.com/pay/18.57", "商品 278.55", 1, 13300000000000000),
            ])
            conn.commit()
            conn.close()
            output = root / "browser_evidence.json"
            events = root / "browser_events.jsonl"
            evidence = collector.collect(output, events, {"edge": history, "chrome": root / "missing"})

            self.assertEqual(evidence["8.5"]["status"], "passed")
            self.assertEqual(evidence["8.5"]["matches"], 1)
            self.assertEqual(evidence["8.5课程"]["status"], "passed")
            self.assertEqual(evidence["8.5课程"]["matches"], 1)
            self.assertNotEqual(evidence["8.5"]["history_matches"], evidence["8.5课程"]["history_matches"])
            self.assertNotIn("8.5g", evidence)
            self.assertNotIn("camera", evidence)
            self.assertNotIn("18.57", json.dumps(evidence["browsers"]["edge"]["all_matches"], ensure_ascii=False))
            self.assertTrue(evidence["history_verified_at"])
            self.assertTrue(evidence["browsers"]["edge"]["history_db_sha256"])
            event_lines = events.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(event_lines), 1)
            serialized = json.dumps(evidence, ensure_ascii=False).lower()
            self.assertNotIn("cookie_value", serialized)
            self.assertNotIn("access_token", serialized)

    def test_85_course_is_required_separately(self) -> None:
        collector = load_collector()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "History"
            conn = sqlite3.connect(history)
            conn.execute("CREATE TABLE urls (url TEXT, title TEXT, visit_count INTEGER, last_visit_time INTEGER)")
            conn.execute("INSERT INTO urls VALUES (?, ?, ?, ?)", (
                "https://chatgpt.com/g/" + collector.PROJECT_URL_PART + "/c/a", "数学 - 8.5课程", 7, 13300000000000000))
            conn.commit()
            conn.close()
            evidence = collector.collect(root / "evidence.json", root / "events.jsonl", {"edge": history, "chrome": root / "missing"})
            self.assertEqual(evidence["8.5"]["status"], "unknown")
            self.assertEqual(evidence["8.5课程"]["status"], "passed")
            self.assertEqual(evidence["8.5课程"]["matches"], 1)


if __name__ == "__main__":
    unittest.main()
