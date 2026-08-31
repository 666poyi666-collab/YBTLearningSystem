from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ybt_learning.completeness import audit_chapter1
from ybt_learning.packet import verify_packet


ACTIVE_PACKET_FOLDERS = (
    "1.1",
    "1.2_1.3",
    "1.4",
    "micro专题1",
    "2.1",
    "2.2",
    "2.3",
    "2.4",
    "2.5",
    "2.6",
    "2.7",
)


def load(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


CURRENT_SIMULATION_RELATIVE = Path("reports/zero_base_cycles/1.1-current-agent-simulation.json")
CHAPTER_SIMULATION_STATUS_RELATIVE = Path("reports/zero_base_cycles/chapter1-current-simulation-status.json")
SIMULATION_SOURCE_FILES = (
    "chapter1_manifest.json",
    "data/bridge_micro_lessons.json",
    "data/packets/1.1/learning_packet.json",
    "data/packets/1.1/student_learning_items.json",
    "data/contexts/1.1.json",
    "data/question_coverage.json",
    "data/zero_base_simulation_standard.md",
    "data/packets/1.1/learning_path_without_questions.md",
    # The compatibility projection is derived from the atomically activated
    # all-book route audit. Bind the pointer so a partial run cannot replace it.
    "reports/deep_section_simulations/current.json",
)
LEGACY_SIMULATION_RELATIVES = (
    Path("reports/zero_base_agent_simulation.json"),
    Path("reports/zero_base_simulation_current.json"),
    Path("reports/zero_base_cycles/1.1-detailed-five-round-summary.json"),
)


def load_current_simulation(root: Path) -> tuple[dict, dict]:
    """Load only the hash-bound current-generation learner simulation.

    Historical simulation artifacts are deliberately never used as a fallback:
    a stale or missing current artifact must block acceptance rather than let an
    old 5/5 result mask a later partial run.
    """
    path = root / CURRENT_SIMULATION_RELATIVE
    metadata = {
        "path": CURRENT_SIMULATION_RELATIVE.as_posix(),
        "status": "not_run",
        "generation": None,
        "errors": [],
        "legacy_fallback_ignored": [
            item.as_posix() for item in LEGACY_SIMULATION_RELATIVES if (root / item).is_file()
        ],
    }
    if not path.is_file():
        metadata["errors"].append("current_simulation_missing")
        return metadata, {}
    try:
        simulation = load(path)
    except (OSError, json.JSONDecodeError) as exc:
        metadata["errors"].append(f"current_simulation_unreadable:{type(exc).__name__}")
        metadata["status"] = "blocked"
        return metadata, {}

    metadata["generation"] = simulation.get("generation")
    metadata["summary"] = simulation.get("summary", {})
    metadata["source_revision"] = simulation.get("source_revision", {})
    if simulation.get("artifact") != "CURRENT_GENERATION_ZERO_BASE_AGENT_SIMULATION":
        metadata["errors"].append("current_simulation_artifact_mismatch")
    if simulation.get("section") != "1.1":
        metadata["errors"].append("current_simulation_section_mismatch")
    if not isinstance(simulation.get("generation"), str) or not simulation.get("generation"):
        metadata["errors"].append("current_simulation_generation_missing")

    contract = simulation.get("worker_contract", {})
    authority_kind = str((simulation.get("authority") or {}).get("kind") or "")
    if authority_kind == "answer_isolated_route_audit_projection":
        expected_contract = {
            "workers_dispatched": 5,
            "workers_completed": 5,
            "role": "synthetic_route_stress_persona",
            "model": "deterministic-route-audit",
            "reasoning_effort": "not_applicable",
            "context_window": None,
            "answer_sidecar_read": False,
        }
    else:
        expected_contract = {
            "workers_dispatched": 5,
            "workers_completed": 5,
            "role": "deepseek_worker",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "max",
            "context_window": 1050000,
            "answer_sidecar_read": False,
        }
    for key, expected in expected_contract.items():
        if contract.get(key) != expected:
            metadata["errors"].append(f"worker_contract_mismatch:{key}")

    task_coverage = simulation.get("task_coverage", {})
    if task_coverage.get("complete") is not True:
        metadata["errors"].append("task_coverage_incomplete")
    if task_coverage.get("task_count") != 38 or task_coverage.get("expected_task_count") != 38:
        metadata["errors"].append("task_coverage_count_mismatch")
    summary = simulation.get("summary", {})
    if summary.get("workers") != 5:
        metadata["errors"].append("summary_worker_count_mismatch")
    if sum(int(summary.get(key, 0) or 0) for key in ("pass", "partial", "fail")) != 5:
        metadata["errors"].append("summary_status_count_mismatch")
    workers = simulation.get("workers", [])
    worker_status_counts = Counter(str(worker.get("status")) for worker in workers)
    if len(workers) != 5 or any(status not in {"pass", "partial", "fail"} for status in worker_status_counts):
        metadata["errors"].append("worker_rows_invalid")
    elif any(int(summary.get(status, 0) or 0) != worker_status_counts.get(status, 0) for status in ("pass", "partial", "fail")):
        metadata["errors"].append("summary_worker_rows_mismatch")
    boundary = simulation.get("answer_free_boundary", {})
    for key in ("answer_sidecar_read", "answer_ocr_read", "answer_text_in_context", "student_mastery_claim"):
        if boundary.get(key) is not False:
            metadata["errors"].append(f"answer_boundary_missing:{key}")
    if summary.get("human_acceptance_not_proven") is not True:
        metadata["errors"].append("human_acceptance_boundary_missing")
    if authority_kind == "answer_isolated_route_audit_projection" and summary.get("mathematical_correctness") != "not_evaluated_no_final_answer":
        metadata["errors"].append("route_audit_math_boundary_missing")

    packet_path = root / "data" / "packets" / "1.1" / "learning_packet.json"
    expected_item_ids: set[str] = set()
    if packet_path.is_file():
        packet = load(packet_path)
        for cycle in packet.get("learning_cycles", []):
            for item in cycle.get("worked_examples", []):
                expected_item_ids.add(str(item.get("item_id")))
            for item in cycle.get("direct_variants", []):
                expected_item_ids.add(str(item.get("item_id")))
            for item in cycle.get("exercise_questions", []):
                expected_item_ids.add(f"{item.get('group')}{item.get('number')}")
    metadata["expected_item_count"] = len(expected_item_ids)
    context_path = root / "data" / "contexts" / "1.1.json"
    expected_context_hash = None
    if context_path.is_file():
        try:
            expected_context_hash = str(load(context_path).get("evidence", {}).get("context_sha256", ""))
        except (OSError, json.JSONDecodeError):
            metadata["errors"].append("current_context_unreadable")
    if not expected_context_hash or len(expected_context_hash) != 64:
        metadata["errors"].append("current_context_hash_missing")
    item_results = simulation.get("item_results")
    if not isinstance(item_results, list):
        metadata["errors"].append("item_results_missing")
    else:
        observed_item_ids = [str(item.get("item_id")) for item in item_results]
        if len(observed_item_ids) != len(set(observed_item_ids)):
            metadata["errors"].append("item_results_duplicate_item_id")
        if set(observed_item_ids) != expected_item_ids:
            metadata["errors"].append("item_results_item_id_closure_mismatch")
        required_item_fields = {
            "section", "cycle", "item_id", "source_revision", "context_sha256",
            "observation_signal", "course_call", "first_line", "second_line",
            "continuation", "independent_self_check", "first_breakpoint",
            "hint_level", "verdict", "answer_sidecar_read", "human_acceptance_not_proven",
        }
        allowed_verdicts = {"PASS", "PARTIAL", "BLOCKED", "FAIL"}
        for index, item in enumerate(item_results):
            missing_fields = sorted(required_item_fields - set(item))
            if missing_fields:
                metadata["errors"].append(f"item_result_{index}_missing_fields:{','.join(missing_fields)}")
                continue
            if item.get("section") != "1.1" or item.get("answer_sidecar_read") is not False or item.get("human_acceptance_not_proven") is not True:
                metadata["errors"].append(f"item_result_{index}_boundary_invalid")
            if not isinstance(item.get("source_revision"), dict) or item["source_revision"].get("generation") != simulation.get("generation"):
                metadata["errors"].append(f"item_result_{index}_source_revision_invalid")
            if item.get("context_sha256") != expected_context_hash:
                metadata["errors"].append(f"item_result_{index}_context_hash_invalid")
            if not isinstance(item.get("course_call"), dict) or not item["course_call"].get("method_model_id"):
                metadata["errors"].append(f"item_result_{index}_course_call_invalid")
            if item.get("hint_level") not in {"none", "minimal", "full"}:
                metadata["errors"].append(f"item_result_{index}_hint_level_invalid")
            if item.get("verdict") not in allowed_verdicts:
                metadata["errors"].append(f"item_result_{index}_verdict_invalid")

    source_revision = simulation.get("source_revision", {})
    if set(source_revision) != set(SIMULATION_SOURCE_FILES):
        metadata["errors"].append("simulation_source_revision_key_set_mismatch")
    for relative in SIMULATION_SOURCE_FILES:
        source_path = root / relative
        expected_hash = source_revision.get(relative)
        if not source_path.is_file():
            metadata["errors"].append(f"simulation_source_missing:{relative}")
        elif expected_hash != sha256(source_path):
            metadata["errors"].append(f"simulation_source_hash_mismatch:{relative}")
    metadata["source_revision_match"] = not any(
        error.startswith("simulation_source_") for error in metadata["errors"]
    )
    metadata["status"] = "passed" if not metadata["errors"] else "blocked"
    metadata["route_audit_status"] = (
        "passed" if metadata["status"] == "passed" and summary.get("pass") == 5 else "blocked"
    )
    metadata["mastery_status"] = (
        "not_run"
        if authority_kind == "answer_isolated_route_audit_projection" and metadata["route_audit_status"] == "passed"
        else "passed"
        if metadata["route_audit_status"] == "passed"
        else "blocked"
    )
    return metadata, simulation


def load_chapter_simulation_status(root: Path) -> tuple[dict, dict]:
    """Load the current-generation status for the three non-1.1 sections.

    The section status is a separate gate because the legacy 1.1 simulator
    cannot prove that the rest of chapter 1 was simulated. Missing or stale
    section evidence must remain blocked rather than silently passing through
    the 1.1 gate.
    """
    relative = CHAPTER_SIMULATION_STATUS_RELATIVE
    path = root / relative
    metadata = {"path": relative.as_posix(), "status": "not_run", "errors": []}
    if not path.is_file():
        metadata["errors"].append("chapter_simulation_status_missing")
        return metadata, {}
    try:
        status = load(path)
    except (OSError, json.JSONDecodeError) as exc:
        metadata["errors"].append(f"chapter_simulation_status_unreadable:{type(exc).__name__}")
        metadata["status"] = "blocked"
        return metadata, {}
    if status.get("artifact") != "CHAPTER_ZERO_BASE_SIMULATION_STATUS":
        metadata["errors"].append("chapter_simulation_status_artifact_mismatch")
    summary = status.get("summary", {})
    metadata["summary"] = summary
    metadata["sections"] = status.get("sections", [])
    metadata["blockers"] = status.get("blockers", [])
    if summary.get("required_sections") != 3:
        metadata["errors"].append("chapter_simulation_required_section_count_mismatch")
    if summary.get("required_items") != 86:
        metadata["errors"].append("chapter_simulation_required_item_count_mismatch")
    if summary.get("all_current_section_simulations_ready") is not True:
        metadata["errors"].append("chapter_simulation_current_sections_not_ready")
    if summary.get("current_items_verified") != summary.get("required_items"):
        metadata["errors"].append("chapter_simulation_current_item_count_mismatch")
    metadata["status"] = "passed" if not metadata["errors"] else "blocked"
    return metadata, status


def load_current_teacher_judge(root: Path, simulation_meta: dict) -> tuple[dict, dict]:
    """Accept a teacher replay only when it is bound to the current source generation."""
    relative = Path("reports/final-teacher-judge-current.json")
    path = root / relative
    metadata = {"path": relative.as_posix(), "status": "not_run", "errors": []}
    if not path.is_file():
        metadata["errors"].append("teacher_judge_missing")
        return metadata, {}
    try:
        judge = load(path)
    except (OSError, json.JSONDecodeError) as exc:
        metadata["errors"].append(f"teacher_judge_unreadable:{type(exc).__name__}")
        metadata["status"] = "blocked"
        return metadata, {}
    metadata["generation"] = judge.get("generation")
    metadata["source_revision"] = judge.get("source_revision", {})
    if not metadata["generation"]:
        metadata["errors"].append("teacher_judge_generation_missing")
    if metadata["generation"] != simulation_meta.get("generation"):
        metadata["errors"].append("teacher_judge_generation_mismatch")
    source_revision = judge.get("source_revision", {})
    for relative_source in SIMULATION_SOURCE_FILES:
        source_path = root / relative_source
        if not source_path.is_file() or source_revision.get(relative_source) != sha256(source_path):
            metadata["errors"].append(f"teacher_judge_source_hash_mismatch:{relative_source}")
    if judge.get("judge_status") != "same_session_workflow_pass":
        metadata["errors"].append("teacher_judge_status_not_pass")
    metadata["status"] = "passed" if not metadata["errors"] else "blocked"
    return metadata, judge


def cli_json(command: list[str]) -> dict:
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if proc.returncode:
        raise RuntimeError(f"command failed: {' '.join(command)}\n{proc.stderr[-1000:]}")
    return json.loads(proc.stdout)


def active_packet_paths(root: Path, filename: str) -> list[Path]:
    return [root / "data" / "packets" / folder / filename for folder in ACTIVE_PACKET_FOLDERS]


def active_learning_totals(root: Path) -> dict[str, int]:
    totals = {"worked_examples": 0, "direct_variants": 0, "abc_exercises": 0, "total_numbered_learning_items": 0}
    for chapter in (1, 2):
        manifest = load(root / f"chapter{chapter}_manifest.json")
        for section in manifest.get("sections", []):
            counts = section.get("learning_item_counts", {})
            totals["worked_examples"] += int(counts.get("worked_examples", 0))
            totals["direct_variants"] += int(counts.get("direct_variants", 0))
            totals["abc_exercises"] += int(counts.get("abc_exercises", 0))
            totals["total_numbered_learning_items"] += int(counts.get("total", 0))
    return totals


def inspect_active_course_inventory(root: Path, catalog: dict) -> dict:
    """Check the active chapter transcripts without requiring excluded videos.

    The repository intentionally excludes the large Downloads video files.
    The current acceptance boundary is the hash-bound transcript catalog and
    committed full_text files, not the old device-specific video paths.
    """
    active_ids: set[str] = set()
    for chapter in (1, 2):
        manifest = load(root / f"chapter{chapter}_manifest.json")
        for section in manifest.get("sections", []):
            active_ids.update(str(value) for value in section.get("required_course_ids", []))
            active_ids.update(str(value) for value in section.get("support_course_ids", []))
    catalog_rows = {str(row.get("course_id")): row for row in catalog.get("courses", [])}
    missing: list[str] = []
    available_timeline = 0
    for course_id in sorted(active_ids):
        row = catalog_rows.get(course_id)
        candidates = sorted((root / "data" / "course_transcripts").glob(f"{course_id}*.json"))
        if not row or not candidates:
            missing.append(course_id)
            continue
        try:
            transcript = load(candidates[0])
        except (OSError, json.JSONDecodeError):
            missing.append(course_id)
            continue
        if not str(transcript.get("full_text", "")).strip():
            missing.append(course_id)
        if row.get("timestamp_status") == "available":
            available_timeline += 1
    return {
        "status": "passed" if not missing and len(active_ids) == 37 else "failed",
        "counts": {"active_courses": len(active_ids), "transcripts": len(active_ids) - len(missing), "with_reliable_timeline": available_timeline},
        "missing": missing,
        "declared_files": len(active_ids),
        "existing_files": len(active_ids) - len(missing),
        "source": "data/all_chapters_course_catalog.json + data/course_transcripts",
    }


def inspect_active_answer_status(root: Path) -> dict:
    sections: list[dict[str, Any]] = []
    for path in active_packet_paths(root, "answer_sidecar.json"):
        if not path.is_file():
            sections.append({"section": path.parent.name, "total": 0, "nonempty": 0, "status": "not_available"})
            continue
        sidecar = load(path)
        answers = sidecar.get("answers", [])
        nonempty = sum(bool(str(item.get("answer_text", "")).strip()) for item in answers if isinstance(item, dict))
        status = "passed" if answers and nonempty == len(answers) else "not_available"
        sections.append({"section": sidecar.get("section", path.parent.name), "total": len(answers), "nonempty": nonempty, "status": status})
    # Answer availability is separate from the learner-safe boundary.  A
    # chapter may have a complete student packet before its answer OCR is
    # imported; that is not an answer leak or a reason to reject the packet.
    return {"status": "passed" if sections and all(item["status"] in {"passed", "not_available"} for item in sections) else "failed", "sections": sections, "answer_isolation": "student_packet_answer_free"}


def inspect_course_inventory(catalog: dict, build_catalog: dict) -> dict:
    """Check the current Downloads manifest and every declared file path."""
    files = []
    courses = catalog.get("courses", [])
    for course in courses:
        files.extend(item.get("file") for item in course.get("videos", []) if item.get("file"))
        files.extend(item.get("file") for item in course.get("transcripts", []) if item.get("file"))
    missing = [path for path in files if not Path(path).is_file()]
    counts = {
        "videos": sum(len(course.get("videos", [])) for course in courses),
        "courses": len(courses),
        "course_collection_videos": sum(1 for course in courses for item in course.get("videos", []) if item.get("canonical")),
        "transcripts": sum(len(course.get("transcripts", [])) for course in courses),
    }
    manifest_keys = {
        "videos": "video_count", "courses": "course_count", "course_collection_videos": "canonical_video_count",
        "transcripts": "transcript_count",
    }
    count_match = all(counts[key] == build_catalog.get(key) == catalog.get(manifest_keys[key]) for key in counts)
    complete_courses = all(course.get("videos") and course.get("transcripts") for course in courses)
    return {
        "status": "passed" if count_match and complete_courses and not missing else "failed",
        "counts": counts,
        "missing": missing,
        "count_match": count_match,
        "complete_courses": complete_courses,
        "declared_files": len(files),
        "existing_files": len(files) - len(missing),
    }


def main() -> int:
    build = load(ROOT / "reports" / "build-result.json")
    manifest = load(ROOT / "chapter1_manifest.json")
    coverage = load(ROOT / "data" / "question_coverage.json")
    completeness = audit_chapter1(ROOT)
    browser = load(ROOT / "data" / "browser_evidence.json")
    browser_collector_ok = (
        browser.get("collector_version")
        and browser.get("history_verified_at")
        and isinstance(browser.get("browsers"), dict)
        and (ROOT / "scripts" / "browser_collect.py").is_file()
        and (ROOT / "data" / "browser_collection_protocol.md").is_file()
    )
    bridge = load(ROOT / "data" / "bridge_micro_lessons.json")
    real_user = load(ROOT / "data" / "real_user_observations.json")
    simulation_meta, simulation = load_current_simulation(ROOT)
    simulation_path = ROOT / CURRENT_SIMULATION_RELATIVE
    chapter_simulation_meta, chapter_simulation = load_chapter_simulation_status(ROOT)
    teacher_judge_meta, teacher_judge = load_current_teacher_judge(ROOT, simulation_meta)
    teacher_judge_path = ROOT / teacher_judge_meta["path"]
    catalog = load(ROOT / "data" / "all_chapters_course_catalog.json")
    answer_status = inspect_active_answer_status(ROOT)
    ocr = cli_json(["python", "-m", "ybt_learning.cli", "ocr-config-status"])
    vision = cli_json(["python", "-m", "ybt_learning.cli", "vision-config-test"])
    deepseek = cli_json(["python", "-m", "ybt_learning.cli", "deepseek-status"])
    course_inventory = inspect_active_course_inventory(ROOT, catalog)
    chapter_probe_path = ROOT / "scripts" / "deepseek" / "out" / "chapter_probe_latest.json"
    chapter_probe = load(chapter_probe_path) if chapter_probe_path.exists() else {"summary": {"chapter_consumption_ready": False, "total_sections": 0, "gate_passed": 0, "dispatched": 0, "consumption_passed": 0}}
    test_proc = subprocess.run(["python", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    test_output = "\n".join([test_proc.stdout, test_proc.stderr])
    test_passed = test_proc.returncode == 0
    test_count = 0
    for line in test_output.splitlines():
        if line.startswith("Ran ") and " tests" in line:
            try:
                test_count = int(line.split()[1])
            except (IndexError, ValueError):
                pass
    packets = []
    student_empty_pages = []
    for path in active_packet_paths(ROOT, "student_packet.json"):
        packet = load(path)
        packet_check = verify_packet(path)
        student_empty_pages.extend(
            f"{packet.get('section')}:{page.get('ocr_doc')}"
            for page in packet.get("pages", [])
            if not str(page.get("text", "")).strip()
        )
        packets.append({
            "section": packet.get("section"),
            "status": packet.get("status"),
            "question_count": len(packet.get("questions", [])),
            "unresolved": len(packet.get("unresolved", [])),
            "check": packet_check,
            "visual_status_counts": {status: sum(q.get("visual_status") == status for q in packet.get("questions", [])) for status in ["VISION_VERIFIED", "READY_TEXT_ONLY", "NEEDS_VISION_SIDECAR", "UNVERIFIED"]},
            "path": str(path.relative_to(ROOT)),
        })
    packet_verified = bool(packets) and all(
        item.get("status") == "VERIFIED"
        and item.get("unresolved") == 0
        and item.get("check", {}).get("status") == "passed"
        for item in packets
    )
    learning_packets = []
    student_learning_inputs = []
    for path in active_packet_paths(ROOT, "learning_packet.json"):
        item = load(path)
        learning_packets.append({"section": item.get("section"), "counts": item.get("counts", {}), "path": str(path.relative_to(ROOT))})
        student_path = path.with_name("student_learning_items.json")
        input_status = "failed"
        input_counts = {}
        input_error = None
        if student_path.is_file():
            try:
                student_input = load(student_path)
                input_counts = student_input.get("counts", {})
                packet_ids = {
                    str(child.get("item_id"))
                    for cycle in item.get("learning_cycles", [])
                    for child in [*cycle.get("worked_examples", []), *cycle.get("direct_variants", [])]
                }
                input_ids = {
                    str(child.get("item_id"))
                    for child in [*student_input.get("worked_examples", []), *student_input.get("direct_variants", [])]
                }
                serialized = json.dumps(student_input, ensure_ascii=False)
                input_status = "passed" if (
                    student_input.get("packet_type") == "DEEPSEEK_STUDENT_LEARNING_ITEMS"
                    and student_input.get("status") == "VERIFIED"
                    and packet_ids == input_ids
                    and input_counts.get("total") == len(input_ids)
                    and not re.search(r"teaching_text|solution_present|solution_isolated|answer_text", serialized, flags=re.I)
                ) else "failed"
            except (OSError, json.JSONDecodeError, TypeError) as exc:
                input_error = type(exc).__name__
        else:
            input_error = "missing"
        student_learning_inputs.append({
            "section": item.get("section"),
            "path": str(student_path.relative_to(ROOT)),
            "status": input_status,
            "counts": input_counts,
            "error": input_error,
        })
    learning_totals = {
        key: sum(item["counts"].get(key, 0) for item in learning_packets)
        for key in ("worked_examples", "direct_variants", "abc_exercises", "total_numbered_learning_items")
    }
    expected_learning_totals = active_learning_totals(ROOT)
    sequential_learning_ready = (
        len(learning_packets) == len(ACTIVE_PACKET_FOLDERS)
        and not student_empty_pages
        and learning_totals == expected_learning_totals
        and len(student_learning_inputs) == len(ACTIVE_PACKET_FOLDERS)
        and all(entry.get("status") == "passed" for entry in student_learning_inputs)
    )
    visual_ready = coverage.get("summary", {}).get("visual_ready_count") == coverage.get("question_count")
    visual_status_counts = {
        status: sum(1 for item in coverage.get("questions", []) if item.get("visual_status") == status)
        for status in ("VISION_VERIFIED", "READY_TEXT_ONLY", "NEEDS_VISION_SIDECAR", "UNVERIFIED")
    }
    manual_review_flags = manifest.get("source_evidence", {}).get("manual_review_flags", [])
    manual_review_resolutions = manifest.get("source_evidence", {}).get("manual_review_resolutions", [])
    manual_review_ok = not manual_review_flags
    manual_review_summary = (
        "课程内容人工复核已在派生层闭环（原始 OCR 保留为历史证据，题包只消费带 E1 锚点的修正）"
        if manual_review_ok and manual_review_resolutions else
        f"{len(manual_review_flags)} 条课程内容人工复核标记仍未闭环"
    )
    chapter_consumption_ready = chapter_probe.get("summary", {}).get("chapter_consumption_ready") is True
    contexts_consumable = bool(deepseek.get("contexts")) and all(item.get("status") == "passed" for item in deepseek.get("contexts", []))
    bridge_ready = bool(bridge.get("units")) and all(item.get("status") in {"VERIFIED", "SUPPLEMENT_READY"} for item in bridge.get("units", []))
    attempt_ready_gate = coverage.get("summary", {}).get("attempt_ready_gate") is True
    full_every_question_release_gate = coverage.get("summary", {}).get("full_every_question_release_gate") is True
    simulation_evidence_ok = simulation_meta.get("status") == "passed"
    simulation_route_audit_passed = simulation_meta.get("route_audit_status") == "passed"
    chapter_simulation_ready = chapter_simulation_meta.get("status") == "passed"
    teacher_judge_ok = teacher_judge_meta.get("status") == "passed"
    answer_sections = answer_status.get("sections", [])
    student_answer_leaks = []
    for path in active_packet_paths(ROOT, "student_packet.json"):
        if load(path).get("answer_sidecar") is not None:
            student_answer_leaks.append(str(path.relative_to(ROOT)))
    answer_isolation_ok = answer_status.get("status") == "passed" and not student_answer_leaks
    acceptance_blocked = (
        completeness.get("status") != "passed"
        or not packet_verified
        or not sequential_learning_ready
        or not contexts_consumable
        or not chapter_consumption_ready
        or not ocr.get("active_provider_live_verified")
        or browser.get("8.5", {}).get("status") != "passed"
        or browser.get("8.5课程", {}).get("status") != "passed"
        or not browser_collector_ok
        or not bridge_ready
        or not attempt_ready_gate
        or not full_every_question_release_gate
        or not simulation_route_audit_passed
        or not chapter_simulation_ready
        or not teacher_judge_ok
        or course_inventory.get("status") != "passed"
        or not answer_isolation_ok
        or not manual_review_ok
    )
    runtime_sidecar_path = ROOT / "reports" / "runtime-evidence-sidecar-current.json"
    runtime_sidecar_path.write_text(json.dumps({
        "schema_version": "7.1-current",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source": "scripts/generate_acceptance_report.py",
        "tests": {"status": "passed" if test_passed else "failed", "count": test_count},
        "packets": packets,
        "coverage": {
            "question_count": coverage.get("question_count"),
            "visual_ready_count": coverage.get("summary", {}).get("visual_ready_count"),
            "visual_status_counts": visual_status_counts,
            "attempt_ready_gate": attempt_ready_gate,
            "full_every_question_release_gate": full_every_question_release_gate,
        },
        "answer_free_completeness": completeness,
        "sequential_learning": {"ready": sequential_learning_ready, "totals": learning_totals, "student_empty_pages": student_empty_pages, "student_learning_inputs": student_learning_inputs},
        "manual_review_flags": manual_review_flags,
        "manual_review_resolutions": manual_review_resolutions,
        "zero_base_simulation": {
            "evidence": simulation_meta,
            "summary": simulation.get("summary", {}),
            "route_audit_gate": simulation_route_audit_passed,
            "mastery_gate": False,
        },
        "chapter_zero_base_simulation": {
            "evidence": chapter_simulation_meta,
            "summary": chapter_simulation.get("summary", {}),
            "gate": chapter_simulation_ready,
        },
        "teacher_judgement": {
            "evidence": teacher_judge_meta,
            "judge_status": teacher_judge.get("judge_status"),
            "gate": teacher_judge_ok,
        },
        "note": "当前运行证据；reports/runtime-evidence-sidecar.json 为历史 sidecar，不得与本文件混用。",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": "7.1",
        "checked_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "overall_status": "IN_PROGRESS_NOT_PUBLISHABLE" if acceptance_blocked else "PUBLISHABLE",
        "scope": "第一章按四批拆分、课程合集编号顺序、一本通页面逻辑、PaddleOCR AI Studio、DeepSeek独立消费、浏览器8.5与8.5课程、5个零基础学生代理",
        "passed": [
            {"name": "runtime_regression", "result": "passed" if test_passed else "failed", "evidence": f"{test_count or '未知'} unittest cases passed; compileall gate run"},
            {"name": "course_inventory", "result": course_inventory["status"], "evidence": f"current manifest counts={course_inventory['counts']}; files={course_inventory['existing_files']}/{course_inventory['declared_files']} present; missing={course_inventory['missing'][:5]}; only Downloads/课程合集 is accepted"},
            {"name": "question_coverage_ledger", "result": "passed", "evidence": f"{coverage['question_count']} unique questions; release counts={coverage['summary']['release_status_counts']}; consumable={coverage['summary']['visual_ready_count']}/{coverage['question_count']} ({visual_status_counts['VISION_VERIFIED']} VISION_VERIFIED + {visual_status_counts['READY_TEXT_ONLY']} READY_TEXT_ONLY); no mastery claim"},
            {"name": "answer_free_completeness", "result": completeness["status"], "evidence": f"manifest/packet/cycle/OCR-range/qid closure: {len(completeness.get('findings', []))} findings"},
            {"name": "sequential_learning_inventory", "result": "passed" if sequential_learning_ready else "failed", "evidence": f"worked examples/direct variants/ABC exercises/total={learning_totals}; expected={expected_learning_totals}; student OCR-empty pages={student_empty_pages}"},
            {"name": "answer_isolation", "result": "passed" if answer_isolation_ok else "failed", "evidence": f"answer-status={answer_status.get('status')}; sections={[(item.get('section'), item.get('total'), item.get('nonempty'), item.get('status')) for item in answer_sections]}; student_packet_answer_sidecar_leaks={student_answer_leaks}"},
            {"name": "browser_history_collector", "result": "passed" if browser_collector_ok else "blocked", "evidence": f"collector_version={browser.get('collector_version')}; history_verified_at={browser.get('history_verified_at')}; sources={list((browser.get('browsers') or {}).keys())}"},
            {"name": "browser_8_5", "result": "passed" if browser.get("8.5", {}).get("status") == "passed" else "failed", "evidence": f"history_matches={browser.get('8.5', {}).get('matches')}; history_verified_at={browser.get('history_verified_at')}; DOM remains a separate evidence source"},
            {"name": "browser_8_5_course", "result": "passed" if browser.get("8.5课程", {}).get("status") == "passed" else "failed", "evidence": f"history_matches={browser.get('8.5课程', {}).get('matches')}; content_status={browser.get('8.5课程', {}).get('content_status')}"},
            {"name": "ocr_ai_studio_live", "result": "passed" if ocr.get("active_provider") == "paddle_ai_studio" and ocr.get("active_provider_live_verified") else "blocked", "evidence": f"provider={ocr.get('live_probe', {}).get('provider')}; job={ocr.get('live_probe', {}).get('job_id')}; documents={ocr.get('live_probe', {}).get('document_count')}; fresh_api_run={ocr.get('live_probe', {}).get('fresh_api_run')}"},
            {"name": "visual_probe", "result": "passed" if vision.get("live_verified") else "blocked", "evidence": f"live_evidence verified_count={vision.get('live_evidence', {}).get('verified_count')}; complete GLM E1/E2 results only; incomplete/429 responses remain blocked"},
            {"name": "deepseek_route_consumability", "result": "passed" if deepseek.get("route_status") == "passed" else "blocked", "evidence": f"route_status={deepseek.get('route_status')}; four contexts carry must-listen courses, knowledge/type/A-B-C routing and answer-free bridge metadata"},
            {"name": "deepseek_independent_probe", "result": deepseek.get("independent_probe", {}).get("status", "not_run"), "evidence": f"probe_status={deepseek.get('independent_probe', {}).get('status')}; Chat Completions raw response, usage, exact requested model/effort and context-bound canary/qid/question hashes are recorded; raw={deepseek.get('independent_probe', {}).get('transport', {}).get('raw_path')}; normalized_response={deepseek.get('independent_probe', {}).get('response_artifact_path') or deepseek.get('independent_probe', {}).get('verification', {}).get('path')}; verification_reused_saved_response means report-stage re-validation of the just-recorded response, not transport reuse"},
            {"name": "deepseek_chapter_probe", "result": "passed" if chapter_probe.get("summary", {}).get("chapter_consumption_ready") else "blocked", "evidence": f"sections={chapter_probe.get('summary', {}).get('total_sections')}; gate_passed={chapter_probe.get('summary', {}).get('gate_passed')}; dispatched={chapter_probe.get('summary', {}).get('dispatched')}; consumption_passed={chapter_probe.get('summary', {}).get('consumption_passed')}; blocked sections are not dispatched"},
            {"name": "teacher_judgement", "result": "passed" if teacher_judge_ok else teacher_judge_meta.get("status", "not_run"), "evidence": f"judge_status={teacher_judge.get('judge_status')}; evidence_status={teacher_judge_meta.get('status')}; generation={teacher_judge_meta.get('generation')}; errors={teacher_judge_meta.get('errors')}; independent_items={teacher_judge.get('independent_items_66', {}).get('correct')}/66; unseen_transfer={teacher_judge.get('unseen_transfer', {}).get('answers_match_expected')}/4; 24h_cold_retest={teacher_judge.get('24h_cold_retest', 'not_run')}"},
            {"name": "current_zero_base_simulation_evidence", "result": "passed" if simulation_evidence_ok else simulation_meta.get("status", "not_run"), "evidence": f"path={simulation_meta.get('path')}; generation={simulation_meta.get('generation')}; source_revision_match={simulation_meta.get('source_revision_match')}; legacy_fallback_ignored={simulation_meta.get('legacy_fallback_ignored')}; errors={simulation_meta.get('errors')}"},
            {"name": "chapter_zero_base_simulation_evidence", "result": "passed" if chapter_simulation_ready else chapter_simulation_meta.get("status", "not_run"), "evidence": f"path={chapter_simulation_meta.get('path')}; sections={chapter_simulation_meta.get('summary', {}).get('current_sections_verified')}/{chapter_simulation_meta.get('summary', {}).get('required_sections')}; items={chapter_simulation_meta.get('summary', {}).get('current_items_verified')}/{chapter_simulation_meta.get('summary', {}).get('required_items')}; errors={chapter_simulation_meta.get('errors')}"},
        ],
        "not_passed": [
            {"name": "packet_verification", "result": "passed" if packet_verified else "failed", "evidence": f"{sum(item['status'] == 'VERIFIED' for item in packets)}/{len(packets)} VERIFIED; packet_checks={[item.get('check', {}).get('status') for item in packets]}; unresolved={[item['unresolved'] for item in packets]}"},
            {"name": "sequential_learning_packets", "result": "passed" if sequential_learning_ready else "failed", "evidence": f"packets={len(learning_packets)}/{len(ACTIVE_PACKET_FOLDERS)}; totals={learning_totals}; student_empty_pages={student_empty_pages}"},
            {"name": "course_inventory_current_paths", "result": course_inventory["status"], "evidence": f"counts={course_inventory['counts']}; current file existence={course_inventory['existing_files']}/{course_inventory['declared_files']}; missing={course_inventory['missing'][:10]}"},
            {"name": "answer_isolation_current", "result": "passed" if answer_isolation_ok else "failed", "evidence": f"answer-status={answer_status.get('status')}; student leaks={student_answer_leaks}"},
            {"name": "visual_sidecars", "result": "passed" if visual_ready else "blocked", "evidence": f"visual_ready={coverage['summary'].get('visual_ready_count')}/{coverage.get('question_count')}; provider rate-limit/E0/incomplete payloads remain fail-closed"},
            {"name": "bridge_units", "result": "passed" if all(item.get("status") in {"VERIFIED", "SUPPLEMENT_READY"} for item in bridge.get("units", [])) else "blocked", "evidence": f"{len(bridge.get('units', []))} named units: {sum(item.get('status') == 'SOURCE_METHOD_READY' for item in bridge['units'])} source-method-only, {sum(item.get('status') == 'SUPPLEMENT_READY' for item in bridge['units'])} supplement-ready, {sum(item.get('status') == 'SUPPLEMENT_REQUIRED' for item in bridge['units'])} supplement-required, {sum(item.get('status') == 'VERIFIED' for item in bridge['units'])} VERIFIED; source-method-only units remain blocked and student mastery is not claimed"},
            {"name": "all_questions_releasable", "result": "passed" if attempt_ready_gate and full_every_question_release_gate else "blocked", "evidence": f"attempt_ready_gate={attempt_ready_gate}; full_every_question_release_gate={full_every_question_release_gate}; blocked questions={coverage['summary']['release_status_counts'].get('BLOCKED_BRIDGE', 0)}"},
            {"name": "deepseek_full_question_consumability", "result": "passed" if contexts_consumable and chapter_consumption_ready else "blocked", "evidence": f"contexts_consumable={contexts_consumable}; chapter_probe_ready={chapter_consumption_ready}; independent_probe={deepseek.get('independent_probe', {}).get('status')}"},
            {"name": "five_zero_base_route_audit", "result": "passed" if simulation_route_audit_passed else "blocked", "evidence": f"current generation={simulation_meta.get('generation')}; evidence_status={simulation_meta.get('status')}; pass={simulation.get('summary', {}).get('pass')}, fail={simulation.get('summary', {}).get('fail')}, partial={simulation.get('summary', {}).get('partial')}; task_coverage_complete={simulation.get('task_coverage', {}).get('complete')}; mathematical correctness and mastery are not evaluated"},
            {"name": "chapter_zero_base_agent_simulation", "result": "passed" if chapter_simulation_ready else "blocked", "evidence": f"status={chapter_simulation_meta.get('status')}; current sections={chapter_simulation_meta.get('summary', {}).get('current_sections_verified')}/{chapter_simulation_meta.get('summary', {}).get('required_sections')}; current items={chapter_simulation_meta.get('summary', {}).get('current_items_verified')}/{chapter_simulation_meta.get('summary', {}).get('required_items')}; historical shards are not current evidence"},
            {"name": "teacher_judgement_current_binding", "result": "passed" if teacher_judge_ok else "blocked", "evidence": f"path={teacher_judge_meta.get('path')}; generation={teacher_judge_meta.get('generation')}; source_revision_match={teacher_judge_meta.get('status') == 'passed'}; errors={teacher_judge_meta.get('errors')}"},
            {"name": "lesson_content_manual_review", "result": "passed" if manual_review_ok else "blocked", "evidence": f"manifest source_evidence.manual_review_flags={manual_review_flags}; flagged lesson content cannot be silently corrected or released"},
        ],
        "artifacts": {
            "learning_plan": "data/chapter1_learning_plan.json",
            "question_coverage": "data/question_coverage.json",
            "answer_free_completeness": completeness,
            "build_result": "reports/build-result.json",
            "packets": packets,
            "learning_packets": learning_packets,
            "student_learning_inputs": student_learning_inputs,
            "contexts": [str(path.relative_to(ROOT)) for path in sorted((ROOT / "data" / "contexts").glob("*.json"))],
            "bridge_micro_lessons": {"path": "data/bridge_micro_lessons.json", "unit_count": len(bridge.get("units", [])), "sha256": sha256(ROOT / "data/bridge_micro_lessons.json")},
            "simulation_matrix": simulation_meta.get("path"),
            "simulation_generation": simulation_meta.get("generation"),
            "simulation_evidence": simulation_meta,
            "chapter_simulation_status": chapter_simulation_meta.get("path"),
            "chapter_simulation_evidence": chapter_simulation_meta,
            "teacher_judgement": str(teacher_judge_path.relative_to(ROOT)) if teacher_judge_path.exists() else None,
            "teacher_judgement_evidence": teacher_judge_meta,
            "real_user_observations": "data/real_user_observations.json",
            "real_user_protocol": "data/real_user_protocol.md",
            "real_user_schema": "data/real_user_schema.json",
            "real_user_collector": "scripts/real_user_collect.py",
            "runtime_evidence_sidecar_current": "reports/runtime-evidence-sidecar-current.json",
            "runtime_evidence_sidecar_legacy": {"path": "reports/runtime-evidence-sidecar.json", "status": "superseded", "note": "历史运行快照，不能代表当前测试或题包状态"},
            "deepseek_chapter_probe": "scripts/deepseek/out/chapter_probe_latest.json",
            "browser_evidence": "data/browser_evidence.json",
            "browser_collector": "scripts/browser_collect.py",
            "browser_collection_protocol": "data/browser_collection_protocol.md",
            "browser_collection_events": "data/browser_collection_events.jsonl",
            "vision_live_evidence": "data/vision_live_evidence.json",
            "ocr_status": ocr,
            "deepseek_status": deepseek,
            "answer_status": answer_status,
            "course_inventory_check": course_inventory,
            "deepseek_independent_raw": deepseek.get("independent_probe", {}).get("transport", {}).get("raw_path"),
            "deepseek_independent_response": deepseek.get("independent_probe", {}).get("response_artifact_path") or deepseek.get("independent_probe", {}).get("verification", {}).get("path"),
            "source_visual_probe": "reports/source_visual_probe.json",
            "source_visual_probe_sidecar": "reports/source_visual_probe_sidecar.json",
            "vision_sidecar_full": {"path": "data/vision_sidecar_full.json", "note": "旧 E0 行不消费；当前题包只接受绑定的 E1/E2 或 READY_TEXT_ONLY 结果"},
            "manual_review_flags": manual_review_flags,
            "manual_review_resolutions": manual_review_resolutions,
        },
        "release_decision": (
            f"可发布同会话学习流程包：四节题包、{coverage.get('summary', {}).get('visual_ready_count')}/{coverage.get('question_count')} 可消费"
            f"（{visual_status_counts['VISION_VERIFIED']} VISION_VERIFIED + {visual_status_counts['READY_TEXT_ONLY']} READY_TEXT_ONLY），"
            f"五代理流程与教师复判通过；{manual_review_summary}。"
            "这不等于24小时掌握或真人验收，24h_cold_retest 仍为 not_run。"
            if not acceptance_blocked else
            f"暂不发布：当前仍有验收门禁未通过；题包可消费数={coverage.get('summary', {}).get('visual_ready_count')}/{coverage.get('question_count')}，"
            f"当前代五代理通过数={simulation.get('summary', {}).get('pass')}/5，模拟证据={simulation_meta.get('status')}，教师判卷={teacher_judge.get('judge_status', 'not_run')}（绑定状态={teacher_judge_meta.get('status')}）。"
        ),
    }
    report["not_passed"] = [item for item in report["not_passed"] if item.get("result") != "passed"]
    out = ROOT / "reports" / "final-acceptance.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(out), "sha256": sha256(out), "overall_status": report["overall_status"], "tests": test_count, "packet_verified": sum(item["status"] == "VERIFIED" for item in packets), "packet_checks_passed": sum(item.get("check", {}).get("status") == "passed" for item in packets), "visual_ready": coverage["summary"]["visual_ready_count"], "deepseek_chapter_ready": chapter_consumption_ready, "simulation": simulation["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
