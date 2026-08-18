from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import build_catalog, build_learning_plan, select_section_plan
from .common import load_json, save_json
from .coverage import build_question_coverage
from .manifest import load_manifest
from .ocr import ocr_config_status
from .packet import PacketBuilder, verify_packet
from .state import StateError, StateStore, run_reward_test
from .simulation import run_ten_person_simulation
from .vision import test_vision_config
from .vision import sidecar_for_question_images
from .deepseek_context import build_context, context_path_for_student_packet, validate_context, verify_worker_probe


ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path(r"C:\Users\poyi\Downloads")
OCR_ROOT = Path(r"C:\开发\小工具\一本通DeepSeek迭代\worker-01-content\ocr")
LIVE_OCR_ROOT = ROOT / "data" / "ocr_live_full"
CURRENT_LIVE_OCR_ROOT = ROOT / "data" / "ocr_live_current" / "first_chapter_69"
TRANSCRIPTS = ROOT / "data" / "course_transcripts"


def active_ocr_root() -> Path:
    """Prefer a complete, hash-checked live OCR run over historical OCR."""
    current_evidence_path = ROOT / "data" / "ocr_live_current_evidence.json"
    if CURRENT_LIVE_OCR_ROOT.exists() and current_evidence_path.exists():
        try:
            evidence = load_json(current_evidence_path)
            if (
                evidence.get("status") == "passed"
                and evidence.get("provider") == "PaddleOCR AI Studio"
                and evidence.get("fresh_api_run") is True
                and evidence.get("document_count") == 69
                and evidence.get("markdown_count") == 69
                and evidence.get("document_sequence_ok") is True
            ):
                return CURRENT_LIVE_OCR_ROOT
        except (OSError, ValueError):
            pass
    evidence_path = ROOT / "data" / "ocr_live_evidence.json"
    if LIVE_OCR_ROOT.exists() and evidence_path.exists():
        try:
            evidence = load_json(evidence_path)
            if evidence.get("status") == "passed" and evidence.get("document_count") == 69 and evidence.get("exact_match_with_historical") is True:
                return LIVE_OCR_ROOT
        except (OSError, ValueError):
            pass
    return OCR_ROOT


def _json_object(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StateError(f"invalid JSON object: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise StateError("source anchor must be a JSON object")
    return value


def _state_for(path: str | Path, *, section: str | None = None) -> StateStore:
    state_path = Path(path)
    if not state_path.exists():
        raise StateError(f"state file does not exist: {state_path}; run init-state first")
    store = StateStore(state_path)
    if section and store.state.get("target_identity", {}).get("section") not in {None, section}:
        raise StateError(f"state target section mismatch: {store.state.get('target_identity', {}).get('section')} != {section}")
    return store


def build_chapter1() -> dict:
    manifest = load_manifest()
    catalog = build_catalog(download_root=DOWNLOADS, transcript_root=TRANSCRIPTS, output_path=ROOT / "data" / "course_catalog.json")
    bridge_path = ROOT / "data" / "bridge_micro_lessons.json"
    bridge_catalog = load_json(bridge_path) if bridge_path.exists() else None
    plan = build_learning_plan(manifest, catalog, bridge_catalog=bridge_catalog)
    save_json(ROOT / "data" / "chapter1_learning_plan.json", plan)
    builder = PacketBuilder(ocr_root=active_ocr_root(), output_root=ROOT / "data" / "packets")
    packets = []
    sidecar_path = ROOT / "data" / "vision_sidecar_full.json"
    if not sidecar_path.exists():
        sidecar_path = ROOT / "data" / "vision_sidecar_sample.json"
    sidecar = load_json(sidecar_path) if sidecar_path.exists() else {"known_visual_recoveries": manifest.get("known_visual_recoveries", [])}
    # Keep only provider-backed, content-bound E1/E2 results.  Source-PDF
    # crops are accepted through the same packet matcher (path or SHA), so a
    # higher-resolution visual probe can repair a low-resolution crop without
    # changing the question text.
    # Older sample calls may contain a valid result absent from the newer batch;
    # merge by question hint, with the full batch taking precedence.
    sample_path = ROOT / "data" / "vision_sidecar_sample.json"
    if sample_path.exists() and sample_path != sidecar_path:
        sample = load_json(sample_path)
        def sidecar_key(item: dict) -> tuple[str | None, str | None]:
            return item.get("question_hint"), item.get("image")
        merged_results = {sidecar_key(x): x for x in sample.get("results", []) if x.get("question_hint")}
        merged_results.update({sidecar_key(x): x for x in sidecar.get("results", []) if x.get("question_hint")})
        sidecar = {**sidecar, "results": list(merged_results.values())}
    source_probe_path = ROOT / "reports" / "source_visual_probe_sidecar.json"
    if source_probe_path.exists():
        source_probe = load_json(source_probe_path)

        def student_visual_row(row: dict) -> bool:
            image = str(row.get("image", "")).lower()
            provenance = row.get("source_provenance") or {}
            source_pdf = str(provenance.get("source_pdf", "")).lower() if isinstance(provenance, dict) else ""
            chinese_answer_book = ("答案册" in image or "答案册" in source_pdf) and ("无答案册" not in image and "无答案册" not in source_pdf)
            return not (chinese_answer_book or "worker-02-solutions" in image or "answer_book" in image or "answer-book" in image)

        # Source-PDF visual probes are a second provider-backed source for the
        # same immutable question image.  A passed source row wins over a
        # transient failed row, while answer-book paths remain forbidden.
        merged_results = {
            (item.get("question_hint"), item.get("image")): item
            for item in sidecar.get("results", [])
            if item.get("question_hint")
        }
        for item in source_probe.get("results", []):
            if not (student_visual_row(item) and item.get("status") == "passed" and item.get("confidence") in {"E1", "E2"} and item.get("structured")):
                continue
            key = (item.get("question_hint"), item.get("image"))
            previous = merged_results.get(key)
            # Prefer the source-probe row when it carries the authoritative
            # PDF provenance.  The same crop may already exist in the generic
            # sidecar without provenance; retaining that older row would make
            # PacketBuilder unable to bind the high-resolution replacement.
            if (
                previous is None
                or previous.get("status") != "passed"
                or previous.get("confidence") not in {"E1", "E2"}
                or (item.get("source_provenance") and not previous.get("source_provenance"))
            ):
                merged_results[key] = item
        sidecar = {**sidecar, "results": list(merged_results.values())}
    answer_roots = manifest.get("source_evidence", {}).get("answer_ocr_roots", {})
    for section in manifest["sections"]:
        combined_sidecar = {
            "known_visual_recoveries": manifest.get("known_visual_recoveries", []),
            "derived_question_corrections": manifest.get("derived_question_corrections", []),
            "results": [x for x in sidecar.get("results", []) if x.get("section") == section["id"]],
        }
        # PacketBuilder uses answer_root only for the isolated answer sidecar;
        # recovery into student questions accepts primary OCR only.
        packets.append(builder.build_section(section, visual_sidecar=combined_sidecar, answer_root=answer_roots.get(section["id"])))
    coverage = build_question_coverage(
        manifest,
        catalog,
        packets,
        bridge_catalog=bridge_catalog,
        output_path=ROOT / "data" / "question_coverage.json",
    )
    # Build contexts only after the current coverage ledger exists.  Otherwise
    # route_support.question_coverage can silently embed the previous build's
    # VERIFIED/UNVERIFIED values and drift from data/question_coverage.json.
    context_results = []
    contexts_root = ROOT / "data" / "contexts"
    for section in manifest["sections"]:
        folder = section["id"].replace("+", "_")
        student_packet = ROOT / "data" / "packets" / folder / "student_packet.json"
        context_path = contexts_root / f"{folder}.json"
        build_context(student_packet, output_path=context_path)
        context_results.append(validate_context(context_path))
    target = dict(manifest["target_identity"])
    target["section"] = "1.1"
    state_path = ROOT / "data" / "main_state.json"
    state = StateStore(state_path) if state_path.exists() else StateStore.create(state_path, target)
    browser_evidence_path = ROOT / "data" / "browser_evidence.json"
    browser_evidence = load_json(browser_evidence_path) if browser_evidence_path.exists() else {
        "status": "partial",
        "collector": "Edge browser collector",
        "checked_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "8.5": {"status": "not_collected", "source": "template", "reason": "采集器输出缺失；模板不得伪造通过证据"},
        "8.5课程": {"status": "not_collected", "source": "template", "reason": "采集器输出缺失；必须读取指定数学项目对话"},
        "privacy": "只读取页面可见内容和浏览历史，不读取 cookies/localStorage，不输入账号，不发送消息",
    }
    browser_evidence.setdefault("status", "partial")
    browser_evidence["last_build_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    save_json(browser_evidence_path, browser_evidence)
    result = {"status": "built", "ocr_source": str(active_ocr_root()), "catalog": {"videos": catalog["video_count"], "courses": catalog["course_count"], "course_collection_videos": catalog["canonical_video_count"], "transcripts": catalog["transcript_count"]}, "packets": [{"section": p["section"], "status": p["status"], "pages": p["manifest"]["page_count"], "questions": p["manifest"]["question_count"], "unresolved": len(p["unresolved"])} for p in packets], "contexts": context_results, "coverage": {"path": str(ROOT / "data" / "question_coverage.json"), "question_count": coverage["question_count"], "summary": coverage["summary"]}, "state": str(ROOT / "data" / "main_state.json"), "browser_evidence": str(ROOT / "data" / "browser_evidence.json")}
    if bridge_path.exists():
        bridge_data = load_json(bridge_path)
        result["bridge_curriculum"] = {
            "path": str(bridge_path),
            "unit_count": len(bridge_data.get("units", [])),
            "status_counts": {status: sum(item.get("status") == status for item in bridge_data.get("units", [])) for status in bridge_data.get("status_values", [])},
            "answer_policy": bridge_data.get("answer_policy"),
        }
    save_json(ROOT / "reports" / "build-result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="一本通 v7 运行层")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build-chapter1")
    sub.add_parser("reward-test")
    init_state = sub.add_parser("init-state")
    init_state.add_argument("--state", required=True)
    init_state.add_argument("--section", required=True)
    attempt = sub.add_parser("record-attempt")
    attempt.add_argument("--state", default=str(ROOT / "data" / "main_state.json"))
    attempt.add_argument("--item-id", required=True)
    attempt.add_argument("--section", default=None)
    attempt.add_argument("--result", choices=["correct", "incorrect", "partial", "guess"], required=True)
    attempt.add_argument("--independent", action="store_true")
    attempt.add_argument("--hint-level", choices=["H0", "H1", "H2", "H3", "H4"], default="H0")
    attempt.add_argument("--answer-seen", action="store_true")
    attempt.add_argument("--process-verified", action="store_true")
    attempt.add_argument("--first-break", default=None)
    attempt.add_argument("--visual-status", choices=["READY_TEXT_ONLY", "VISION_VERIFIED", "NEEDS_VISION_SIDECAR", "UNVERIFIED"], default="READY_TEXT_ONLY")
    attempt.add_argument("--source-anchor-json", default="{}")
    attempt.add_argument("--at", default=None)
    near = sub.add_parser("record-near-variant")
    near.add_argument("--state", default=str(ROOT / "data" / "main_state.json"))
    near.add_argument("--item-id", required=True)
    near.add_argument("--variant-item-id", required=True)
    near.add_argument("--section", default=None)
    near.add_argument("--result", choices=["correct", "incorrect", "partial", "guess"], required=True)
    near.add_argument("--independent", action="store_true")
    near.add_argument("--process-verified", action="store_true")
    near.add_argument("--visual-status", choices=["READY_TEXT_ONLY", "VISION_VERIFIED", "NEEDS_VISION_SIDECAR", "UNVERIFIED"], default="READY_TEXT_ONLY")
    near.add_argument("--source-anchor-json", default="{}")
    near.add_argument("--at", default=None)
    review = sub.add_parser("review-item")
    review.add_argument("--state", default=str(ROOT / "data" / "main_state.json"))
    review.add_argument("--item-id", required=True)
    review.add_argument("--result", choices=["correct", "incorrect", "partial", "guess"], required=True)
    review.add_argument("--process-verified", action="store_true")
    review.add_argument("--at", default=None)
    complete = sub.add_parser("complete-section")
    complete.add_argument("--state", default=str(ROOT / "data" / "main_state.json"))
    complete.add_argument("--section", required=True)
    complete.add_argument("--item-id", action="append", required=True)
    complete.add_argument("--evidence", action="append", required=True)
    complete.add_argument("--at", default=None)
    pending = sub.add_parser("pending-reviews")
    pending.add_argument("--state", default=str(ROOT / "data" / "main_state.json"))
    pending.add_argument("--at", default=None)
    sub.add_parser("answer-status")
    sub.add_parser("deepseek-status")
    simulation = sub.add_parser("simulate-five")
    simulation.add_argument("--out", default=str(ROOT / "reports" / "zero_base_simulation_current.json"))
    simulation_compat = sub.add_parser("simulate-ten")
    simulation_compat.add_argument("--out", default=str(ROOT / "reports" / "zero_base_simulation_current.json"))
    sub.add_parser("vision-config-test")
    vision_batch = sub.add_parser("vision-question-batch")
    vision_batch.add_argument("--out", required=True)
    vision_batch.add_argument("--start", type=int, default=0)
    vision_batch.add_argument("--count", type=int, default=1)
    vision_batch.add_argument("--profile", default=None)
    vision_batch.add_argument("--max-tokens", type=int, default=1536)
    vision_batch.add_argument("--prompt", default=None)
    sub.add_parser("ocr-config-status")
    verify = sub.add_parser("verify-packet")
    verify.add_argument("--packet", required=True)
    context = sub.add_parser("build-deepseek-context")
    context.add_argument("--student-packet", required=True)
    context.add_argument("--out", required=True)
    validate = sub.add_parser("validate-deepseek-context")
    validate.add_argument("--context", required=True)
    probe = sub.add_parser("verify-deepseek-probe")
    probe.add_argument("--context", required=True)
    probe.add_argument("--response", required=True)
    plan_section = sub.add_parser("plan-section")
    plan_section.add_argument("--section", required=True, help="1/2/3/4 或 1.1/1.2/1.4/微专题1")
    args = parser.parse_args()
    if args.command == "build-chapter1":
        print(json.dumps(build_chapter1(), ensure_ascii=False, indent=2))
    elif args.command == "reward-test":
        print(json.dumps(run_reward_test(ROOT / "data" / "reward-test-state.json"), ensure_ascii=False, indent=2))
    elif args.command == "init-state":
        manifest = load_manifest()
        target = dict(manifest["target_identity"])
        target["section"] = args.section
        store = StateStore.create(args.state, target)
        print(json.dumps({"status": "created", "state": str(store.path), "target_identity": target}, ensure_ascii=False, indent=2))
    elif args.command == "record-attempt":
        store = _state_for(args.state, section=args.section)
        result = store.record_attempt(
            args.item_id,
            independent=args.independent,
            result=args.result,
            hint_level=args.hint_level,
            answer_seen=args.answer_seen,
            process_verified=args.process_verified,
            first_break=args.first_break,
            section=args.section,
            source_anchor=_json_object(args.source_anchor_json),
            visual_status=args.visual_status,
            at=args.at,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "record-near-variant":
        store = _state_for(args.state, section=args.section)
        result = store.record_near_variant(
            args.item_id,
            variant_item_id=args.variant_item_id,
            independent=args.independent,
            result=args.result,
            process_verified=args.process_verified,
            visual_status=args.visual_status,
            source_anchor=_json_object(args.source_anchor_json),
            section=args.section,
            at=args.at,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "review-item":
        store = _state_for(args.state)
        print(json.dumps(store.review_item(args.item_id, result=args.result, process_verified=args.process_verified, at=args.at), ensure_ascii=False, indent=2))
    elif args.command == "complete-section":
        store = _state_for(args.state, section=args.section)
        print(json.dumps(store.complete_section(args.section, args.item_id, required_evidence=args.evidence, at=args.at), ensure_ascii=False, indent=2))
    elif args.command == "pending-reviews":
        store = _state_for(args.state)
        print(json.dumps({"status": "passed", "pending": store.pending_reviews(at=args.at)}, ensure_ascii=False, indent=2))
    elif args.command == "answer-status":
        statuses = []
        for path in sorted((ROOT / "data" / "packets").glob("*/answer_sidecar.json")):
            sidecar = load_json(path)
            answers = sidecar.get("answers", [])
            nonempty = sum(bool(str(item.get("answer_text", "")).strip()) for item in answers)
            statuses.append({"section": sidecar.get("section"), "path": str(path), "total": len(answers), "nonempty": nonempty, "status": "passed" if answers and nonempty == len(answers) else "failed"})
        print(json.dumps({"status": "passed" if statuses and all(item["status"] == "passed" for item in statuses) else "failed", "sections": statuses, "answer_isolation": "answer_sidecar_only"}, ensure_ascii=False, indent=2))
    elif args.command == "deepseek-status":
        statuses = [validate_context(path) for path in sorted((ROOT / "data" / "contexts").glob("*.json"))]
        probe_path = ROOT / "data" / "deepseek_http_probe_1.1.json"
        probe = load_json(probe_path) if probe_path.exists() else {"status": "not_run", "path": str(probe_path)}
        print(json.dumps({"status": "passed" if statuses and all(item["status"] == "passed" for item in statuses) and probe.get("status") == "passed" else "failed", "route_status": "passed" if statuses and all(item.get("route_status") == "passed" for item in statuses) else "failed", "consumer": "deepseek_worker", "contexts": statuses, "independent_probe": probe}, ensure_ascii=False, indent=2))
    elif args.command in {"simulate-five", "simulate-ten"}:
        print(json.dumps(run_ten_person_simulation(args.out), ensure_ascii=False, indent=2))
    elif args.command == "vision-config-test":
        print(json.dumps(test_vision_config(), ensure_ascii=False, indent=2))
    elif args.command == "vision-question-batch":
        items = []
        for packet_path in sorted((ROOT / "data" / "packets").glob("*/packet.json")):
            packet = load_json(packet_path)
            for question in packet.get("questions", []):
                if question.get("visual_status") != "NEEDS_VISION_SIDECAR":
                    continue
                for image in question.get("image_refs", []):
                    items.append((f"{packet['section']}-{question['group']}{question['number']}", image["path"]))
        selected = items[args.start : args.start + args.count]
        print(json.dumps(sidecar_for_question_images(selected, output_path=args.out, profile=args.profile, max_tokens=args.max_tokens, prompt=args.prompt), ensure_ascii=False, indent=2))
    elif args.command == "ocr-config-status":
        print(json.dumps(ocr_config_status(), ensure_ascii=False, indent=2))
    elif args.command == "verify-packet":
        print(json.dumps(verify_packet(args.packet), ensure_ascii=False, indent=2))
    elif args.command == "build-deepseek-context":
        print(json.dumps(build_context(args.student_packet, output_path=args.out), ensure_ascii=False, indent=2))
    elif args.command == "validate-deepseek-context":
        print(json.dumps(validate_context(args.context), ensure_ascii=False, indent=2))
    elif args.command == "verify-deepseek-probe":
        print(json.dumps(verify_worker_probe(args.context, args.response), ensure_ascii=False, indent=2))
    elif args.command == "plan-section":
        plan_path = ROOT / "data" / "chapter1_learning_plan.json"
        if not plan_path.exists():
            build_chapter1()
        plan = load_json(plan_path)
        print(json.dumps(select_section_plan(plan, args.section), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
