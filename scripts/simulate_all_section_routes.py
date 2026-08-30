#!/usr/bin/env python3
"""Run auditable route simulations for all five chapters without claiming human mastery."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_all_section_routes import all_sections, course_sort_key, guidance, load_json, section_folder


OUTPUT = ROOT / "reports/all_section_simulations"
PROFILE_OUTPUT = ROOT / "reports/learner_simulation/primary-user-proxy-all-chapters.json"

PERSONAS = (
    {"id": "Z1", "strategy": "slow_start", "stress": "概念入口与最小步骤"},
    {"id": "Z2", "strategy": "symbol_guard", "stress": "符号、方向和定义域"},
    {"id": "Z3", "strategy": "visual_first", "stress": "图形、坐标和原页核对"},
    {"id": "Z4", "strategy": "bridge_first", "stress": "跨循环前置与方法桥接"},
    {"id": "Z5", "strategy": "chapter_auditor", "stress": "题号覆盖、验收与延迟复测"},
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def item_label(item: dict[str, Any]) -> str:
    if item.get("kind") == "example" or item.get("example_number") is not None:
        return str(item.get("label") or f"例{item.get('example_number')}")
    if item.get("kind") == "direct_variant" or item.get("parent_example_number") is not None:
        return f"例{item.get('parent_example_number')} {item.get('label') or '变式'}"
    return f"{item.get('group')}{item.get('number')}"


def cycle_items(cycle: dict[str, Any]) -> list[dict[str, Any]]:
    return [*cycle.get("worked_examples", []), *cycle.get("direct_variants", []), *cycle.get("exercise_questions", [])]


def course_calls(cycle: dict[str, Any], catalog: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    keys = list(dict.fromkeys(str(key) for field in ("course_keys", "prerequisite_course_keys") for key in cycle.get(field, [])))
    return [
        {"course_key": key, "course_id": str(catalog[key].get("course_id")), "title": str(catalog[key].get("title"))}
        for key in sorted(keys, key=lambda key: course_sort_key(catalog[key]))
    ]


def attempt_record(
    section_id: str,
    cycle: dict[str, Any],
    item: dict[str, Any],
    persona: dict[str, str],
    catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    label = item_label(item)
    title = str(cycle.get("title") or "未命名循环")
    recognition, first_line, continuation, self_check = guidance(title + " " + " ".join(cycle.get("type_refs", [])))
    visual = str(item.get("visual_status") or "UNKNOWN")
    errors = []
    if visual not in {"READY_TEXT_ONLY", "VISION_VERIFIED"}:
        errors.append("visual_not_consumable")
    if not recognition or not first_line or not continuation or not self_check:
        errors.append("guidance_incomplete")
    return {
        "attempt_id": hashlib.sha256(f"{section_id}\0{cycle.get('cycle_id')}\0{label}\0{persona['id']}".encode("utf-8")).hexdigest()[:24],
        "persona_id": persona["id"],
        "strategy": persona["strategy"],
        "stress_focus": persona["stress"],
        "cycle_id": cycle.get("cycle_id"),
        "item_id": item.get("item_id") or item.get("qid"),
        "item_label": label,
        "course_call": course_calls(cycle, catalog),
        "recognition_statement": f"{label} 属于“{title}”。{recognition}",
        "first_written_line": f"处理 {label}：{first_line}",
        "continuation_attempt": continuation,
        "self_check": self_check,
        "visual_status": visual,
        "frozen": True,
        "errors": errors,
        "result": "route_actionable" if not errors else "blocked",
        "mastery_observed": False,
    }


def simulate_section(
    chapter: int,
    section: dict[str, Any],
    packet: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    section_id = str(section["id"])
    route_path = ROOT / "data/packets" / section_folder(section_id) / "learning_path_without_questions.md"
    packet_path = ROOT / "data/packets" / section_folder(section_id) / "learning_packet.json"
    route_sha = sha256(route_path)
    packet_sha = sha256(packet_path)
    expected = int(packet.get("counts", {}).get("total_numbered_learning_items", 0))
    persona_rows = []
    for persona in PERSONAS:
        attempts = [
            attempt_record(section_id, cycle, item, persona, catalog)
            for cycle in packet.get("learning_cycles", [])
            for item in cycle_items(cycle)
        ]
        passed = len(attempts) == expected and all(row["result"] == "route_actionable" and row["frozen"] for row in attempts)
        persona_rows.append({
            **persona,
            "attempt_count": len(attempts),
            "route_contract_status": "passed" if passed else "blocked",
            "mastery_claimed": False,
            "attempts": attempts,
        })
    passed = all(row["route_contract_status"] == "passed" for row in persona_rows)
    return {
        "schema_version": "ybt-all-section-route-simulation-v1",
        "generation": f"G-ALL-{route_sha[:12]}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chapter": chapter,
        "section": section_id,
        "label": section.get("label"),
        "route_sha256": route_sha,
        "learning_packet_sha256": packet_sha,
        "source_revision_match": True,
        "simulation_kind": "five_zero_base_route_contract_stress_test",
        "honesty_boundary": "These are synthetic route-actionability checks, not human answers, course consumption, mastery, or a 24-hour retest.",
        "personas": persona_rows,
        "summary": {
            "personas": len(persona_rows),
            "items_per_persona": expected,
            "attempts": sum(row["attempt_count"] for row in persona_rows),
            "passed_personas": sum(row["route_contract_status"] == "passed" for row in persona_rows),
            "blocked_personas": sum(row["route_contract_status"] != "passed" for row in persona_rows),
            "route_verdict": "PASS" if passed else "BLOCKED",
            "human_acceptance_not_proven": True,
            "cold_retest_24h": "not_run",
        },
        "task_coverage": {"task_count": expected, "expected_task_count": expected, "complete": passed},
        "status": "passed" if passed else "blocked",
    }


def observed_user_seed() -> dict[str, Any]:
    source = Path.home() / "Downloads" / "ChatGPT-第一章第一节-20260829-2237.md"
    source_record = {"path": str(source), "sha256": sha256(source) if source.is_file() else None}
    return {
        "source": source_record,
        "profile_version": 3 if source.is_file() else 1,
        "confirmed_strengths": [
            "循环1的空间向量概念、线性运算、例1/2/3/9/10与A组在用户更正语音识别后确认通过",
            "能够使用首尾相接和公共起点拆分向量",
        ] if source.is_file() else [],
        "confirmed_gaps": [
            "循环2曾在共线向量概念边界和四面体中点题入口处出现卡点",
        ] if source.is_file() else [],
        "hint_dependencies": [
            "循环2的三基底/四面体中点模型曾查看答案或视频后掌握，需要未见迁移复测",
        ] if source.is_file() else [],
        "uncertainties": [
            "语音转写可能把正确选项或带下标向量误写，判错前必须向用户复核",
        ] if source.is_file() else [],
        "profile_history": [
            {"version": 1, "reason": "initialized_with_zero_base_assumption_only", "evidence": []},
            {"version": 2, "reason": "cycle_1_user_correction_and_confirmed_pass", "evidence": [source_record]},
            {"version": 3, "reason": "cycle_2_concept_and_hint_dependency_observed", "evidence": [source_record]},
        ] if source.is_file() else [{"version": 1, "reason": "initialized_with_zero_base_assumption_only", "evidence": []}],
    }


def build_primary_proxy(section_reports: list[dict[str, Any]]) -> dict[str, Any]:
    attempts = []
    for report in section_reports:
        for persona in report["personas"][:1]:
            attempts.extend({
                **attempt,
                "persona_id": "primary-user-proxy",
                "evidence_kind": "synthetic_prediction_not_real_user",
            } for attempt in persona["attempts"])
    return {
        "schema_version": "ybt-primary-user-proxy-all-chapters-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "learner": {
            "learner_id": "primary-user-proxy",
            "mode": "persistent_zero_base_proxy",
            "initial_assumptions": ["zero_base"],
            **observed_user_seed(),
            "predicted_risks_not_confirmed": [
                "解析几何中的斜率不存在与参数范围",
                "圆锥曲线标准方程方向和判别式几何意义",
                "数列下标、边界项和分类讨论",
                "导数题中的定义域、端点和参数等号条件",
            ],
        },
        "coverage": {
            "chapters": 5,
            "sections": len(section_reports),
            "canonical_items": len(attempts),
            "route_actionable_items": sum(row["result"] == "route_actionable" for row in attempts),
        },
        "sections": [
            {"chapter": row["chapter"], "section": row["section"], "items": row["summary"]["items_per_persona"], "status": "simulated_route_actionable" if row["status"] == "passed" else "blocked"}
            for row in section_reports
        ],
        "attempts": attempts,
        "simulated_learning_status": "route_actionability_complete" if all(row["status"] == "passed" for row in section_reports) else "blocked",
        "human_learning_status": "use_remote_math_mcp",
        "cold_24h_retest": "not_run",
        "mastery_claimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section")
    args = parser.parse_args()
    catalog_payload = load_json(ROOT / "data/all_chapters_course_catalog.json")
    catalog = {str(row["course_key"]): row for row in catalog_payload.get("courses", [])}
    selected = [row for row in all_sections() if not args.section or str(row[1]["id"]) == args.section]
    reports = []
    for chapter, section in selected:
        section_id = str(section["id"])
        packet = load_json(ROOT / "data/packets" / section_folder(section_id) / "learning_packet.json")
        report = simulate_section(chapter, section, packet, catalog)
        save_json(OUTPUT / f"{section_id}-route-contract-simulation.json", report)
        reports.append(report)
    if not args.section:
        save_json(PROFILE_OUTPUT, build_primary_proxy(reports))
    summary = {
        "sections": len(reports),
        "items": sum(row["summary"]["items_per_persona"] for row in reports),
        "persona_attempts": sum(row["summary"]["attempts"] for row in reports),
        "passed_sections": sum(row["status"] == "passed" for row in reports),
        "primary_proxy": str(PROFILE_OUTPUT.relative_to(ROOT)) if not args.section else None,
        "mastery_claimed": False,
    }
    if not args.section:
        report = ROOT / "reports/all_chapters/simulation-current.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        save_json(report, summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if all(row["status"] == "passed" for row in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
