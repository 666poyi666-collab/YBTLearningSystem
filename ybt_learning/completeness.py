from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def expected_question_keys(group_ranges: dict[str, list[int]]) -> set[str]:
    return {
        f"{group}{number}"
        for group, bounds in group_ranges.items()
        for number in range(int(bounds[0]), int(bounds[1]) + 1)
    }


def packet_question_keys(packet: dict[str, Any]) -> set[str]:
    return {
        f"{item.get('group')}{item.get('number')}"
        for item in packet.get("exercise_questions", [])
    }


_GROUP_MARKER_RE = re.compile(r"^\s*#{0,6}\s*([ABC])\s*组\b")
_NUMBERED_LINE_RE = re.compile(
    r"^\s*#{0,6}\s*(?:\\)?(?P<number>\d{1,2})\s*(?:\\?[.．]|[、。:：])\s*(?P<rest>.*)$"
)


def ocr_question_scan(
    ocr_root: Path,
    ocr_range: list[int] | tuple[int, int],
    question_groups: dict[str, list[int]],
) -> tuple[set[str], set[str]]:
    """Extract printed A/B/C question numbers from answer-free OCR pages.

    The manifest is intentionally not the only source for question coverage:
    this scan reads the OCR source pages independently and then compares its
    result with both the manifest ranges and the generated packet.
    """

    if len(ocr_range) != 2:
        return set(), set()
    allowed = expected_question_keys(question_groups)
    found: set[str] = set()
    out_of_range: set[str] = set()
    first_doc, last_doc = int(ocr_range[0]), int(ocr_range[1])
    current_group: str | None = None
    for number in range(first_doc, last_doc + 1):
        path = ocr_root / f"doc_{number}.md"
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        for index, line in enumerate(lines):
            marker = _GROUP_MARKER_RE.match(line)
            if marker:
                current_group = marker.group(1)
                continue
            if current_group is None:
                continue
            match = _NUMBERED_LINE_RE.match(line)
            if not match:
                continue
            question_number = int(match.group("number"))
            question_key = f"{current_group}{question_number}"
            rest = match.group("rest").strip()
            next_nonempty = ""
            for candidate in lines[index + 1 :]:
                if candidate.strip():
                    next_nonempty = candidate.strip()
                    break
            # A question heading normally contains its year or opening
            # parenthesis. The next-line check covers OCR split headings such
            # as ``12\\.`` followed by ``（2025...``.
            looks_like_heading = bool(
                re.search(r"20\d{2}|^[（(]|^\\?$", rest)
                or re.search(r"20\d{2}|^[（(]", next_nonempty)
            )
            if looks_like_heading and question_key not in allowed:
                out_of_range.add(question_key)
            elif looks_like_heading:
                found.add(question_key)
    return found, out_of_range


def ocr_question_keys(
    ocr_root: Path,
    ocr_range: list[int] | tuple[int, int],
    question_groups: dict[str, list[int]],
) -> set[str]:
    """Compatibility wrapper returning only in-range OCR question keys."""
    found, _ = ocr_question_scan(ocr_root, ocr_range, question_groups)
    return found


def _recovery_anchor_is_valid(
    recovery: dict[str, Any],
    ocr_root: Path,
    ocr_range: list[int] | tuple[int, int],
) -> bool:
    if recovery.get("source_kind") != "primary_ocr":
        return False
    source_doc = recovery.get("source_doc")
    if not isinstance(source_doc, int) or not (int(ocr_range[0]) <= source_doc <= int(ocr_range[1])):
        return False
    source = ocr_root / f"doc_{source_doc}.md"
    if not source.is_file() or not recovery.get("start_regex"):
        return False
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    if re.search(str(recovery["start_regex"]), text, flags=re.M) is None:
        return False
    end_regex = recovery.get("end_regex")
    return not end_regex or re.search(str(end_regex), text, flags=re.M) is not None


def _cycle_item_keys(packet: dict[str, Any]) -> dict[str, list[str]]:
    cycles = packet.get("learning_cycles", [])
    return {
        "examples": [
            str(item.get("example_number"))
            for cycle in cycles
            for item in cycle.get("worked_examples", [])
        ],
        "variants": [
            str(item.get("item_id"))
            for cycle in cycles
            for item in cycle.get("direct_variants", [])
        ],
        "exercises": [
            f"{item.get('group')}{item.get('number')}"
            for cycle in cycles
            for item in cycle.get("exercise_questions", [])
        ],
    }


def _packet_item_keys(packet: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "examples": [str(item.get("example_number")) for item in packet.get("worked_examples", [])],
        "variants": [str(item.get("item_id")) for item in packet.get("direct_variants", [])],
        "exercises": packet_question_keys(packet),
    }


def _resolve_ocr_root(root: Path, manifest: dict[str, Any]) -> Path:
    """Resolve legacy OCR provenance to the repository's active OCR snapshot.

    Manifests intentionally preserve the original machine path as provenance,
    but executable audits must use the checked-in current live run when that
    path is unavailable after a device migration.
    """
    declared = Path(str(manifest.get("source_evidence", {}).get("ocr_root", "")))
    if declared.is_dir():
        return declared
    candidates = (
        root / "data" / "ocr_live_current" / "first_chapter_69",
        root / "data" / "ocr_live_full",
    )
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("doc_*.md")):
            return candidate
    return declared


def audit_chapter1(root: str | Path) -> dict[str, Any]:
    """Audit the answer-free chapter inventory without opening answer sidecars.

    The manifest remains the source-of-truth for expected counts and printed
    exercise ranges. The audit cross-checks generated packets, cycles, OCR
    document continuity, and the question coverage ledger. It deliberately
    does not inspect answer text.
    """

    root = Path(root)
    manifest = load_json(root / "chapter1_manifest.json")
    coverage = load_json(root / "data" / "question_coverage.json")
    coverage_by_section: dict[str, set[str]] = {}
    for item in coverage.get("questions", []):
        coverage_by_section.setdefault(str(item.get("section")), set()).add(str(item.get("question_key")))

    findings: list[dict[str, Any]] = []
    ocr_questions_by_section: dict[str, list[str]] = {}
    ocr_out_of_range_by_section: dict[str, list[str]] = {}
    known_recoveries = {
        (
            str(item.get("section")),
            str(item.get("group")) + str(item.get("number")),
        ): item
        for item in manifest.get("known_visual_recoveries", [])
    }

    def finding(code: str, status: str, message: str, section: str | None = None) -> None:
        findings.append({"code": code, "status": status, "message": message, "section": section})

    manifest_total = manifest.get("source_evidence", {}).get("learning_item_counts", {})
    actual_total = {"worked_examples": 0, "direct_variants": 0, "abc_exercises": 0, "total_numbered_learning_items": 0}

    for section in manifest.get("sections", []):
        section_id = str(section["id"])
        folder = section_folder(section_id)
        packet_path = root / "data" / "packets" / folder / "learning_packet.json"
        packet_json_path = root / "data" / "packets" / folder / "packet.json"
        if not packet_path.exists() or not packet_json_path.exists():
            finding("packet_missing", "blocked", "section packet artifacts are missing", section_id)
            continue

        packet = load_json(packet_path)
        raw_packet = load_json(packet_json_path)
        expected_counts = section.get("learning_item_counts", {})
        packet_counts = packet.get("counts", {})
        for key in ("worked_examples", "direct_variants", "abc_exercises", "total_numbered_learning_items"):
            expected = int(expected_counts.get("total" if key == "total_numbered_learning_items" else key, 0))
            actual = int(packet_counts.get(key, 0))
            actual_total[key] += actual
            if expected != actual:
                finding("count_mismatch", "blocked", f"{key}: manifest={expected}, packet={actual}", section_id)

        if packet.get("status") != "VERIFIED" or packet.get("unresolved"):
            finding("packet_not_verified", "blocked", "learning packet is not VERIFIED or has unresolved entries", section_id)

        expected_questions = expected_question_keys(section.get("question_groups", {}))
        packet_questions = packet_question_keys(packet)
        raw_questions = {
            f"{item.get('group')}{item.get('number')}"
            for item in raw_packet.get("questions", [])
        }
        if packet_questions != expected_questions:
            finding(
                "question_range_mismatch",
                "blocked",
                f"expected={sorted(expected_questions)}, observed={sorted(packet_questions)}",
                section_id,
            )
        if raw_questions != expected_questions:
            finding(
                "raw_ocr_packet_manifest_mismatch",
                "blocked",
                f"expected={sorted(expected_questions)}, raw_packet={sorted(raw_questions)}",
                section_id,
            )
        if coverage_by_section.get(section_id, set()) != expected_questions:
            finding("coverage_range_mismatch", "blocked", "question coverage keys do not equal manifest ranges", section_id)

        ocr_start, ocr_end = section.get("ocr_docs", [None, None])
        ocr_root = _resolve_ocr_root(root, manifest)
        ocr_questions, ocr_out_of_range = (
            ocr_question_scan(ocr_root, [ocr_start, ocr_end], section.get("question_groups", {}))
            if ocr_start is not None and ocr_end is not None
            else (set(), set())
        )
        ocr_questions_by_section[section_id] = sorted(ocr_questions)
        ocr_out_of_range_by_section[section_id] = sorted(ocr_out_of_range)
        if ocr_out_of_range:
            finding(
                "ocr_question_out_of_range",
                "blocked",
                f"expected={sorted(expected_questions)}, OCR out of range={sorted(ocr_out_of_range)}",
                section_id,
            )
        missing_ocr_questions = expected_questions - ocr_questions
        unanchored_missing = []
        invalid_recovery = []
        if ocr_start is None or ocr_end is None:
            unanchored_missing.extend(sorted(missing_ocr_questions))
        else:
            for question_key in sorted(missing_ocr_questions):
                recovery = known_recoveries.get((section_id, question_key))
                if not recovery:
                    unanchored_missing.append(question_key)
                elif not _recovery_anchor_is_valid(recovery, ocr_root, [ocr_start, ocr_end]):
                    invalid_recovery.append(question_key)
        if unanchored_missing or invalid_recovery:
            finding(
                "ocr_question_labels_unanchored",
                "blocked",
                f"missing={sorted(missing_ocr_questions)}, unanchored={unanchored_missing}, invalid_recovery={invalid_recovery}",
                section_id,
            )
        elif missing_ocr_questions:
            finding(
                "ocr_question_labels_incomplete",
                "warning",
                f"OCR numbering scan found={sorted(ocr_questions)}; missing keys have verified primary OCR recovery anchors: {sorted(missing_ocr_questions)}",
                section_id,
            )
        recovery_missing_allowed = bool(missing_ocr_questions) and not unanchored_missing and not invalid_recovery
        if raw_questions != ocr_questions and not (
            raw_questions == expected_questions and recovery_missing_allowed
        ):
            finding(
                "packet_ocr_question_mismatch",
                "blocked",
                f"raw_packet={sorted(raw_questions)}, OCR={sorted(ocr_questions)}",
                section_id,
            )

        cycle_keys = _cycle_item_keys(packet)
        packet_keys = _packet_item_keys(packet)
        for kind in ("examples", "variants", "exercises"):
            cycle_values = cycle_keys[kind]
            packet_values = list(packet_keys[kind])
            if sorted(cycle_values) != sorted(packet_values) or len(cycle_values) != len(set(cycle_values)):
                finding("cycle_item_mismatch", "blocked", f"{kind} are not covered exactly once", section_id)

        if ocr_root and ocr_start is not None and ocr_end is not None:
            expected_docs = {f"doc_{number}.md" for number in range(int(ocr_start), int(ocr_end) + 1)}
            observed_docs = {path.name for path in ocr_root.glob("doc_*.md") if int(path.stem.split("_")[-1]) in range(int(ocr_start), int(ocr_end) + 1)}
            if observed_docs != expected_docs:
                finding("ocr_doc_range_mismatch", "blocked", "OCR document range is incomplete", section_id)

        raw_question_qids = {
            f"{item.get('group')}{item.get('number')}": str(item.get("qid"))
            for item in raw_packet.get("questions", [])
        }
        ledger_qids = {
            str(item.get("question_key")): str(item.get("qid"))
            for item in coverage.get("questions", [])
            if str(item.get("section")) == section_id
        }
        if raw_question_qids != ledger_qids:
            finding("qid_cross_artifact_mismatch", "blocked", "packet and question coverage qid maps differ", section_id)

    expected_total = {
        "worked_examples": int(manifest_total.get("worked_examples", 0)),
        "direct_variants": int(manifest_total.get("direct_variants", 0)),
        "abc_exercises": int(manifest_total.get("abc_exercises", 0)),
        "total_numbered_learning_items": int(manifest_total.get("total_numbered_learning_items", 0)),
    }
    if actual_total != expected_total:
        finding("chapter_total_mismatch", "blocked", f"manifest={expected_total}, packets={actual_total}")

    question_count = int(coverage.get("question_count", 0))
    expected_question_count = sum(len(expected_question_keys(section.get("question_groups", {}))) for section in manifest.get("sections", []))
    if question_count != expected_question_count:
        finding("coverage_total_mismatch", "blocked", f"coverage={question_count}, manifest={expected_question_count}")

    blocked = [item for item in findings if item["status"] == "blocked"]
    return {
        "schema_version": 1,
        "artifact": "ANSWER_FREE_LEARNING_COMPLETENESS_AUDIT",
        "status": "blocked" if blocked else "passed",
        "manifest_totals": expected_total,
        "packet_totals": actual_total,
        "expected_question_count": expected_question_count,
        "coverage_question_count": question_count,
        "ocr_question_keys": ocr_questions_by_section,
        "ocr_out_of_range_keys": ocr_out_of_range_by_section,
        "findings": findings,
    }


def assert_chapter1_complete(root: str | Path) -> dict[str, Any]:
    result = audit_chapter1(root)
    if result["status"] != "passed":
        details = "; ".join(f"{item['code']}: {item['message']}" for item in result["findings"])
        raise AssertionError(details or "chapter completeness audit failed")
    return result
