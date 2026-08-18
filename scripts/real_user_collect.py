#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一本通 v7 真实用户观察采集与验证 harness（只写 data/real_user* 与自身）。

职责：
1. 五名真实零基础用户逐人注册（participant_id 必须真人自选 + consent artifact）；
2. 先采集 baseline_check，再按节采集 course_listened / knowledge_point_study / example_solved /
   type_training / question_attempt / recap / cold_review / near_variant /
   section_complete 事件，事件按追加式 JSONL 落盘，artifact 复制并哈希；
3. verify 机器检查：must_listen 课程、逐知识点、逐题 A/B/C 顺序、视觉题当次
   图形证据、全节后 answer_free 复述、>=24h 冷复测、无答案泄漏、artifact 哈希和事件哈希链；
4. export 只从真实事件同步 data/real_user_observations.json；
5. self-test 在临时目录跑通全流程，绝不触碰 data/ 真实存储。

反伪造硬规则：没有真人 participant_id 与 consent artifact 不注册；record 必须
observed_by 等于已注册 participant_id；本程序没有任何生产模拟开关；代理轨迹
不得写入本存储。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA_VERSION = "7.3"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = Path("data") / "chapter1_learning_plan.json"
COVERAGE_REL = Path("data") / "question_coverage.json"
SCHEMA_REL = Path("data") / "real_user_schema.json"
CONTRACT_REL = Path("data") / "real_user_observations.json"
RECORDS_REL = Path("data") / "real_user_records"
SLOT_IDS = ["real-user-01", "real-user-02", "real-user-03", "real-user-04", "real-user-05"]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).astimezone()
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("invalid occurred_at %r (use ISO8601 like 2026-08-14T10:00:00+08:00)" % value) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_schema(root: Path) -> dict:
    data = load_json(root / SCHEMA_REL)
    if not data:
        raise SystemExit("real-user schema missing: %s" % (root / SCHEMA_REL))
    return data


def load_plan_index(root: Path) -> dict[str, dict]:
    data = load_json(root / PLAN_REL)
    if not data:
        raise SystemExit("learning plan missing; run build-chapter1 first")
    return {item["section"]: item for item in data["plan"]}


def required_sections(schema: dict, plan_index: dict[str, dict]) -> list[str]:
    """返回真实用户必须覆盖的章节，并保留 schema 声明顺序。"""
    declared = schema.get("rules", {}).get("required_sections")
    if not declared:
        return list(plan_index)
    return [section for section in declared if section in plan_index]


def load_coverage_index(root: Path) -> dict[tuple[str, str], dict]:
    data = load_json(root / COVERAGE_REL)
    if not data:
        raise SystemExit("question coverage missing")
    return {(q["section"], q["question_key"]): q for q in data.get("questions", [])}


def records_root(root: Path) -> Path:
    return root / RECORDS_REL


def slot_dir(root: Path, slot: str) -> Path:
    return records_root(root) / slot


def identity_path(root: Path, slot: str) -> Path:
    return slot_dir(root, slot) / "identity.json"


def events_path(root: Path, slot: str) -> Path:
    return slot_dir(root, slot) / "events.jsonl"


def artifacts_dir(root: Path, slot: str) -> Path:
    return slot_dir(root, slot) / "artifacts"


def load_identity(root: Path, slot: str) -> dict:
    data = load_json(identity_path(root, slot))
    if not data:
        raise ValueError("slot %s is not registered; run register first" % slot)
    return data


def read_events(root: Path, slot: str) -> list[dict]:
    path = events_path(root, slot)
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def append_event(root: Path, slot: str, event: dict) -> None:
    path = events_path(root, slot)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = read_events(root, slot)
    event["prev_event_hash"] = event_digest(previous[-1]) if previous else None
    event["event_hash"] = event_digest(event)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def event_digest(event: dict) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def event_artifact_required(kind: str, schema: dict) -> bool:
    return kind in set(schema.get("rules", {}).get("artifact_required_kinds", []))


def event_phase(kind: str) -> int:
    return {
        "baseline_check": 5,
        "course_listened": 10,
        # Knowledge-point notes and their right-side examples form one
        # teaching phase; users may alternate them point-by-point.
        "knowledge_point_study": 20,
        "example_solved": 20,
        "type_training": 40,
        "question_attempt": 50,
        "recap": 60,
        "cold_review": 70,
        "review": 70,
        "near_variant": 80,
        "section_complete": 90,
    }.get(kind, 999)


def copy_artifact(root: Path, slot: str, src: Path, prefix: str, kind: str) -> dict:
    if not src.is_file():
        raise ValueError("artifact file not found: %s" % src)
    dest_dir = artifacts_dir(root, slot)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / ("%s_%s_%s" % (prefix, kind, src.name))
    shutil.copy2(src, dest)
    return {
        "path": str(dest.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(dest),
        "size": dest.stat().st_size,
        "kind": kind,
    }


def ordered_question_keys(plan: dict) -> list[str]:
    keys: list[str] = []
    for group in plan.get("exercise_order", []):
        for number in group.get("numbers", []):
            keys.append("%s%s" % (group["group"], number))
    return keys


def validate_details_against_plan(kind: str, details: dict, plan: dict, section: str) -> None:
    if kind == "course_listened":
        allowed = {c.get("course_key") for c in plan.get("must_listen_courses", [])}
        if details.get("course_key") not in allowed:
            raise ValueError("course_key %r not in must-listen set %s" % (details.get("course_key"), sorted(allowed)))
    elif kind == "knowledge_point_study":
        allowed = {kp.get("id") for kp in plan.get("knowledge_points", [])}
        if details.get("knowledge_point_id") not in allowed:
            raise ValueError("knowledge_point_id %r not in section %s" % (details.get("knowledge_point_id"), section))
    elif kind == "example_solved":
        all_examples = {e for kp in plan.get("knowledge_points", []) for e in kp.get("examples", [])}
        for label in details.get("example_labels", []):
            if label not in all_examples:
                raise ValueError("example label %r not in section %s examples" % (label, section))
    elif kind == "type_training":
        allowed = {t.get("type") for t in plan.get("type_training", [])}
        if details.get("type_label") not in allowed:
            raise ValueError("type_label %r not in section %s" % (details.get("type_label"), section))
    elif kind in ("question_attempt", "review", "cold_review"):
        allowed = set(ordered_question_keys(plan))
        if details.get("question_key") not in allowed:
            raise ValueError("question_key %r not in section %s order %s" % (details.get("question_key"), section, sorted(allowed)))
    elif kind == "near_variant":
        allowed = set(ordered_question_keys(plan))
        for key in (details.get("question_key"), details.get("variant_question_key")):
            if key not in allowed:
                raise ValueError("question_key %r not in section %s" % (key, section))
    elif kind == "section_complete":
        expected = plan.get("exit_gate")
        if details.get("exit_gate") != expected:
            raise ValueError("exit_gate mismatch; expected %r" % expected)


def merge_flag_details(args, schema: dict) -> dict:
    details: dict = json.loads(args.details) if args.details else {}
    if not isinstance(details, dict):
        raise ValueError("--details must be a JSON object")
    mapping = {
        "baseline_status": getattr(args, "baseline_status", None),
        "course_key": args.course_key,
        "knowledge_point_id": args.knowledge_point_id,
        "type_label": args.type_label,
        "question_key": args.question_key,
        "variant_question_key": args.variant_question_key,
        "result": args.result,
        "hint_level": args.hint_level,
        "batch_id": args.batch_id,
        "first_break": args.first_break,
    }
    for field, value in mapping.items():
        if value is not None:
            details[field] = value
    if args.example_labels:
        details["example_labels"] = [part.strip() for part in args.example_labels.replace("，", ",").split(",") if part.strip()]
    if args.independent:
        details["independent"] = True
    if args.process_verified:
        details["process_verified"] = True
    return details


def build_event(root: Path, slot: str, kind: str, section: str, details: dict,
                artifacts: list[Path], visual_evidence: Path | None,
                at: str | None, observed_by: str) -> dict:
    identity = load_identity(root, slot)
    if not observed_by or observed_by != identity["participant_id"]:
        raise ValueError("observed_by must equal the registered participant_id (anti-fabrication)")
    schema = load_schema(root)
    kind_schema = schema["event_kinds"].get(kind)
    if not kind_schema:
        raise ValueError("unknown event kind %s" % kind)
    plan_index = load_plan_index(root)
    if section not in plan_index:
        raise ValueError("unknown section %s; available %s" % (section, sorted(plan_index)))
    plan = plan_index[section]
    occurred = parse_at(at)
    registered_at = parse_at(identity.get("registered_at"))
    if occurred < registered_at:
        raise ValueError("occurred_at cannot precede participant registration")
    if occurred > datetime.now(timezone.utc).astimezone() + timedelta(minutes=5):
        raise ValueError("occurred_at is in the future; use the actual observation time")
    if kind == "section_complete":
        details.setdefault("section", section)
    if kind in schema["rules"].get("answer_free_kinds", []):
        details.setdefault("answer_free", True)
    if kind == "baseline_check" and details.get("baseline_status") != "zero_base":
        raise ValueError("baseline_check requires details.baseline_status=zero_base")
    if kind == "baseline_check" and details.get("answer_free") is not True:
        raise ValueError("baseline_check requires details.answer_free=true")
    if kind == "cold_review":
        gap = compute_gap_hours(root, slot, section, details["question_key"], occurred)
        min_gap = schema["rules"].get("cold_review_min_gap_hours", 24)
        if gap < min_gap:
            raise ValueError("cold_review gap %.1f h < %d h; use kind=review for same-day rechecks" % (gap, min_gap))
        details["gap_hours"] = round(gap, 2)
        details["answer_free"] = True
    for field in kind_schema.get("required", []):
        if field not in details:
            raise ValueError("event kind %s requires details.%s" % (kind, field))
    enums = schema.get("enums", {})
    for field, allowed in enums.items():
        if field in details and details[field] not in allowed:
            raise ValueError("details.%s must be one of %s" % (field, sorted(allowed)))
    for field in schema.get("rules", {}).get("forbidden_fields", []):
        if field in details:
            raise ValueError("details.%s is forbidden by answer policy" % field)
    validate_details_against_plan(kind, details, plan, section)
    event_id = uuid.uuid4().hex[:12]
    stored_artifacts = []
    for src in artifacts:
        stored_artifacts.append(copy_artifact(root, slot, src, event_id, "work"))
    if visual_evidence is not None:
        stored_artifacts.append(copy_artifact(root, slot, visual_evidence, event_id, "visual_evidence"))
    if event_artifact_required(kind, schema) and not stored_artifacts:
        raise ValueError("event kind %s requires at least one artifact" % kind)
    if kind == "question_attempt":
        coverage = load_coverage_index(root)
        q = coverage.get((section, details["question_key"]))
        if q is None:
            raise ValueError("question %s/%s not in coverage" % (section, details["question_key"]))
        visual_required = q.get("visual_status") in schema["rules"].get("visual_evidence_required_statuses", [])
        has_visual = any(a["kind"] == "visual_evidence" for a in stored_artifacts)
        if visual_required and not has_visual:
            raise ValueError("visual question %s requires --visual-evidence (该次作答的图形证据)" % details["question_key"])
        details["visual_evidence_required"] = visual_required
        details["visual_evidence_present"] = bool(has_visual)
    event = {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "slot": slot,
        "kind": kind,
        "section": section,
        "occurred_at": occurred.isoformat(timespec="seconds"),
        "recorded_at": now_iso(),
        "observed_by": identity["participant_id"],
        "details": details,
        "artifacts": stored_artifacts,
        "answer_policy_checked": True,
    }
    append_event(root, slot, event)
    return event


def compute_gap_hours(root: Path, slot: str, section: str, question_key: str, review_at: datetime) -> float:
    first_attempt = None
    for ev in read_events(root, slot):
        if ev.get("kind") != "question_attempt" or ev.get("section") != section:
            continue
        if ev.get("details", {}).get("question_key") != question_key:
            continue
        t = parse_at(ev.get("occurred_at"))
        if first_attempt is None or t < first_attempt:
            first_attempt = t
    if first_attempt is None:
        raise ValueError("cold_review requires a prior question_attempt for %s/%s" % (section, question_key))
    return (review_at - first_attempt).total_seconds() / 3600.0


def recompute_gap_hours(root: Path, slot: str, section: str, question_key: str, review_at: datetime) -> float | None:
    try:
        return compute_gap_hours(root, slot, section, question_key, review_at)
    except ValueError:
        return None


def verify_slot(root: Path, slot: str, schema: dict, plan_index: dict, coverage_index: dict) -> dict:
    issues: list[str] = []
    required = required_sections(schema, plan_index)
    undeclared = [section for section in schema.get("rules", {}).get("required_sections", []) if section not in plan_index]
    issues.extend("required_section_unknown_%s" % section for section in undeclared)
    empty_sections = {
        section: {
            "status": "not_run",
            "must_listen_missing": [c.get("course_key") for c in plan_index[section].get("must_listen_courses", [])],
            "attempted_questions": [],
            "knowledge_point_checks": [
                {"id": kp.get("id"), "studied": False, "example_done": False}
                for kp in plan_index[section].get("knowledge_points", [])
            ],
            "recap_ok": False,
            "cold_review_ok": False,
            "section_complete_ok": False,
        }
        for section in required
    }
    identity = load_json(identity_path(root, slot))
    participant_id = None
    if not identity:
        return {"slot": slot, "status": "not_run", "has_records": False, "participant_id": None,
                "issues": sorted(set(issues + ["not_registered"])), "observed_questions": [], "knowledge_point_checks": [],
                "session_artifacts": [], "per_section": empty_sections}
    participant_id = identity.get("participant_id")
    if not participant_id or not str(participant_id).strip():
        issues.append("participant_id_empty")
    else:
        for other_slot in SLOT_IDS:
            if other_slot == slot:
                continue
            other_identity = load_json(identity_path(root, other_slot)) or {}
            if str(other_identity.get("participant_id", "")).strip() == str(participant_id).strip():
                issues.append("participant_id_duplicate_with_%s" % other_slot)
    consent = identity.get("consent_artifact", {})
    if consent.get("path"):
        path = root / consent["path"]
        if not path.is_file():
            issues.append("consent_artifact_missing")
        elif sha256_file(path) != consent.get("sha256"):
            issues.append("consent_artifact_hash_mismatch")
    else:
        issues.append("consent_artifact_missing")
    events = read_events(root, slot)
    if not events:
        issues.append("no_events")
    try:
        registered_at = parse_at(identity.get("registered_at"))
    except (TypeError, ValueError):
        registered_at = None
        issues.append("registered_at_invalid")
    forbidden = schema.get("rules", {}).get("forbidden_fields", [])
    previous_event = None
    for ev in events:
        try:
            occurred_at = parse_at(ev.get("occurred_at"))
            recorded_at = parse_at(ev.get("recorded_at"))
            if registered_at is not None and occurred_at < registered_at:
                issues.append("event_before_registration_%s" % ev.get("event_id", ev.get("kind")))
            if occurred_at > recorded_at + timedelta(minutes=5):
                issues.append("event_time_in_future_%s" % ev.get("event_id", ev.get("kind")))
        except (TypeError, ValueError):
            issues.append("event_timestamp_invalid_%s" % ev.get("event_id", ev.get("kind")))
        expected_prev = event_digest(previous_event) if previous_event else None
        if ev.get("prev_event_hash") != expected_prev:
            issues.append("event_chain_prev_hash_mismatch_%s" % ev.get("event_id", ev.get("kind")))
        if ev.get("event_hash") != event_digest(ev):
            issues.append("event_chain_hash_mismatch_%s" % ev.get("event_id", ev.get("kind")))
        previous_event = ev
        for field in forbidden:
            if field in ev.get("details", {}):
                issues.append("forbidden_field_%s" % field)
        if ev.get("observed_by") != participant_id:
            issues.append("observed_by_mismatch")
        if event_artifact_required(ev.get("kind"), schema) and not ev.get("artifacts"):
            issues.append("%s_artifact_missing" % ev.get("event_id", ev.get("kind")))
        if ev.get("kind") == "cold_review":
            details = ev.get("details", {})
            review_at = parse_at(ev.get("occurred_at"))
            recomputed = recompute_gap_hours(root, slot, ev.get("section"), details.get("question_key"), review_at)
            stored_gap = details.get("gap_hours")
            if recomputed is None:
                issues.append("cold_review_prior_attempt_missing")
            elif stored_gap is None:
                issues.append("cold_review_gap_missing")
            else:
                try:
                    if abs(float(stored_gap) - recomputed) > 0.01:
                        issues.append("cold_review_gap_mismatch")
                except (TypeError, ValueError):
                    issues.append("cold_review_gap_invalid")
                if recomputed < schema["rules"].get("cold_review_min_gap_hours", 24):
                    issues.append("cold_review_gap_too_short")
    by_section: dict[str, list[dict]] = {}
    for ev in events:
        by_section.setdefault(ev.get("section"), []).append(ev)
    section_first_times = {}
    for section in required:
        section_events = by_section.get(section, [])
        if section_events:
            section_first_times[section] = min(parse_at(ev.get("occurred_at")) for ev in section_events)
    previous_section_time = None
    for section in required:
        current = section_first_times.get(section)
        if current is None:
            continue
        if previous_section_time is not None and current < previous_section_time:
            issues.append("section_order_broken_at_%s" % section)
        previous_section_time = current
    per_section: dict[str, dict] = {}
    observed_questions: list[str] = []
    knowledge_point_checks: list[dict] = []
    for section in required:
        plan = plan_index[section]
        section_events = by_section.get(section, [])
        if not section_events:
            issues.append("%s_events_missing" % section)
            per_section[section] = empty_sections[section]
            continue
        before = len(issues)
        per_section[section] = check_section(section, plan, section_events, coverage_index, schema, issues)
        per_section[section]["status"] = "passed" if len(issues) == before else "failed"
        observed_questions.extend(per_section[section]["attempted_questions"])
        knowledge_point_checks.extend(per_section[section]["knowledge_point_checks"])
    unknown = set(by_section) - set(required)
    for section in sorted(unknown):
        issues.append("unknown_section_%s" % section)
    session_artifacts = []
    for ev in events:
        for artifact in ev.get("artifacts", []):
            path = root / artifact["path"]
            if not path.is_file():
                issues.append("artifact_missing_%s" % artifact["path"])
            elif sha256_file(path) != artifact.get("sha256"):
                issues.append("artifact_hash_mismatch_%s" % artifact["path"])
            else:
                session_artifacts.append(artifact["path"])
    baseline_events = [ev for ev in events if ev.get("kind") == "baseline_check"]
    first_course = min((parse_at(ev.get("occurred_at")) for ev in events if ev.get("kind") == "course_listened"), default=None)
    if not baseline_events:
        issues.append("baseline_check_missing")
    else:
        baseline_time = min(parse_at(ev.get("occurred_at")) for ev in baseline_events)
        if first_course is not None and baseline_time > first_course:
            issues.append("baseline_check_after_first_course")
        if any(ev.get("details", {}).get("baseline_status") != "zero_base" or ev.get("details", {}).get("answer_free") is not True for ev in baseline_events):
            issues.append("baseline_check_invalid")
    status = "passed" if not issues else "failed"
    return {"slot": slot, "status": status, "has_records": bool(events) or bool(identity),
            "participant_id": participant_id, "issues": sorted(set(issues)),
            "observed_questions": sorted(set(observed_questions)),
            "knowledge_point_checks": knowledge_point_checks,
            "session_artifacts": sorted(set(session_artifacts)), "per_section": per_section}


def check_section(section: str, plan: dict, events: list[dict], coverage_index: dict, schema: dict, issues: list[str]) -> dict:
    phase_times: dict[int, list[datetime]] = {}
    for ev in events:
        phase_times.setdefault(event_phase(ev.get("kind")), []).append(parse_at(ev.get("occurred_at")))
    previous_phase_time = None
    for phase in sorted(phase_times):
        current = min(phase_times[phase])
        if previous_phase_time is not None and current < previous_phase_time:
            issues.append("%s_event_phase_order_broken_at_%s" % (section, phase))
        previous_phase_time = max(phase_times[phase])
    must_keys = {c.get("course_key") for c in plan.get("must_listen_courses", [])}
    listened = {ev.get("details", {}).get("course_key") for ev in events if ev.get("kind") == "course_listened"}
    missing_courses = sorted(must_keys - listened)
    if missing_courses:
        issues.append("%s_missing_courses_%s" % (section, ",".join(missing_courses)))
    plan_kps = {kp.get("id"): kp for kp in plan.get("knowledge_points", [])}
    studied = {ev.get("details", {}).get("knowledge_point_id") for ev in events if ev.get("kind") == "knowledge_point_study"}
    missing_kps = sorted(set(plan_kps) - studied)
    if missing_kps:
        issues.append("%s_missing_knowledge_points_%s" % (section, ",".join(missing_kps)))
    example_covered: set[str] = set()
    for ev in events:
        if ev.get("kind") != "example_solved":
            continue
        labels = set(ev.get("details", {}).get("example_labels", []))
        for kp_id, kp in plan_kps.items():
            if labels & set(kp.get("examples", [])):
                example_covered.add(kp_id)
    missing_examples = sorted(set(plan_kps) - example_covered)
    if missing_examples:
        issues.append("%s_missing_examples_%s" % (section, ",".join(missing_examples)))
    type_labels = {t.get("type") for t in plan.get("type_training", [])}
    trained = {ev.get("details", {}).get("type_label") for ev in events if ev.get("kind") == "type_training"}
    missing_types = sorted(type_labels - trained)
    if missing_types:
        issues.append("%s_missing_type_training_%s" % (section, ",".join(missing_types)))
    ordered = ordered_question_keys(plan)
    first_times: dict[str, datetime] = {}
    attempts_by_key: dict[str, list[dict]] = {}
    for ev in events:
        if ev.get("kind") != "question_attempt":
            continue
        key = ev.get("details", {}).get("question_key")
        attempts_by_key.setdefault(key, []).append(ev)
        t = parse_at(ev.get("occurred_at"))
        if key not in first_times or t < first_times[key]:
            first_times[key] = t
    missing_questions = [key for key in ordered if key not in first_times]
    if missing_questions:
        issues.append("%s_missing_questions_%s" % (section, ",".join(missing_questions)))
    prev_time = None
    order_broken = None
    for key in ordered:
        if key not in first_times:
            continue
        t = first_times[key]
        if prev_time is not None and t < prev_time:
            order_broken = key
            break
        prev_time = t
    if order_broken:
        issues.append("%s_question_order_broken_at_%s" % (section, order_broken))
    visual_required_statuses = schema["rules"].get("visual_evidence_required_statuses", [])
    for key, attempts in attempts_by_key.items():
        q = coverage_index.get((section, key))
        if q is None or q.get("visual_status") not in visual_required_statuses:
            continue
        for ev in attempts:
            has = any(a.get("kind") == "visual_evidence" for a in ev.get("artifacts", []))
            if not has:
                issues.append("%s_%s_missing_visual_evidence" % (section, key))
            if ev.get("details", {}).get("visual_evidence_present") is not has:
                issues.append("%s_%s_visual_evidence_declaration_mismatch" % (section, key))
    attempt_times = [parse_at(ev.get("occurred_at")) for ev in events if ev.get("kind") == "question_attempt"]
    max_attempt = max(attempt_times) if attempt_times else None
    recap_ok = False
    for ev in events:
        if ev.get("kind") != "recap":
            continue
        if ev.get("details", {}).get("answer_free") is not True:
            issues.append("%s_recap_not_answer_free" % section)
            continue
        if max_attempt is None or parse_at(ev.get("occurred_at")) >= max_attempt:
            recap_ok = True
    if not recap_ok:
        issues.append("%s_recap_missing_or_before_last_attempt" % section)
    min_gap = schema["rules"].get("cold_review_min_gap_hours", 24)
    cold_ok = any(
        ev.get("kind") == "cold_review"
        and ev.get("details", {}).get("answer_free") is True
        and ev.get("details", {}).get("gap_hours", 0) >= min_gap
        for ev in events
    )
    if not cold_ok:
        issues.append("%s_cold_review_missing_or_gap_too_short" % section)
    section_complete_ok = any(
        ev.get("kind") == "section_complete"
        and ev.get("details", {}).get("section") == section
        and ev.get("details", {}).get("exit_gate") == plan.get("exit_gate")
        for ev in events
    )
    if not section_complete_ok:
        issues.append("%s_section_complete_missing" % section)
    kp_checks = [{"id": kp_id, "studied": kp_id in studied, "example_done": kp_id in example_covered} for kp_id in plan_kps]
    return {
        "must_listen_missing": missing_courses,
        "attempted_questions": sorted(set(first_times)),
        "knowledge_point_checks": kp_checks,
        "recap_ok": recap_ok,
        "cold_review_ok": cold_ok,
        "section_complete_ok": section_complete_ok,
    }


def cmd_register(root: Path, args) -> dict:
    if args.slot not in SLOT_IDS:
        raise ValueError("slot must be one of %s" % SLOT_IDS)
    if not args.participant_id or not args.participant_id.strip():
        raise ValueError("participant_id is required and must be chosen by the real person; empty identity refused")
    if not args.consent_artifact:
        raise ValueError("consent_artifact is required (photo/scan of handwritten pseudonym + date)")
    if identity_path(root, args.slot).exists():
        raise ValueError("slot %s already registered; refusing to overwrite" % args.slot)
    for other_slot in SLOT_IDS:
        if other_slot == args.slot:
            continue
        existing = load_json(identity_path(root, other_slot)) or {}
        if str(existing.get("participant_id", "")).strip() == args.participant_id.strip():
            raise ValueError("participant_id already registered in %s; one real person cannot occupy multiple slots" % other_slot)
    consent = copy_artifact(root, args.slot, Path(args.consent_artifact), "identity", "consent")
    identity = {
        "schema_version": SCHEMA_VERSION,
        "slot": args.slot,
        "participant_id": args.participant_id.strip(),
        # registered_at is injectable only by the temporary self-test namespace;
        # the public CLI never exposes a backdating switch.
        "registered_at": getattr(args, "registered_at", None) or now_iso(),
        "consent_artifact": consent,
        "evidence_note": "participant_id 由真人自选；无真人同意件不得注册",
    }
    save_json(identity_path(root, args.slot), identity)
    return {"status": "registered", "slot": args.slot, "participant_id": identity["participant_id"],
            "identity_file": str(identity_path(root, args.slot))}


def cmd_record(root: Path, args) -> dict:
    schema = load_schema(root)
    details = merge_flag_details(args, schema)
    artifacts = [Path(path) for path in (args.artifact or [])]
    visual = Path(args.visual_evidence) if args.visual_evidence else None
    event = build_event(root, args.slot, args.kind, args.section, details,
                        artifacts, visual, args.at, args.observed_by)
    return {"status": "recorded", "event_id": event["event_id"], "slot": args.slot,
            "kind": args.kind, "section": args.section,
            "artifacts": [a["path"] for a in event["artifacts"]]}


def cmd_verify(root: Path, args) -> dict:
    schema = load_schema(root)
    plan_index = load_plan_index(root)
    coverage_index = load_coverage_index(root)
    slots = [args.slot] if args.slot else SLOT_IDS
    results = [verify_slot(root, slot, schema, plan_index, coverage_index) for slot in slots]
    for result in results:
        status = result["status"]
        print("%s  %s  participant=%s  issues=%s" % (
            result["slot"], status.upper(), result["participant_id"], len(result["issues"])))
        for issue in result["issues"][:40]:
            print("    - %s" % issue)
    passed = sum(1 for r in results if r["status"] == "passed")
    print("real_user_e2e: required=%d recorded=%d passed=%d" % (len(slots), sum(1 for r in results if r["has_records"]), passed))
    return {"results": results, "passed": passed, "total": len(slots)}


def cmd_export(root: Path, contract_out: Path | None = None) -> dict:
    out = contract_out or (root / CONTRACT_REL)
    schema = load_schema(root)
    plan_index = load_plan_index(root)
    coverage_index = load_coverage_index(root)
    existing = load_json(root / CONTRACT_REL) or {}
    records_out = []
    any_records = False
    all_passed = True
    for slot in SLOT_IDS:
        v = verify_slot(root, slot, schema, plan_index, coverage_index)
        any_records = any_records or v["has_records"]
        if v["status"] != "passed":
            all_passed = False
        base = {}
        for item in existing.get("records", []):
            if item.get("slot") == slot:
                base = item
                break
        record = dict(base)
        record.update({
            "slot": slot,
            "status": v["status"],
            "participant_id": v["participant_id"],
            "session_artifacts": v["session_artifacts"],
            "observed_questions": v["observed_questions"],
            "knowledge_point_checks": v["knowledge_point_checks"],
            "mastery_result": "not_assessed",
            "issues": v["issues"][:20],
        })
        records_out.append(record)
    status = "passed" if all_passed else ("not_run" if not any_records else "in_progress")
    new_contract = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "title": existing.get("title", "第一章零基础真实用户观察记录"),
        "purpose": existing.get("purpose", "为五名真实零基础用户的听课、逐题作答、知识点复述和冷复测留存可审计记录；代理模拟不得填充此文件。"),
        "required_zero_base_users": existing.get("required_zero_base_users", 5),
        "records": records_out,
        "minimum_evidence": existing.get("minimum_evidence", [
            "每名用户实际听完该批次必听课程并留存批次与时间",
            "按知识点讲解、右侧例题、类型题、A/B/C习题顺序逐题记录",
            "每道题保留独立作答结果，视觉题保留当次图像证据",
            "全节完成后进行不看答案的知识点复述与冷复测",
            "记录只能证明观察到的行为，不把建议流程或代理轨迹记为掌握",
        ]),
        "answer_policy": "NO_FINAL_ANSWERS_IN_STUDENT_OBSERVATION_RECORDS",
        "verification_engine": "python scripts/real_user_collect.py verify --all",
        "protocol": "data/real_user_protocol.md",
        "schema_file": "data/real_user_schema.json",
        "note": "本文件由采集 harness 根据 data/real_user_records/* 的真实事件导出；无真人事件时保持 not_run，代理轨迹不得写入。",
    }
    new_text = json.dumps(new_contract, ensure_ascii=False, indent=2) + "\n"
    changed = True
    if out.exists():
        changed = out.read_text(encoding="utf-8") != new_text
    if changed:
        save_json(out, new_contract)
    return {"status": status, "required": len(SLOT_IDS), "passed": sum(1 for r in records_out if r["status"] == "passed"),
            "recorded": any_records, "contract": str(out), "changed": changed}


def cmd_self_test(root: Path) -> dict:
    """在临时目录跑完整采集流程（合成测试数据只写临时目录，绝不触碰 data/）。"""
    with tempfile.TemporaryDirectory(prefix="ybt_real_user_selftest_") as tmp:
        scratch = Path(tmp)
        data_dir = scratch / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        for rel in (PLAN_REL, COVERAGE_REL, SCHEMA_REL):
            shutil.copy2(root / rel, scratch / rel)
        plan_index = load_plan_index(scratch)
        coverage = load_coverage_index(scratch)
        visual_required = set(load_schema(scratch)["rules"].get("visual_evidence_required_statuses", []))
        base_start = datetime.now(timezone.utc).astimezone() - timedelta(days=120)
        step = timedelta(minutes=10)

        def replay(slot: str, participant: str, day_offset: int) -> None:
            consent = scratch / ("consent_%s.txt" % slot)
            consent.write_text("SELF_TEST consent placeholder for %s\n" % participant, encoding="utf-8")
            register_args = argparse.Namespace(slot=slot, participant_id=participant,
                                               consent_artifact=str(consent),
                                               registered_at=(base_start + timedelta(days=day_offset * 20) - timedelta(hours=1)).isoformat(timespec="seconds"))
            registered = cmd_register(scratch, register_args)
            assert registered["status"] == "registered"
            for section_index, (section, plan) in enumerate(plan_index.items()):
                # Keep each section's first attempt and cold review in a
                # deterministic chronological order.  A slot therefore
                # exercises the whole chapter, not just the first section.
                start = base_start + timedelta(days=day_offset * 20 + section_index * 4)
                cursor = start
                section_tag = "section_%02d" % (section_index + 1)

                def make_artifact(name: str, text: str) -> Path:
                    path = scratch / ("%s_%s_%s" % (slot, section_tag, name))
                    path.write_text(text, encoding="utf-8")
                    return path

                def rec(kind: str, details: dict, artifact: Path | None = None,
                        visual: Path | None = None, at: datetime | None = None):
                    nonlocal cursor
                    at = at or cursor
                    cursor = at + step
                    build_event(scratch, slot, kind, section, details,
                                [artifact] if artifact else [], visual,
                                at.isoformat(timespec="seconds"), participant)

                if section_index == 0:
                    rec("baseline_check", {
                        "baseline_status": "zero_base",
                        "answer_free": True,
                        "sample_question_keys": ordered_question_keys(plan)[:2],
                    }, make_artifact("baseline.txt", "SELF_TEST zero-base baseline"))
                for course in plan["must_listen_courses"]:
                    rec("course_listened", {"course_key": course["course_key"], "role": course["role"], "batch_id": "selftest-batch"},
                        make_artifact("listen_%s.txt" % course["course_key"], "SELF_TEST listening log"))
                for kp in plan["knowledge_points"]:
                    rec("knowledge_point_study", {"knowledge_point_id": kp["id"], "label": kp["label"]},
                        make_artifact("kp_%s.txt" % kp["id"], "SELF_TEST study note"))
                    rec("example_solved", {"example_labels": kp["examples"]},
                        make_artifact("ex_%s.txt" % kp["id"], "SELF_TEST example work"))
                for t in plan["type_training"]:
                    rec("type_training", {"type_label": t["type"], "example_numbers": t.get("example_numbers", [])},
                        make_artifact("type_%s.txt" % t["type"][:4], "SELF_TEST type work"))
                ordered = ordered_question_keys(plan)
                for key in ordered:
                    q = coverage.get((section, key), {})
                    need_visual = q.get("visual_status") in visual_required
                    rec("question_attempt", {"question_key": key, "result": "correct", "independent": True,
                                             "process_verified": True, "hint_level": "H0"},
                        make_artifact("q_%s.txt" % key, "SELF_TEST handwritten work for %s" % key),
                        make_artifact("fig_%s.txt" % key, "SELF_TEST figure evidence for %s" % key) if need_visual else None)
                rec("recap", {"answer_free": True, "knowledge_point_ids": [kp["id"] for kp in plan["knowledge_points"]]},
                    make_artifact("recap.txt", "SELF_TEST closed-book recap"))
                first_key = ordered[0]
                cold_at = start + timedelta(days=2)
                rec("cold_review", {"question_key": first_key, "result": "correct"},
                    make_artifact("cold_%s.txt" % first_key, "SELF_TEST cold redo"), at=cold_at)
                rec("section_complete", {"section": section, "exit_gate": plan["exit_gate"], "items_full_pass": [f"{section}-{first_key}"]},
                    make_artifact("complete.txt", "SELF_TEST section completion record"), at=cold_at + step)

        for index, slot in enumerate(SLOT_IDS):
            replay(slot, "SELF_TEST_USER_%02d" % (index + 1), index)
        schema = load_schema(scratch)
        coverage_index = load_coverage_index(scratch)
        results = [verify_slot(scratch, slot, schema, plan_index, coverage_index) for slot in SLOT_IDS]
        exported = cmd_export(scratch, contract_out=scratch / CONTRACT_REL)
        for result in results:
            if result["status"] != "passed":
                print("SELF_TEST verify issues for %s:" % result["slot"])
                for issue in result["issues"]:
                    print("  - %s" % issue)
                raise SystemExit(1)
        assert exported["status"] == "passed", exported
        total_kps = sum(len(plan.get("knowledge_points", [])) for plan in plan_index.values())
        total_types = sum(len(plan.get("type_training", [])) for plan in plan_index.values())
        total_questions = sum(len(ordered_question_keys(plan)) for plan in plan_index.values())
        print("SELF_TEST passed: 5 槽 × 4 节全章 (register -> %d 知识点/例题 -> %d 类型题 -> %d 逐题 -> recap -> 冷复测 -> section_complete) -> verify 5/5 -> export status=passed" % (
            total_kps, total_types, total_questions))
        print("SELF_TEST 数据仅写入临时目录（已自动清理），未触碰 data/real_user_records")
    return {"status": "passed"}


def build_parser(schema: dict) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="一本通 v7 真实用户观察采集/验证（只写 data/real_user*）")
    parser.add_argument("--root", default=str(PROJECT_ROOT), help="项目根目录（默认自动探测）")
    sub = parser.add_subparsers(dest="command", required=True)

    reg = sub.add_parser("register", help="注册一名真人（participant_id 自选 + consent artifact）")
    reg.add_argument("--slot", required=True)
    reg.add_argument("--participant-id", required=True)
    reg.add_argument("--consent-artifact", required=True)

    rec = sub.add_parser("record", help="追加一条观察事件（校验通过才写入）")
    rec.add_argument("--slot", required=True)
    rec.add_argument("--observed-by", required=True)
    rec.add_argument("--section", required=True)
    rec.add_argument("--kind", required=True, choices=sorted(schema["event_kinds"]))
    rec.add_argument("--details", default=None, help="JSON 对象，一次传入事件 details")
    rec.add_argument("--artifact", action="append", help="证据文件（可重复）")
    rec.add_argument("--visual-evidence", default=None, help="视觉题当次图形证据")
    rec.add_argument("--at", default=None, help="实际发生时间 ISO8601（默认现在）")
    rec.add_argument("--course-key")
    rec.add_argument("--baseline-status", choices=["zero_base"])
    rec.add_argument("--knowledge-point-id")
    rec.add_argument("--type-label")
    rec.add_argument("--question-key")
    rec.add_argument("--variant-question-key")
    rec.add_argument("--result", choices=["correct", "incorrect", "partial", "guess"])
    rec.add_argument("--hint-level", choices=["H0", "H1", "H2", "H3", "H4"])
    rec.add_argument("--independent", action="store_true")
    rec.add_argument("--process-verified", action="store_true")
    rec.add_argument("--first-break")
    rec.add_argument("--batch-id")
    rec.add_argument("--example-labels", help="逗号分隔的例题标签")

    ver = sub.add_parser("verify", help="校验一槽或全部槽位证据完整性")
    ver.add_argument("--slot", default=None)
    ver.add_argument("--all", action="store_true")

    sub.add_parser("export", help="从真实事件同步 data/real_user_observations.json")
    sub.add_parser("self-test", help="临时目录自测（不触碰 data/）")
    return parser


def main() -> int:
    schema = load_schema(PROJECT_ROOT)
    args = build_parser(schema).parse_args()
    root = Path(args.root)
    try:
        if args.command == "register":
            print(json.dumps(cmd_register(root, args), ensure_ascii=False, indent=2))
        elif args.command == "record":
            print(json.dumps(cmd_record(root, args), ensure_ascii=False, indent=2))
        elif args.command == "verify":
            result = cmd_verify(root, args)
            return 0 if result["passed"] == result["total"] else 1
        elif args.command == "export":
            print(json.dumps(cmd_export(root), ensure_ascii=False, indent=2))
        elif args.command == "self-test":
            print(json.dumps(cmd_self_test(root), ensure_ascii=False, indent=2))
        else:
            raise SystemExit("unknown command")
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
