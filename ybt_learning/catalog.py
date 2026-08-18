from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .common import now_iso, save_json


COURSE_IDS = [
    "3.1.1.1", "3.1.2.1", "3.1.2.2", "3.1.3.1", "3.1.3.2", "3.1.3.3",
    "3.1.4.1", "3.1.4.2", "3.1.4.3", "3.1.4.4", "3.1.4.5",
    "3.1.4.6.a", "3.1.4.6.b", "3.1.4.7", "3.1.4.8",
]
COURSE_IDS_BY_SPECIFICITY = sorted(COURSE_IDS, key=len, reverse=True)


def course_id_from_stem(stem: str) -> str | None:
    """优先匹配最长编号，避免 3.1.4.5a 被截成 3.1.4.5。"""
    return next((course_id for course_id in COURSE_IDS_BY_SPECIFICITY if stem.startswith(course_id)), None)


def semantic_course_key(name: str) -> str | None:
    """Map the ordered course-collection filenames to stable semantic keys."""
    value = name.lower()
    if "空间向量的运算与拆分" in value or "空间向量的运算" in value and "拆分" not in value and "等值面" not in value:
        return "space_vector_ops"
    if "拆分法" in value:
        return "decomposition"
    if "等值面法" in value:
        return "equal_surface"
    if "空间直角坐标系" in value:
        return "coordinate_system"
    if "坐标表示" in value and "空间直角坐标系" not in value:
        return "coordinate_ops"
    if "平面方程" in value:
        if "上" in value:
            return "plane_equation_upper"
        if "下" in value:
            return "plane_equation_lower"
        return "plane_equation"
    if "方向向量" in value or "法向量" in value:
        return "direction_normal"
    if "平行垂直" in value or "基本应用" in value:
        return "parallel_perpendicular"
    if "证明共面" in value:
        return "coplanar"
    if "向量夹角" in value or "直线夹角" in value:
        return "line_line_angle"
    if "直线与平面的夹角" in value:
        return "line_plane_angle"
    if "平面与平面的夹角" in value:
        return "plane_plane_angle"
    if "距离问题" in value:
        return "distance"
    if "动点问题" in value:
        return "moving_point"
    return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _duration(path: Path) -> float | None:
    try:
        raw = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], text=True, stderr=subprocess.DEVNULL, timeout=30)
        return float(raw.strip())
    except Exception:
        return None


def scan_courses(download_root: str | Path) -> list[dict[str, Any]]:
    root = Path(download_root)
    course_root = root / "课程合集" / "3.1 空间向量与立体几何"
    files = [
        path for path in course_root.glob("*.mp4")
        if any(path.stem.startswith(course_id) for course_id in COURSE_IDS)
    ]
    candidates = []
    for path in sorted(set(files)):
        stem = path.stem
        course_id = course_id_from_stem(stem)
        course_key = semantic_course_key(stem)
        digest = _sha256(path)
        candidates.append({
            "course_id": course_id,
            "course_key": course_key,
            "file": str(path),
            "size": path.stat().st_size,
            "sha256": digest,
            "duration_s": _duration(path),
            "required_candidate": bool(course_id),
            "canonical": True,
            "variant": "course_collection",
            "evidence": "ordered_course_collection_filename",
        })
    return sorted(candidates, key=lambda x: (x["course_id"] or "", x["file"]))


def scan_transcripts(
    transcript_root: str | Path,
    courses: list[dict[str, Any]],
    normalized_root: str | Path,
    provenance_video_root: str | Path,
) -> list[dict[str, Any]]:
    root = Path(transcript_root)
    normalized = Path(normalized_root)
    normalized.mkdir(parents=True, exist_ok=True)
    canonical_by_stem = {Path(item["file"]).stem: item for item in courses}
    provenance_root = Path(provenance_video_root)
    records = []
    for path in sorted(root.glob("*.json")):
        course = canonical_by_stem.get(path.stem)
        if not course:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        already_bound = data.get("source_video_sha256") == course["sha256"]
        provenance_video = provenance_root / f"{path.stem}.mp4"
        byte_identical_source = provenance_video.is_file() and _sha256(provenance_video) == course["sha256"]
        if not already_bound and not byte_identical_source:
            continue
        normalized_path = normalized / path.name
        normalized_data = dict(data)
        normalized_data["source_video_file"] = course["file"]
        normalized_data["source_video_sha256"] = course["sha256"]
        normalized_data["provenance"] = "transcript source video is byte-identical to the Downloads/课程合集 video by SHA-256"
        save_json(normalized_path, normalized_data)
        records.append({"course_id": course_id_from_stem(path.stem), "course_key": semantic_course_key(path.stem), "file": str(normalized_path), "source_video_file": course["file"], "source_video_sha256": course["sha256"], "duration_s": data.get("duration_s"), "text_chars": len(data.get("full_text", "")), "text_sha256": hashlib.sha256(data.get("full_text", "").encode("utf-8")).hexdigest(), "evidence": "course_collection_transcript_with_video_sha256"})
    return records


def build_catalog(*, download_root: str | Path, transcript_root: str | Path, output_path: str | Path) -> dict[str, Any]:
    courses = scan_courses(download_root)
    transcripts = scan_transcripts(
        transcript_root,
        courses,
        Path(output_path).parent / "course_transcripts",
        Path(download_root) / "e" / "2",
    )
    by_id: dict[str, dict[str, Any]] = {}
    for record in courses + transcripts:
        cid = record.get("course_key") or (record.get("course_id") or "unmapped")
        by_id.setdefault(cid, {"course_key": record.get("course_key"), "course_id": record.get("course_id"), "videos": [], "transcripts": []})
        (by_id[cid]["videos"] if "size" in record else by_id[cid]["transcripts"]).append(record)
    result = {"schema_version": "7.2", "created_at": now_iso(), "video_count": len(courses), "course_count": len(by_id), "canonical_video_count": len(courses), "variant_video_count": 0, "transcript_count": len(transcripts), "courses": list(by_id.values()), "notes": ["唯一视频来源是 Downloads/课程合集，按文件编号顺序使用。", "课程标题不是覆盖或掌握证据；覆盖必须结合转写和一本通题目动作核验。"]}
    save_json(output_path, result)
    return result


def build_learning_plan(
    manifest: dict[str, Any],
    catalog: dict[str, Any],
    bridge_catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    by_id = {c.get("course_key") or c.get("course_id"): c for c in catalog.get("courses", [])}
    output = []
    for section in manifest["sections"]:
        required = []
        course_ids = section["required_course_ids"]
        course_keys = section.get("required_course_keys", course_ids)
        if len(course_ids) != len(course_keys):
            raise ValueError(f"manifest course mapping length mismatch: {section['id']}")
        def course_entry(course_id: str, course_key: str, role: str) -> dict[str, Any]:
            entry = by_id.get(course_key, {"course_key": course_key, "course_id": course_id, "videos": [], "transcripts": []})
            videos = entry.get("videos", [])
            ordered = [x["file"] for x in sorted(videos, key=lambda item: (item.get("course_id") or "", item["file"]))]
            return {"role": role, "course_key": course_key, "original_course_ids": [course_id], "original_course_id": course_id, "course_id_variants": sorted({x.get("course_id") for x in videos if x.get("course_id")}), "video_files": ordered, "recommended_video_files": ordered, "recommended_variant": "course_collection", "transcript_files": [x["file"] for x in entry.get("transcripts", [])], "coverage_status": "COVERED" if entry.get("transcripts") else "CANDIDATE_ONLY", "coverage_note": "课程库存存在不等于该小节所有难题方法已覆盖；必须结合转写、一本通例题/变式/习题逐项核验。"}

        for course_id, course_key in zip(course_ids, course_keys):
            required.append(course_entry(course_id, course_key, "required"))
        support_ids = section.get("support_course_ids", [])
        support_keys = section.get("support_course_keys", support_ids)
        if len(support_ids) != len(support_keys):
            raise ValueError(f"manifest support course mapping length mismatch: {section['id']}")
        support = [course_entry(course_id, course_key, "support") for course_id, course_key in zip(support_ids, support_keys)]
        exercise_order = [{"group": group, "numbers": list(range(bounds[0], bounds[1] + 1))} for group, bounds in section["question_groups"].items()]
        bridge_units = section.get("bridge_units", [])
        if bridge_catalog:
            bridge_units = []
            prefix = section["id"] + "-"
            for unit in bridge_catalog.get("units", []):
                if section["id"] not in unit.get("sections", []):
                    continue
                item = dict(unit)
                targets = list(item.get("target_questions", []))
                item["target_question_keys"] = targets
                item["target_questions"] = [target[len(prefix):] for target in targets if target.startswith(prefix)]
                bridge_units.append(item)
        coverage_gaps = section.get("coverage_gaps", [])
        output.append({
            "section": section["id"],
            "label": section["label"],
            "step_order": ["核验课程实际覆盖", "按课程合集编号听当前方法", "立即做对应知识点及右侧例题", "立即做该方法直属变式和类型题", "立即做对应A/B/C习题", "记录首个断点并最小提示", "未污染近迁移", "隔天冷复测"],
            "course_selection_rule": "只使用 Downloads\\课程合集\\3.1 空间向量与立体几何，严格按文件编号顺序；不使用其他下载副本。",
            "completion_semantics": {
                "video_only_sufficient": not bool(coverage_gaps) and not bool(bridge_units),
                "required_path": "视频课程 + 讲义顺序 + 无答案桥接微单元 + 独立作答" if bridge_units or coverage_gaps else "视频课程 + 讲义顺序 + 独立作答",
                "bridge_required_before_target_questions": sorted({target for unit in bridge_units for target in unit.get("target_questions", [])}),
                "honesty_note": "课程库存和字幕存在不等于所有难题方法已覆盖；必须完成列出的桥接单元后才进入对应题目。" if coverage_gaps or bridge_units else "当前题目没有登记的课程覆盖缺口。",
            },
            "required_courses": required,
            "support_courses": support,
            "must_listen_courses": required + support,
            "question_groups": section["question_groups"],
            "exercise_order": exercise_order,
            "layout_kind": section.get("layout_kind", "knowledge_points_then_type_training_then_exercises"),
            "knowledge_points": section["knowledge_points"],
            "type_labels": section["type_labels"],
            "type_training": section.get("type_training", []),
            "direct_variants": section.get("direct_variants", []),
            "micro_units": section["micro_units"],
            "bridge_units": bridge_units,
            "coverage_gaps": coverage_gaps,
            "exit_gate": section["exit_gate"],
        })
    return {"schema_version": "7.2", "plan": output}


def normalize_section(value: str) -> str:
    raw = value.strip().replace("第", "").replace("节", "")
    aliases = {
        "1": "1.1", "1.1": "1.1",
        "2": "1.2+1.3", "1.2": "1.2+1.3", "1.3": "1.2+1.3", "1.2+1.3": "1.2+1.3",
        "3": "1.4", "1.4": "1.4",
        "4": "micro专题1", "微专题1": "micro专题1", "micro专题1": "micro专题1",
    }
    if raw not in aliases:
        raise ValueError(f"unknown section: {value}")
    return aliases[raw]


def select_section_plan(plan: dict[str, Any], section: str) -> dict[str, Any]:
    wanted = normalize_section(section)
    for item in plan.get("plan", []):
        if item.get("section") == wanted:
            return item
    raise ValueError(f"section not found in plan: {wanted}")
