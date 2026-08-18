#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双 OCR 逐页交替核验驱动：PaddleOCR 文本（doc_*.md 已有输出）与 GLM-4.6V-Flash
（deepseek-eyes describe.py）逐页采集/合并，产出可审计的逐页记录。

用途：第 1 章 69 页及后续各章页面，保证每一页都有双源证据、不跳页、不漏题。
用法示例：
  python -B scripts/verify_pages_dual_ocr.py --name ch1 --glm
  python -B scripts/verify_pages_dual_ocr.py --name ch1 --glm --start 40 --limit 10
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAGES_DIR = ROOT / "data" / "ocr_live_current" / "first_chapter_69"
DEFAULT_DESCRIBE = Path(r"C:\Users\poyi\.agents\skills\deepseek-eyes\scripts\describe.py")
DEFAULT_PROMPT = (
    "这是高中数学《一本通》教材页。请逐字转写页面上全部中文文字、数学公式、题号"
    "（如例1、变式1、A组/B组/C组题号），并说明版面结构（左栏知识点/右栏例题/类型题/习题区）。"
    "不要概括，尽量完整。"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_question_refs(text: str) -> list[str]:
    """从页面文本中提取题号引用（例X、变式X、A组/B组/C组 题号、类型Ⅰ/Ⅱ/Ⅲ）。"""
    refs: list[str] = []
    for m in re.finditer(r"(例\s*\d+)|(变式\s*\d*)|([ABC]组\s*[-—~]?\s*\d+)|(类型\s*[ⅠⅡⅢIV1-3])", text):
        refs.append(m.group(0).replace(" ", ""))
    return refs


def run_glm(describe: Path, image: Path, prompt: str, timeout_s: int = 120) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, str(describe), str(image), "--prompt", prompt],
            capture_output=True, text=True, timeout=timeout_s, encoding="utf-8", errors="replace",
        )
        out = (proc.stdout or "").strip()
        if proc.returncode != 0:
            return {"status": "error", "text": "", "error": (proc.stderr or out)[:500]}
        if not out:
            return {"status": "empty", "text": "", "error": "empty output"}
        return {"status": "ok", "text": out, "error": None}
    except subprocess.TimeoutExpired:
        return {"status": "error", "text": "", "error": "timeout"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "text": "", "error": str(exc)[:500]}


def discover_pages(pages_dir: Path) -> list[int]:
    indexes: list[int] = []
    for img in pages_dir.glob("layout_det_res_*.jpg"):
        m = re.match(r"layout_det_res_(\d+)\.jpg$", img.name)
        if m:
            indexes.append(int(m.group(1)))
    return sorted(set(indexes))


def main() -> int:
    ap = argparse.ArgumentParser(description="双 OCR 逐页交替核验")
    ap.add_argument("--pages-dir", type=Path, default=DEFAULT_PAGES_DIR)
    ap.add_argument("--name", default="ch1")
    ap.add_argument("--out", type=Path, default=None,
                    help="输出 JSON（默认 data/ocr_verify/<name>/pages.json）")
    ap.add_argument("--glm", action="store_true", help="调用 GLM describe.py 采集第二源")
    ap.add_argument("--describe", type=Path, default=DEFAULT_DESCRIBE)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=3.0, help="GLM 逐页间隔秒数")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--no-resume", action="store_true", help="不跳过输出中已存在的页")
    args = ap.parse_args()

    pages_dir = args.pages_dir
    if not pages_dir.is_dir():
        print(f"pages dir not found: {pages_dir}")
        return 2
    indexes = discover_pages(pages_dir)
    if args.start:
        indexes = [i for i in indexes if i >= args.start]
    if args.limit:
        indexes = indexes[: args.limit]
    if not indexes:
        print("no pages discovered")
        return 2

    out_path = args.out or (ROOT / "data" / "ocr_verify" / args.name / "pages.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    if out_path.exists() and not args.no_resume:
        try:
            records = json.loads(out_path.read_text(encoding="utf-8")).get("pages", [])
        except Exception:  # noqa: BLE001
            records = []
    existing = {r.get("page_index") for r in records}

    for idx in indexes:
        if idx in existing and not args.no_resume:
            print(f"page {idx}: resume (skip)")
            continue
        image = pages_dir / f"layout_det_res_{idx}.jpg"
        doc = pages_dir / f"doc_{idx}.md"
        rec: dict = {
            "page_index": idx,
            "image": str(image),
            "image_sha256": sha256(image) if image.is_file() else None,
            "doc_file": str(doc),
            "paddle_char_count": 0,
            "paddle_has_text": False,
            "paddle_question_refs": [],
            "glm_status": "not_run",
            "glm_text": "",
            "glm_error": None,
        }
        if doc.is_file():
            try:
                text = doc.read_text(encoding="utf-8", errors="replace")
                rec["paddle_char_count"] = len(text.strip())
                rec["paddle_has_text"] = bool(text.strip())
                rec["paddle_question_refs"] = extract_question_refs(text)
            except Exception as exc:  # noqa: BLE001
                rec["paddle_error"] = str(exc)[:300]
        if args.glm:
            glm = run_glm(args.describe, image, args.prompt, timeout_s=args.timeout)
            rec["glm_status"] = glm["status"]
            rec["glm_text"] = glm["text"]
            rec["glm_error"] = glm["error"]
            time.sleep(args.sleep)
        records = [r for r in records if r.get("page_index") != idx] + [rec]
        out_path.write_text(
            json.dumps({"name": args.name, "pages": records}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        print(f"page {idx}: paddle_chars={rec['paddle_char_count']} glm={rec['glm_status']}")

    total = len(records)
    empty = [r["page_index"] for r in records if not r.get("paddle_has_text")]
    glm_ok = [r["page_index"] for r in records if r.get("glm_status") == "ok"]
    summary = {
        "name": args.name,
        "total_pages": total,
        "paddle_empty_pages": empty,
        "glm_ok_pages": len(glm_ok),
        "glm_error_pages": [r["page_index"] for r in records if r.get("glm_status") not in ("ok", "not_run")],
    }
    out_path.write_text(
        json.dumps({"name": args.name, "summary": summary, "pages": records}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
