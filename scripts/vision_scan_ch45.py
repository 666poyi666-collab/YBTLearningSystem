# -*- coding: utf-8 -*-
"""
第4/5章无答案册逐页视觉题号盘点（worker build-ch4-5 产物）。

流程：fitz 渲染 data/ocr_sources/ 下合并无答案 PDF 每页 -> describe.py (GLM-4.6V-Flash)
识别章节标题/题号（例、变式、A/B/C 组、练习）/是否出现答案。
输出：data/ocr_sources/vision_notes/<chapter>/page_<n>.json（可断点续跑）。

用法（python -B）：
    python scripts/vision_scan_ch45.py 4       # 扫第4章 100 页
    python scripts/vision_scan_ch45.py 4 5     # 扫第4、5章
    python scripts/vision_scan_ch45.py 4 --resume
    python scripts/vision_scan_ch45.py --status
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OCR_SOURCES = ROOT / "data" / "ocr_sources"
NOTES = OCR_SOURCES / "vision_notes"
DESCRIBE = Path.home() / ".agents" / "skills" / "deepseek-eyes" / "scripts" / "describe.py"
DPI = 110

PDFS = {
    "4": OCR_SOURCES / "第4章 数列（无答案册）.pdf",
    "5": OCR_SOURCES / "第5章 一元函数的导数及其应用（无答案册）.pdf",
}

PROMPT = (
    "这是一本高中数学教辅《一本通》的扫描页（无答案册，方法册+习题册部分）。"
    "请用中文回答：1)本页所属章节（读页眉/标题，如'第1节 数列的概念'）；"
    "2)本页类型：知识讲解/例题/变式/类型题/A组习题/B组习题/C组习题/其他；"
    "3)本页出现的全部题号逐一列出（如例1、例2、变式1、A1、B3、C5、练习1等），注意题干或页眉中的编号；"
    "4)是否出现'答案'字样或解答过程（无答案册不应有答案页）；"
    "5)若页面顶部有页码请给出。只描述事实，不要猜测，看不清楚就写'无法辨认'。"
)


def render_page(pdf: Path, index: int, out_dir: Path) -> Path:
    import fitz
    out = out_dir / f"page_{index:03d}.png"
    if not out.exists():
        doc = fitz.open(str(pdf))
        pix = doc[index].get_pixmap(dpi=DPI)
        pix.save(str(out))
        doc.close()
    return out


def describe(image: Path, note_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(DESCRIBE), str(image), "--prompt", PROMPT],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
    )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    ok = "错误:" not in stdout and "错误:" not in stderr and proc.returncode == 0
    note = {
        "page": image.stem,
        "status": "passed" if ok else "failed",
        "text": stdout if ok else "",
        "error": "" if ok else (stderr or stdout)[:400],
    }
    note_path.write_text(json.dumps(note, ensure_ascii=False, indent=2), encoding="utf-8")
    return note


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chapters", nargs="*", default=["4", "5"], help="要扫描的章：4 / 5")
    ap.add_argument("--resume", action="store_true", help="跳过已有成功笔记")
    ap.add_argument("--status", action="store_true", help="只输出完成/缺口")
    args = ap.parse_args()

    for ch in args.chapters:
        pdf = PDFS[ch]
        import fitz
        doc = fitz.open(str(pdf))
        n_pages = len(doc)
        doc.close()
        out_dir = NOTES / f"chapter{ch}"
        out_dir.mkdir(parents=True, exist_ok=True)

        if args.status:
            done = sum(1 for p in out_dir.glob("page_*.json") if json.loads(p.read_text(encoding="utf-8")).get("status") == "passed")
            print(f"chapter{ch}: {done}/{n_pages} passed")
            continue

        failed = 0
        for i in range(n_pages):
            note_path = out_dir / f"page_{i:03d}.json"
            if args.resume and note_path.exists():
                try:
                    if json.loads(note_path.read_text(encoding="utf-8")).get("status") == "passed":
                        print(f"[skip] page {i:03d}", flush=True)
                        continue
                except Exception:
                    pass
            image = render_page(pdf, i, out_dir)
            note = describe(image, note_path)
            if note["status"] == "passed":
                print(f"[ok]   page {i:03d}: {note['text'][:80]}", flush=True)
            else:
                failed += 1
                print(f"[fail] page {i:03d}: {note['error'][:120]}", flush=True)
                # 限流时放慢，避免打爆配额
                import time
                time.sleep(30)
        print(f"chapter{ch}: done, failed={failed}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
