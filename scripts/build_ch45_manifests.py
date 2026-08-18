# -*- coding: utf-8 -*-
"""
第4/5章 manifest 骨架生成器（worker build-ch4-5 产物）。

读取 data/ocr_sources/merge_report.json（无答案合并 PDF 的页范围/哈希）与
Downloads/课程合集 4.1~4.4 视频清单，生成：
  - chapter4_manifest.json （教材第四章 数列 = 课程 4.3/4.4）
  - chapter5_manifest.json （教材第五章 一元函数的导数及其应用 = 课程 4.1/4.2）
并写出 reports/builds/ch4-build.json 与 ch5-build.json（阶段标记）。

结构与 chapter1_manifest.json（schema 7.3）保持一致；凡依赖 OCR/视觉
验证的字段一律显式标记 PENDING，绝不臆造题号。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path(r"C:\Users\poyi\Downloads")
COURSE_ROOT = DOWNLOADS / "课程合集"
OCR_SOURCES = ROOT / "data" / "ocr_sources"
TRANSCRIPTS = ROOT / "data" / "course_transcripts"
REPORTS = ROOT / "reports" / "builds"

SCHEMA_VERSION = "7.3"
NOW = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

# 教材第4章（数列）8 节 -> 课程 4.3/4.4 映射（标题假设，待视觉/OCR 核验）
CH4_SECTIONS = [
    {"id": "4.1", "label": "第1节 数列的概念", "pdf_pages": [1, 21],
     "required_course_ids": ["4.3.1.1.a", "4.3.1.1.b"],
     "support_course_ids": []},
    {"id": "4.2", "label": "第2节 等差数列的概念", "pdf_pages": [22, 34],
     "required_course_ids": ["4.3.2.1", "4.3.2.2", "4.3.2.3"],
     "support_course_ids": []},
    {"id": "4.3", "label": "第3节 等差数列的前n项和公式", "pdf_pages": [35, 51],
     "required_course_ids": ["4.3.2.4"],
     "support_course_ids": ["4.3.2.1"]},
    {"id": "4.4", "label": "第4节 等比数列的概念", "pdf_pages": [52, 64],
     "required_course_ids": ["4.3.3.1", "4.3.3.2", "4.3.3.3"],
     "support_course_ids": []},
    {"id": "4.5", "label": "第5节 等比数列的前n项和公式", "pdf_pages": [65, 77],
     "required_course_ids": ["4.3.3.4"],
     "support_course_ids": ["4.3.3.1"]},
    {"id": "4.6", "label": "第6节 数学归纳法", "pdf_pages": [78, 82],
     "required_course_ids": ["4.4.9.1", "4.4.9.2"],
     "support_course_ids": []},
    {"id": "4.7", "label": "第7节 微专题1：几类常见的求前n项和的方法", "pdf_pages": [83, 91],
     "required_course_ids": ["4.4.3.1.a", "4.4.3.1.b", "4.4.3.2", "4.4.4.1", "4.4.4.2", "4.4.5.1.a", "4.4.5.1.b"],
     "support_course_ids": []},
    {"id": "4.8", "label": "第8节 微专题2：数列拔高题型", "pdf_pages": [92, 100],
     "required_course_ids": ["4.4.1.1", "4.4.1.2.a", "4.4.1.2.b", "4.4.1.2.c", "4.4.1.2.d", "4.4.1.2.e", "4.4.1.3", "4.4.2.1", "4.4.2.2", "4.4.2.3", "4.4.6.1", "4.4.6.2", "4.4.7.1", "4.4.8.1", "4.4.8.2"],
     "support_course_ids": []},
]

# 教材第5章（导数）6 节 -> 课程 4.1/4.2 映射（标题假设，待视觉/OCR 核验）
CH5_SECTIONS = [
    {"id": "5.1", "label": "第1节 导数的概念及其意义", "pdf_pages": [1, 9],
     "required_course_ids": ["4.1.1.1 导数的定义（上）", "4.1.1.1 导数的定义（下）", "4.1.1.2", "4.1.1.3", "4.1.1.4", "4.1.1.5", "4.1.1.6", "4.1.1.7"],
     "support_course_ids": []},
    {"id": "5.2", "label": "第2节 导数的运算", "pdf_pages": [10, 21],
     "required_course_ids": ["4.1.2.1 基本初等函数的导数及运算法则", "4.1.2.1 基本初等函数的导数及运算法则（进阶）", "4.1.2.2", "4.1.2.3 导数的原函数构造之速解技巧", "4.1.2.3 导数的原函数构造（基础）", "4.1.2.3 导数的原函数构造（进阶）"],
     "support_course_ids": []},
    {"id": "5.3", "label": "第3节 函数的单调性", "pdf_pages": [22, 42],
     "required_course_ids": ["4.1.3.1", "4.1.3.2 二次方程根的分布（上）", "4.1.3.2 二次方程根的分布（下）", "4.1.3.3", "4.1.4.1", "4.1.4.2 含参函数单调性讨论之可因式分解型（上）", "4.1.4.2 含参函数单调性讨论之可因式分解型（中）", "4.1.4.2 含参函数单调性讨论之可因式分解型（下）", "4.1.4.3", "4.1.4.4 含参函数单调性讨论之不可因式分解型（上）", "4.1.4.4 含参函数单调性讨论之不可因式分解型（中）", "4.1.4.4 含参函数单调性讨论之不可因式分解型（下）", "4.1.4.5", "4.1.4.6", "4.1.4.7"],
     "support_course_ids": []},
    {"id": "5.4", "label": "第4节 函数的极值与最大（小）值", "pdf_pages": [43, 59],
     "required_course_ids": ["4.1.4.8 极值与极值点（基础）", "4.1.4.8 极值与极值点（进阶）", "4.1.4.9", "4.1.4.10"],
     "support_course_ids": ["4.1.4.1", "4.1.4.2 含参函数单调性讨论之可因式分解型（上）"]},
    {"id": "5.5", "label": "第5节 微专题3：导数综合大题", "pdf_pages": [60, 75],
     "required_course_ids": ["4.2.1.1", "4.2.1.2", "4.2.1.3", "4.2.1.4", "4.2.1.5", "4.2.2.1 主元法（基础）", "4.2.2.1 主元法（进阶）", "4.2.2.2", "4.2.2.3", "4.2.3.1 参变分离法（基础）", "4.2.3.1 参变分离法（提高）", "4.2.3.1 参变分离法（进阶）", "4.2.3.2 导数可因式分解型分类讨论（基础）", "4.2.3.2 导数可因式分解型分类讨论（进阶）", "4.2.4.1 极值点偏移模型（上）", "4.2.4.1 极值点偏移模型（下）", "4.2.4.2", "4.2.5.1", "4.2.5.2 双极值点问题（上）", "4.2.5.2 双极值点问题（下）"],
     "support_course_ids": []},
    {"id": "5.6", "label": "第6节 微专题4：导数真题集训", "pdf_pages": [76, 95],
     "required_course_ids": ["4.2.6.1 求和型放缩（上）", "4.2.6.1 求和型放缩（下）"],
     "support_course_ids": []},
]

COURSE_DIRS = {
    "ch4": ["4.3 数列", "4.4 数列的综合提升"],
    "ch5": ["4.1 一元函数的导数及其应用", "4.2 一元函数的导数及其应用的综合提升"],
}


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_courses(dirs: list[str]) -> list[dict]:
    out = []
    for d in dirs:
        p = COURSE_ROOT / d
        for f in sorted(p.glob("*.mp4")):
            out.append({
                "course_id": f.stem.split(" ")[0],
                "file_stem": f.stem,
                "file": f.name,
                "path": str(f),
                "sha256": sha256_file(f),
                "dir": d,
            })
    return out


def transcript_gaps(courses: list[dict]) -> dict:
    gaps, done = [], []
    for c in courses:
        out = TRANSCRIPTS / f"{c['file_stem']}.json"
        if out.exists() and out.stat().st_size > 0:
            done.append(c["file_stem"])
        else:
            gaps.append(c["file_stem"])
    return {"missing": gaps, "present": done}


def build_sections(chapter: str, courses: list[dict]) -> list[dict]:
    sections = CH4_SECTIONS if chapter == "ch4" else CH5_SECTIONS
    by_id = {c["course_id"]: c for c in courses}
    result = []
    for s in sections:
        def resolve(ids: list[str]) -> list[str]:
            resolved = []
            for cid in ids:
                exact = by_id.get(cid)
                if exact:
                    resolved.append(exact["file_stem"])
                    continue
                matches = [c for c in courses if c["file_stem"].startswith(cid)]
                if matches:
                    resolved.extend(c["file_stem"] for c in matches)
                else:
                    resolved.append(f"{cid}#UNRESOLVED")
            return resolved

        result.append({
            "id": s["id"],
            "label": s["label"],
            "pdf_pages": s["pdf_pages"],
            "ocr_docs": None,
            "specialized_pdf_pages": s["pdf_pages"][1] - s["pdf_pages"][0] + 1,
            "question_groups": None,
            "question_groups_status": "PENDING_VISION_OCR",
            "verified_question_count": None,
            "learning_item_counts": None,
            "knowledge_points": [],
            "knowledge_points_status": "PENDING_VISION_OCR",
            "type_labels": [],
            "type_training": [],
            "direct_variants": [],
            "required_course_ids": resolve(s["required_course_ids"]),
            "support_course_ids": resolve(s["support_course_ids"]),
            "course_mapping_status": "TITLE_HYPOTHESIS_PENDING_VISION",
            "course_keys": [],
            "micro_units": [],
            "coverage_gaps": [],
            "bridge_units": [],
            "learning_cycles": [],
            "learning_cycles_status": "PENDING_OCR_AND_VISION",
            "exit_gate": "知识点闭卷复述；方法册代表题至少2题FULL_PASS；A组独立校准；一题隔天冷重做。",
            "coverage_status": "UNVERIFIED",
            "coverage_gate": "题包门禁未开始：OCR 文档缺失（PaddleOCR token 未配置），题号与页面对账未执行。",
        })
    return result


def build_manifest(chapter: str, merge: dict, courses: list[dict]) -> dict:
    ch_label = "第四章 数列" if chapter == "ch4" else "第五章 一元函数的导数及其应用"
    module = "数列" if chapter == "ch4" else "一元函数的导数及其应用"
    merge_key = "第4章 数列" if chapter == "ch4" else "第5章 一元函数的导数及其应用"
    m = merge[merge_key]
    pdf_path = Path(m["merged_pdf"])
    gaps = transcript_gaps(courses)
    return {
        "schema_version": SCHEMA_VERSION,
        "target_identity": {
            "module": module,
            "chapter": ch_label,
            "source_set": "2025-2026版选择性必修第2册",
            "primary_file": pdf_path.name,
            "primary_file_path": str(pdf_path),
            "primary_file_sha256": m["merged_sha256"],
            "mapping_note": "按既定计划：第4章(数列)=课程 4.3/4.4；第5章(导数)=课程 4.1/4.2；与教材实际章节一致（选择性必修第2册 第4章 数列 / 第5章 一元函数的导数及其应用）。",
        },
        "source_evidence": {
            "merged_pdf_pages": m["total_pages"],
            "ocr_doc_range": None,
            "ocr_status": "BLOCKED_PADDLE_TOKEN_MISSING",
            "ocr_root": None,
            "course_root": {d: str(COURSE_ROOT / d) for d in COURSE_DIRS[chapter]},
            "course_source_rule": "only Downloads/课程合集, strictly ordered by filename",
            "transcript_root": str(TRANSCRIPTS),
            "transcript_gaps": gaps,
            "no_answer_verification": "PENDING_VISION_SPOT_CHECK",
            "source_pdfs": m["sections"],
            "manual_review_flags": [],
            "learning_item_counts": None,
            "generated_by": "worker build-ch4-5",
            "generated_at": NOW,
        },
        "sections": build_sections(chapter, courses),
        "known_visual_recoveries": [],
        "verification_status": {
            "question_groups": "PENDING_VISION_OCR",
            "ocr_docs": "PENDING (PaddleOCR token 未配置)",
            "course_mapping": "TITLE_HYPOTHESIS",
            "packets": "BLOCKED (无 OCR 文档)",
        },
    }


def build_report(chapter: str, manifest: dict, courses: list[dict], merge: dict) -> dict:
    ch = "4" if chapter == "ch4" else "5"
    gaps = manifest["source_evidence"]["transcript_gaps"]
    return {
        "worker_id": "build-ch4-5",
        "chapter": manifest["target_identity"]["chapter"],
        "generated_at": NOW,
        "stages": {
            "course_inventory": {
                "status": "done",
                "detail": f"{len(courses)} 个视频，按文件名排序",
                "videos": [c["file"] for c in courses],
            },
            "transcript": {
                "status": "partial" if gaps["present"] else "blocked",
                "tool": "faster-whisper large-v3 (int8, cuda)，脚本 scripts/transcribe_courses_ch45.py",
                "present": len(gaps["present"]),
                "missing": len(gaps["missing"]),
                "missing_files": gaps["missing"],
            },
            "textbook_source": {
                "status": "done",
                "detail": "【2025-2026版】选择性必修第2册 各节（方法册+习题册）扫描 PDF 合并为无答案册；无答案属性待视觉抽检确认",
                "merged_pdf": manifest["target_identity"]["primary_file_path"],
                "merged_pdf_pages": manifest["source_evidence"]["merged_pdf_pages"],
                "merged_sha256": manifest["target_identity"]["primary_file_sha256"],
                "per_section_pages": [{s["label"]: s["pdf_pages"]} for s in manifest["sections"]],
            },
            "question_list": {
                "status": "blocked",
                "reason": "GLM-4.6V-Flash 免费档限流（429 code 1302/1305），视觉题号读取未完成；PaddleOCR token 未配置，无 OCR 文档可用",
                "gap": "各节 例题/变式/A-B-C 题号与题量、知识点清单均待视觉或 OCR 核验",
            },
            "manifest": {
                "status": "done_skeleton",
                "path": f"chapter{ch}_manifest.json",
                "detail": "结构对齐 chapter1_manifest.json(schema 7.3)，未验证字段显式 PENDING",
            },
            "packets": {
                "status": "blocked",
                "reason": "无 OCR 文档：PADDLE_OCR_TOKEN 未配置（ybt_learning/ocr.py 唯一入口 paddle_ai_studio），data/packets/4.x、5.x 未产出",
            },
            "contexts_and_routes": {
                "status": "blocked",
                "reason": "data/contexts/4.x.json 与 learning_path_without_questions 依赖 learning_packet（依赖 OCR 文档），未产出",
            },
            "hard_gate": {
                "status": "not_run",
                "detail": "题包题号与教材页逐项对账：等待 OCR/视觉题号清单与题包产出后执行",
            },
        },
        "blocked": [
            "PaddleOCR AI Studio token (PADDLE_OCR_TOKEN) 未配置：OCR 文档与题包无法产出",
            "GLM-4.6V-Flash 免费档限流：题号清单/无答案抽检未完成",
            "data/course_transcripts 4.x 转写缺失（生成中，large-v3 本地转写）",
        ],
        "artifacts": {
            "merged_no_answer_pdf": manifest["target_identity"]["primary_file_path"],
            "manifest": str(ROOT / f"chapter{ch}_manifest.json"),
            "merge_report": str(OCR_SOURCES / "merge_report.json"),
            "transcribe_script": str(ROOT / "scripts" / "transcribe_courses_ch45.py"),
            "report": str(REPORTS / f"ch{ch}-build.json"),
        },
    }


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    merge = load_json(OCR_SOURCES / "merge_report.json")
    for chapter in ("ch4", "ch5"):
        courses = scan_courses(COURSE_DIRS[chapter])
        manifest = build_manifest(chapter, merge, courses)
        report = build_report(chapter, manifest, courses, merge)
        num = "4" if chapter == "ch4" else "5"
        out_manifest = ROOT / f"chapter{num}_manifest.json"
        out_report = REPORTS / f"ch{num}-build.json"
        out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{out_manifest.name}: sections={len(manifest['sections'])} videos={len(courses)} "
              f"transcript_missing={len(manifest['source_evidence']['transcript_gaps']['missing'])}")
        print(f"{out_report.name}: stages={ {k: v['status'] for k, v in report['stages'].items()} }")


if __name__ == "__main__":
    main()
