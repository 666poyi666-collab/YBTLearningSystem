# -*- coding: utf-8 -*-
"""重建 data/packets/2.x/README.md（修复内联 bash 转义导致的命令行丢失）。"""
import json
from pathlib import Path

BASE = Path(r"C:\开发\小工具\一本通学习系统_v7\data\packets")
SECTIONS = [
    ("2.1", "第1节 直线的倾斜角与斜率", [1, 13]),
    ("2.2", "第2节 直线的方程", [14, 26]),
    ("2.3", "第3节 直线的交点坐标与距离公式", [27, 44]),
    ("2.4", "第4节 微专题2：直线有关的对称问题", [45, 56]),
    ("2.5", "第5节 圆的方程", [57, 71]),
    ("2.6", "第6节 直线与圆的位置关系", [72, 93]),
    ("2.7", "第7节 圆与圆的位置关系", [94, 109]),
]
PDF = r"C:\Users\poyi\Downloads\【2025-2025版】选择性必修第1册\按章节合并（无答案册）\第2章 直线和圆的方程（无答案册）.pdf"
OCR_SCRIPT = r"C:\开发\ocr本地\paddleocr_ai_studio.py"
OUT_ROOT = r"C:\开发\小工具\一本通学习系统_v7\data\ocr_live_current\second_chapter_109"

for sid, label, pages in SECTIONS:
    readme = (
        "# 第 2 章题包骨架：{sid} {label}\n\n"
        "状态：PENDING_OCR（骨架占位，**不含任何题目内容**）。\n\n"
        "- 页范围：PDF 第 {lo}–{hi} 页（来自第 2 章无答案册书签目录，已确认）。\n"
        "- 缺题门禁：题号/例题/变式/A-B-C 分组均未确认 → 全部页 needs_manual。\n"
        "- 阻断原因：本构建会话无 PADDLE_OCR_TOKEN；教材为扫描件（无文本层）。\n"
        "- 后续动作（主控）：配置 token 后运行\n\n"
        "  ```\n"
        "  python \"{ocr}\" \"{pdf}\" --out \"{out}\"\n"
        "  ```\n\n"
        "  再按 1.1 流程生成 packet/learning_packet/student_packet/answer_sidecar 并 verify-packet。\n"
        "- 纪律：不得用答案册（习题册+答案册 PDF）填充本题包；OCR 完成前不得标注 VERIFIED。\n"
    ).format(sid=sid, label=label, lo=pages[0], hi=pages[1], ocr=OCR_SCRIPT, pdf=PDF, out=OUT_ROOT)
    (BASE / sid / "README.md").write_text(readme, encoding="utf-8")
    manifest = json.loads((BASE / sid / "manifest.json").read_text(encoding="utf-8"))
    print(sid, "OK", manifest["status"])
print("READMEs rebuilt")
