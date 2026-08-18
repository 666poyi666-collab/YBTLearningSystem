# -*- coding: utf-8 -*-
"""
ocr-glm-ch1 worker: 主批完成后对 error/empty 页的补跑脚本。
读取 data/ocr_verify/ch1_glm_pages.json, 仅重跑 status in (error, empty) 的页
(blocked 为内容过滤, 不重试; not_run 为额度耗尽, 不重试)。
页间 sleep 10-20s (限流退避放宽)。原错误保留在 first_error 字段, 成功页如实标注。
"""
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_glm_ch1 import OUT_JSON, PROMPT, IMG_DIR  # noqa: E402
from run_glm_ch1 import run_one  # noqa: E402

RETRYABLE = ("error", "empty")


def main():
    with open(OUT_JSON, encoding="utf-8") as f:
        data = json.load(f)
    pages = data["pages"]
    targets = [p for p in pages if p["status"] in RETRYABLE]
    if not targets:
        print("no retryable pages; done")
        return
    print("retrying %d pages: %s" % (len(targets),
          [p["page_index"] for p in targets]), flush=True)
    recovered = 0
    for idx, p in enumerate(targets):
        i = p["page_index"]
        img = os.path.join(IMG_DIR, p["image"])
        status, text, err = run_one(img)
        if status in ("error", "empty"):
            # 补跑再失败: 保留原状态, 追加补跑记录
            p["retry_note"] = "batch-retry failed: %s" % (err[:200])
            print("page %d still %s" % (i, status), flush=True)
        else:
            p["first_error"] = p.get("error", "")
            p["error"] = err
            p["text"] = text
            p["status"] = status
            p["retry_note"] = "recovered in batch retry"
            recovered += 1
            print("page %d recovered -> %s (%d chars)" % (i, status, len(text)), flush=True)
        # 增量落盘
        with open(OUT_JSON + ".tmp", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        if idx < len(targets) - 1:
            time.sleep(random.uniform(10, 20))

    counts = {}
    for s in ("ok", "empty", "error", "blocked", "not_run"):
        counts[s] = sum(1 for p in pages if p["status"] == s)
    data["summary"]["status_counts"] = counts
    data["summary"]["retry_pass"] = {
        "attempted": len(targets),
        "recovered": recovered,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.remove(OUT_JSON + ".tmp")
    print("RETRY DONE. counts=%s recovered=%d" % (counts, recovered), flush=True)


if __name__ == "__main__":
    main()
