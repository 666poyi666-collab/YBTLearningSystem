from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stable_id(*parts: object, length: int = 16) -> str:
    raw = "|".join(str(x) for x in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:length]


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: str | Path, value: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    return re.sub(r"[\u0001-\u0008\u000b\u000c\u000e-\u001f]", "", text)


def normalize_math(text: str) -> str:
    # 先处理显示公式，再处理单行公式；不要把两个 $$ 端点都替换成左定界符。
    text = re.sub(r"\$\$([\s\S]*?)\$\$", lambda m: r"\[" + m.group(1).strip() + r"\]", text)
    text = re.sub(r"(?<!\$)\$([^$\n]+)\$(?!\$)", lambda m: r"\(" + m.group(1).strip() + r"\)", text)
    return text


def delimiter_errors(text: str) -> list[str]:
    errors: list[str] = []
    if text.count("$") % 2:
        errors.append("unbalanced_dollar")
    if text.count(r"\(") != text.count(r"\)"):
        errors.append("unbalanced_inline_math")
    if text.count(r"\[") != text.count(r"\]"):
        errors.append("unbalanced_display_math")
    # OCR 可能把分母中的 5 误识别为希腊字母 π；这类结果不能直接进入可学习题包。
    if re.search(r"\\frac\{[34]\}\{\\pi\}", text):
        errors.append("suspicious_fraction_denominator_pi_manual_review")
    return errors
