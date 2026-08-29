#!/usr/bin/env python3
"""Build a source-page-backed index for the supplementary practice book.

OCR is deliberately treated as search evidence. Question wording, formulas and
diagrams remain unverified until the original page image is inspected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUESTION_RE = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*(.*)$")
HEADING_TOKENS = ("章", "节", "课时", "专题", "训练", "检测", "强化", "题型")
LEVEL_MARKERS = ("刷基础", "刷提升", "刷能力", "刷难关", "刷速度", "刷真题", "刷原创", "刷综合")


PRACTICE_UNITS: list[dict[str, Any]] = [
    {"start": 1, "end": 2, "chapter": "1", "section": "1.1", "unit": "1.1.1", "title": "空间向量及其线性运算", "courses": ["space_vector_ops"], "cycles": ["1.1-cycle-1"], "cadence": "after_course"},
    {"start": 3, "end": 5, "chapter": "1", "section": "1.1", "unit": "1.1.2", "title": "空间向量的数量积运算", "courses": ["line_line_angle"], "cycles": ["1.1-cycle-5", "1.1-cycle-6", "1.1-cycle-7"], "cadence": "after_course"},
    {"start": 6, "end": 6, "chapter": "1", "section": "1.2+1.3", "unit": "1.2", "title": "空间向量基本定理", "courses": ["decomposition", "equal_surface"], "cycles": ["1.2_1.3-cycle-1", "1.2_1.3-cycle-4"], "cadence": "after_course"},
    {"start": 7, "end": 8, "chapter": "1", "section": "1.2+1.3", "unit": "1.3", "title": "空间向量及其运算的坐标表示", "courses": ["coordinate_system", "coordinate_ops"], "cycles": ["1.2_1.3-cycle-2", "1.2_1.3-cycle-3", "1.2_1.3-cycle-5", "1.2_1.3-cycle-6", "1.2_1.3-cycle-7", "1.2_1.3-cycle-8"], "cadence": "after_course"},
    {"start": 9, "end": 10, "chapter": "1", "section": "1.2+1.3", "unit": "1.1-1.3-review", "title": "第1.1-1.3节综合训练", "courses": ["coordinate_ops"], "cycles": ["1.2_1.3-cycle-9", "1.2_1.3-cycle-10"], "cadence": "after_section"},
    {"start": 11, "end": 11, "chapter": "1", "section": "1.4", "unit": "1.4.1-lesson-1", "title": "空间中点、直线和平面的向量表示", "courses": ["direction_normal"], "cycles": ["1.4-cycle-1"], "cadence": "after_course"},
    {"start": 12, "end": 13, "chapter": "1", "section": "1.4", "unit": "1.4.1-lesson-2", "title": "空间线面位置关系的判定", "courses": ["parallel_perpendicular", "coplanar"], "cycles": ["1.4-cycle-2", "1.4-cycle-3"], "cadence": "after_course"},
    {"start": 14, "end": 15, "chapter": "1", "section": "1.4", "unit": "1.4.2-lesson-1", "title": "用空间向量研究距离问题", "courses": ["plane_equation_upper", "plane_equation_lower", "distance"], "cycles": ["1.4-cycle-5"], "cadence": "after_course"},
    {"start": 16, "end": 19, "chapter": "1", "section": "1.4", "unit": "1.4.2-lesson-2", "title": "用空间向量研究夹角问题", "courses": ["line_line_angle", "line_plane_angle", "plane_plane_angle"], "cycles": ["1.4-cycle-2", "1.4-cycle-4"], "cadence": "after_course"},
    {"start": 20, "end": 21, "chapter": "1", "section": "1.4", "unit": "1.4-review", "title": "第1.4节综合训练", "courses": ["moving_point", "distance"], "cycles": ["1.4-cycle-6", "1.4-cycle-7"], "cadence": "after_section"},
    {"start": 22, "end": 22, "chapter": "1", "section": "micro专题1", "unit": "topic-1", "title": "空间中的动点问题", "courses": ["moving_point"], "cycles": ["micro-cycle-1", "micro-cycle-5"], "cadence": "after_course"},
    {"start": 23, "end": 26, "chapter": "1", "section": "chapter-1", "unit": "chapter-1-test", "title": "第一章素养检测", "courses": [], "cycles": [], "cadence": "after_chapter"},
    {"start": 27, "end": 28, "chapter": "1", "section": "chapter-1", "unit": "chapter-1-gaokao", "title": "第一章高考强化", "courses": [], "cycles": [], "cadence": "after_chapter"},
    {"start": 29, "end": 30, "chapter": "2", "section": "2.1", "unit": "2.1", "title": "直线的倾斜角与斜率", "courses": ["slope_angle_relation", "moving_line_region"], "cycles": ["2.1-cycle-1", "2.1-cycle-2", "2.1-cycle-3", "2.1-cycle-4"], "cadence": "after_section"},
    {"start": 31, "end": 34, "chapter": "2", "section": "2.2", "unit": "2.2", "title": "直线的方程", "courses": ["line_five_forms", "line_equation_application", "line_parallel_perpendicular"], "cycles": ["2.2-cycle-1", "2.2-cycle-2", "2.2-cycle-3"], "cadence": "after_section"},
    {"start": 35, "end": 38, "chapter": "2", "section": "2.3", "unit": "2.3", "title": "直线的交点坐标与距离公式", "courses": ["point_line_distance", "line_parallel_perpendicular", "line_family_fixed_point"], "cycles": ["2.3-cycle-1", "2.3-cycle-2", "2.3-cycle-3", "2.3-cycle-4"], "cadence": "after_section"},
    {"start": 39, "end": 40, "chapter": "2", "section": "2.4", "unit": "topic-2-3", "title": "与直线有关的对称与最值问题", "courses": ["point_line_symmetry_upper", "point_line_symmetry_lower", "line_line_symmetry_upper", "line_line_symmetry_lower", "line_family_fixed_point"], "cycles": ["2.4-cycle-1", "2.4-cycle-2", "2.4-cycle-3", "2.4-cycle-4", "2.4-cycle-5"], "cadence": "after_section"},
    {"start": 41, "end": 43, "chapter": "2", "section": "2.5", "unit": "2.4", "title": "圆的方程", "courses": ["circle_standard_general", "circle_determination", "circle_equiv_algebra", "circle_equiv_geometry"], "cycles": ["2.5-cycle-1", "2.5-cycle-2", "2.5-cycle-3"], "cadence": "after_section"},
    {"start": 44, "end": 45, "chapter": "2", "section": "2.6", "unit": "2.5.1", "title": "直线与圆的位置关系", "courses": ["line_circle_position", "tangent", "chord_length", "longest_shortest_chord", "line_circle_extreme", "pole_polar_chord"], "cycles": ["2.6-cycle-1", "2.6-cycle-2", "2.6-cycle-3", "2.6-cycle-4", "2.6-cycle-5"], "cadence": "after_section"},
    {"start": 46, "end": 47, "chapter": "2", "section": "2.7", "unit": "2.5.2", "title": "圆与圆的位置关系", "courses": ["circle_circle_position", "pole_polar_chord", "circle_equiv_algebra", "circle_equiv_geometry"], "cycles": ["2.7-cycle-1", "2.7-cycle-2", "2.7-cycle-3", "2.7-cycle-4", "2.7-cycle-5", "2.7-cycle-6"], "cadence": "after_section"},
    {"start": 48, "end": 48, "chapter": "2", "section": "2.6+2.7-review", "unit": "2.5-review", "title": "直线与圆、圆与圆综合训练", "courses": [], "cycles": [], "cadence": "after_section"},
    {"start": 49, "end": 49, "chapter": "2", "section": "chapter-2", "unit": "topic-4", "title": "与圆有关的轨迹问题", "courses": [], "cycles": [], "cadence": "after_section"},
    {"start": 50, "end": 52, "chapter": "2", "section": "chapter-2", "unit": "chapter-2-test", "title": "第二章素养检测", "courses": [], "cycles": [], "cadence": "after_chapter"},
    {"start": 53, "end": 53, "chapter": "2", "section": "chapter-2", "unit": "chapter-2-gaokao", "title": "第二章高考强化", "courses": [], "cycles": [], "cadence": "after_chapter"},
    {"start": 54, "end": 55, "chapter": "3", "section": "ch3.s1", "unit": "3.1.1", "title": "椭圆及其标准方程", "courses": ["ellipse_definition", "ellipse_standard_equations"], "cycles": ["ch3.s1-cycle-1", "ch3.s1-cycle-2", "ch3.s1-cycle-3", "ch3.s1-cycle-4", "ch3.s1-cycle-5", "ch3.s1-cycle-6", "ch3.s1-cycle-7", "ch3.s1-cycle-8"], "cadence": "after_section"},
    {"start": 56, "end": 62, "chapter": "3", "section": "ch3.s2", "unit": "3.1.2", "title": "椭圆的简单几何性质", "courses": ["ellipse_eccentricity"], "cycles": ["ch3.s2-cycle-1", "ch3.s2-cycle-2", "ch3.s2-cycle-3", "ch3.s2-cycle-4", "ch3.s2-cycle-5", "ch3.s2-cycle-6"], "cadence": "after_section"},
    {"start": 63, "end": 64, "chapter": "3", "section": "ch3.s4", "unit": "3.2.1", "title": "双曲线及其标准方程", "courses": ["hyperbola_definition_equation"], "cycles": ["ch3.s4-cycle-1", "ch3.s4-cycle-2", "ch3.s4-cycle-3", "ch3.s4-cycle-4"], "cadence": "after_section"},
    {"start": 65, "end": 71, "chapter": "3", "section": "ch3.s5", "unit": "3.2.2", "title": "双曲线的简单几何性质", "courses": ["hyperbola_eccentricity_asymptote"], "cycles": ["ch3.s5-cycle-1", "ch3.s5-cycle-2", "ch3.s5-cycle-3", "ch3.s5-cycle-4", "ch3.s5-cycle-5", "ch3.s5-cycle-6", "ch3.s5-cycle-7"], "cadence": "after_section"},
    {"start": 72, "end": 73, "chapter": "3", "section": "ch3.s7", "unit": "3.3.1", "title": "抛物线及其标准方程", "courses": ["parabola_definition_equation"], "cycles": ["ch3.s7-cycle-1", "ch3.s7-cycle-2", "ch3.s7-cycle-3", "ch3.s7-cycle-4", "ch3.s7-cycle-5", "ch3.s7-cycle-6"], "cadence": "after_section"},
    {"start": 74, "end": 77, "chapter": "3", "section": "ch3.s8", "unit": "3.3.2", "title": "抛物线的简单几何性质", "courses": ["parabola_properties"], "cycles": ["ch3.s8-cycle-1", "ch3.s8-cycle-2", "ch3.s8-cycle-3", "ch3.s8-cycle-4"], "cadence": "after_section"},
    {"start": 78, "end": 78, "chapter": "3", "section": "ch3.s3+ch3.s6-review", "unit": "topic-5", "title": "椭圆与双曲线离心率综合", "courses": ["ellipse_eccentricity", "hyperbola_eccentricity_asymptote"], "cycles": [], "cadence": "after_section"},
    {"start": 79, "end": 79, "chapter": "3", "section": "ch3.s9", "unit": "topic-6", "title": "圆锥曲线中的中点弦、对称问题", "courses": ["chord_midpoint_extended"], "cycles": ["ch3.s9-cycle-1", "ch3.s9-cycle-2", "ch3.s9-cycle-3", "ch3.s9-cycle-4"], "cadence": "after_section"},
    {"start": 80, "end": 80, "chapter": "3", "section": "chapter-3", "unit": "topic-7", "title": "圆锥曲线中的范围、最值问题", "courses": ["range_upper", "range_mid", "range_lower"], "cycles": [], "cadence": "after_section"},
    {"start": 81, "end": 81, "chapter": "3", "section": "ch3.s11", "unit": "topic-8", "title": "圆锥曲线定点、定值问题", "courses": ["constant_value_1", "fixed_point_1"], "cycles": ["ch3.s11-cycle-1", "ch3.s11-cycle-2", "ch3.s11-cycle-3", "ch3.s11-cycle-4", "ch3.s11-cycle-5"], "cadence": "after_section"},
    {"start": 82, "end": 82, "chapter": "3", "section": "ch3.s13", "unit": "topic-9", "title": "圆锥曲线存在、探索性问题", "courses": ["moving_point_basic"], "cycles": ["ch3.s13-cycle-1", "ch3.s13-cycle-2", "ch3.s13-cycle-3", "ch3.s13-cycle-4", "ch3.s13-cycle-5"], "cadence": "after_section"},
    {"start": 83, "end": 90, "chapter": "3", "section": "chapter-3", "unit": "chapter-3-assessment", "title": "第三章检测与高考强化", "courses": [], "cycles": [], "cadence": "after_chapter"},
    {"start": 91, "end": 94, "chapter": "all", "section": "module", "unit": "new-exam-specials", "title": "新定义与开放题专练", "courses": [], "cycles": [], "cadence": "after_chapter"},
    {"start": 95, "end": 98, "chapter": "all", "section": "module", "unit": "module-test", "title": "模块综合测试", "courses": [], "cycles": [], "cadence": "after_chapter"},
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_unit(unit: dict[str, Any]) -> dict[str, Any]:
    value = {**unit, "courses": list(unit["courses"]), "cycles": list(unit["cycles"])}
    if value["cadence"] != "after_course":
        value["cycles"] = []
    return value


def page_unit(printed_page: int | None) -> dict[str, Any] | None:
    if printed_page is None:
        return None
    unit = next((unit for unit in PRACTICE_UNITS if unit["start"] <= printed_page <= unit["end"]), None)
    return normalized_unit(unit) if unit else None


def ordered_rows(result: Any, width: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in result or []:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        box, text, score = item[0], str(item[1]).strip(), item[2]
        if not text:
            continue
        try:
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            center_x = statistics.mean(xs)
            center_y = statistics.mean(ys)
            rows.append({
                "text": text,
                "confidence": round(float(score), 4),
                "bbox": [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)],
                "column": "left" if center_x < width * 0.5 else "right",
                "center_x": center_x,
                "center_y": center_y,
            })
        except (TypeError, ValueError, IndexError):
            continue
    return rows


def reading_order(rows: list[dict[str, Any]], width: int) -> list[dict[str, Any]]:
    full_width = [row for row in rows if row["bbox"][0] < width * 0.25 and row["bbox"][2] > width * 0.75]
    body = [row for row in rows if row not in full_width]
    result = sorted(full_width, key=lambda row: (row["center_y"], row["center_x"]))
    for column in ("left", "right"):
        result.extend(sorted((row for row in body if row["column"] == column), key=lambda row: (row["center_y"], row["center_x"])))
    return result


def extract_questions(rows: list[dict[str, Any]], source_id: str, printed_page: int, pdf_page: int, unit: dict[str, Any], image_height: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    occurrences: dict[tuple[int, str], int] = {}
    for column in ("left", "right"):
        column_rows = sorted((row for row in rows if row["column"] == column), key=lambda row: (row["center_y"], row["center_x"]))
        starts: list[tuple[int, re.Match[str]]] = []
        for index, row in enumerate(column_rows):
            match = QUESTION_RE.match(row["text"])
            remainder = match.group(2).strip() if match else ''
            section_heading = bool(remainder[:1].isdigit() and row["center_y"] < image_height * 0.22)
            footer_noise = row["center_y"] > image_height * 0.93
            if match and remainder and not section_heading and not footer_noise and not re.fullmatch(r"[\d.．\s]+", remainder):
                starts.append((index, match))
        for position, (start_index, match) in enumerate(starts):
            end_index = starts[position + 1][0] if position + 1 < len(starts) else min(len(column_rows), start_index + 14)
            excerpt_rows = column_rows[start_index:end_index]
            excerpt = "\n".join(row["text"] for row in excerpt_rows).strip()
            number = int(match.group(1))
            occurrence_key = (number, column)
            occurrences[occurrence_key] = occurrences.get(occurrence_key, 0) + 1
            occurrence = occurrences[occurrence_key]
            prior_text = [row["text"] for row in column_rows[:start_index]]
            practice_level = next((marker for text in reversed(prior_text) for marker in LEVEL_MARKERS if marker in text), "未标级")
            source_type_title = next((text for text in reversed(prior_text) if "题型" in text), "未标题型")
            cadence = unit["cadence"]
            if cadence == "after_course" and practice_level in {"刷提升", "刷能力", "刷难关", "刷速度"}:
                cadence = "after_section"
            item_id = f"{source_id}:p{printed_page}:q{number}:{column}:r{occurrence}"
            items.append({
                "item_id": item_id,
                "label": f"第{printed_page}页第{number}题" + (f"（第{occurrence}组）" if occurrence > 1 else ""),
                "question_number": number,
                "occurrence": occurrence,
                "printed_page": printed_page,
                "pdf_page": pdf_page,
                "column": column,
                "unit": unit["unit"],
                "chapter": unit["chapter"],
                "section": unit["section"],
                "title": unit["title"],
                "source_type_title": source_type_title,
                "practice_level": practice_level,
                "course_keys": unit["courses"],
                "cycle_ids": unit["cycles"],
                "cadence": cadence,
                "mapping_status": "course_cycle_candidate" if cadence == "after_course" and unit["cycles"] else "source_range_candidate",
                "ocr_excerpt": excerpt[:2200],
                "ocr_excerpt_sha256": sha256_bytes(excerpt.encode("utf-8")),
                "visual_status": "NEEDS_SOURCE_PAGE_REVIEW",
                "answer_status": "not_in_source_pdf",
            })
    if printed_page == 80:
        # Source page 80 contains question 2's equation fragment "=1" in the
        # left column. OCR turns that continuation into a second question 1.
        items = [item for item in items if not (item["question_number"] == 1 and item["occurrence"] > 1)]
    if printed_page == 78 and not any(item["question_number"] == 5 for item in items):
        # The source page visibly contains question 5 across the bottom-left and
        # top-right columns, but OCR drops its printed number. Keep only the
        # source-verified identity; the exact stem still requires the page image.
        excerpt = "原页可见第5题，跨栏题面未被 OCR 完整识别；读取原页图后再核对公式与题意。"
        items.append({
            "item_id": f"{source_id}:p78:q5:left:r1",
            "label": "第78页第5题",
            "question_number": 5,
            "occurrence": 1,
            "printed_page": 78,
            "pdf_page": pdf_page,
            "column": "left",
            "unit": unit["unit"],
            "chapter": unit["chapter"],
            "section": unit["section"],
            "title": unit["title"],
            "source_type_title": "题型1 求离心率的值",
            "practice_level": "刷难关",
            "course_keys": unit["courses"],
            "cycle_ids": unit["cycles"],
            "cadence": "after_section",
            "mapping_status": "source_range_candidate",
            "ocr_excerpt": excerpt,
            "ocr_excerpt_sha256": sha256_bytes(excerpt.encode("utf-8")),
            "visual_status": "NEEDS_SOURCE_PAGE_REVIEW",
            "answer_status": "not_in_source_pdf",
        })
    labeled_levels = [item["practice_level"] for item in items if item["practice_level"] != "未标级"]
    if labeled_levels and len(set(labeled_levels)) == 1:
        inherited_level = Counter(labeled_levels).most_common(1)[0][0]
        for item in items:
            if item["practice_level"] != "未标级":
                continue
            item["practice_level"] = inherited_level
            if unit["cadence"] == "after_course" and inherited_level in {"刷提升", "刷能力", "刷难关", "刷速度"}:
                item["cadence"] = "after_section"
                item["cycle_ids"] = []
                item["mapping_status"] = "source_range_candidate"
    return sorted(items, key=lambda item: (item["question_number"], item["column"]))


def heading_candidates(text: str) -> list[str]:
    candidates = []
    for line in text.splitlines():
        clean = line.strip()
        if clean and any(token in clean for token in HEADING_TOKENS):
            candidates.append(clean)
    return candidates[:16]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--remap-only", action="store_true")
    args = parser.parse_args()
    if not args.pdf.is_file():
        raise SystemExit(f"missing PDF: {args.pdf}")
    if args.remap_only:
        index_path = args.out / "index.json"
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        items: list[dict[str, Any]] = []
        for page in payload.get("pages", []):
            rows = []
            for raw in page.get("ocr_lines", []):
                bbox = raw.get("bbox", [0, 0, 0, 0])
                rows.append({
                    **raw,
                    "center_x": (float(bbox[0]) + float(bbox[2])) / 2,
                    "center_y": (float(bbox[1]) + float(bbox[3])) / 2,
                })
            unit = page_unit(page.get("printed_page"))
            page["unit"] = unit["unit"] if unit else None
            page["chapter"] = unit["chapter"] if unit else None
            page["section"] = unit["section"] if unit else None
            page["unit_title"] = unit["title"] if unit else None
            page["course_keys"] = unit["courses"] if unit else []
            page["cycle_ids"] = unit["cycles"] if unit else []
            page["cadence"] = unit["cadence"] if unit else None
            page["page_role"] = "content" if unit else "front_matter"
            page_items = extract_questions(rows, payload["source_id"], int(page["printed_page"]), int(page["pdf_page"]), unit, int(page["image_height"])) if unit and page.get("printed_page") else []
            page["question_item_ids"] = [item["item_id"] for item in page_items]
            items.extend(page_items)
        payload["units"] = [normalized_unit(unit) for unit in PRACTICE_UNITS]
        payload["items"] = items
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "remapped", "pages": len(payload["pages"]), "items": len(items)}, ensure_ascii=False))
        return 0
    try:
        import pymupdf
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as error:
        raise SystemExit("pymupdf and rapidocr_onnxruntime are required for a full rebuild") from error

    source_sha = sha256_file(args.pdf)
    source_id = f"bishua-rja-2026-{source_sha[:12]}"
    pages_root = args.out / "pages"
    pages_root.mkdir(parents=True, exist_ok=True)
    ocr = RapidOCR()
    document = pymupdf.open(str(args.pdf))
    pages: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    try:
        for index in range(len(document)):
            pdf_page = index + 1
            printed_page = pdf_page - 8 if pdf_page >= 9 else None
            image_path = pages_root / f"page-{pdf_page:03d}.jpg"
            if image_path.is_file():
                image_bytes = image_path.read_bytes()
                pixmap = pymupdf.Pixmap(image_bytes)
            else:
                pixmap = document[index].get_pixmap(dpi=args.dpi, alpha=False)
                image_bytes = pixmap.tobytes("jpg", jpg_quality=86)
                image_path.write_bytes(image_bytes)
            result, _ = ocr(str(image_path))
            rows = ordered_rows(result, pixmap.width)
            ordered = reading_order(rows, pixmap.width)
            text = "\n".join(row["text"] for row in ordered)
            unit = page_unit(printed_page)
            page_items = extract_questions(rows, source_id, int(printed_page), pdf_page, unit, pixmap.height) if unit and printed_page else []
            items.extend(page_items)
            pages.append({
                "source_id": source_id,
                "pdf_page": pdf_page,
                "printed_page": printed_page,
                "page_role": "content" if unit else "front_matter",
                "unit": unit["unit"] if unit else None,
                "chapter": unit["chapter"] if unit else None,
                "section": unit["section"] if unit else None,
                "unit_title": unit["title"] if unit else None,
                "course_keys": unit["courses"] if unit else [],
                "cycle_ids": unit["cycles"] if unit else [],
                "cadence": unit["cadence"] if unit else None,
                "heading_candidates": heading_candidates(text),
                "ocr_lines": [{key: row[key] for key in ("text", "confidence", "bbox", "column")} for row in rows],
                "question_item_ids": [item["item_id"] for item in page_items],
                "ocr_text": text,
                "ocr_text_sha256": sha256_bytes(text.encode("utf-8")),
                "ocr_confidence": round(statistics.mean(row["confidence"] for row in rows), 4) if rows else 0,
                "ocr_status": "passed" if text else "empty",
                "visual_status": "NEEDS_SOURCE_PAGE_REVIEW" if unit else "FRONT_MATTER",
                "page_image_path": f"pages/page-{pdf_page:03d}.jpg",
                "page_image_sha256": sha256_bytes(image_bytes),
                "image_width": pixmap.width,
                "image_height": pixmap.height,
            })
            if pdf_page == 1 or pdf_page % 10 == 0 or pdf_page == len(document):
                print(f"practice book: {pdf_page}/{len(document)}, items={len(items)}", flush=True)
    finally:
        document.close()

    payload = {
        "schema_version": "math-practice-book-index-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": source_id,
        "title": "2026版 高中必刷题数学 选择性必修第一册 RJA",
        "file_name": args.pdf.name,
        "source_pdf_sha256": source_sha,
        "page_count": len(pages),
        "content_page_count": sum(page["page_role"] == "content" for page in pages),
        "printed_page_offset": 8,
        "printed_page_anchor_evidence": [
            {"pdf_page": 9, "printed_page": 1},
            {"pdf_page": 103, "printed_page": 95},
            {"pdf_page": 106, "printed_page": 98},
        ],
        "ocr_provider": "rapidocr_onnxruntime",
        "text_is_search_aid_only": True,
        "source_page_is_question_authority": True,
        "answer_status": "not_in_source_pdf",
        "route_policy": {
            "default": "course_first",
            "order": ["course", "ybt", "practice_basic", "practice_advanced", "acceptance"],
            "within_unit": "preserve source page and question order",
        },
        "units": [normalized_unit(unit) for unit in PRACTICE_UNITS],
        "pages": pages,
        "items": items,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_id": source_id, "pages": len(pages), "items": len(items), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
