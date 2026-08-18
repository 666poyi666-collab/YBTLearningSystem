#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run one Qianfan visual/OCR probe and persist only redacted evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ybt_learning.ocr import QIANFAN_DEFAULT_MODEL, qianfan_credentials_status, run_qianfan_vision


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = ROOT
    parser = argparse.ArgumentParser(description="千帆视觉 OCR 单图 live 探针")
    parser.add_argument("image")
    parser.add_argument("--out", default=str(root / "data" / "qianfan_probe_output"))
    parser.add_argument("--evidence", default=str(root / "data" / "qianfan_live_evidence.json"))
    parser.add_argument("--prompt", default=None)
    args = parser.parse_args()
    image = Path(args.image)
    result = run_qianfan_vision(image, args.out, prompt=args.prompt)
    credential_status = qianfan_credentials_status()
    evidence = {
        "status": result.get("status"),
        "provider": result.get("provider"),
        "model": result.get("model"),
        "configured_model": credential_status.get("model") or QIANFAN_DEFAULT_MODEL,
        "model_status": "returned_by_live_response" if result.get("model") else "configured_default_not_live",
        "credentials_configured": bool(credential_status.get("configured")),
        "image": str(image),
        "image_sha256": sha256(image) if image.is_file() else None,
        "text_length": result.get("text_length"),
        "output_dir": result.get("output_dir"),
        "reason": result.get("reason"),
        "note": "正文仅保存在 output_dir 文本工件；本 evidence 不写 API key 或模型返回正文。",
    }
    evidence_path = Path(args.evidence)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
