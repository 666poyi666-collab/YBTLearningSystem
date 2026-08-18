#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并第 1 章 GLM 逐页转写的三部分 → 最终 data/ocr_verify/ch1_glm_pages.json（69 页全覆盖）。

来源：
1. w2 worker 的 data/ocr_verify/ch1_glm_pages.json.tmp（页 0-52，含 5 个 error）
2. 主控补跑 data/ocr_verify/ch1/pages.json（页 53-68）
3. error 页重试结果（可选，--retry-file）

合并规则：每页取"ok"优先；无 ok 时保留最新尝试（含 error/not_run）；最终必须 69 页全部出现。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--w2-tmp", default=str(ROOT / "data/ocr_verify/ch1_glm_pages.json.tmp"))
    ap.add_argument("--backfill", default=str(ROOT / "data/ocr_verify/ch1/pages.json"))
    ap.add_argument("--retry-file", default=None)
    ap.add_argument("--out", default=str(ROOT / "data/ocr_verify/ch1_glm_pages.json"))
    args = ap.parse_args()

    by_page: dict[int, dict] = {}

    def absorb(path: Path) -> None:
        if not path.is_file():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        for p in data.get("pages", []):
            idx = int(p.get("page_index"))
            cur = by_page.get(idx)
            if cur is None:
                by_page[idx] = p
            elif p.get("status") == "ok" and cur.get("status") != "ok":
                by_page[idx] = p

    absorb(Path(args.w2_tmp))
    absorb(Path(args.backfill))
    if args.retry_file:
        absorb(Path(args.retry_file))

    pages = [by_page[i] for i in sorted(by_page) if i in by_page]
    missing = [i for i in range(69) if i not in by_page]
    ok = sum(1 for p in pages if p.get("status") == "ok")
    out = {
        "name": "ch1_glm_pages",
        "summary": {
            "total_pages": len(pages),
            "ok_pages": ok,
            "error_pages": [p.get("page_index") for p in pages if p.get("status") != "ok"],
            "missing_pages": missing,
        },
        "pages": pages,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["summary"], ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
