from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ybt_learning.isolated_simulation import (
    SectionRef,
    build_answer_free_packet,
    canonical_sha,
    load_jsonl,
    project_student_item,
    section_folder,
    sha256_file,
    simulate_section,
)


ROOT = Path(__file__).resolve().parents[1]


class AnswerIsolatedSimulationTests(unittest.TestCase):
    def test_all_attempts_are_frozen_before_grader_material_is_loaded(self) -> None:
        summary = json.loads((ROOT / "reports/all_chapters/simulation-current.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["schema_version"], "ybt-deep-simulation-summary-v3")
        self.assertEqual(summary["sections"], 38)
        self.assertEqual(summary["items"], 1209)
        self.assertEqual(summary["attempts"], 30225)
        self.assertEqual(summary["route_assessments"], 30225)
        self.assertEqual(summary["mathematical_correctness"], "not_evaluated_no_final_answer")
        self.assertFalse(summary["mastery_claimed"])
        self.assertTrue(summary["global_attempt_ids_unique"])
        pointer = json.loads((ROOT / "reports/deep_section_simulations/current.json").read_text(encoding="utf-8"))
        self.assertEqual(pointer["run_id"], summary["run_id"])
        run_root = ROOT / pointer["run_path"]

        report_paths = [
            run_root / f"{section_folder(str(section['id']))}.json"
            for chapter in range(1, 6)
            for section in json.loads((ROOT / f"chapter{chapter}_manifest.json").read_text(encoding="utf-8"))["sections"]
        ]
        self.assertEqual(len(report_paths), 38)
        for report_path in report_paths:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            chapter = int(report["chapter"])
            section_id = str(report["section"])
            packet_root = ROOT / "data/packets" / section_folder(section_id)
            self.assertEqual(report["source_binding"]["manifest_sha256"], sha256_file(ROOT / f"chapter{chapter}_manifest.json"))
            self.assertEqual(report["source_binding"]["student_learning_items_sha256"], sha256_file(packet_root / "student_learning_items.json"))
            self.assertEqual(report["source_binding"]["student_packet_sha256"], sha256_file(packet_root / "student_packet.json"))
            self.assertEqual(report["source_binding"]["grader_learning_packet_sha256"], sha256_file(packet_root / "learning_packet.json"))
            self.assertEqual(report["source_binding"]["route_sha256"], sha256_file(packet_root / "learning_path_without_questions.md"))
            frozen_path = ROOT / report["answer_isolation"]["frozen_attempts_path"]
            assessment_path = ROOT / report["answer_isolation"]["route_assessments_path"]
            self.assertEqual(sha256_file(frozen_path), report["answer_isolation"]["frozen_attempts_sha256"])
            self.assertEqual(sha256_file(assessment_path), report["answer_isolation"]["route_assessments_sha256"])
            frozen_rows = load_jsonl(frozen_path)
            assessment_rows = load_jsonl(assessment_path)
            self.assertFalse(frozen_rows[0]["_meta"]["answer_material_loaded"])
            self.assertEqual(assessment_rows[0]["_meta"]["frozen_attempts_sha256"], sha256_file(frozen_path))
            attempts = frozen_rows[1:]
            assessments = {row["attempt_id"]: row for row in assessment_rows[1:]}
            self.assertEqual(len(attempts), report["summary"]["items"] * 25)
            self.assertEqual(len(assessments), len(attempts))
            for attempt in attempts:
                body = {key: value for key, value in attempt.items() if key not in {"attempt_id", "attempt_sha256"}}
                self.assertEqual(canonical_sha(body), attempt["attempt_sha256"])
                self.assertFalse(attempt["answer_material_loaded"])
                self.assertTrue(attempt["frozen_before_evaluation"])
                serialized = json.dumps(attempt, ensure_ascii=False)
                self.assertNotIn("answer_sidecar", serialized)
                self.assertNotIn("answer_text", serialized)
                assessment = assessments[attempt["attempt_id"]]
                self.assertEqual(assessment["frozen_attempt_sha256"], attempt["attempt_sha256"])
                self.assertEqual(assessment["mathematical_correctness"], "not_evaluated_no_final_answer")
                self.assertFalse(assessment["mastery_observed"])

    def test_one_section_generator_runs_from_current_answer_free_inputs(self) -> None:
        manifest_path = ROOT / "chapter3_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        section = next(row for row in manifest["sections"] if str(row["id"]) == "ch3.s13")
        catalog_payload = json.loads((ROOT / "data/all_chapters_course_catalog.json").read_text(encoding="utf-8"))
        catalog = {str(row["course_key"]): row for row in catalog_payload["courses"]}
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="isolated-sim-", dir=ROOT / "tmp") as output:
            report = simulate_section(ROOT, SectionRef(3, section, manifest_path), catalog, Path(output))
            self.assertEqual(report["summary"]["items"], 10)
            self.assertEqual(report["summary"]["attempts"], 250)
            self.assertEqual(report["answer_isolation"]["status"], "passed")
            frozen_path = ROOT / report["answer_isolation"]["frozen_attempts_path"]
            self.assertTrue(frozen_path.is_file())
            self.assertFalse(load_jsonl(frozen_path)[0]["_meta"]["answer_material_loaded"])

    def test_solution_canary_is_quarantined_before_persona_projection(self) -> None:
        projected = project_student_item({
            "item_id": "canary",
            "kind": "example",
            "label": "例CANARY",
            "example_number": 1,
            "question_text": "题干：求参数范围。\n参考答案：CANARY-DO-NOT-LEAK",
            "source_docs": [1],
            "image_refs": [],
            "visual_status": "READY_TEXT_ONLY",
        }, strict_learning_item=True)
        self.assertEqual(projected["source_quality"]["status"], "blocked")
        self.assertEqual(projected["question_text"], "")
        self.assertNotIn("CANARY-DO-NOT-LEAK", json.dumps(projected, ensure_ascii=False))

    def test_real_student_learning_items_have_no_quarantined_source_text(self) -> None:
        blocked: list[str] = []
        for chapter in range(1, 6):
            manifest = json.loads((ROOT / f"chapter{chapter}_manifest.json").read_text(encoding="utf-8"))
            for section in manifest["sections"]:
                section_id = str(section["id"])
                folder = ROOT / "data/packets" / section_folder(section_id)
                packet = build_answer_free_packet(
                    section,
                    json.loads((folder / "student_learning_items.json").read_text(encoding="utf-8")),
                    json.loads((folder / "student_packet.json").read_text(encoding="utf-8")),
                )
                for cycle in packet["learning_cycles"]:
                    for item in [*cycle["worked_examples"], *cycle["direct_variants"], *cycle["exercise_questions"]]:
                        quality = item["source_quality"]
                        if quality["status"] != "passed":
                            blocked.append(f"{section_id}:{item.get('item_id') or item.get('qid')}:{quality['reasons']}")
        self.assertEqual(blocked, [], "learner question text remains quarantined:\n" + "\n".join(blocked))

    def test_persistent_proxy_does_not_promote_simulation_to_real_progress(self) -> None:
        proxy = json.loads((ROOT / "reports/learner_simulation/primary-user-proxy-all-chapters.json").read_text(encoding="utf-8"))
        self.assertEqual(proxy["schema_version"], "ybt-primary-user-proxy-all-chapters-v3")
        self.assertEqual(proxy["coverage"]["sections"], 38)
        self.assertEqual(proxy["coverage"]["canonical_items"], 1209)
        self.assertEqual(proxy["learner"]["initial_assumptions"], ["zero_base"])
        self.assertEqual(proxy["learner"]["confirmed_strengths"], [])
        self.assertEqual(proxy["learner"]["confirmed_gaps"], [])
        self.assertEqual(proxy["human_learning_status"], "use_remote_math_mcp")
        self.assertFalse(proxy["mastery_claimed"])
        self.assertTrue(all(row["evidence_kind"] == "synthetic_proxy_attempt_not_human" for row in proxy["attempts"]))
        self.assertTrue(all(row["mathematical_correctness"] == "not_evaluated_no_final_answer" for row in proxy["attempts"]))
        self.assertTrue((ROOT / "reports/learner_simulation/runs" / f"{proxy['run_id']}.json").is_file())
        self.assertEqual(proxy["simulated_learning_status"], "not_run_no_final_learner_answers")
        self.assertTrue(all(
            record["status"] == "blocked"
            or all(
                evidence["kind"] == "transcript_loaded_for_proxy"
                and evidence["full_text_chars"] > 0
                and evidence["full_text_sha256"]
                for evidence in record["availability_evidence"]
            )
            for record in proxy["course_ledger"]["records"]
        ))


if __name__ == "__main__":
    unittest.main()
