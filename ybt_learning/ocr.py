from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


OCR_SCRIPT = Path(r"C:\开发\ocr本地\paddleocr_ai_studio.py")

PROVIDER_PADDLE = "paddle_ai_studio"
PROVIDER_BAIDU = "baidu_standard"
PROVIDER_QIANFAN = "qianfan_vision"

# 百度智能云 / 千帆 OCR：只从环境变量读取凭据，绝不把密钥写入代码、输出或报告。
BAIDU_OCR_API_KEY_ENV = "BAIDU_OCR_API_KEY"
BAIDU_OCR_SECRET_KEY_ENV = "BAIDU_OCR_SECRET_KEY"
BAIDU_OCR_TOKEN_URL_ENV = "BAIDU_OCR_TOKEN_URL"
BAIDU_OCR_ENDPOINT_ENV = "BAIDU_OCR_ENDPOINT"
YBT_OCR_PROVIDER_ENV = "YBT_OCR_PROVIDER"

BAIDU_OCR_DEFAULT_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_OCR_DEFAULT_ENDPOINT = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
# accurate_basic 要求 base64 编码后不超过 4MB。
BAIDU_OCR_BASE64_LIMIT = 4 * 1024 * 1024

QIANFAN_API_KEY_ENV = "QIANFAN_API_KEY"
QIANFAN_API_KEY_ALIASES = ("BAIDU_QIANFAN_API_KEY", "QIANFAN_ACCESS_TOKEN")
QIANFAN_ENDPOINT_ENV = "QIANFAN_VISION_ENDPOINT"
QIANFAN_MODEL_ENV = "QIANFAN_VISION_MODEL"
QIANFAN_DEFAULT_ENDPOINT = "https://qianfan.baidubce.com/v2/chat/completions"
QIANFAN_DEFAULT_MODEL = "qwen2.5-vl-7b-instruct"
QIANFAN_IMAGE_LIMIT = 10 * 1024 * 1024


def _env_flag(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def _redacted_env(name: str) -> str:
    """返回值只用于展示：有值返回名称来源，不返回密钥本身。"""
    return "environment" if _env_flag(name) else "not_set"


def _qianfan_key() -> tuple[str, str]:
    if _env_flag(QIANFAN_API_KEY_ENV):
        return os.environ[QIANFAN_API_KEY_ENV].strip(), QIANFAN_API_KEY_ENV
    for name in QIANFAN_API_KEY_ALIASES:
        if _env_flag(name):
            return os.environ[name].strip(), name
    return "", "not_set"


def qianfan_credentials_status() -> dict[str, Any]:
    key, source = _qianfan_key()
    return {
        "provider": PROVIDER_QIANFAN,
        "api_key_present": bool(key),
        "api_key_source": source,
        "endpoint_source": "custom" if _env_flag(QIANFAN_ENDPOINT_ENV) else "default",
        "model": os.environ.get(QIANFAN_MODEL_ENV, "").strip() or QIANFAN_DEFAULT_MODEL,
        "configured": bool(key),
        "live_verified": False,
    }


def baidu_ocr_credentials_status() -> dict[str, Any]:
    """只报告哪些环境变量已配置，永不返回密钥内容。"""
    api_key = _env_flag(BAIDU_OCR_API_KEY_ENV)
    secret_key = _env_flag(BAIDU_OCR_SECRET_KEY_ENV)
    return {
        "provider": PROVIDER_BAIDU,
        "api_key_present": api_key,
        "secret_key_present": secret_key,
        "api_key_source": _redacted_env(BAIDU_OCR_API_KEY_ENV),
        "secret_key_source": _redacted_env(BAIDU_OCR_SECRET_KEY_ENV),
        "token_url_source": "custom" if _env_flag(BAIDU_OCR_TOKEN_URL_ENV) else "default",
        "endpoint_source": "custom" if _env_flag(BAIDU_OCR_ENDPOINT_ENV) else "default",
        "configured": api_key and secret_key,
        "live_verified": False,
    }


def _build_token_request(api_key: str, secret_key: str, token_url: str) -> urllib.request.Request:
    query = urllib.parse.urlencode(
        {"grant_type": "client_credentials", "client_id": api_key, "client_secret": secret_key}
    )
    return urllib.request.Request(f"{token_url}?{query}", data=b"", method="POST")


def _build_ocr_request(access_token: str, image_base64: str, endpoint: str) -> urllib.request.Request:
    body = urllib.parse.urlencode({"image": image_base64}).encode("ascii")
    url = f"{endpoint}?{urllib.parse.urlencode({'access_token': access_token})}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    return req


def baidu_ocr_fetch_token(*, timeout_s: int = 30) -> dict[str, Any]:
    """换取百度 OCR access token。返回的 token 仅供 run_baidu_ocr 内部使用，不得序列化进任何报告。"""
    creds = baidu_ocr_credentials_status()
    if not creds["configured"]:
        return {
            "status": "not_run",
            "provider": PROVIDER_BAIDU,
            "reason": "BAIDU_OCR_API_KEY/BAIDU_OCR_SECRET_KEY_not_set",
            "detail": "没有环境凭据，拒绝发起网络请求；请先用环境变量配置百度/千帆 OCR 凭据",
        }
    token_url = os.environ.get(BAIDU_OCR_TOKEN_URL_ENV, "").strip() or BAIDU_OCR_DEFAULT_TOKEN_URL
    req = _build_token_request(
        os.environ[BAIDU_OCR_API_KEY_ENV].strip(),
        os.environ[BAIDU_OCR_SECRET_KEY_ENV].strip(),
        token_url,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"status": "failed", "provider": PROVIDER_BAIDU, "reason": "token_http_error", "http_code": exc.code, "error": exc.read().decode("utf-8", "replace")[:300]}
    except Exception as exc:
        return {"status": "failed", "provider": PROVIDER_BAIDU, "reason": "token_request_error", "error": str(exc)[:300]}
    token = data.get("access_token")
    if not token:
        return {"status": "failed", "provider": PROVIDER_BAIDU, "reason": "token_missing_in_response", "error": json.dumps(data, ensure_ascii=False)[:300]}
    return {"status": "passed", "provider": PROVIDER_BAIDU, "access_token": token}


def run_baidu_ocr(source: str | Path, output_dir: str | Path | None = None, *, timeout_s: int = 60) -> dict[str, Any]:
    """百度/千帆 OCR 单图识别入口。无环境凭据时返回 not_run，绝不静默回退到旧脚本或模拟结果。"""
    image = Path(source)
    if not image.is_file():
        return {"status": "failed", "provider": PROVIDER_BAIDU, "reason": "missing_image", "path": str(image)}
    creds = baidu_ocr_credentials_status()
    if not creds["configured"]:
        return {
            "status": "not_run",
            "provider": PROVIDER_BAIDU,
            "path": str(image),
            "reason": "BAIDU_OCR_API_KEY/BAIDU_OCR_SECRET_KEY_not_set",
            "detail": "没有环境凭据，拒绝发起网络请求；代码与测试均不得伪造 live pass",
        }
    image_base64 = base64.b64encode(image.read_bytes()).decode("ascii")
    if len(image_base64) > BAIDU_OCR_BASE64_LIMIT:
        return {"status": "failed", "provider": PROVIDER_BAIDU, "path": str(image), "reason": "image_base64_too_large", "limit_bytes": BAIDU_OCR_BASE64_LIMIT}
    token_result = baidu_ocr_fetch_token(timeout_s=timeout_s)
    if token_result["status"] != "passed":
        return {**token_result, "path": str(image), "detail": "token 获取失败，未发起 OCR 请求"}
    endpoint = os.environ.get(BAIDU_OCR_ENDPOINT_ENV, "").strip() or BAIDU_OCR_DEFAULT_ENDPOINT
    req = _build_ocr_request(token_result["access_token"], image_base64, endpoint)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"status": "failed", "provider": PROVIDER_BAIDU, "path": str(image), "reason": "ocr_http_error", "http_code": exc.code, "error": exc.read().decode("utf-8", "replace")[:300]}
    except Exception as exc:
        return {"status": "failed", "provider": PROVIDER_BAIDU, "path": str(image), "reason": "ocr_request_error", "error": str(exc)[:300]}
    if isinstance(data, dict) and data.get("error_code"):
        return {"status": "failed", "provider": PROVIDER_BAIDU, "path": str(image), "reason": "ocr_api_error", "error_code": data.get("error_code"), "error_msg": str(data.get("error_msg"))[:200]}
    words = [item.get("words", "") for item in data.get("words_result", []) if isinstance(item, dict) and item.get("words")]
    nl = chr(10)
    text = nl.join(words)
    result: dict[str, Any] = {
        "status": "passed",
        "provider": PROVIDER_BAIDU,
        "path": str(image),
        "words_count": len(words),
        "text": text,
    }
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        stem = image.stem
        (out / f"{stem}_baidu_ocr.txt").write_text(text + nl, encoding="utf-8")
        metadata = {k: v for k, v in result.items() if k != "text"}
        (out / f"{stem}_baidu_ocr.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + nl, encoding="utf-8")
        result["output_dir"] = str(out)
    return result


def _qianfan_text(data: dict[str, Any]) -> str:
    choices = data.get("choices") if isinstance(data, dict) else None
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()
    return ""


def run_qianfan_vision(source: str | Path, output_dir: str | Path | None = None,
                       *, prompt: str | None = None, timeout_s: int = 60) -> dict[str, Any]:
    """Call Qianfan's OpenAI-compatible visual-understanding API for OCR.

    Qianfan supports image_url content with either a public URL or a base64 data
    URL.  The project uses the latter so local workbook pages never need to be
    uploaded to a separate file host.  No key means ``not_run`` and no request.
    """
    image = Path(source)
    if not image.is_file():
        return {"status": "failed", "provider": PROVIDER_QIANFAN, "reason": "missing_image", "path": str(image)}
    api_key, key_source = _qianfan_key()
    if not api_key:
        return {
            "status": "not_run",
            "provider": PROVIDER_QIANFAN,
            "path": str(image),
            "reason": "QIANFAN_API_KEY_not_set",
            "detail": "没有千帆 API key，拒绝发起网络请求；不把百度标准或历史 Paddle 回放冒充千帆 live",
        }
    raw = image.read_bytes()
    if len(raw) > QIANFAN_IMAGE_LIMIT:
        return {"status": "failed", "provider": PROVIDER_QIANFAN, "path": str(image), "reason": "image_too_large", "limit_bytes": QIANFAN_IMAGE_LIMIT}
    encoded = base64.b64encode(raw).decode("ascii")
    suffix = image.suffix.lower().lstrip(".") or "jpeg"
    media = "jpg" if suffix == "jpg" else suffix
    body = {
        "model": os.environ.get(QIANFAN_MODEL_ENV, "").strip() or QIANFAN_DEFAULT_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/{media};base64,{encoded}"}},
                {"type": "text", "text": prompt or "请用中文提取图片中的题号、文字、公式和图形关系；只输出结构化 OCR/视觉描述，不输出原题最终答案。"},
            ],
        }],
    }
    req = urllib.request.Request(
        os.environ.get(QIANFAN_ENDPOINT_ENV, "").strip() or QIANFAN_DEFAULT_ENDPOINT,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"status": "failed", "provider": PROVIDER_QIANFAN, "path": str(image), "reason": "qianfan_http_error", "http_code": exc.code, "error": exc.read().decode("utf-8", "replace")[:300]}
    except Exception as exc:
        return {"status": "failed", "provider": PROVIDER_QIANFAN, "path": str(image), "reason": "qianfan_request_error", "error": str(exc)[:300]}
    text = _qianfan_text(data)
    if not text:
        return {"status": "failed", "provider": PROVIDER_QIANFAN, "path": str(image), "reason": "empty_qianfan_content"}
    result: dict[str, Any] = {
        "status": "passed",
        "provider": PROVIDER_QIANFAN,
        "path": str(image),
        "model": body["model"],
        "key_source": key_source,
        "text_length": len(text),
        "text": text,
    }
    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        stem = image.stem
        (out / f"{stem}_qianfan_vision.txt").write_text(text + "\n", encoding="utf-8")
        metadata = {key: value for key, value in result.items() if key != "text"}
        (out / f"{stem}_qianfan_vision.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["output_dir"] = str(out)
    return result


def _selected_provider() -> str:
    """The learning system accepts only its configured PaddleOCR AI Studio API."""
    return PROVIDER_PADDLE


def ocr_config_status() -> dict[str, Any]:
    """只检查配置来源，不显示密钥。"""
    legacy_env = bool(os.environ.get("PADDLE_OCR_TOKEN"))
    source = "environment" if legacy_env else "environment_required"
    historical_docs = []
    historical_root = Path(r"C:\开发\小工具\一本通DeepSeek迭代\worker-01-content\ocr")
    if historical_root.exists():
        historical_docs = sorted(historical_root.glob("doc_*.md"))
    baidu = baidu_ocr_credentials_status()
    qianfan = qianfan_credentials_status()
    provider = _selected_provider()
    selected_ready = legacy_env
    project_root = Path(__file__).resolve().parents[1]
    project_live_evidence = project_root / "data" / "ocr_live_evidence.json"
    current_live_evidence_path = project_root / "data" / "ocr_live_current_evidence.json"
    qianfan_live_evidence_path = Path(__file__).resolve().parents[1] / "data" / "qianfan_live_evidence.json"
    historical_live_probe: dict[str, Any] = {}
    if project_live_evidence.exists():
        try:
            candidate = json.loads(project_live_evidence.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                historical_live_probe = candidate
        except json.JSONDecodeError:
            historical_live_probe = {"status": "failed", "reason": "malformed_live_evidence"}
    current_live_probe: dict[str, Any] = {}
    if current_live_evidence_path.exists():
        try:
            candidate = json.loads(current_live_evidence_path.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                current_live_probe = candidate
        except json.JSONDecodeError:
            current_live_probe = {"status": "failed", "reason": "malformed_current_live_evidence"}
    current_api_live = (
        current_live_probe.get("status") == "passed"
        and current_live_probe.get("provider") == "PaddleOCR AI Studio"
        and current_live_probe.get("fresh_api_run") is True
        and current_live_probe.get("document_count") == current_live_probe.get("expected_document_count")
        and Path(current_live_probe.get("output_root", "")).is_dir()
    )
    historical_api_live = historical_live_probe.get("status") == "passed" and historical_live_probe.get("exact_match_with_historical") is True
    configured_api_live = current_api_live or historical_api_live
    live_probe = current_live_probe if current_api_live else historical_live_probe
    qianfan_live: dict[str, Any] = {}
    if qianfan_live_evidence_path.exists():
        try:
            candidate = json.loads(qianfan_live_evidence_path.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                qianfan_live = candidate
        except json.JSONDecodeError:
            qianfan_live = {"status": "failed", "reason": "malformed_qianfan_live_evidence"}
    qianfan_verified = qianfan_live.get("status") == "passed" and qianfan_live.get("provider") == PROVIDER_QIANFAN
    # The project conversation's configured OCR API is the historical
    # PaddleOCR AI Studio client.  Keep the standard Baidu AK/SK adapter
    # separately observable, but let the verified configured API serve the
    # packet build/replay gate without relabelling it as Baidu standard OCR.
    active_provider = PROVIDER_PADDLE
    return {
        "script": str(OCR_SCRIPT),
        "provider": "PaddleOCR AI Studio (project configured API)",
        "selected_provider": provider,
        "active_provider": active_provider,
        "active_provider_live_verified": configured_api_live,
        "baidu_qianfan_verified": qianfan_verified,
        "qianfan_verified": qianfan_verified,
        "exists": OCR_SCRIPT.exists(),
        "token_source": source,
        "safe_for_new_run": selected_ready and OCR_SCRIPT.exists(),
        "status": "ready" if configured_api_live or (selected_ready and OCR_SCRIPT.exists()) else "not_run",
        "baidu_qianfan": {
            **baidu,
            "status": "ready" if baidu["configured"] else "not_run",
            "note": "兼容旧字段名；此对象实际是百度标准 OCR AK/SK 适配器，不是千帆视觉接口",
        },
        "baidu_standard": {
            **baidu,
            "status": "ready" if baidu["configured"] else "not_run",
        },
        "qianfan": {
            **qianfan,
            "status": "ready" if qianfan["configured"] else "not_run",
            "live_verified": qianfan_verified,
            "live_evidence_path": str(qianfan_live_evidence_path),
            "note": "千帆视觉理解 API；无 key 或无本次 live 证据时保持 not_run",
        },
        "historical_corpus": {
            "root": str(historical_root),
            "doc_count": len(historical_docs),
            "status": "available" if historical_docs else "missing",
            "fresh_api_run": "passed" if current_api_live else ("not_run" if not legacy_env else "ready"),
            "live_replay_verified": historical_api_live,
        },
        "live_probe": {
            "status": live_probe.get("status", "not_run"),
            "provider": live_probe.get("provider"),
            "job_id": live_probe.get("job_id"),
            "document_count": live_probe.get("document_count"),
            "source_pdf_sha256": live_probe.get("source_pdf_sha256"),
            "output_root": live_probe.get("output_root"),
            "exact_match_with_historical": live_probe.get("exact_match_with_historical"),
            "fresh_api_run": current_api_live,
            "current_live": current_api_live,
            "evidence_path": str(current_live_evidence_path if current_api_live else project_live_evidence),
            "note": "这是本次 PaddleOCR AI Studio API live 探针；历史回放仅作为独立对照，不等同于百度标准 OCR AK/SK。" if current_api_live else "这是历史 PaddleOCR AI Studio 客户端的真实探针；不等同于百度标准 OCR AK/SK live_verified。",
        },
        "qianfan_live_probe": {
            "status": qianfan_live.get("status", "not_run"),
            "provider": qianfan_live.get("provider"),
            "model": qianfan_live.get("model"),
            "text_length": qianfan_live.get("text_length"),
            "image_sha256": qianfan_live.get("image_sha256"),
            "evidence_path": str(qianfan_live_evidence_path),
        },
    }


def run_ocr(source: str | Path, output_dir: str | Path, *, timeout_s: int = 900) -> dict[str, Any]:
    """历史 PaddleOCR 本地脚本路径（保留原契约，仅供对比，不再作为百度/千帆入口）。"""
    if not OCR_SCRIPT.exists():
        return {"status": "failed", "reason": "missing_ocr_script"}
    if not os.environ.get("PADDLE_OCR_TOKEN"):
        return {"status": "blocked", "reason": "PADDLE_OCR_TOKEN_not_set", "detail": "拒绝使用脚本内置凭据；请先把凭据放入环境变量"}
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([sys.executable, str(OCR_SCRIPT), str(source), "--out", str(output_dir)], capture_output=True, text=True, timeout=timeout_s, check=False)
    return {"status": "passed" if proc.returncode == 0 else "failed", "returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:], "output_dir": str(output_dir)}
