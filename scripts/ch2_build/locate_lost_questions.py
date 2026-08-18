# -*- coding: utf-8 -*-
"""定位 OCR 丢失题号的题面（供 known_visual_recoveries 锚点）。"""
import re
from pathlib import Path

ROOT = Path(r"C:\开发\小工具\一本通学习系统_v7\data\ocr_live_current\second_chapter_109")
SEC_DOCS = {"2.1": (0, 12), "2.2": (13, 25), "2.3": (26, 43), "2.4": (44, 55), "2.5": (56, 70), "2.6": (71, 92), "2.7": (93, 108)}
MISSING = {"2.1": [9, 11], "2.2": [7], "2.3": [21], "2.4": [5], "2.5": [12], "2.6": [8]}
NUM = re.compile(r"^#{0,6}\s*(\d+)\s*\\?[.、．]\s*")

for sec, nums in MISSING.items():
    lo, hi = SEC_DOCS[sec]
    texts = {i: (ROOT / f"doc_{i}.md").read_text(encoding="utf-8") for i in range(lo, hi + 1)}
    for num in nums:
        prev, nxt = num - 1, num + 1
        found = False
        for i in range(lo, hi + 1):
            seg = ""
            for j in range(i, min(i + 3, hi + 1)):
                seg = seg + "\n" + texts[j]
                m_nxt = NUM.search(seg)
                # 找最后一个出现 prev 的位置与第一个出现 nxt 的位置
                prev_matches = list(NUM.finditer(seg))
                prev_pos = None
                for pm in prev_matches:
                    if int(pm.group(1)) == prev:
                        prev_pos = pm
                if prev_pos is None:
                    continue
                nxt_m = NUM.search(seg, prev_pos.end())
                if nxt_m and int(nxt_m.group(1)) == nxt:
                    body = seg[prev_pos.end():nxt_m.start()]
                    print(f"--- {sec} Q{num} missing; docs {i}..{j}")
                    print(body.strip()[:260].replace("\n", " | "))
                    print()
                    found = True
                    break
            if found:
                break
        if not found:
            print(f"--- {sec} Q{num} NOT LOCATED")
