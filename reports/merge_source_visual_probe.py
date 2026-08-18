from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "reports" / "source_visual_probe.json"
SIDE = ROOT / "reports" / "source_visual_probe_sidecar.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


CHAPTER_PDF = Path(r"C:\Users\poyi\Downloads\【2025-2025版】选择性必修第1册\按章节合并（无答案册）\第1章 空间向量与立体几何（无答案册）.pdf")
PROVENANCE = {
    "b5_source_page_030_crop.png": (CHAPTER_PDF, 30, [250, 145, 370, 300], Path(r"C:\开发\小工具\一本通学习系统_v7\data\ocr_live_full\imgs\img_in_image_box_522_288_695_483.jpg")),
    "b13_source_page_032_crop.png": (CHAPTER_PDF, 32, [420, 360, 595, 530], Path(r"C:\Users\poyi\Downloads\placeholder")),
    "pyramid_b4_source_page_051_crop.png": (CHAPTER_PDF, 51, [420, 145, 595, 390], Path(r"C:\Users\poyi\Downloads\placeholder")),
    "micro_b1_source_page_065_crop.png": (CHAPTER_PDF, 65, [450, 500, 595, 650], Path(r"C:\开发\小工具\一本通DeepSeek迭代\worker-01-content\ocr\imgs\img_in_image_box_905_1029_1095_1209.jpg")),
    "micro_b4_source_page_067_crop.png": (CHAPTER_PDF, 67, [405, 135, 595, 360], Path(r"C:\Users\poyi\Downloads\placeholder")),
}

# These three single-image questions use live OCR crops; their provenance is
# resolved by the hash of the question image and does not need a fixed path.
QUESTION_IMAGE_BY_HINT = {
    "1.2+1.3-B13": Path(r"C:\开发\小工具\一本通学习系统_v7\data\ocr_live_full\imgs\img_in_image_box_897_830_1094_1011.jpg"),
    "1.4-B4": Path(r"C:\开发\小工具\一本通学习系统_v7\data\ocr_live_full\imgs\img_in_image_box_896_353_1093_566.jpg"),
    "micro专题1-B4": Path(r"C:\开发\小工具\一本通学习系统_v7\data\ocr_live_full\imgs\img_in_image_box_832_343_1093_610.jpg"),
}


data = json.loads(PROBE.read_text(encoding="utf-8"))


def is_student_visual(row: dict) -> bool:
    image = str(row.get("image", "")).lower()
    provenance = row.get("source_provenance") or {}
    source_pdf = str(provenance.get("source_pdf", "")).lower() if isinstance(provenance, dict) else ""
    chinese_answer_book = ("答案册" in image or "答案册" in source_pdf) and ("无答案册" not in image and "无答案册" not in source_pdf)
    banned = ("worker-02-solutions", "answer_book", "answer-book", "answerbook")
    return not (chinese_answer_book or any(marker in image or marker in source_pdf for marker in banned))


# A provider retry may return an empty/truncated caption even though an
# earlier call for the same immutable crop already produced a valid result.
# Preserve that current-run, content-bound result rather than erasing it with
# a transient failure; a new passed row always wins for the same image.
fallback_full = ROOT / "data" / "vision_sidecar_full.json"
fallback_rows = []
legacy_sidecar_rows = []
if SIDE.is_file():
    legacy_payload = json.loads(SIDE.read_text(encoding="utf-8"))
    legacy_sidecar_rows = [
        row for row in legacy_payload.get("results", [])
        if row.get("status") == "passed"
        and row.get("confidence") in {"E1", "E2"}
        and row.get("structured")
        and is_student_visual(row)
    ]
if fallback_full.is_file():
    fallback_payload = json.loads(fallback_full.read_text(encoding="utf-8"))
    fallback_rows = [
        row for row in fallback_payload.get("results", [])
        if str(row.get("image", "")).startswith(str(ROOT / "reports" / "source_visuals2"))
        and is_student_visual(row)
        and row.get("status") == "passed"
        and row.get("confidence") in {"E1", "E2"}
        and row.get("structured")
    ]
candidate_rows = {(row.get("question_hint"), row.get("image")): row for row in legacy_sidecar_rows}
for row in fallback_rows:
    key = (row.get("question_hint"), row.get("image"))
    previous = candidate_rows.get(key)
    if previous is None or (row.get("status") == "passed" and row.get("confidence") in {"E1", "E2"} and row.get("structured")):
        candidate_rows[key] = row
for row in data.get("results", []):
    if not is_student_visual(row):
        continue
    if row.get("status") == "passed" and row.get("confidence") in {"E1", "E2"} and row.get("structured"):
        candidate_rows[(row.get("question_hint"), row.get("image"))] = row

results = []
for row in candidate_rows.values():
    path = Path(row["image"])
    source_record = PROVENANCE.get(path.name)
    if not source_record:
        raise SystemExit(f"missing source provenance mapping for {path.name}")
    source_pdf, pdf_page, crop_rect, default_derived = source_record
    derived = QUESTION_IMAGE_BY_HINT.get(row["question_hint"], default_derived)
    if not source_pdf.is_file() or not derived.is_file():
        raise SystemExit(f"missing provenance input: source={source_pdf} derived={derived}")
    results.append({
        "status": "passed",
        "question_hint": row["question_hint"],
        "section": row["question_hint"].rsplit("-", 1)[0],
        "image": str(path),
        "image_sha256": sha(path),
        "confidence": row["confidence"],
        "model": row.get("model"),
        "structured": row["structured"],
        "source_provenance": {
            "source_kind": "high_resolution_source_pdf_crop",
            "source_pdf": str(source_pdf),
            "source_pdf_sha256": sha(source_pdf),
            "pdf_page": pdf_page,
            "crop_rect": crop_rect,
            "derived_from_image_path": str(derived),
            "derived_from_image_sha256": sha(derived),
        },
    })
SIDE.write_text(json.dumps({"schema_version": "7.2", "status": "passed", "provider": data.get("provider"), "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"sidecar": str(SIDE), "passed": len(results), "hints": [r["question_hint"] for r in results]}, ensure_ascii=False))
raise SystemExit(0)
