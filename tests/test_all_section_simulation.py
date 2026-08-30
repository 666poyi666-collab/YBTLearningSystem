from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AllSectionSimulationTests(unittest.TestCase):
    def test_all_section_simulations_are_current_and_answer_free(self) -> None:
        reports = []
        for chapter in range(1, 6):
            manifest = json.loads((ROOT / f"chapter{chapter}_manifest.json").read_text(encoding="utf-8"))
            for section in manifest["sections"]:
                path = ROOT / "reports/all_section_simulations" / f"{section['id']}-route-contract-simulation.json"
                self.assertTrue(path.is_file(), str(path))
                report = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(report["source_revision_match"])
                self.assertEqual(report["status"], "passed")
                self.assertEqual(len(report["personas"]), 5)
                self.assertFalse(any(persona["mastery_claimed"] for persona in report["personas"]))
                reports.append(report)
        self.assertEqual(len(reports), 38)
        self.assertEqual(sum(row["summary"]["items_per_persona"] for row in reports), 1209)
        self.assertEqual(sum(row["summary"]["attempts"] for row in reports), 6045)

    def test_primary_proxy_keeps_real_and_synthetic_evidence_separate(self) -> None:
        path = ROOT / "reports/learner_simulation/primary-user-proxy-all-chapters.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["coverage"]["canonical_items"], 1209)
        self.assertEqual(payload["learner"]["initial_assumptions"], ["zero_base"])
        self.assertEqual(payload["human_learning_status"], "use_remote_math_mcp")
        self.assertFalse(payload["mastery_claimed"])
        self.assertTrue(all(row["evidence_kind"] == "synthetic_prediction_not_real_user" for row in payload["attempts"]))


if __name__ == "__main__":
    unittest.main()
