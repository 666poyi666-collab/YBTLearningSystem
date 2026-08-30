#!/usr/bin/env python3
"""Build and audit every current section in chapters 1-5."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ybt_learning.common import save_json, stable_id
from ybt_learning.packet import PacketBuilder


COURSE_ROOT = Path(os.environ["YBT_COURSE_ROOT"]).expanduser().resolve() if os.environ.get("YBT_COURSE_ROOT") else ROOT / ".external-course-source-unavailable"
TRANSCRIPT_ROOT = ROOT / "data" / "course_transcripts"
PACKET_ROOT = ROOT / "data" / "packets"
REPORT_ROOT = ROOT / "reports" / "all_chapters"
COURSE_DIRS = (
    "3.1 空间向量与立体几何",
    "3.2 直线与圆的方程",
    "3.3 圆锥曲线的方程",
    "3.4 圆锥曲线方程的综合提升",
    "4.1 一元函数的导数及其应用",
    "4.2 一元函数的导数及其应用的综合提升",
    "4.3 数列",
    "4.4 数列的综合提升",
)
CHAPTERS = {
    1: {
        "manifest": ROOT / "chapter1_manifest.json",
        "ocr_root": ROOT / "data" / "ocr_live_current" / "first_chapter_69",
    },
    2: {
        "manifest": ROOT / "chapter2_manifest.json",
        "ocr_root": ROOT / "data" / "ocr_live_current" / "second_chapter_109",
    },
    3: {
        "manifest": ROOT / "chapter3_manifest.json",
        "ocr_root": ROOT / "data" / "ocr_live_current" / "third_chapter_180",
    },
    4: {
        "manifest": ROOT / "chapter4_manifest.json",
        "ocr_root": ROOT / "data" / "ocr_live_current" / "chapter4_100",
    },
    5: {
        "manifest": ROOT / "chapter5_manifest.json",
        "ocr_root": ROOT / "data" / "ocr_live_current" / "chapter5_95",
    },
}
SIDECAR_PATHS = (
    ROOT / "data" / "vision_sidecar_sample.json",
    ROOT / "data" / "vision_sidecar_full.json",
    ROOT / "reports" / "source_visual_probe_sidecar.json",
    ROOT / "data" / "vision_sidecar_all_chapters.json",
)
COURSE_ID_RE = re.compile(r"^(\d+(?:\.\d+){2,}(?:\.[a-z])?)\s+(.+)$", re.I)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def manifest_totals(manifests: dict[int, dict[str, Any]]) -> dict[str, int]:
    totals = {
        "chapters": len(manifests),
        "sections": 0,
        "worked_examples": 0,
        "direct_variants": 0,
        "abc_exercises": 0,
        "total_numbered_learning_items": 0,
    }
    for manifest in manifests.values():
        totals["sections"] += len(manifest.get("sections", []))
        for section in manifest.get("sections", []):
            counts = section.get("learning_item_counts") or {}
            totals["worked_examples"] += int(counts.get("worked_examples", 0))
            totals["direct_variants"] += int(counts.get("direct_variants", 0))
            totals["abc_exercises"] += int(counts.get("abc_exercises", 0))
            totals["total_numbered_learning_items"] += int(counts.get("total", 0))
    return totals


def _chapter_course_metadata(chapter: int, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    if chapter == 1:
        plan_path = ROOT / "data" / "chapter1_learning_plan.json"
        if plan_path.is_file():
            plan = load_json(plan_path)
            for section in plan.get("plan", []):
                plan_courses = section.get("must_listen_courses") or [
                    *section.get("required_courses", []),
                    *section.get("support_courses", []),
                ]
                for item in plan_courses:
                    key = str(item.get("course_key") or "")
                    if key:
                        metadata[key] = dict(item)
    elif chapter == 2:
        for item in (manifest.get("course_inventory") or {}).get("courses", []):
            key = str(item.get("course_key") or "")
            if key:
                metadata[key] = dict(item)
    elif chapter == 3:
        for rows in (manifest.get("courses") or {}).values():
            for item in rows:
                key = str(item.get("course_key") or "")
                if key:
                    metadata[key] = dict(item)

    for section in manifest.get("sections", []):
        for key in (
            *section.get("required_course_keys", []),
            *section.get("support_course_keys", []),
            *[
                course_key
                for cycle in section.get("learning_cycles", [])
                for field in ("course_keys", "prerequisite_course_keys", "optional_course_keys")
                for course_key in cycle.get(field, [])
            ],
        ):
            value = str(key)
            if value in metadata:
                continue
            match = COURSE_ID_RE.match(value)
            metadata[value] = {
                "course_key": value,
                "course_id": match.group(1) if match else value,
                "title": match.group(2) if match else value,
            }
    return metadata


def _video_inventory() -> tuple[dict[str, Path], dict[str, list[Path]], list[Path]]:
    by_stem: dict[str, Path] = {}
    by_id: dict[str, list[Path]] = {}
    videos: list[Path] = []
    for dirname in COURSE_DIRS:
        directory = COURSE_ROOT / dirname
        if not directory.is_dir():
            raise FileNotFoundError(f"allowed course directory missing: {directory}")
        for path in sorted(directory.glob("*.mp4"), key=lambda item: item.name):
            resolved = path.resolve()
            if not resolved.is_relative_to(COURSE_ROOT.resolve()):
                raise ValueError(f"course escaped allowed root: {resolved}")
            if path.stem in by_stem:
                raise ValueError(f"duplicate course stem in allowed source: {path.stem}")
            by_stem[path.stem] = path
            course_id = path.stem.split(" ", 1)[0]
            by_id.setdefault(course_id, []).append(path)
            videos.append(path)
    return by_stem, by_id, videos


def _resolve_video(
    key: str,
    item: dict[str, Any],
    by_stem: dict[str, Path],
    by_id: dict[str, list[Path]],
) -> Path:
    raw_files = item.get("recommended_video_files") or item.get("video_files") or []
    if isinstance(raw_files, (str, Path)):
        raw_files = [raw_files]
    for raw in raw_files:
        path = Path(str(raw))
        if path.is_file() and path.resolve().is_relative_to(COURSE_ROOT.resolve()):
            return path
    if key in by_stem:
        return by_stem[key]
    filename = str(item.get("file") or "")
    if filename:
        matches = [path for path in by_stem.values() if path.name == filename]
        if len(matches) == 1:
            return matches[0]
    course_id = str(item.get("course_id") or item.get("original_course_id") or "")
    title = str(item.get("title") or "")
    candidates = list(by_id.get(course_id, []))
    exact = [path for path in candidates if path.stem == f"{course_id} {title}".strip()]
    if len(exact) == 1:
        return exact[0]
    titled = [path for path in candidates if title and title in path.stem]
    if len(titled) == 1:
        return titled[0]
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError(f"course key does not resolve uniquely: {key}; candidates={[p.name for p in candidates]}")


def build_course_catalog(
    manifests: dict[int, dict[str, Any]],
    *,
    verify_hashes: bool = True,
) -> dict[str, Any]:
    metadata: dict[str, dict[str, Any]] = {}
    used_keys: set[str] = set()
    for chapter, manifest in manifests.items():
        metadata.update(_chapter_course_metadata(chapter, manifest))
        for section in manifest.get("sections", []):
            used_keys.update(str(key) for key in section.get("required_course_keys", []))
            used_keys.update(str(key) for key in section.get("support_course_keys", []))
            for cycle in section.get("learning_cycles", []):
                for field in ("course_keys", "prerequisite_course_keys", "optional_course_keys"):
                    used_keys.update(str(key) for key in cycle.get(field, []))

    missing_course_directories = [name for name in COURSE_DIRS if not (COURSE_ROOT / name).is_dir()]
    frozen_fallback = bool(verify_hashes and missing_course_directories)
    if frozen_fallback:
        verify_hashes = False

    if not verify_hashes:
        frozen_path = ROOT / "data" / "all_chapters_course_catalog.json"
        frozen = load_json(frozen_path)
        frozen_by_key = {str(row["course_key"]): row for row in frozen.get("courses", [])}
        declared_keys = set(metadata)
        if not used_keys.issubset(declared_keys):
            raise ValueError(f"course keys missing from manifest metadata: {sorted(used_keys - declared_keys)}")
        rows = []
        for key in sorted(declared_keys):
            item = metadata[key]
            existing = frozen_by_key.get(key)
            course_id = str(item.get("course_id") or item.get("original_course_id") or key)
            title = str(item.get("title") or key)
            transcript = TRANSCRIPT_ROOT / f"{course_id} {title}.json"
            if existing:
                transcript = TRANSCRIPT_ROOT / Path(str(existing.get("transcript_file") or transcript.name)).name
            if not transcript.is_file():
                raise FileNotFoundError(f"frozen course transcript missing: {key}: {transcript}")
            transcript_data = load_json(transcript)
            sentences = transcript_data.get("sentences")
            rows.append({
                **(existing or {}),
                "course_key": key,
                "course_id": course_id,
                "title": title,
                "video_file": Path(str((existing or {}).get("video_file") or f"{course_id} {title}.mp4")).name,
                "video_sha256": str(transcript_data.get("source_video_sha256") or (existing or {}).get("video_sha256") or item.get("sha256") or ""),
                "transcript_file": f"data/course_transcripts/{transcript.name}",
                "transcript_sha256": sha256_file(transcript),
                "transcript_text_sha256": hashlib.sha256(str(transcript_data.get("full_text") or "").encode("utf-8")).hexdigest(),
                "duration_s": transcript_data.get("duration_s"),
                "sentence_count": len(sentences) if isinstance(sentences, list) else 0,
                "timestamp_status": "available" if isinstance(sentences, list) and sentences else "not_available_legacy_full_text",
                "source_rule": "frozen transcript catalog; source video hash retained",
            })
        return {
            **frozen,
            "status": "passed_frozen_video_hashes",
            "course_count": len(rows),
            "used_course_count": len(used_keys),
            "courses": rows,
            "frozen_catalog_source": str(frozen_path.relative_to(ROOT)).replace("\\", "/"),
            "frozen_fallback": frozen_fallback,
            "missing_course_directories": missing_course_directories,
            "allowed_course_directories": list(COURSE_DIRS),
            "source_rule": "repository transcripts plus frozen source-video hashes when the original course directory is unavailable",
        }

    by_stem, by_id, inventory = _video_inventory()

    rows: list[dict[str, Any]] = []
    for key in sorted(used_keys):
        item = metadata.get(key, {"course_key": key})
        video = _resolve_video(key, item, by_stem, by_id)
        transcript = TRANSCRIPT_ROOT / f"{video.stem}.json"
        if not transcript.is_file():
            raise FileNotFoundError(f"course transcript missing: {transcript}")
        transcript_data = load_json(transcript)
        if len(str(transcript_data.get("full_text") or "")) < 100:
            raise ValueError(f"course transcript too short: {transcript}")
        sentences = transcript_data.get("sentences")
        sentence_count = len(sentences) if isinstance(sentences, list) else 0
        video_sha = sha256_file(video) if verify_hashes else str(
            transcript_data.get("source_video_sha256") or item.get("sha256") or ""
        )
        if verify_hashes and transcript_data.get("source_video_sha256") != video_sha:
            raise ValueError(f"course transcript video hash mismatch: {video}")
        declared_sha = item.get("sha256")
        if verify_hashes and declared_sha and declared_sha != video_sha:
            raise ValueError(f"manifest video hash mismatch: {video}")
        rows.append(
            {
                "course_key": key,
                "course_id": item.get("course_id") or item.get("original_course_id") or video.stem.split(" ", 1)[0],
                "title": item.get("title") or video.stem.split(" ", 1)[-1],
                "video_file": str(video),
                "video_sha256": video_sha,
                "transcript_file": str(transcript),
                "transcript_sha256": sha256_file(transcript),
                "transcript_text_sha256": hashlib.sha256(
                    str(transcript_data["full_text"]).encode("utf-8")
                ).hexdigest(),
                "duration_s": transcript_data.get("duration_s"),
                "sentence_count": sentence_count,
                "timestamp_status": (
                    "available"
                    if sentence_count
                    else "not_available_legacy_full_text"
                ),
                "source_rule": "configured YBT_COURSE_ROOT only",
            }
        )
    resolved_stems = {Path(row["video_file"]).stem for row in rows}
    return {
        "schema_version": 1,
        "status": "passed",
        "allowed_course_directories": list(COURSE_DIRS),
        "course_count": len(rows),
        "available_video_count": len(inventory),
        "unreferenced_allowed_videos": [
            str(path) for path in inventory if path.stem not in resolved_stems
        ],
        "courses": rows,
        "pollution_excluded": ["老人版课程", "8.5g", "数学摄像头"],
    }


def _sidecar_score(item: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(item.get("status") == "passed" and item.get("confidence") in {"E1", "E2"}),
        int(bool(item.get("structured") or item.get("vision"))),
        int(bool(item.get("source_provenance"))),
    )


def load_visual_results() -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for path in SIDECAR_PATHS:
        if not path.is_file():
            continue
        for item in load_json(path).get("results", []):
            key = (str(item.get("question_hint") or ""), str(item.get("image") or ""))
            if not key[0]:
                continue
            previous = merged.get(key)
            if previous is None or _sidecar_score(item) >= _sidecar_score(previous):
                merged[key] = item
    return list(merged.values())


def _visual_inventory(section_id: str, packet: dict[str, Any], learning: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    collections = (
        ("abc_exercise", packet.get("questions", [])),
        ("worked_example", learning.get("worked_examples", [])),
        ("direct_variant", learning.get("direct_variants", [])),
    )
    for kind, items in collections:
        for item in items:
            if not item.get("image_refs") or item.get("visual_status") == "VISION_VERIFIED":
                continue
            hint = (
                f"{section_id}-{item.get('group')}{item.get('number')}"
                if kind == "abc_exercise"
                else item.get("vision_hint")
            )
            for image in item.get("image_refs", []):
                rows.append(
                    {
                        "section": section_id,
                        "kind": kind,
                        "item_id": item.get("qid") or item.get("item_id"),
                        "label": item.get("label") or f"{item.get('group')}{item.get('number')}",
                        "question_hint": hint,
                        "question_text": item.get("question_text"),
                        "image": image.get("path"),
                        "image_ref": image.get("ref"),
                        "image_exists": image.get("exists"),
                        "source_docs": item.get("source_docs")
                        or [item.get("source_anchor", {}).get("ocr_doc")],
                        "visual_status": item.get("visual_status"),
                    }
                )
    return rows


def build_all(
    selected_chapters: list[int],
    *,
    verify_course_hashes: bool = True,
    use_visual_sidecars: bool = True,
) -> dict[str, Any]:
    manifests = {
        chapter: load_json(Path(CHAPTERS[chapter]["manifest"]))
        for chapter in selected_chapters
    }
    expected = manifest_totals(manifests)
    if selected_chapters == [1, 2, 3, 4, 5]:
        required = {
            "sections": 38,
            "worked_examples": 379,
            "direct_variants": 284,
            "abc_exercises": 546,
            "total_numbered_learning_items": 1209,
        }
        for key, value in required.items():
            if expected[key] != value:
                raise ValueError(f"all-chapter manifest total drift: {key}={expected[key]} != {value}")

    course_catalog = build_course_catalog(manifests, verify_hashes=verify_course_hashes)
    save_json(ROOT / "data" / "all_chapters_course_catalog.json", course_catalog)
    visual_results = load_visual_results() if use_visual_sidecars else []
    section_rows: list[dict[str, Any]] = []
    visual_rows: list[dict[str, Any]] = []
    actual = {
        "worked_examples": 0,
        "direct_variants": 0,
        "abc_exercises": 0,
        "total_numbered_learning_items": 0,
    }

    for chapter in selected_chapters:
        manifest = manifests[chapter]
        builder = PacketBuilder(
            ocr_root=Path(CHAPTERS[chapter]["ocr_root"]),
            output_root=PACKET_ROOT,
        )
        answer_roots = (manifest.get("source_evidence") or {}).get("answer_ocr_roots") or {}
        for section in manifest.get("sections", []):
            section_id = str(section["id"])
            combined_sidecar = {
                "known_visual_recoveries": manifest.get("known_visual_recoveries", []),
                "derived_question_corrections": manifest.get("derived_question_corrections", []),
                "results": [
                    item for item in visual_results if item.get("section") == section_id
                ],
            }
            packet = builder.build_section(
                section,
                visual_sidecar=combined_sidecar,
                answer_root=answer_roots.get(section_id),
            )
            folder = PACKET_ROOT / section_folder(section_id)
            learning_path = folder / "learning_packet.json"
            learning = load_json(learning_path)
            counts = learning.get("counts") or {}
            declared = section.get("learning_item_counts") or {}
            for key in ("worked_examples", "direct_variants", "abc_exercises"):
                if int(counts.get(key, -1)) != int(declared.get(key, -2)):
                    raise ValueError(
                        f"{section_id} count mismatch: {key}={counts.get(key)} != {declared.get(key)}"
                    )
                actual[key] += int(counts[key])
            if int(counts.get("total_numbered_learning_items", -1)) != int(declared.get("total", -2)):
                raise ValueError(
                    f"{section_id} total mismatch: {counts.get('total_numbered_learning_items')} "
                    f"!= {declared.get('total')}"
                )
            actual["total_numbered_learning_items"] += int(counts["total_numbered_learning_items"])
            visual_rows.extend(_visual_inventory(section_id, packet, learning))
            section_rows.append(
                {
                    "chapter": chapter,
                    "section": section_id,
                    "label": section.get("label"),
                    "packet_status": packet.get("status"),
                    "learning_status": learning.get("status"),
                    "counts": counts,
                    "packet_unresolved": packet.get("unresolved", []),
                    "learning_unresolved": learning.get("unresolved", []),
                    "packet_sha256": sha256_file(folder / "packet.json"),
                    "learning_packet_sha256": sha256_file(learning_path),
                }
            )

    if actual != {key: expected[key] for key in actual}:
        raise ValueError(f"all-chapter generated total mismatch: actual={actual}, expected={expected}")
    inventory = {
        "schema_version": 1,
        "status": "passed" if not visual_rows else "blocked",
        "item_image_count": len(visual_rows),
        "unique_image_count": len({row["image"] for row in visual_rows}),
        "missing_image_count": sum(not row["image_exists"] for row in visual_rows),
        "items": visual_rows,
    }
    save_json(REPORT_ROOT / "visual-inventory-current.json", inventory)
    all_verified = all(
        row["packet_status"] == "VERIFIED" and row["learning_status"] == "VERIFIED"
        for row in section_rows
    )
    report = {
        "schema_version": 1,
        "build_id": "YBT-ALL-" + stable_id(section_rows, course_catalog, length=20),
        "status": "passed" if all_verified and course_catalog["status"] == "passed" else "in_progress",
        "chapters": selected_chapters,
        "expected": expected,
        "actual": actual,
        "course_catalog": {
            "path": "data/all_chapters_course_catalog.json",
            "status": course_catalog["status"],
            "course_count": course_catalog["course_count"],
        },
        "visual_inventory": {
            "path": "reports/all_chapters/visual-inventory-current.json",
            "status": inventory["status"],
            "item_image_count": inventory["item_image_count"],
            "unique_image_count": inventory["unique_image_count"],
            "missing_image_count": inventory["missing_image_count"],
        },
        "visual_source_mode": "current_sidecars" if use_visual_sidecars else "ignored_for_source_inventory",
        "sections": section_rows,
        "simulation_status": "not_run",
        "human_acceptance": "not_run",
        "cold_24h_retest": "not_run",
    }
    save_json(REPORT_ROOT / "packet-build-current.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", choices=["all", "1", "2", "3", "4", "5"], default="all")
    parser.add_argument("--skip-course-hash", action="store_true")
    parser.add_argument(
        "--ignore-visual-sidecars",
        action="store_true",
        help="Build a complete question-image source inventory without consuming existing sidecars.",
    )
    args = parser.parse_args()
    selected = [1, 2, 3, 4, 5] if args.chapter == "all" else [int(args.chapter)]
    report = build_all(
        selected,
        verify_course_hashes=not args.skip_course_hash,
        use_visual_sidecars=not args.ignore_visual_sidecars,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"passed", "in_progress"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
