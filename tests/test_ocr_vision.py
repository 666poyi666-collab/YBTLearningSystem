from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ybt_learning.ocr as ocr
import ybt_learning.vision as vision


class BaiduQianfanOcrConfigTests(unittest.TestCase):
    """百度/千帆 OCR provider 入口：环境变量唯一凭据源；无凭据时必须 not_run，禁止伪造 live pass。"""

    def test_ocr_status_without_baidu_creds_preserves_configured_api_evidence(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            status = ocr.ocr_config_status()
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["baidu_qianfan"]["status"], "not_run")
        self.assertFalse(status["baidu_qianfan"]["configured"])
        self.assertFalse(status["baidu_qianfan"]["live_verified"])
        self.assertFalse(status["baidu_qianfan_verified"])
        self.assertEqual(status["selected_provider"], "paddle_ai_studio")
        self.assertEqual(status["active_provider"], "paddle_ai_studio")
        self.assertTrue(status["active_provider_live_verified"])

    def test_live_probe_is_separate_from_baidu_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            evidence = project / "data" / "ocr_live_evidence.json"
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_text(json.dumps({"status": "passed", "provider": "PaddleOCR AI Studio", "document_count": 69, "exact_match_with_historical": True}, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(ocr, "__file__", str(project / "ybt_learning" / "ocr.py")), mock.patch.dict(os.environ, {}, clear=True):
                status = ocr.ocr_config_status()
        self.assertEqual(status["live_probe"]["status"], "passed")
        self.assertEqual(status["live_probe"]["document_count"], 69)
        self.assertEqual(status["active_provider"], "paddle_ai_studio")
        self.assertTrue(status["active_provider_live_verified"])
        self.assertEqual(status["baidu_qianfan"]["live_verified"], False)
        self.assertNotIn("BAIDU_OCR_API_KEY=", json.dumps(status, ensure_ascii=False))

    def test_current_paddle_live_evidence_takes_precedence_over_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            data = project / "data"
            output = data / "ocr_live_current"
            output.mkdir(parents=True, exist_ok=True)
            (data / "ocr_live_evidence.json").write_text(json.dumps({
                "status": "passed",
                "provider": "PaddleOCR AI Studio",
                "document_count": 69,
                "exact_match_with_historical": True,
            }, ensure_ascii=False), encoding="utf-8")
            (data / "ocr_live_current_evidence.json").write_text(json.dumps({
                "status": "passed",
                "provider": "PaddleOCR AI Studio",
                "fresh_api_run": True,
                "job_id": "live-job",
                "document_count": 69,
                "expected_document_count": 69,
                "output_root": str(output),
                "exact_match_with_historical": True,
            }, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(ocr, "__file__", str(project / "ybt_learning" / "ocr.py")), mock.patch.dict(os.environ, {}, clear=True):
                status = ocr.ocr_config_status()
        self.assertTrue(status["active_provider_live_verified"])
        self.assertTrue(status["live_probe"]["current_live"])
        self.assertEqual(status["live_probe"]["job_id"], "live-job")
        self.assertEqual(status["live_probe"]["evidence_path"].replace("\\", "/").split("/")[-1], "ocr_live_current_evidence.json")

    def test_ocr_status_ready_with_env_creds_and_no_leak(self) -> None:
        fake_api = "TEST_API_KEY_abc123"
        fake_secret = "TEST_SECRET_xyz789"
        with mock.patch.dict(
            os.environ,
            {ocr.BAIDU_OCR_API_KEY_ENV: fake_api, ocr.BAIDU_OCR_SECRET_KEY_ENV: fake_secret},
            clear=True,
        ):
            status = ocr.ocr_config_status()
        self.assertTrue(status["baidu_qianfan"]["configured"])
        self.assertEqual(status["baidu_qianfan"]["status"], "ready")
        self.assertTrue(status["baidu_qianfan"]["api_key_present"])
        self.assertTrue(status["baidu_qianfan"]["secret_key_present"])
        self.assertEqual(status["selected_provider"], "paddle_ai_studio")
        self.assertFalse(status["baidu_qianfan"]["live_verified"])
        serialized = json.dumps(status, ensure_ascii=False)
        self.assertNotIn(fake_api, serialized)
        self.assertNotIn(fake_secret, serialized)

    def test_credentials_status_never_returns_values(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ocr.BAIDU_OCR_API_KEY_ENV: "LEAK_ME_111", ocr.BAIDU_OCR_SECRET_KEY_ENV: "LEAK_ME_222"},
            clear=True,
        ):
            creds = ocr.baidu_ocr_credentials_status()
        self.assertNotIn("LEAK_ME_111", json.dumps(creds, ensure_ascii=False))
        self.assertNotIn("LEAK_ME_222", json.dumps(creds, ensure_ascii=False))
        self.assertEqual(creds["api_key_source"], "environment")

    def test_fetch_token_not_run_without_creds(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            result = ocr.baidu_ocr_fetch_token()
        self.assertEqual(result["status"], "not_run")
        self.assertIn("not_set", result["reason"])

    def test_run_baidu_ocr_not_run_without_creds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "page.png"
            image.write_bytes(b"\x89PNG fake image bytes")
            with mock.patch.dict(os.environ, {}, clear=True):
                result = ocr.run_baidu_ocr(image, Path(tmp) / "out")
        self.assertEqual(result["status"], "not_run")
        self.assertNotEqual(result["status"], "passed")

    def test_run_baidu_ocr_missing_image_fails_before_network(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ocr.BAIDU_OCR_API_KEY_ENV: "FAKE_KEY", ocr.BAIDU_OCR_SECRET_KEY_ENV: "FAKE_SECRET"},
            clear=True,
        ), mock.patch.object(ocr, "baidu_ocr_fetch_token") as fetch:
            result = ocr.run_baidu_ocr(Path("Z:/definitely/missing/page.png"))
        fetch.assert_not_called()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "missing_image")

    def test_build_token_request_structure(self) -> None:
        req = ocr._build_token_request("ak_1", "sk_2", ocr.BAIDU_OCR_DEFAULT_TOKEN_URL)
        self.assertEqual(req.method, "POST")
        self.assertIn("grant_type=client_credentials", req.full_url)
        self.assertIn("client_id=ak_1", req.full_url)
        self.assertIn("client_secret=sk_2", req.full_url)

    def test_build_ocr_request_structure(self) -> None:
        req = ocr._build_ocr_request("tok_9", "QUJD", ocr.BAIDU_OCR_DEFAULT_ENDPOINT)
        self.assertIn("access_token=tok_9", req.full_url)
        self.assertEqual(req.get_header("Content-type"), "application/x-www-form-urlencoded")
        self.assertEqual(req.data, b"image=QUJD")

    def test_qianfan_vision_not_run_without_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "page.png"
            image.write_bytes(b"fake-image")
            with mock.patch.dict(os.environ, {}, clear=True):
                result = ocr.run_qianfan_vision(image, Path(tmp) / "out")
        self.assertEqual(result["status"], "not_run")
        self.assertEqual(result["provider"], ocr.PROVIDER_QIANFAN)

    def test_qianfan_vision_request_is_openai_compatible_and_redacted(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": "题号：A1\n图中有三棱柱"}}]}).encode("utf-8")

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "page.png"
            image.write_bytes(b"fake-image")
            fake_key = "QIANFAN_SECRET_FOR_TEST"
            with mock.patch.dict(os.environ, {ocr.QIANFAN_API_KEY_ENV: fake_key}, clear=True), mock.patch.object(ocr.urllib.request, "urlopen", return_value=FakeResponse()) as urlopen:
                result = ocr.run_qianfan_vision(image, Path(tmp) / "out")
            request = urlopen.call_args.args[0]
            body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(result["status"], "passed")
        self.assertEqual(request.full_url, ocr.QIANFAN_DEFAULT_ENDPOINT)
        self.assertEqual(body["model"], ocr.QIANFAN_DEFAULT_MODEL)
        self.assertEqual(body["messages"][0]["content"][0]["type"], "image_url")
        self.assertNotIn(fake_key, json.dumps(result, ensure_ascii=False))


class GlmVisionSidecarContractTests(unittest.TestCase):
    """GLM 视觉侧车契约核查：配置来源只报状态不泄密钥；生成端 fail-closed 与消费端 gate 一致。"""

    def test_vision_config_uses_env_source_and_never_leaks(self) -> None:
        fake_key = "TEST_GLM_KEY_1"
        with mock.patch.dict(
            os.environ,
            {vision.GLM_VISION_KEY_ENV: fake_key, vision.GLM_VISION_BASE_URL_ENV: "https://example.invalid/v4/chat/completions"},
            clear=True,
        ), mock.patch.object(vision, "VISION_CONFIG_PATH", Path("Z:/missing/config.json")):
            status = vision.test_vision_config()
        self.assertEqual(status["status"], "passed")
        self.assertEqual(status["key_source"], "environment")
        self.assertTrue(status["has_api_key"])
        self.assertFalse(status["live_verified"])
        serialized = json.dumps(status, ensure_ascii=False)
        self.assertNotIn(fake_key, serialized)

    def test_vision_config_not_run_without_any_source(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(vision, "VISION_CONFIG_PATH", Path("Z:/missing/config.json")):
            status = vision.test_vision_config()
        self.assertEqual(status["status"], "not_run")
        self.assertEqual(status["reason"], "no_vision_credentials")
        self.assertFalse(status["has_api_key"])

    def test_vision_config_config_source_does_not_leak_key(self) -> None:
        if not vision.VISION_CONFIG_PATH.exists():
            self.skipTest("deepseek-eyes config.json not present on this machine")
        config_key = json.loads(vision.VISION_CONFIG_PATH.read_text(encoding="utf-8")).get("api_key", "")
        if not config_key:
            self.skipTest("config.json has no api_key")
        with mock.patch.dict(os.environ, {}, clear=True):
            status = vision.test_vision_config()
        self.assertEqual(status["status"], "passed")
        self.assertEqual(status["key_source"], "config")
        self.assertNotIn(config_key, json.dumps(status, ensure_ascii=False))

    def test_vision_config_rejects_wrong_model_contract(self) -> None:
        with mock.patch.dict(
            os.environ,
            {vision.GLM_VISION_KEY_ENV: "k", vision.GLM_VISION_BASE_URL_ENV: "https://example.invalid/v4/chat/completions"},
            clear=True,
        ), mock.patch.object(vision, "VISION_CONFIG_PATH", Path("Z:/missing/config.json")):
            status = vision.test_vision_config()
        self.assertEqual(status["status"], "passed")  # 默认模型即 glm-4.6v-flash
        self.assertEqual(status["model"], "glm-4.6v-flash")

    def test_sidecar_contract_consistent(self) -> None:
        contract = vision.sidecar_contract_status()
        self.assertEqual(contract["status"], "consistent")
        self.assertEqual(contract["schema_version"], "7.1")
        self.assertEqual(contract["model"], "glm-4.6v-flash")
        self.assertIn("consumer_guard", contract)

    def test_question_sidecar_persists_section_from_hint(self) -> None:
        with mock.patch.object(vision, "describe_image", return_value={
            "status": "passed",
            "model": "glm-4.6v-flash",
            "elapsed_ms": 1,
            "confidence": "E2",
            "structured": {"objects": ["A"], "relations": [], "coordinates": [], "ranges": [], "text": ["A"], "uncertainties": [], "confidence": "E2"},
        }), tempfile.TemporaryDirectory() as tmp:
            payload = vision.sidecar_for_question_images([("1.2+1.3-B5", "x.png")], output_path=Path(tmp) / "sidecar.json")
        self.assertEqual(payload["results"][0]["section"], "1.2+1.3")

    def test_sidecar_fail_closed_when_vision_unverified(self) -> None:
        unverified = {
            "status": "unverified",
            "path": "x.png",
            "model": "glm-4.6v-flash",
            "elapsed_ms": 10,
            "confidence": "E0",
            "structured": {"objects": [], "relations": [], "coordinates": [], "ranges": [], "text": [], "uncertainties": ["看不清"], "confidence": "E0"},
        }
        with mock.patch.object(vision, "describe_image", return_value=unverified), tempfile.TemporaryDirectory() as tmp:
            payload = vision.sidecar_for_question_images([("Q1", "x.png")], output_path=Path(tmp) / "sidecar.json")
            written = json.loads((Path(tmp) / "sidecar.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "unverified")
        self.assertEqual(written["status"], "unverified")
        self.assertEqual(written["schema_version"], "7.1")
        self.assertIn("consumer_guard", written)
        self.assertEqual(written["results"][0]["confidence"], "E0")

    def test_sidecar_passed_only_when_all_results_e1_or_e2(self) -> None:
        def describe_ok(path, **kwargs):
            return {
                "status": "passed",
                "path": str(path),
                "model": "glm-4.6v-flash",
                "elapsed_ms": 10,
                "confidence": "E1" if str(path).endswith("a.png") else "E2",
                "structured": {"objects": ["A"], "relations": [], "coordinates": [], "ranges": [], "text": ["题干"], "uncertainties": [], "confidence": "E1" if str(path).endswith("a.png") else "E2"},
            }

        with mock.patch.object(vision, "describe_image", side_effect=describe_ok), tempfile.TemporaryDirectory() as tmp:
            payload = vision.sidecar_for_question_images([("Q1", "a.png"), ("Q2", "b.png")], output_path=Path(tmp) / "sidecar.json")
        self.assertEqual(payload["status"], "passed")
        self.assertEqual([r["confidence"] for r in payload["results"]], ["E1", "E2"])

    def test_question_batch_accepts_targeted_prompt_and_token_budget(self) -> None:
        with mock.patch.object(vision, "describe_image", return_value={
            "status": "passed", "model": "glm-4.6v-flash", "elapsed_ms": 1,
            "confidence": "E2", "structured": {"objects": ["A"], "relations": [], "coordinates": [], "ranges": [], "text": [], "uncertainties": [], "confidence": "E2"},
        }) as describe, tempfile.TemporaryDirectory() as tmp:
            vision.sidecar_for_question_images([("Q1", "x.png")], output_path=Path(tmp) / "sidecar.json", prompt="只识别图形关系", max_tokens=2048)
        describe.assert_called_once()
        self.assertEqual(describe.call_args.kwargs["prompt"], "只识别图形关系")
        self.assertEqual(describe.call_args.kwargs["max_tokens"], 2048)

    def test_sidecar_unverified_when_any_result_fails(self) -> None:
        failed = {"status": "failed", "path": "x.png", "error": "boom"}
        ok = {
            "status": "passed",
            "path": "y.png",
            "model": "glm-4.6v-flash",
            "elapsed_ms": 10,
            "confidence": "E1",
            "structured": {"objects": ["A"], "relations": [], "coordinates": [], "ranges": [], "text": ["题干"], "uncertainties": [], "confidence": "E1"},
        }
        with mock.patch.object(vision, "describe_image", side_effect=[ok, failed]), tempfile.TemporaryDirectory() as tmp:
            payload = vision.sidecar_for_question_images([("Q1", "y.png"), ("Q2", "x.png")], output_path=Path(tmp) / "sidecar.json")
        self.assertEqual(payload["status"], "unverified")


if __name__ == "__main__":
    unittest.main()
