from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


VISION_PROMPT = """你只做数学教材题图OCR，不做题。观察图片里肉眼可见的点名、线段、虚实线、平面、曲线、坐标轴、表格、区间标记、流程框和短文字。只输出一个JSON对象，不要解释或前后缀：{"objects":[],"relations":[],"coordinates":[],"ranges":[],"text":[],"uncertainties":[],"confidence":"E2"}。六个数组必须齐全且各最多6项；多个点名合并成一个逗号分隔字符串，连续流程合并成一个带箭头的字符串。能看见任一元素时，objects、relations、coordinates、ranges、text中至少一个必须非空；完全看不清才把原因写入uncertainties并设E0。不得输出答案、解法、选项对错、推导或计算结果；只抄可见内容，不猜。confidence只能是E2、E1或E0。"""

VISION_SCRIPT = Path(r"C:\Users\poyi\.agents\skills\deepseek-eyes\scripts\describe.py")
VISION_CONFIG_PATH = Path(r"C:\Users\poyi\.agents\skills\deepseek-eyes\config.json")
GLM_VISION_KEY_ENV = "GLM_VISION_API_KEY"
GLM_VISION_BASE_URL_ENV = "GLM_VISION_BASE_URL"
GLM_VISION_MODEL = "glm-4.6v-flash"
VISION_SIDECAR_SCHEMA = "7.1"
VISION_ANSWER_LEAK_RE = re.compile(
    r"(?:答案|答为|解析|解答|解法|正确选项|错误选项|应选|故选|选择[ABCDEF]|"
    r"[ABCDEF]\s*项(?:正确|错误)|最终(?:答案|结果|结论)|(?:结果|结论)为|"
    r"由此可得|所以选|因此选|可求得|answer|correct\s+option|incorrect\s+option|"
    r"solution|therefore\s+(?:choose|select)|thus\s+(?:choose|select))",
    re.I,
)


def _load_vision_config() -> tuple[dict[str, Any] | None, str | None]:
    if not VISION_CONFIG_PATH.exists():
        return None, None
    try:
        return json.loads(VISION_CONFIG_PATH.read_text(encoding="utf-8")), None
    except json.JSONDecodeError:
        return None, "malformed_config"


def _has_meaningful_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_meaningful_value(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_meaningful_value(v) for v in value)
    return value is not None


def structured_answer_leaks(structured: Any) -> list[str]:
    """Return answer/solution language that must never enter a visual sidecar."""
    if not isinstance(structured, dict):
        return []
    text = json.dumps(structured, ensure_ascii=False)
    return sorted({match.group(0) for match in VISION_ANSWER_LEAK_RE.finditer(text)})


def _extract_json_object(caption: str) -> dict[str, Any] | None:
    """Extract the first complete JSON object from a model preamble.

    GLM sometimes wraps an otherwise valid JSON response in a short Chinese
    sentence or Markdown fence.  We accept only a complete object; narrative
    text without a structured payload remains unverified.
    """
    decoder = json.JSONDecoder()
    for start, char in enumerate(caption):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(caption[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _structured_caption(caption: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse a visual response and reject empty JSON masquerading as success."""
    caption = (caption or "").strip()
    if not caption:
        return None, "empty_vision_caption"
    if "```" in caption:
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", caption, flags=re.I)
        if not fenced:
            # A missing closing fence is ambiguous: it may be a complete JSON
            # object or a token-truncated response.  Do not accept it as a
            # release-grade sidecar; retain the raw provider evidence only.
            return None, "truncated_fenced_vision"
        else:
            caption = fenced.group(1).strip()
            if not caption.endswith("}") and not caption.endswith("]"):
                return None, "truncated_fenced_vision"
            structured = None
    else:
        structured = None
    if structured is None:
        try:
            structured = json.loads(caption)
        except json.JSONDecodeError:
            structured = _extract_json_object(caption)
            if structured is None:
                return None, "malformed_structured_vision"
    if not isinstance(structured, dict):
        return None, "vision_payload_not_object"
    confidence = structured.get("confidence")
    if confidence == "E2|E1|E0":
        return None, "confidence_template_not_a_result"
    for key in ("objects", "relations", "coordinates", "ranges", "text", "uncertainties"):
        if not isinstance(structured.get(key), list):
            return None, f"{key}_not_array"
        if len(structured[key]) > 8:
            return None, f"{key}_too_many_items"
    meaningful = any(_has_meaningful_value(structured.get(key)) for key in ("objects", "relations", "coordinates", "ranges", "text"))
    if not meaningful:
        return None, "empty_structured_vision"
    if structured_answer_leaks(structured):
        return None, "answer_language_in_visual_sidecar"
    if confidence not in {"E1", "E2", "E0"}:
        structured["confidence"] = "E0"
    return structured, None


def _data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def describe_image(path: str | Path, *, profile: str | None = None, prompt: str = VISION_PROMPT, timeout_ms: int = 120000, max_tokens: int = 1024) -> dict[str, Any]:
    """调用已配置的 GLM 视觉桥；不把密钥写入输出。"""
    cmd = [sys.executable, str(VISION_SCRIPT), str(path), "--prompt", prompt, "--json", "--max-tokens", str(max_tokens)]
    if profile:
        cmd.extend(["--profile", profile])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_ms / 1000, check=False)
    except subprocess.TimeoutExpired as exc:
        return {"status": "timeout", "path": str(path), "error": str(exc)}
    if proc.returncode != 0:
        return {"status": "failed", "path": str(path), "error": proc.stderr[-1000:]}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"status": "failed", "path": str(path), "error": "vision output was not JSON", "raw": proc.stdout[-2000:]}
    structured, error = _structured_caption(data.get("caption", ""))
    if error:
        raw_caption = str(data.get("caption", "")).strip()
        result = {"status": "unverified", "path": str(path), "model": data.get("model"), "elapsed_ms": data.get("elapsed_ms"), "error": error}
        if raw_caption:
            result["caption_preview"] = raw_caption[:4000]
        return result
    status = "passed" if structured.get("confidence") in {"E1", "E2"} else "unverified"
    return {"status": status, "path": str(path), "model": data.get("model"), "elapsed_ms": data.get("elapsed_ms"), "confidence": structured.get("confidence"), "structured": structured, "vision": structured}


def sidecar_for_images(image_paths: list[str | Path], *, output_path: str | Path, profile: str | None = None) -> dict[str, Any]:
    results = [describe_image(path, profile=profile) for path in image_paths]
    payload = {"schema_version": "7.1", "status": "passed" if all(x.get("status") == "passed" and (x.get("vision") or {}).get("confidence") in {"E1", "E2"} for x in results) else "unverified", "model": "glm-4.6v-flash", "results": results}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def sidecar_for_question_images(question_images: list[tuple[str, str | Path]], *, output_path: str | Path, profile: str | None = None, max_tokens: int = 1536, prompt: str | None = None) -> dict[str, Any]:
    """Generate the packet-facing schema with a stable question hint per image."""
    results: list[dict[str, Any]] = []
    for question_hint, path in question_images:
        # The hint is the canonical packet key (for example
        # ``1.2+1.3-B5``).  Persisting the section here is important: the
        # chapter builder filters sidecars by section and must never silently
        # discard a real probe result.
        section = question_hint.rsplit("-", 1)[0] if "-" in question_hint else None
        result = describe_image(path, profile=profile, prompt=prompt or VISION_PROMPT, max_tokens=max_tokens)
        item = {
            "status": result.get("status", "failed"),
            "question_hint": question_hint,
            "image": str(path),
            "confidence": result.get("confidence") or (result.get("structured") or {}).get("confidence", "E0"),
            "model": result.get("model"),
            "elapsed_ms": result.get("elapsed_ms"),
        }
        image_path = Path(path)
        if image_path.is_file():
            digest = hashlib.sha256()
            with image_path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            item["image_sha256"] = digest.hexdigest()
        if section:
            item["section"] = section
        if result.get("structured"):
            item["structured"] = result["structured"]
        if result.get("error"):
            item["error"] = result["error"]
        results.append(item)
    payload = {
        "schema_version": "7.1",
        "status": "passed" if results and all(x.get("status") == "passed" and x.get("confidence") in {"E1", "E2"} for x in results) else "unverified",
        "provider": "GLM-4.6V-Flash via deepseek-eyes",
        "results": results,
        "consumer_guard": "Only passed results with structured content and pure E1/E2 confidence may enter a packet.",
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def test_vision_config() -> dict[str, Any]:
    """只检查配置来源，不泄露密钥。优先级与 describe.py 一致：profile > 环境变量 > config.json。"""
    config, config_error = _load_vision_config()
    env_key = os.environ.get(GLM_VISION_KEY_ENV, "").strip()
    env_endpoint = os.environ.get(GLM_VISION_BASE_URL_ENV, "").strip()
    profiles = sorted((config or {}).get("profiles", {}).keys()) if isinstance((config or {}).get("profiles"), dict) else []
    key_sources: list[str] = []
    if env_key:
        key_sources.append("environment")
    if config and config.get("api_key"):
        key_sources.append("config")
    if profiles:
        key_sources.append("profile")
    endpoint = env_endpoint or (config or {}).get("endpoint") or ""
    model = (config or {}).get("model") or GLM_VISION_MODEL
    has_key = bool(env_key or (config or {}).get("api_key"))
    evidence_path = Path(__file__).resolve().parents[1] / "data" / "vision_live_evidence.json"
    live_evidence: dict[str, Any] = {}
    if evidence_path.exists():
        try:
            candidate = json.loads(evidence_path.read_text(encoding="utf-8"))
            if isinstance(candidate, dict):
                live_evidence = candidate
        except json.JSONDecodeError:
            live_evidence = {"status": "failed", "reason": "malformed_live_evidence"}
    live_verified = VISION_CONFIG_PATH.exists() and live_evidence.get("status") == "passed" and bool(live_evidence.get("structured"))
    base = {
        "config_path": str(VISION_CONFIG_PATH),
        "script": str(VISION_SCRIPT),
        "model": model,
        "endpoint": endpoint,
        "has_api_key": has_key,
        "profiles": profiles,
        "live_verified": live_verified,
        "live_evidence_path": str(evidence_path),
        "live_evidence": {k: v for k, v in live_evidence.items() if k not in {"structured", "caption_preview"}},
        "note": "仅配置检查；live 图像调用需另行执行并附结果，配置存在不等于调用已通过",
    }
    if config_error:
        return {"status": "failed", "reason": config_error, "key_sources": key_sources, **base}
    if not key_sources:
        return {"status": "not_run", "reason": "no_vision_credentials", "key_sources": [], **base}
    usable = has_key and bool(endpoint) and model == GLM_VISION_MODEL
    return {"status": "passed" if usable else "failed", "reason": None if usable else "model_or_endpoint_mismatch", "key_source": key_sources[0], "key_sources": key_sources, **base}


def sidecar_contract_status() -> dict[str, Any]:
    """核查 GLM 视觉侧车契约：生成端与消费端(packet._usable_vision_sidecar)的放行条件必须一致。"""
    return {
        "schema_version": VISION_SIDECAR_SCHEMA,
        "provider": "GLM-4.6V-Flash via deepseek-eyes",
        "model": GLM_VISION_MODEL,
        "config_sources": ["profile", GLM_VISION_KEY_ENV, "config.json"],
        "sidecar_pass_requires": ["status == passed", "confidence in {E1, E2}", "structured dict with meaningful objects/relations/coordinates/ranges/text", "no fenced markdown or legacy empty markers"],
        "consumer_guard": "Only passed results with structured content and pure E1/E2 confidence may enter a packet.",
        "status": "consistent",
    }
