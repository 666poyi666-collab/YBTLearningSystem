# -*- coding: utf-8 -*-
"""
ocr-glm-ch1 worker: 用 GLM-4.6V-Flash(免费) 逐页转写第 1 章 69 张页图,
作为与 PaddleOCR 交替核验的第二源。

产物: data/ocr_verify/ch1_glm_pages.json (UTF-8)
规则:
  - 串行, 页间 sleep 2-5s
  - 单页失败(error/empty)重试 1 次
  - HTTP 400 内容过滤 -> blocked, 不重试
  - 额度耗尽(402/quota/insufficient/额度等) -> 停止, 剩余页如实标记 not_run
  - 每页成功后写 .tmp 增量, 中断可自动续跑
"""
import hashlib
import json
import os
import random
import subprocess
import sys
import time

# 本脚本位于 <项目根>/data/ocr_verify/ 下, 向上 3 层即项目根
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMG_DIR = os.path.join(ROOT, "data", "ocr_live_current", "first_chapter_69")
OUT_DIR = os.path.join(ROOT, "data", "ocr_verify")
OUT_JSON = os.path.join(OUT_DIR, "ch1_glm_pages.json")
TMP_JSON = OUT_JSON + ".tmp"
DESCRIBE = r"C:\Users\poyi\.agents\skills\deepseek-eyes\scripts\describe.py"
PROMPT = ("这是高中数学《一本通》教材页。请逐字转写页面上全部中文文字、数学公式、"
          "题号（如例1、变式1、A组/B组/C组题号），并说明版面结构"
          "（左栏知识点/右栏例题/类型题/习题区）。不要概括，尽量完整。")
TOTAL = 69
QUOTA_MARKERS = ("402", "insufficient", "quota", "balance", "额度", "资源包")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_error(err):
    low = err.lower()
    if "http 400" in low:
        return "blocked"
    if any(m in low or m in err for m in QUOTA_MARKERS):
        return "quota"
    return "error"


def run_one(image_path):
    """调用 describe.py 一次, 返回 (status, text, error)。
    status: ok / empty / error / blocked / quota"""
    try:
        p = subprocess.run(
            [sys.executable, "-B", DESCRIBE, image_path,
             "--prompt", PROMPT, "--max-tokens", "4096"],
            capture_output=True, timeout=300, text=True,
            encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return "error", "", "timeout 300s"
    except Exception as e:
        return "error", "", "subprocess failed: %r" % e
    err = (p.stderr or "").strip()
    if p.returncode != 0:
        status = classify_error(err)
        return status, "", (err[:500] or "exit %d" % p.returncode)
    text = (p.stdout or "").strip()
    if not text:
        return "empty", "", (err[:500] if err else "empty stdout")
    return "ok", text, ""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    pages = []
    # 增量续跑: 加载已有 .tmp
    if os.path.exists(TMP_JSON):
        try:
            with open(TMP_JSON, encoding="utf-8") as f:
                prev = json.load(f)
            pages = prev.get("pages", [])
            print("[resume] loaded %d pages from tmp" % len(pages), flush=True)
        except Exception as e:
            print("[resume] tmp load failed, start fresh: %r" % e, flush=True)
            pages = []

    quota_hit = any("quota" in (p.get("error") or "").lower()
                    and p.get("status") == "not_run" for p in pages)
    start = time.time()

    for i in range(len(pages), TOTAL):
        img = "layout_det_res_%d.jpg" % i
        path = os.path.join(IMG_DIR, img)
        try:
            sha = sha256_file(path)
        except OSError as e:
            sha = ""
            pages.append({"page_index": i, "image": img, "sha256": "",
                          "status": "error", "text": "",
                          "error": "image unreadable: %r" % e})
            print("[%d/%d] page %d: error(image unreadable)" % (i + 1, TOTAL, i), flush=True)
            continue

        if quota_hit:
            pages.append({"page_index": i, "image": img, "sha256": sha,
                          "status": "not_run", "text": "",
                          "error": "quota exhausted - not run"})
            continue

        status, text, err = run_one(path)
        if status in ("error", "empty"):
            time.sleep(random.uniform(3, 8))
            status, text, err = run_one(path)  # 重试 1 次
            if status in ("error", "empty") and err:
                err = "retry-failed: " + err

        pages.append({"page_index": i, "image": img, "sha256": sha,
                      "status": status, "text": text, "error": err})
        print("[%d/%d] page %d: %s text=%d chars err=%s elapsed=%.0fs"
              % (i + 1, TOTAL, i, status, len(text),
                 (err[:100] if err else "-"), time.time() - start), flush=True)

        if status == "quota":
            quota_hit = True
        else:
            # 增量落盘
            with open(TMP_JSON, "w", encoding="utf-8") as f:
                json.dump({"pages": pages}, f, ensure_ascii=False, indent=1)
            if i < TOTAL - 1:
                time.sleep(random.uniform(2, 5))

    counts = {}
    for s in ("ok", "empty", "error", "blocked", "not_run"):
        counts[s] = sum(1 for p in pages if p["status"] == s)
    remaining = [p["page_index"] for p in pages if p["status"] == "not_run"]
    failed = [p["page_index"] for p in pages if p["status"] in ("error", "blocked")]
    data = {
        "source": "glm-4.6v-flash via deepseek-eyes describe.py",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "chapter": "第1章",
        "total_pages": TOTAL,
        "summary": {
            "status_counts": counts,
            "remaining_pages": remaining,
            "failed_pages": failed,
        },
        "pages": pages,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    if os.path.exists(TMP_JSON):
        os.remove(TMP_JSON)
    print("DONE. counts=%s remaining=%s failed=%s"
          % (counts, remaining, failed), flush=True)


if __name__ == "__main__":
    main()
