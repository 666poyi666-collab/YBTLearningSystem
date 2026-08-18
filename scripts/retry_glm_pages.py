#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GLM 逐页转写收尾重试器：对缺失/error 页用长退避重试（429 限流场景）。

用法：
  python -B scripts/retry_glm_pages.py --pages 16,28,38,39,49,55 --sleep 45 --attempts 6
输出写到 data/ocr_verify/ch1_retry/pages.json（供 merge_ch1_glm_pages.py --retry-file 消费）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESCRIBE = Path(r"C:\Users\poyi\.agents\skills\deepseek-eyes\scripts\describe.py")
IMG_DIR = ROOT / "data" / "ocr_live_current" / "first_chapter_69"
PROMPT = ("这是高中数学《一本通》教材页。请逐字转写页面上全部中文文字、数学公式、题号"
          "（如例1、变式1、A组/B组/C组题号），并说明版面结构（左栏知识点/右栏例题/类型题/习题区）。"
          "不要概括，尽量完整。")


def attempt(idx: int, timeout_s: int) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, str(DESCRIBE), str(IMG_DIR / f"layout_det_res_{idx}.jpg"), "--prompt", PROMPT],
            capture_output=True, text=True, timeout=timeout_s, encoding="utf-8", errors="replace",
        )
        out = (proc.stdout or "").strip()
        if proc.returncode != 0:
            return {"status": "error", "text": "", "error": (proc.stderr or out)[:300]}
        if not out:
            return {"status": "empty", "text": "", "error": "empty output"}
        return {"status": "ok", "text": out, "error": None}
    except subprocess.TimeoutExpired:
        return {"status": "error", "text": "", "error": "timeout"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "text": "", "error": str(exc)[:300]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="逗号分隔页号")
    ap.add_argument("--sleep", type=float, default=45.0)
    ap.add_argument("--attempts", type=int, default=6)
    ap.add_argument("--out", default=str(ROOT / "data/ocr_verify/ch1_retry/pages.json"))
    args = ap.parse_args()

    pages = [int(x) for x in args.pages.split(",") if x.strip()]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for idx in pages:
        rec: dict = {"page_index": idx, "status": "not_run", "text": "", "error": None}
        for attempt_no in range(1, args.attempts + 1):
            result = attempt(idx, timeout_s=150)
            if result["status"] == "ok":
                rec = {"page_index": idx, "status": "ok", "text": result["text"], "error": None}
                break
            rec = {"page_index": idx, "status": result["status"], "text": "", "error": result["error"]}
            print(f"page {idx} attempt {attempt_no}/{args.attempts}: {result['status']}", flush=True)
            time.sleep(args.sleep)
        records.append(rec)
        out_path.write_text(json.dumps({"pages": records}, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(10)
    ok = sum(1 for r in records if r["status"] == "ok")
    print(json.dumps({"total": len(pages), "ok": ok, "failed": [r["page_index"] for r in records if r["status"] != "ok"]}))
    return 0 if ok == len(pages) else 1


if __name__ == "__main__":
    raise SystemExit(main())
