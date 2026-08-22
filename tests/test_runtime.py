from __future__ import annotations

import json
import argparse
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

from ybt_learning.packet import PacketBuilder
from ybt_learning.packet import _sha256_file
from ybt_learning.state import StateError, StateStore, run_reward_test
from ybt_learning.deepseek_context import build_context, validate_context, derived_probe, verify_worker_probe
from ybt_learning.deepseek_context import context_path_for_student_packet
from ybt_learning.common import delimiter_errors
from ybt_learning.catalog import course_id_from_stem
from ybt_learning.coverage import build_question_coverage
from ybt_learning.manifest import load_manifest
from ybt_learning.vision import _structured_caption


def _load_real_user_collector():
    path = Path(__file__).resolve().parents[1] / "scripts" / "real_user_collect.py"
    spec = importlib.util.spec_from_file_location("ybt_real_user_collect_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_project_script(module_name: str, relative_path: str):
    path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StateRuntimeTests(unittest.TestCase):
    def test_reward_gate_and_idempotency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_reward_test(Path(tmp) / "reward.json")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["points"], 50)
        self.assertEqual(len(result["grants"]), 3)

    def test_near_transfer_requires_a_distinct_verified_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            first = store.record_attempt("base", independent=True, result="correct", process_verified=True, at="2026-08-10T00:00:00+00:00")
            with self.assertRaises(StateError):
                store.record_near_variant("base", variant_item_id="base", independent=True, result="correct", process_verified=True)
            near = store.record_near_variant("base", variant_item_id="near", independent=True, result="correct", process_verified=True, at="2026-08-10T01:00:00+00:00")
            replay = store.record_near_variant("base", variant_item_id="near", independent=True, result="correct", process_verified=True, at="2026-08-10T02:00:00+00:00")
        self.assertEqual(len(first["granted"]), 1)
        self.assertIsNotNone(near["grant"])
        self.assertTrue(replay["idempotent"])

    def test_hint_and_guess_never_get_full_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            hinted = store.record_attempt("x", independent=True, result="correct", hint_level="H1", process_verified=True)
            guessed = store.record_attempt("y", independent=True, result="guess")
        self.assertEqual(hinted["item"]["mastery_status"], "U3")
        self.assertFalse(hinted["item"]["release"]["full_pass"])
        self.assertEqual(guessed["item"]["mastery_status"], "CF")
        self.assertEqual(guessed["granted"], [])

    def test_first_image_reward_requires_visual_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            blocked = store.record_attempt(
                "first-blocked",
                independent=True,
                result="correct",
                process_verified=True,
                visual_status="NEEDS_VISION_SIDECAR",
            )
            verified = store.record_attempt(
                "first-verified",
                independent=True,
                result="correct",
                process_verified=True,
                visual_status="VISION_VERIFIED",
                source_anchor={"visual_evidence": "E2"},
            )
        self.assertEqual(blocked["granted"], [])
        self.assertEqual(blocked["item"]["progress_status"], "ATTEMPTED_UNVERIFIED")
        self.assertTrue(verified["granted"])
        self.assertIn("visual_verified", verified["granted"][0]["evidence"])

    def test_reward_test_binds_first_image_to_real_first_question_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_reward_test(Path(tmp) / "reward.json")
        self.assertEqual(result["first_image_grant"]["item_id"], "1.1-A1")
        self.assertEqual(result["first_image_evidence"]["question_hint"], "1.1-A1")
        self.assertTrue(result["first_image_conditions"]["first_image_file_present"])
        self.assertTrue(result["first_image_conditions"]["first_image_sidecar_verified"])

    def test_first_image_visual_status_cannot_be_forged_without_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            with self.assertRaises(StateError):
                store.record_attempt("forged", independent=True, result="correct", process_verified=True, visual_status="VISION_VERIFIED")

    def test_delayed_review_needs_clock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            out = store.record_attempt("x", independent=True, result="correct", hint_level="H1", process_verified=True, at="2026-08-10T00:00:00+00:00")
            with self.assertRaises(StateError):
                store.review_item("x", result="correct", process_verified=True, at="2026-08-10T12:00:00+00:00")
            done = store.review_item("x", result="correct", process_verified=True, at="2026-08-11T00:00:00+00:00")
        self.assertEqual(done["item"]["mastery_status"], "U6")

    def test_verified_item_attempt_replay_is_idempotent_and_does_not_downgrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            store.record_attempt("done", independent=True, result="correct", process_verified=True, at="2026-08-10T00:00:00+00:00")
            store.review_item("done", result="correct", process_verified=True, at="2026-08-11T00:00:00+00:00")
            replay = store.record_attempt("done", independent=True, result="correct", process_verified=True, at="2026-08-10T00:00:00+00:00")
        self.assertTrue(replay["idempotent"])
        self.assertEqual(replay["item"]["mastery_status"], "U6")
        self.assertIsNone(replay["item"]["review_due"])
        self.assertEqual(replay["granted"], [])

    def test_prompted_correct_is_not_labeled_independent_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            result = store.record_attempt("prompted", independent=True, result="correct", hint_level="H1", process_verified=True)
        self.assertEqual(result["item"]["progress_status"], "ATTEMPTED_CONTAMINATED")

    def test_section_reward_requires_all_cold_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            store.record_attempt("a", independent=True, result="correct", process_verified=True, at="2026-08-10T00:00:00+00:00")
            with self.assertRaises(StateError):
                store.complete_section("1.1", ["a"], required_evidence=["section_gate"], at="2026-08-10T12:00:00+00:00")
            store.review_item("a", result="correct", process_verified=True, at="2026-08-11T00:00:00+00:00")
            first = store.complete_section("1.1", ["a"], required_evidence=["section_gate"], at="2026-08-11T00:00:00+00:00")
            second = store.complete_section("1.1", ["a"], required_evidence=["section_gate"], at="2026-08-11T00:00:01+00:00")
        self.assertIsNotNone(first["grant"])
        self.assertIsNone(second["grant"])

    def test_course_return_guards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            payload = {"package_id": "P1", "base_state_id": store.state["main_state_id"], "target_identity": {"section": "1.1"}, "evidence": []}
            self.assertEqual(store.merge_course_return(payload)["status"], "MERGED")
            self.assertEqual(store.merge_course_return(payload)["status"], "IDEMPOTENT_NOOP")
            mismatch = dict(payload, package_id="P2", target_identity={"section": "1.2"})
            self.assertEqual(store.merge_course_return(mismatch)["status"], "REJECT_TARGET_MISMATCH")


class PacketRuntimeTests(unittest.TestCase):
    def test_source_method_bridge_does_not_release_independent_attempt(self) -> None:
        manifest = {
            "sections": [{
                "id": "1.1",
                "question_groups": {"B": [8, 8]},
                "bridge_units": [],
            }]
        }
        catalog = {"courses": [{"transcripts": [{"course_key": "line_line_angle"}]}]}
        packets = [{
            "section": "1.1",
            "status": "VERIFIED",
            "questions": [{
                "group": "B",
                "number": 8,
                "qid": "q-b8",
                "visual_status": "READY_TEXT_ONLY",
                "question_text": "无答案题面",
            }],
        }]
        source_only = build_question_coverage(
            manifest,
            catalog,
            packets,
            bridge_catalog={"units": [{"id": "bridge-1.1-polarization", "status": "SOURCE_METHOD_READY"}]},
        )
        self.assertEqual(source_only["questions"][0]["release_status"], "BLOCKED_BRIDGE")

        supplement = build_question_coverage(
            manifest,
            catalog,
            packets,
            bridge_catalog={"units": [{"id": "bridge-1.1-polarization", "status": "SUPPLEMENT_READY"}]},
        )
        self.assertEqual(supplement["questions"][0]["release_status"], "READY_FOR_INDEPENDENT_ATTEMPT")

    def test_zero_base_bridge_gate_blocks_until_closed(self) -> None:
        manifest = {
            "sections": [{
                "id": "1.1",
                "question_groups": {"B": [7, 7]},
                "bridge_units": [],
            }]
        }
        catalog = {"courses": [{"transcripts": [{"course_key": "line_line_angle"}]}]}
        packets = [{
            "section": "1.1",
            "status": "VERIFIED",
            "questions": [{
                "group": "B",
                "number": 7,
                "qid": "q-b7",
                "visual_status": "VISION_VERIFIED",
                "question_text": "无答案题面",
            }],
        }]
        result = build_question_coverage(
            manifest,
            catalog,
            packets,
            bridge_catalog={"units": [{
                "id": "bridge-1.1-dihedral-definition",
                "status": "SUPPLEMENT_READY",
                "zero_base_status": "NOT_CLOSED",
            }]},
        )
        self.assertEqual(result["questions"][0]["release_status"], "BLOCKED_BRIDGE")
        self.assertEqual(result["questions"][0]["bridge_status"], "NOT_CLOSED")
        self.assertEqual(result["questions"][0]["zero_base_status"], "NOT_CLOSED")

    def test_real_user_verify_requires_every_manifest_section(self) -> None:
        collector = _load_real_user_collector()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            for rel in (collector.PLAN_REL, collector.COVERAGE_REL, collector.SCHEMA_REL):
                source = collector.PROJECT_ROOT / rel
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
            slot = collector.SLOT_IDS[0]
            slot_dir = root / collector.RECORDS_REL / slot
            slot_dir.mkdir(parents=True)
            consent = slot_dir / "consent.txt"
            consent.write_text("TEST CONSENT\n", encoding="utf-8")
            identity = {
                "schema_version": collector.SCHEMA_VERSION,
                "slot": slot,
                "participant_id": "TEST_USER",
                "consent_artifact": {"path": str(consent.relative_to(root)), "sha256": collector.sha256_file(consent)},
            }
            (slot_dir / "identity.json").write_text(json.dumps(identity, ensure_ascii=False), encoding="utf-8")
            result = collector.verify_slot(
                root,
                slot,
                collector.load_schema(root),
                collector.load_plan_index(root),
                collector.load_coverage_index(root),
            )
        self.assertEqual(result["status"], "failed")
        self.assertIn("1.2+1.3_events_missing", result["issues"])
        self.assertIn("1.4_events_missing", result["issues"])
        self.assertIn("micro专题1_events_missing", result["issues"])
        self.assertEqual(set(result["per_section"]), {"1.1", "1.2+1.3", "1.4", "micro专题1"})

    def test_sidecar_binds_by_image_hash_when_ocr_root_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "current.jpg"
            historical = root / "historical.jpg"
            current.write_bytes(b"same-figure")
            historical.write_bytes(b"same-figure")
            sidecar = {"image": str(historical), "image_sha256": _sha256_file(historical)}
            refs = [{"path": str(current), "exists": True}]
            self.assertTrue(PacketBuilder._sidecar_matches_question(sidecar, refs))
            historical.write_bytes(b"different-figure")
            self.assertFalse(PacketBuilder._sidecar_matches_question(sidecar, refs))

    def test_source_pdf_provenance_binds_only_to_declared_question_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_pdf = root / "source.pdf"
            current = root / "current.jpg"
            crop = root / "source-crop.png"
            source_pdf.write_bytes(b"authoritative-source-pdf")
            current.write_bytes(b"question-crop")
            crop.write_bytes(b"high-resolution-figure")
            provenance = {
                "source_kind": "high_resolution_source_pdf_crop",
                "source_pdf": str(source_pdf),
                "source_pdf_sha256": _sha256_file(source_pdf),
                "pdf_page": 1,
                "crop_rect": [1, 2, 10, 20],
                "derived_from_image_path": str(current),
                "derived_from_image_sha256": _sha256_file(current),
            }
            sidecar = {"image": str(crop), "image_sha256": _sha256_file(crop), "source_provenance": provenance}
            self.assertTrue(PacketBuilder._sidecar_matches_question(sidecar, [{"path": str(current)}]))
            provenance["derived_from_image_sha256"] = "0" * 64
            self.assertFalse(PacketBuilder._sidecar_matches_question(sidecar, [{"path": str(current)}]))

    def test_multi_image_question_requires_a_sidecar_for_every_figure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            first = root / "first.jpg"
            second = root / "second.jpg"
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            (root / "doc_0.md").write_text("# B组\n1. 双图题 ![图1](first.jpg) ![图2](second.jpg)\n", encoding="utf-8")
            structured = {"objects": ["figure"], "relations": [], "coordinates": [], "ranges": [], "text": [], "confidence": "E2"}
            one = {"question_hint": "test-B1", "image": str(first), "status": "passed", "confidence": "E2", "structured": structured}
            two = {"question_hint": "test-B1", "image": str(second), "status": "passed", "confidence": "E2", "structured": structured}
            partial = PacketBuilder(ocr_root=root, output_root=Path(tmp) / "partial").build_section(
                {"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"B": [1, 1]}},
                visual_sidecar={"results": [one]},
            )
            self.assertEqual(partial["questions"][0]["visual_status"], "NEEDS_VISION_SIDECAR")
            complete = PacketBuilder(ocr_root=root, output_root=Path(tmp) / "complete").build_section(
                {"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"B": [1, 1]}},
                visual_sidecar={"results": [one, two]},
            )
            self.assertEqual(complete["questions"][0]["visual_status"], "VISION_VERIFIED")
            self.assertEqual(len(complete["questions"][0]["vision_sidecars"]), 2)

    def test_duplicate_question_keeps_verified_visual_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            image = root / "figure.jpg"
            image.write_bytes(b"figure")
            (root / "doc_0.md").write_text("# B组\n1. 短题面 ![图](figure.jpg)\n1. 这是同一题的较长 OCR 重复文本 ![图](figure.jpg)\n", encoding="utf-8")
            sidecar = {"results": [{
                "question_hint": "test-B1", "image": str(image), "status": "passed", "confidence": "E1",
                "structured": {"objects": ["图"], "relations": [], "coordinates": [], "ranges": [], "text": [], "confidence": "E1"},
            }]}
            packet = PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out").build_section(
                {"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"B": [1, 1]}},
                visual_sidecar=sidecar,
            )
            self.assertEqual(packet["questions"][0]["visual_status"], "VISION_VERIFIED")

    def test_recovered_question_can_receive_visual_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            image = root / "recovered.jpg"
            image.write_bytes(b"recovered-figure")
            (root / "doc_0.md").write_text("# B组\n1. 前一题\n2. 恢复题 ![图](recovered.jpg)\n", encoding="utf-8")
            sidecar = {
                "known_visual_recoveries": [{
                    "section": "test", "group": "B", "number": 2, "source_kind": "primary_ocr", "source_doc": 0,
                    "start_regex": "^2[.．、]", "end_regex": None, "evidence": "explicit",
                }],
                "results": [{
                    "question_hint": "test-B2", "image": str(image), "status": "passed", "confidence": "E1",
                    "structured": {"objects": ["图"], "relations": [], "coordinates": [], "ranges": [], "text": [], "confidence": "E1"},
                }],
            }
            packet = PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out").build_section(
                {"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"B": [1, 2]}},
                visual_sidecar=sidecar,
            )
            recovered = next(item for item in packet["questions"] if item["number"] == 2)
            self.assertEqual(recovered["visual_status"], "VISION_VERIFIED")
            self.assertEqual(packet["status"], "VERIFIED")

    def test_visual_caption_rejects_empty_plain_and_template_payloads(self) -> None:
        for caption, expected in [
            ("", "empty_vision_caption"),
            ("无法识别图形", "malformed_structured_vision"),
            ('{"objects": [], "confidence": "E2|E1|E0"}', "confidence_template_not_a_result"),
            ('```json\n{"objects":["A"],"relations":[],"coordinates":[],"ranges":[],"text":[],"uncertainties":[],"confidence":"E1"}\n```', None),
            ('可辨识结果：{"objects":["A"],"relations":[],"coordinates":[],"ranges":[],"text":[],"uncertainties":[],"confidence":"E1"}', None),
            ('```json\n{"objects": ["A"], "confidence": "E1"}', "truncated_fenced_vision"),
            ('```json\n{"objects": ["A"]}', "truncated_fenced_vision"),
        ]:
            structured, error = _structured_caption(caption)
            if expected:
                self.assertIsNone(structured)
                self.assertEqual(error, expected)
            else:
                self.assertEqual(error, None)
                self.assertEqual(structured["objects"], ["A"])

    def test_packet_rejects_legacy_visual_fallback_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            image = root / "figure.jpg"
            image.write_bytes(b"fake")
            (root / "doc_0.md").write_text("# A组\n1. 题干 ![图](figure.jpg)\n", encoding="utf-8")
            sidecar = {
                "results": [{
                    "question_hint": "test-A1", "status": "passed", "confidence": "E1",
                    "structured": {"text": [""], "uncertainties": ["视觉模型未返回结构化JSON"], "confidence": "E1"},
                }]
            }
            packet = PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out").build_section(
                {"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"A": [1, 1]}},
                visual_sidecar=sidecar,
            )
            self.assertEqual(packet["questions"][0]["visual_status"], "NEEDS_VISION_SIDECAR")
            self.assertEqual(packet["status"], "UNVERIFIED")

    def test_packet_fail_closed_on_missing_visual(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            (root / "doc_0.md").write_text("# A组\n1. 题干 ![图](missing.jpg)\n答案：A\n", encoding="utf-8")
            out_root = Path(tmp) / "out"
            builder = PacketBuilder(ocr_root=root, output_root=out_root)
            section = {"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"A": [1, 1]}}
            packet = builder.build_section(section)
            self.assertEqual(packet["status"], "UNVERIFIED")
            self.assertTrue(packet["unresolved"])
            answer_sidecar = json.loads((out_root / "test" / "answer_sidecar.json").read_text(encoding="utf-8"))
            self.assertEqual(answer_sidecar["answers"][0]["answer_text"], "答案：A")
            student = json.loads((out_root / "test" / "student_packet.json").read_text(encoding="utf-8"))
            self.assertNotIn("answer_text", json.dumps(student, ensure_ascii=False))
            self.assertNotIn("答案：", json.dumps(student, ensure_ascii=False))

    def test_student_packet_removes_solution_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            (root / "doc_0.md").write_text("# A组\n1. 题干\n证明：设 x=1，所以答案为 2。\n", encoding="utf-8")
            packet = PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out").build_section({"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"A": [1, 1]}})
            student = json.loads((Path(tmp) / "out" / "test" / "student_packet.json").read_text(encoding="utf-8"))
            student_text = json.dumps(student, ensure_ascii=False)
            self.assertNotIn("证明：", student_text)
        self.assertNotIn("答案为", student_text)

    def test_student_packet_rejects_bare_answer_line_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            (root / "doc_0.md").write_text("# B组\n1. 题干\n\n### 1. B\n", encoding="utf-8")
            PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out").build_section(
                {"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"B": [1, 1]}}
            )
            student = json.loads((Path(tmp) / "out" / "test" / "student_packet.json").read_text(encoding="utf-8"))
            student_text = json.dumps(student, ensure_ascii=False)
            self.assertNotRegex(student_text, r"(?m)^\s*#{0,6}\s*1\s*[.．、]\s*B\s*$")
            self.assertEqual(__import__("ybt_learning.packet", fromlist=["verify_packet"]).verify_packet(Path(tmp) / "out" / "test" / "student_packet.json")["status"], "passed")

    def test_student_packet_separates_lesson_examples_from_attempt_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            (root / "doc_0.md").write_text("# A组\n【例1】讲解题面\n解：教师完整方法\n## 强化训练\n1. 学生题面\n", encoding="utf-8")
            PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out").build_section({"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"A": [1, 1]}})
            lesson = json.loads((Path(tmp) / "out" / "test" / "lesson_packet.json").read_text(encoding="utf-8"))
            student = json.loads((Path(tmp) / "out" / "test" / "student_packet.json").read_text(encoding="utf-8"))
            self.assertIn("教师完整方法", json.dumps(lesson, ensure_ascii=False))
            self.assertNotIn("教师完整方法", json.dumps(student, ensure_ascii=False))
            self.assertIn("学生题面", json.dumps(student, ensure_ascii=False))

    def test_sequential_learning_packet_teaches_example_before_answer_free_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            image = root / "example.jpg"
            image.write_bytes(b"example-figure")
            (root / "doc_0.md").write_text(
                "## 知识点1\n【例1】例题题面 ![图](example.jpg)\n解：教师方法\n【变式】变式题面\n解法1：变式答案\n## A组\n1. 学生题面\n",
                encoding="utf-8",
            )
            section = {
                "id": "test",
                "label": "测试",
                "ocr_docs": [0, 0],
                "question_groups": {"A": [1, 1]},
                "knowledge_points": [{"id": "k1", "examples": ["例1"]}],
                "type_training": [],
            }
            builder = PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out")
            builder.build_section(section)
            learning = json.loads((Path(tmp) / "out" / "test" / "learning_packet.json").read_text(encoding="utf-8"))
            self.assertEqual(learning["counts"], {"worked_examples": 1, "direct_variants": 1, "abc_exercises": 1, "total_numbered_learning_items": 3})
            self.assertIn("知识点1", json.dumps(learning["knowledge_and_type_pages"], ensure_ascii=False))
            self.assertIn("教师方法", learning["worked_examples"][0]["teaching_text"])
            self.assertEqual(learning["worked_examples"][0]["visual_status"], "NEEDS_VISION_SIDECAR")
            vision_hint = learning["worked_examples"][0]["vision_hint"]
            builder.build_section(section, visual_sidecar={"results": [{
                "question_hint": vision_hint,
                "image": str(image),
                "status": "passed",
                "confidence": "E1",
                "structured": {"objects": ["图"], "relations": [], "coordinates": [], "ranges": [], "text": [], "confidence": "E1"},
            }]})
            learning = json.loads((Path(tmp) / "out" / "test" / "learning_packet.json").read_text(encoding="utf-8"))
            self.assertEqual(learning["worked_examples"][0]["visual_status"], "VISION_VERIFIED")
            self.assertEqual(learning["worked_examples"][0]["vision_hint"], vision_hint)
            serialized_variant = json.dumps(learning["direct_variants"][0], ensure_ascii=False)
            self.assertIn("变式题面", serialized_variant)
            self.assertNotIn("变式答案", serialized_variant)
            self.assertNotIn("解法1", serialized_variant)

    def test_student_learning_items_project_examples_and_variants_without_teaching_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            (root / "doc_0.md").write_text(
                "## 知识点1\n【例1】例题题面\n解：教师方法\n【变式】变式题面\n解法1：变式答案\n## A组\n1. 学生题面\n",
                encoding="utf-8",
            )
            section = {
                "id": "test",
                "label": "测试",
                "ocr_docs": [0, 0],
                "question_groups": {"A": [1, 1]},
                "knowledge_points": [{"id": "k1", "examples": ["例1"]}],
                "type_training": [],
            }
            PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out").build_section(section)
            student_items = json.loads(
                (Path(tmp) / "out" / "test" / "student_learning_items.json").read_text(encoding="utf-8")
            )
            serialized = json.dumps(student_items, ensure_ascii=False)
        self.assertEqual(student_items["counts"]["total"], 2)
        self.assertEqual(student_items["worked_examples"][0]["question_text"], "【例1】例题题面")
        self.assertIn("变式题面", serialized)
        self.assertNotIn("teaching_text", serialized)
        self.assertNotIn("教师方法", serialized)
        self.assertNotIn("变式答案", serialized)
        self.assertNotIn("解法1", serialized)

    def test_markdown_solution_headings_bound_student_learning_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            (root / "doc_0.md").write_text(
                "## 知识点1\n"
                "【例1】例题题面\n"
                "## 解：教师完整方法\n"
                "【变式】变式题面\n"
                "## 解法10：变式完整方法\n"
                "## A组\n"
                "1. 学生题面\n",
                encoding="utf-8",
            )
            section = {
                "id": "test",
                "label": "测试",
                "ocr_docs": [0, 0],
                "question_groups": {"A": [1, 1]},
                "knowledge_points": [{"id": "k1", "examples": ["例1"]}],
                "type_training": [],
            }
            PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out").build_section(section)
            learning = json.loads(
                (Path(tmp) / "out" / "test" / "learning_packet.json").read_text(encoding="utf-8")
            )
            student_items = json.loads(
                (Path(tmp) / "out" / "test" / "student_learning_items.json").read_text(encoding="utf-8")
            )
            lesson_text = json.dumps(learning, ensure_ascii=False)
            student_text = json.dumps(student_items, ensure_ascii=False)

        self.assertIn("教师完整方法", lesson_text)
        self.assertEqual(student_items["worked_examples"][0]["question_text"], "【例1】例题题面")
        self.assertEqual(student_items["direct_variants"][0]["question_text"], "【变式】变式题面")
        self.assertNotIn("教师完整方法", student_text)
        self.assertNotIn("变式完整方法", student_text)
        self.assertNotIn("解法10", student_text)

    def test_current_context_contains_complete_answer_free_learning_items(self) -> None:
        root = Path(__file__).resolve().parents[1]
        context = json.loads(
            (root / "data" / "contexts" / "1.1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(context["learning_items_manifest"]["counts"]["total"], 24)
        self.assertEqual(len(context["learning_items"]), 24)
        serialized = json.dumps(context["learning_items"], ensure_ascii=False)
        self.assertNotIn("teaching_text", serialized)
        self.assertNotIn("solution_present", serialized)
        self.assertNotIn("answer_text", serialized)
        self.assertEqual(__import__("ybt_learning.deepseek_context", fromlist=["validate_context"]).validate_context(root / "data" / "contexts" / "1.1.json")["status"], "passed")

    def test_student_packet_removes_inline_proof_from_page_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            (root / "doc_0.md").write_text("# A组\n1. 题干\n（1）证明：题目要求保留这句。\n解法1：设 x=1，所以答案为 2。\n", encoding="utf-8")
            packet = PacketBuilder(ocr_root=root, output_root=Path(tmp) / "out").build_section({"id": "test", "label": "测试", "ocr_docs": [0, 0], "question_groups": {"A": [1, 1]}})
            student = json.loads((Path(tmp) / "out" / "test" / "student_packet.json").read_text(encoding="utf-8"))
            student_text = json.dumps(student, ensure_ascii=False)
            self.assertIn("（1）证明：题目要求保留这句", student_text)
            self.assertNotIn("解法1", student_text)
            self.assertNotIn("答案为", student_text)

    def test_progress_status_does_not_claim_independent_for_guess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore.create(Path(tmp) / "state.json", {"section": "1.1"})
            result = store.record_attempt("x", independent=False, result="correct")
        self.assertEqual(result["item"]["progress_status"], "ATTEMPTED_CONTAMINATED")

    def test_deepseek_student_context_has_no_answers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            student = Path(tmp) / "student_packet.json"
            student.write_text(json.dumps({"packet_type": "DEEPSEEK_STUDENT_PACKET", "section": "1.1", "status": "VERIFIED", "manifest": {}, "pages": [], "questions": [], "unresolved": [], "answer_sidecar": None}, ensure_ascii=False), encoding="utf-8")
            context = Path(tmp) / "context.json"
            build_context(student, output_path=context)
            result = validate_context(context)
        self.assertEqual(result["status"], "passed")

    def test_deepseek_context_includes_route_support_without_answer_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_dir = root / "data" / "packets" / "1.1"
            packet_dir.mkdir(parents=True)
            (root / "data" / "chapter1_learning_plan.json").write_text(json.dumps({
                "plan": [{"section": "1.1", "must_listen_courses": [{"course_key": "space_vector_ops"}], "type_training": [{"type": "类型Ⅰ", "example_numbers": [9]}]}]
            }, ensure_ascii=False), encoding="utf-8")
            (root / "data" / "question_coverage.json").write_text(json.dumps({"questions": [{"section": "1.1", "question_key": "A1", "release_status": "COURSE_READY_NOT_MASTERY"}]}, ensure_ascii=False), encoding="utf-8")
            (root / "data" / "bridge_micro_lessons.json").write_text(json.dumps({"units": [{"id": "u1", "sections": ["1.1"], "status": "SOURCE_METHOD_READY", "lesson_steps": ["不含答案"]}]}, ensure_ascii=False), encoding="utf-8")
            (packet_dir / "learning_packet.json").write_text(json.dumps({
                "status": "VERIFIED",
                "counts": {"worked_examples": 1, "direct_variants": 0, "abc_exercises": 1},
                "workflow_order": ["repeat_each_learning_cycle_in_order"],
                "learning_cycles": [{
                    "cycle_id": "1.1-cycle-1", "sequence": 1, "title": "当前方法",
                    "course_keys": ["space_vector_ops"], "prerequisite_course_keys": [],
                    "knowledge_refs": ["1.1-k1"], "type_refs": ["类型Ⅰ"],
                    "worked_examples": [{"example_number": 1}], "direct_variants": [],
                    "exercise_questions": [{"group": "A", "number": 1}], "bridge_unit_ids": [],
                    "action_order": ["watch_current_courses"], "advance_gate": "本批通过后推进", "failure_rule": "停在当前批",
                }],
            }, ensure_ascii=False), encoding="utf-8")
            packet = packet_dir / "student_packet.json"
            packet.write_text(json.dumps({"packet_type": "DEEPSEEK_STUDENT_PACKET", "section": "1.1", "status": "VERIFIED", "manifest": {"question_count": 1}, "pages": [], "questions": [{"qid": "Q1", "question_text": "题面", "visual_status": "READY_TEXT_ONLY"}], "unresolved": [], "answer_sidecar": None}, ensure_ascii=False), encoding="utf-8")
            context_path = root / "data" / "contexts" / "1.1.json"
            context = build_context(packet, output_path=context_path)
        self.assertEqual(context["route_support"]["learning_plan"]["must_listen_courses"][0]["course_key"], "space_vector_ops")
        self.assertEqual(context["route_support"]["question_coverage"][0]["question_key"], "A1")
        sequential = context["route_support"]["sequential_learning_packet"]
        self.assertEqual(sequential["planning_scope"], "complete_section_route")
        self.assertEqual(sequential["execution_scope"], "current_cycle_only")
        self.assertIsInstance(sequential["current_cycle"], dict)
        self.assertNotIn("answer_sidecar", json.dumps(context["route_support"], ensure_ascii=False))

    def test_deepseek_probe_verifier_requires_full_context_bound_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            student = root / "student_packet.json"
            student.write_text(json.dumps({
                "packet_type": "DEEPSEEK_STUDENT_PACKET", "section": "1.1", "status": "VERIFIED",
                "manifest": {"question_count": 1}, "pages": [],
                "questions": [{"qid": "Q1", "question_text": "题面", "visual_status": "READY_TEXT_ONLY"}],
                "unresolved": [], "answer_sidecar": None,
            }, ensure_ascii=False), encoding="utf-8")
            context_path = root / "context.json"
            context = build_context(student, output_path=context_path)
            q = context["questions"][0]
            response = {
                "runtime": {"model": "opencode-go/deepseek-v4-flash", "reasoning_effort": "max", "context_window": 1000000},
                "context_sha256": context["evidence"]["context_sha256"],
                "canary": context["evidence"]["canary"],
                "qid_probes": {"Q1": derived_probe(context["evidence"]["canary"], "Q1")},
                "question_echo": {"Q1": {"question_text_sha256": __import__("hashlib").sha256(q["question_text"].encode("utf-8")).hexdigest(), "visual_status": "READY_TEXT_ONLY"}},
                "understanding_summary": "仅确认结构和顺序，不输出答案。",
            }
            response_path = root / "response.json"
            response_path.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(verify_worker_probe(context_path, response_path)["status"], "passed")
            response["qid_probes"]["Q1"] = "deadbeef"
            response_path.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
            self.assertIn("probe_mismatch:Q1", verify_worker_probe(context_path, response_path)["errors"])

    def test_canonical_context_path_is_not_packet_local(self) -> None:
        packet = Path("C:/project/data/packets/1.1/student_packet.json")
        self.assertEqual(context_path_for_student_packet(packet), Path("C:/project/data/contexts/1.1.json"))

    def test_student_packet_visual_gate_checks_every_question(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = Path(tmp) / "student_packet.json"
            packet.write_text(json.dumps({
                "packet_type": "DEEPSEEK_STUDENT_PACKET",
                "status": "VERIFIED",
                "manifest": {"page_count": 0, "question_count": 2},
                "pages": [],
                "questions": [
                    {"qid": "Q1", "question_text": "有题面", "visual_status": "READY_TEXT_ONLY"},
                    {"qid": "Q2", "question_text": "有题面", "visual_status": "NEEDS_PAGE_VISUAL"},
                ],
                "unresolved": [],
                "answer_sidecar": None,
            }, ensure_ascii=False), encoding="utf-8")
            result = __import__("ybt_learning.packet", fromlist=["verify_packet"]).verify_packet(packet)
        self.assertIn("Q2:visual_not_consumable", result["errors"])

    def test_deepseek_context_rejects_final_answer_phrase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = Path(tmp) / "context.json"
            context.write_text(json.dumps({"consumer": "deepseek_worker", "model_contract": {"model": "opencode-go/deepseek-v4-flash", "reasoning_effort": "max", "context_window": 1000000}, "pages": [{"ocr_doc": 1, "text": "最终答案是 3/5", "image_refs": [], "math_errors": []}], "questions": []}, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(validate_context(context)["status"], "failed")

    def test_deepseek_context_rejects_bare_answer_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = Path(tmp) / "context.json"
            context.write_text(json.dumps({
                "consumer": "deepseek_worker",
                "packet_type": "DEEPSEEK_STUDENT_CONTEXT",
                "model_contract": {"model": "opencode-go/deepseek-v4-flash", "reasoning_effort": "max", "context_window": 1000000},
                "status": "VERIFIED",
                "manifest": {"question_count": 1},
                "pages": [{"ocr_doc": 1, "text": "### 1. B", "image_refs": [], "math_errors": []}],
                "questions": [{"qid": "Q1", "question_text": "题面", "visual_status": "READY_TEXT_ONLY"}],
                "unresolved": [],
            }, ensure_ascii=False), encoding="utf-8")
            self.assertIn("answer_leak", validate_context(context)["errors"])

    def test_deepseek_context_rejects_unverified_or_incomplete_questions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context = Path(tmp) / "context.json"
            context.write_text(json.dumps({
                "consumer": "deepseek_worker",
                "packet_type": "DEEPSEEK_STUDENT_CONTEXT",
                "model_contract": {"model": "opencode-go/deepseek-v4-flash", "reasoning_effort": "max", "context_window": 1000000},
                "status": "VERIFIED",
                "manifest": {"question_count": 1},
                "pages": [],
                "questions": [{"qid": "Q1", "question_text": "", "visual_status": "NEEDS_VISION_SIDECAR"}],
                "unresolved": [],
            }, ensure_ascii=False), encoding="utf-8")
            errors = validate_context(context)["errors"]
        self.assertIn("empty_question_text", errors)
        self.assertIn("visual_not_consumable", errors)

    def test_suspicious_ocr_formula_is_not_silently_accepted(self) -> None:
        self.assertIn("suspicious_fraction_denominator_pi_manual_review", delimiter_errors(r"结果为 \(\frac{3}{\pi}\)"))

    def test_micro_b3_visual_correction_restores_am_without_inventing_e(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "micro专题1" / "student_packet.json").read_text(encoding="utf-8"))
        question = next(item for item in packet["questions"] if item.get("group") == "B" and item.get("number") == 3)
        self.assertIn("直线 AM 与平面 PBD 交于 O", question["question_text"])
        self.assertNotIn("直线 EM", question["question_text"])

    def test_current_student_packets_have_no_synthetic_ocr_empty_pages(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for path in (root / "data" / "packets").glob("*/student_packet.json"):
            packet = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(packet["pages"], path)
            self.assertFalse([page["ocr_doc"] for page in packet["pages"] if not str(page.get("text", "")).strip()], path)

    def test_learning_packet_instruction_and_variants_do_not_leak_solutions(self) -> None:
        root = Path(__file__).resolve().parents[1]
        leak = re.compile(r"答案\s*[：:]|解法\s*[一二两12]?\s*[：:]|解析\s*[：:]|解答\s*[：:]|最终答案|故答案|故\s*[A-D]\s*项(?:正确|错误)")
        for path in (root / "data" / "packets").glob("*/learning_packet.json"):
            packet = json.loads(path.read_text(encoding="utf-8"))
            instruction_text = json.dumps(packet.get("knowledge_and_type_pages", []), ensure_ascii=False)
            variant_text = json.dumps(packet.get("direct_variants", []), ensure_ascii=False)
            self.assertIsNone(leak.search(instruction_text), path)
            self.assertIsNone(leak.search(variant_text), path)
            self.assertNotIn("为方法册教学续页", instruction_text, path)

    def test_variant_without_analysis_heading_stops_at_option_judgement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ocr"
            root.mkdir()
            (root / "question.jpg").write_bytes(b"question")
            (root / "solution.jpg").write_bytes(b"solution")
            (root / "doc_0.md").write_text(
                "【例1】例题。\n解：教师方法。\n"
                "【变式1】（多选）题干（ ）\n"
                "A. 选项一\nB. 选项二\nC. 选项三\nD. 选项四 ![题图](question.jpg)\n"
                "设参数 d，由题意可得某关系，故 A 项错误； ![解法图](solution.jpg)\n"
                "B 项继续计算，故 B 项正确。\n",
                encoding="utf-8",
            )
            out = Path(tmp) / "out"
            PacketBuilder(ocr_root=root, output_root=out).build_section(
                {
                    "id": "test",
                    "label": "测试",
                    "ocr_docs": [0, 0],
                    "question_groups": {},
                    "knowledge_points": [],
                    "type_training": [],
                }
            )
            packet = json.loads((out / "test" / "learning_packet.json").read_text(encoding="utf-8"))
            variant = packet["direct_variants"][0]["question_text"]
            self.assertIn("D. 选项四", variant)
            self.assertNotIn("故 A 项错误", variant)
            self.assertNotIn("B 项继续计算", variant)
            self.assertEqual(
                [Path(ref["path"]).name for ref in packet["direct_variants"][0]["image_refs"]],
                ["question.jpg"],
            )

    def test_section_11_visual_corrections_reach_question_text(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "1.1" / "student_packet.json").read_text(encoding="utf-8"))
        questions = {item["number"]: item["question_text"] for item in packet["questions"]}
        self.assertIn("新疆巴音郭楞期末", questions[1])
        self.assertIn("\\overrightarrow{OA} = a - 2b + c", questions[13])
        self.assertNotIn("C组 拓展提升", questions[12])

    def test_section_11_question_visual_relations_match_current_stems(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "1.1" / "student_packet.json").read_text(encoding="utf-8"))
        questions = {f"{item['group']}{item['number']}": item for item in packet["questions"]}
        expected = {
            "A3": "G在线段CC1上",
            "B7": "A与B在公共棱l上",
            "B10": "F为AC中点",
            "B12": "连接PA、PB、PC",
        }
        for key, relation in expected.items():
            self.assertEqual(questions[key]["visual_status"], "VISION_VERIFIED", key)
            self.assertIn(relation, json.dumps(questions[key]["vision_sidecars"], ensure_ascii=False), key)

    def test_section_11_variant_11_fc_relation_matches_source_derivation(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "1.1" / "learning_packet.json").read_text(encoding="utf-8"))
        variant = next(
            item
            for item in packet["direct_variants"]
            if item.get("parent_example_number") == 11 and item.get("label") == "变式1"
        )
        compact_question = variant["question_text"].replace(" ", "")
        self.assertIn(r"\overrightarrow{FC}", compact_question)
        self.assertNotIn(r"\overrightarrow{FC_1}", compact_question)
        visual = json.dumps(variant["vision_sidecars"], ensure_ascii=False)
        self.assertIn("E在A1D1", visual)
        self.assertIn("F在A1C", visual)
        self.assertNotIn("E、F、B共线", visual)

        source = (root / "data" / "ocr_live_current" / "first_chapter_69" / "doc_6.md").read_text(encoding="utf-8")
        compact_source = source.replace(" ", "")
        self.assertIn(r"\overrightarrow{EF}=\frac{2}{5}\overrightarrow{EB}", compact_source)

    def test_section_14_example4_is_complete_and_not_in_instruction_pages(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "1.4" / "learning_packet.json").read_text(encoding="utf-8"))
        example = next(item for item in packet["worked_examples"] if item.get("label") == "例4")
        self.assertIn("alpha\\parallel\\beta", example["teaching_text"].replace(" ", ""))
        self.assertIn("k=-4", example["teaching_text"].replace(" ", ""))
        self.assertTrue(example["solution_present"])
        instruction = json.dumps(packet["knowledge_and_type_pages"], ensure_ascii=False).replace(" ", "")
        self.assertNotIn("k=-4", instruction)

    def test_section_11_cross_column_examples_have_complete_teaching(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "1.1" / "learning_packet.json").read_text(encoding="utf-8"))
        examples = {item["example_number"]: item for item in packet["worked_examples"]}
        for number in (2, 4, 5, 7):
            self.assertTrue(examples[number]["solution_present"], number)
        self.assertIn("overrightarrow{AC_1}", examples[2]["teaching_text"])
        self.assertNotIn("交换律", examples[2]["teaching_text"])
        self.assertIn("答案：BC", examples[4]["teaching_text"])
        self.assertIn("答案：D", examples[5]["teaching_text"])
        self.assertIn("frac{1}{4}", examples[7]["teaching_text"])
        self.assertNotIn("投影类型", examples[7]["teaching_text"])
        instruction = json.dumps(packet["knowledge_and_type_pages"], ensure_ascii=False)
        instruction_plain = "\n".join(item["text"] for item in packet["knowledge_and_type_pages"])
        self.assertIn("类型 I：空间向量的线性运算", instruction)
        self.assertIn("\\(A,P,B\\) 共线当且仅当 \\(x+y=1", instruction_plain)
        self.assertIn("不能推出 \\(a=c\\)", instruction_plain)
        self.assertNotIn("u+v=AD+BC=AC", instruction)

    def test_section_11_learning_item_visuals_have_complete_sidecars(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "1.1" / "learning_packet.json").read_text(encoding="utf-8"))
        visual_items = [
            item
            for item in [*packet.get("worked_examples", []), *packet.get("direct_variants", [])]
            if item.get("image_refs")
        ]
        inventory = json.loads(
            (
                root
                / "reports"
                / "all_chapters"
                / "visual-inventory-source-question-only.json"
            ).read_text(encoding="utf-8")
        )
        expected_images = [
            row
            for row in inventory["items"]
            if row.get("section") == "1.1"
            and row.get("kind") in {"worked_example", "direct_variant"}
        ]
        self.assertEqual(
            sum(len(item["image_refs"]) for item in visual_items),
            len(expected_images),
        )
        for item in visual_items:
            self.assertEqual(item.get("visual_status"), "VISION_VERIFIED", item.get("label"))
            self.assertEqual(len(item.get("vision_sidecars", [])), len(item["image_refs"]), item.get("label"))
            self.assertTrue(item.get("vision_hint", "").startswith("1.1-LI"), item.get("label"))

    def test_section_12_example3_cross_column_solution_is_rejoined(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "1.2_1.3" / "learning_packet.json").read_text(encoding="utf-8"))
        example = next(item for item in packet["worked_examples"] if item["example_number"] == 3)
        self.assertTrue(example["solution_present"])
        self.assertIn("A'(0,2,-3)", example["teaching_text"])
        self.assertIn("答案：B", example["teaching_text"])
        self.assertNotIn("对称点坐标", example["teaching_text"])

    def test_section_14_reported_ocr_defects_are_repaired(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "1.4" / "learning_packet.json").read_text(encoding="utf-8"))
        examples = {item["example_number"]: item for item in packet["worked_examples"]}
        self.assertNotIn("答案：C", examples[7]["teaching_text"])
        self.assertIn("答案：B", examples[7]["teaching_text"])
        self.assertIn("ABCD-A_1B_1C_1D_1", examples[16]["question_text"])
        self.assertIn("sqrt{|\\overrightarrow{AB}|^2", examples[18]["teaching_text"])
        self.assertIn("平面 \\(CDC_1\\) 的一个法向量", examples[22]["teaching_text"])
        instruction = json.dumps(packet["knowledge_and_type_pages"], ensure_ascii=False)
        self.assertNotIn("则k=", instruction)
        self.assertNotIn("则式①可改写", instruction)
        b5 = next(item for item in packet["exercise_questions"] if item["group"] == "B" and item["number"] == 5)
        b7 = next(item for item in packet["exercise_questions"] if item["group"] == "B" and item["number"] == 7)
        self.assertIn("AB=AD=AA_{1}=1", b5["question_text"].replace(" ", ""))
        self.assertIn("\\angle A_{1}AB", b5["question_text"])
        self.assertNotRegex(b5["question_text"], r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
        self.assertNotIn("数·高中数学一本通", b7["question_text"])

    def test_section_12_exercise_provenance_is_restored(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "1.2_1.3" / "learning_packet.json").read_text(encoding="utf-8"))
        questions = {item["number"]: item for item in packet["exercise_questions"]}
        self.assertIn("2025·广东清远期末", questions[5]["question_text"])
        self.assertIn("2025·安徽阜阳期末", questions[9]["question_text"])
        self.assertIn("2025·河北廊坊期末", questions[11]["question_text"])
        self.assertNotIn("一数·高中数学一本通", questions[5]["question_text"])
        self.assertEqual(questions[9]["source_anchor"]["pdf_page"], 31)

    def test_micro_reported_ocr_defects_are_repaired(self) -> None:
        root = Path(__file__).resolve().parents[1]
        packet = json.loads((root / "data" / "packets" / "micro专题1" / "learning_packet.json").read_text(encoding="utf-8"))
        examples = {item["example_number"]: item for item in packet["worked_examples"]}
        self.assertIn("A_1EGF\\) 为矩形", examples[2]["teaching_text"])
        self.assertIn(r"P\left(1,1,\frac{1}{3}\right)", examples[5]["teaching_text"])
        self.assertNotIn(r"P\left(1,1,\frac{1}{2}\right)", examples[5]["teaching_text"])
        self.assertIn(r"\frac{\pi}{2}", examples[7]["teaching_text"])
        self.assertNotIn(r"\frac{\pi}{7}", examples[7]["teaching_text"])
        c7 = next(item for item in packet["exercise_questions"] if item["group"] == "C" and item["number"] == 7)
        self.assertNotIn("数·高中数学一本通", c7["question_text"])
        self.assertEqual(c7["visual_status"], "VISION_VERIFIED")

    def test_course_id_matching_prefers_specific_suffix(self) -> None:
        self.assertEqual(course_id_from_stem("3.1.4.6.a 平面方程与法向量（上）"), "3.1.4.6.a")
        self.assertEqual(course_id_from_stem("3.1.4.6.a 平面方程与法向量（上）"), "3.1.4.6.a")

    def test_current_plan_listens_to_every_coverage_course_dependency(self) -> None:
        root = Path(__file__).resolve().parents[1]
        plan = json.loads((root / "data" / "chapter1_learning_plan.json").read_text(encoding="utf-8"))
        coverage = json.loads((root / "data" / "question_coverage.json").read_text(encoding="utf-8"))
        by_section = {item["section"]: {course.get("course_key") for course in item.get("must_listen_courses", [])} for item in plan["plan"]}
        for question in coverage["questions"]:
            missing = set(question.get("course_keys", [])) - by_section[question["section"]]
            self.assertFalse(missing, "%s/%s missing must-listen courses: %s" % (question["section"], question["question_key"], sorted(missing)))

    def test_bridge_targets_are_consistent_across_manifest_plan_and_coverage(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest = load_manifest(root / "chapter1_manifest.json")
        plan = json.loads((root / "data" / "chapter1_learning_plan.json").read_text(encoding="utf-8"))
        coverage = json.loads((root / "data" / "question_coverage.json").read_text(encoding="utf-8"))
        canonical = {unit["id"]: set(unit.get("target_questions", [])) for unit in json.loads((root / "data" / "bridge_micro_lessons.json").read_text(encoding="utf-8"))["units"]}
        coverage_targets = {unit_id: set() for unit_id in canonical}
        for question in coverage["questions"]:
            for unit in question.get("bridge_units", []):
                coverage_targets.setdefault(unit["id"], set()).add(question["section"] + "-" + question["question_key"])
        plan_targets = {unit_id: set() for unit_id in canonical}
        for section in plan["plan"]:
            for unit in section.get("bridge_units", []):
                plan_targets.setdefault(unit["id"], set()).update(unit.get("target_question_keys", []))
        manifest_ids = {unit["id"] for section in manifest["sections"] for unit in section.get("bridge_units", [])}
        for unit_id, targets in canonical.items():
            self.assertIn(unit_id, manifest_ids)
            self.assertEqual(targets, coverage_targets.get(unit_id, set()), unit_id)
            self.assertEqual(targets, plan_targets.get(unit_id, set()), unit_id)

    def test_real_user_artifact_and_identity_guards_are_enforced(self) -> None:
        collector = _load_real_user_collector()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            for rel in (collector.PLAN_REL, collector.COVERAGE_REL, collector.SCHEMA_REL):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((collector.PROJECT_ROOT / rel).read_bytes())
            consent = root / "consent.txt"
            consent.write_text("CONSENT\n", encoding="utf-8")
            first = collector.cmd_register(root, argparse.Namespace(slot="real-user-01", participant_id="DUPLICATE", consent_artifact=str(consent)))
            self.assertEqual(first["status"], "registered")
            with self.assertRaises(ValueError):
                collector.cmd_register(root, argparse.Namespace(slot="real-user-02", participant_id="DUPLICATE", consent_artifact=str(consent)))
            plan = collector.load_plan_index(root)
            with self.assertRaises(ValueError):
                collector.build_event(root, "real-user-01", "section_complete", "1.1", {"section": "1.1", "exit_gate": plan["1.1"]["exit_gate"]}, [], None, None, "DUPLICATE")

    def test_current_zero_base_simulation_is_the_only_authoritative_source(self) -> None:
        root = Path(__file__).resolve().parents[1]
        acceptance = _load_project_script(
            "ybt_acceptance_evidence_test",
            "scripts/generate_acceptance_report.py",
        )
        metadata, simulation = acceptance.load_current_simulation(root)
        self.assertEqual(metadata["path"], "reports/zero_base_cycles/1.1-current-agent-simulation.json")
        self.assertEqual(metadata["status"], "passed", metadata)
        self.assertEqual(metadata["mastery_status"], "passed")
        self.assertEqual(simulation["summary"]["pass"], 5)
        self.assertEqual(len(simulation["item_results"]), 38)
        self.assertEqual(metadata["source_revision_match"], True)
        self.assertIn("reports/zero_base_agent_simulation.json", metadata["legacy_fallback_ignored"])
        self.assertEqual(metadata["errors"], [])

    def test_stale_current_simulation_does_not_fallback_to_legacy_five_of_five(self) -> None:
        root = Path(__file__).resolve().parents[1]
        acceptance = _load_project_script(
            "ybt_acceptance_evidence_stale_test",
            "scripts/generate_acceptance_report.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            current = temp_root / "reports" / "zero_base_cycles" / "1.1-current-agent-simulation.json"
            current.parent.mkdir(parents=True)
            legacy = temp_root / "reports" / "zero_base_agent_simulation.json"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text(json.dumps({"summary": {"pass": 5}}), encoding="utf-8")
            current.write_text(json.dumps({
                "artifact": "CURRENT_GENERATION_ZERO_BASE_AGENT_SIMULATION",
                "section": "1.1",
                "generation": "G-test",
                "summary": {"workers": 5, "pass": 5, "partial": 0, "fail": 0},
            }), encoding="utf-8")
            metadata, simulation = acceptance.load_current_simulation(temp_root)
        self.assertEqual(metadata["status"], "blocked")
        self.assertEqual(metadata["mastery_status"], "blocked")
        self.assertEqual(simulation["summary"]["pass"], 5)
        self.assertIn("worker_contract_mismatch:workers_dispatched", metadata["errors"])

    def test_context_enriches_knowledge_pages_from_kat(self) -> None:
        """知识页（如投影向量定义）必须进入学生上下文，不能被中性锚点整页剥掉。"""
        root = Path(__file__).resolve().parents[1]
        ctx = json.loads((root / "data" / "contexts" / "1.1.json").read_text(encoding="utf-8"))
        pages = {p.get("ocr_doc"): p for p in ctx.get("pages", [])}
        doc4 = pages.get(4)
        self.assertIsNotNone(doc4, "context must keep knowledge page ocr_doc=4")
        self.assertIn("投影向量", doc4.get("text", ""))
        self.assertIn("向向量投影", doc4.get("text", ""))
        self.assertNotIn("为方法册教学续页", doc4.get("text", ""))
        anchors = sorted(d for d, p in pages.items() if "为方法册教学续页" in p.get("text", ""))
        self.assertTrue(set(anchors).issubset({6, 8, 11}), anchors)

    def test_legacy_teacher_judgement_is_not_current_evidence(self) -> None:
        root = Path(__file__).resolve().parents[1]
        acceptance = _load_project_script(
            "ybt_acceptance_teacher_binding_test",
            "scripts/generate_acceptance_report.py",
        )
        metadata, judge = acceptance.load_current_teacher_judge(root, {"generation": "G-20260816-02"})
        self.assertEqual(metadata["status"], "blocked")
        self.assertEqual(judge["judge_status"], "same_session_workflow_pass")
        self.assertIn("teacher_judge_generation_missing", metadata["errors"])
        self.assertIn("teacher_judge_source_hash_mismatch:data/question_coverage.json", metadata["errors"])

    def test_generation_snapshot_hashes_current_simulation(self) -> None:
        root = Path(__file__).resolve().parents[1]
        snapshot = _load_project_script(
            "ybt_generation_snapshot_test",
            "scripts/create_generation_snapshot.py",
        )
        groups = snapshot._input_groups(root)
        evidence_paths = {path.resolve() for path in groups["student_evidence"]}
        current = (root / "reports" / "zero_base_cycles" / "1.1-current-agent-simulation.json").resolve()
        self.assertIn(current, evidence_paths)
        self.assertNotIn((root / "reports" / "zero_base_agent_simulation.json").resolve(), evidence_paths)
        result = snapshot.create_snapshot(root, "G-test-current")
        self.assertIn("reports/zero_base_cycles/1.1-current-agent-simulation.json", result["revisions"]["student_evidence"]["files"])
        current_generation = json.loads(current.read_text(encoding="utf-8"))["generation"]
        self.assertEqual(result["release_gates"]["current_zero_base_simulation_generation"], current_generation)
        # 模拟层面 mastery 门通过（5/5 全覆盖）；发布门仍必须关闭（24h 冷复测/真人未运行）。
        self.assertTrue(result["release_gates"]["current_zero_base_simulation_mastery_gate"])
        self.assertFalse(result["release_gates"]["all_questions_release"])
        self.assertFalse(result["release_gates"]["full_every_question_release_gate"])

    def test_without_question_route_uses_shared_method_prompts_without_answer_skeletons(self) -> None:
        root = Path(__file__).resolve().parents[1]
        route = (root / "data" / "packets" / "1.1" / "learning_path_without_questions.md").read_text(encoding="utf-8-sig")
        self.assertIn("结合课程", route)
        self.assertNotIn("看到‘中点 + 求一条端点到中点的向量’", route)
        self.assertNotIn("看到二面角中两条都垂直于公共棱", route)
        self.assertNotIn("先把 CD 拆成 CA、AB、BD 三段", route)
        self.assertNotIn(r"\overrightarrow{CD}=\overrightarrow{CA}+\overrightarrow{AB}+\overrightarrow{BD}", route)


if __name__ == "__main__":
    unittest.main()

class LiveEvidenceChainTests(unittest.TestCase):
    """提交库内真实证据链回归（只读，不生成新证据）：第一张图奖励、样本侧车与 1.1 包绑定。"""

    ROOT = Path(__file__).resolve().parents[1]
    FIRST_IMAGE_CURRENT = ROOT / "data" / "ocr_live_current" / "first_chapter_69" / "imgs" / "img_in_image_box_523_429_694_610.jpg"
    FIRST_IMAGE_LIVE = ROOT / "data" / "ocr_live_full" / "imgs" / "img_in_image_box_523_429_694_610.jpg"

    def test_first_image_reward_chain_committed_artifacts(self) -> None:
        self.assertTrue(self.FIRST_IMAGE_CURRENT.is_file(), "第一张图当前 OCR 根文件必须存在")
        self.assertTrue(self.FIRST_IMAGE_LIVE.is_file(), "第一张图 live OCR 根文件必须存在")
        self.assertEqual(
            _sha256_file(self.FIRST_IMAGE_CURRENT),
            _sha256_file(self.FIRST_IMAGE_LIVE),
            "两棵根的图片必须逐字节一致（PacketBuilder 内容哈希绑定）",
        )
        first_state = json.loads((self.ROOT / "data" / "first-image-reward-test-state.json").read_text(encoding="utf-8"))
        grant = next(g for g in first_state["rewards"]["grants"] if g["item_id"] == "1.1-A1")
        self.assertEqual(grant["milestone"], "full_pass")
        self.assertEqual(grant["points"], 10)
        self.assertIn("visual_verified", grant["evidence"])
        packet = json.loads((self.ROOT / "data" / "packets" / "1.1" / "student_packet.json").read_text(encoding="utf-8"))
        a1 = next(q for q in packet["questions"] if q.get("group") == "A" and q.get("number") == 1)
        self.assertEqual(a1["visual_status"], "VISION_VERIFIED")
        self.assertTrue(a1.get("evidence"))
        self.assertTrue(any(Path(str(ref.get("ref") or ref.get("path") or "")).name == self.FIRST_IMAGE_CURRENT.name for ref in a1.get("image_refs", [])))
        self.assertTrue(any(row.get("confidence") in {"E1", "E2"} for row in a1.get("vision_sidecars", []) if isinstance(row, dict)))

    def test_committed_reward_test_state_invariants(self) -> None:
        state = json.loads((self.ROOT / "data" / "reward-test-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["rewards"]["points"], 50)
        grants = state["rewards"]["grants"]
        self.assertEqual(len(grants), 3)
        self.assertEqual({g["milestone"] for g in grants}, {"full_pass", "near_transfer", "delayed_recall"})
        self.assertEqual(len({g["idempotency_key"] for g in grants}), 3)
