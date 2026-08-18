from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def section_from_hint(question_hint: str) -> str | None:
    """Derive the manifest section from the canonical section-group-number key."""
    if not isinstance(question_hint, str) or "-" not in question_hint:
        return None
    return question_hint.rsplit("-", 1)[0]


def image_sha256(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_student_visual(row: dict) -> bool:
    """Reject answer-book OCR/crops before they reach packet-facing evidence."""
    image = str(row.get("image", "")).lower()
    provenance = row.get("source_provenance") or {}
    source_pdf = str(provenance.get("source_pdf", "")).lower() if isinstance(provenance, dict) else ""
    chinese_answer_book = ("答案册" in image or "答案册" in source_pdf) and ("无答案册" not in image and "无答案册" not in source_pdf)
    banned = ("worker-02-solutions", "answer_book", "answer-book", "answerbook")
    return not (chinese_answer_book or any(marker in image or marker in source_pdf for marker in banned))


def historical_verified_source_rows() -> list[dict]:
    """Recover only exact-hash source-visual successes from the prior matrix.

    A provider retry may return malformed output after a successful call.  The
    matrix is usable as a historical evidence index only when the immutable
    crop, source PDF, and derived OCR image still match their recorded hashes.
    """
    matrix_path = ROOT / "reports" / "simulation_matrix_current.json"
    if not matrix_path.is_file():
        return []
    try:
        payload = read(matrix_path)
    except (OSError, json.JSONDecodeError):
        return []
    rows: list[dict] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if value.get("question_hint") and value.get("confidence") in {"E1", "E2"} and value.get("structured"):
                image = Path(str(value.get("image", "")))
                provenance = value.get("source_provenance")
                if (
                    image.is_file()
                    and str(image).startswith(str(ROOT / "reports" / "source_visuals2"))
                    and isinstance(provenance, dict)
                    and provenance.get("source_kind") == "high_resolution_source_pdf_crop"
                ):
                    source_pdf = Path(str(provenance.get("source_pdf", "")))
                    derived = Path(str(provenance.get("derived_from_image_path", "")))
                    image_hash = image_sha256(str(image))
                    source_hash = image_sha256(str(source_pdf))
                    derived_hash = image_sha256(str(derived))
                    if (
                        image_hash
                        and image_hash == value.get("image_sha256")
                        and source_hash
                        and source_hash == provenance.get("source_pdf_sha256")
                        and derived_hash
                        and derived_hash == provenance.get("derived_from_image_sha256")
                        and is_student_visual(value)
                    ):
                        rows.append({
                            "status": "passed",
                            "question_hint": value.get("question_hint"),
                            "section": value.get("section") or section_from_hint(value.get("question_hint")),
                            "image": str(image),
                            "image_sha256": image_hash,
                            "confidence": value.get("confidence"),
                            "model": value.get("model"),
                            "structured": value.get("structured"),
                            "source_provenance": provenance,
                            "historical_reused": True,
                        })
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    unique: dict[tuple[str | None, str | None], dict] = {}
    for row in rows:
        unique[(row.get("question_hint"), row.get("image"))] = row
    return list(unique.values())


def main() -> int:
    probe_path = Path(__import__("sys").argv[1])
    probe = read(probe_path)
    results = [
        dict(item)
        for item in probe.get("results", [])
        if item.get("question_hint")
        and item.get("status") == "passed"
        and item.get("confidence") in {"E1", "E2"}
        and item.get("structured")
        and is_student_visual(item)
    ]
    results.extend(historical_verified_source_rows())
    for item in results:
        # Older probe files were generated before the section field was
        # persisted.  Backfill it deterministically from the canonical hint;
        # never leave a result to be silently filtered out by build_chapter1.
        item.setdefault("section", section_from_hint(item.get("question_hint")))
        if item.get("image_sha256") is None:
            item["image_sha256"] = image_sha256(item.get("image"))
    full_path = ROOT / "data" / "vision_sidecar_full.json"
    full = read(full_path) if full_path.exists() else {"schema_version": "7.1", "results": []}
    full["results"] = [item for item in full.get("results", []) if is_student_visual(item)]
    # Keep one result per question+image, not one result per question.  A
    # question may contain two figures (micro专题1-B1 and 1.4-C10 are known
    # examples); collapsing by hint would silently discard one visual fact.
    def result_key(item: dict) -> tuple[str | None, str | None]:
        return item.get("question_hint"), item.get("image_sha256") or item.get("image")

    def is_passed(item: dict) -> bool:
        return item.get("status") == "passed" and item.get("confidence") in {"E1", "E2"} and bool(item.get("structured"))

    by_key = {result_key(item): item for item in full.get("results", []) if item.get("question_hint")}
    for item in full.get("results", []):
        if not is_student_visual(item):
            continue
        item.setdefault("section", section_from_hint(item.get("question_hint")))
        if item.get("image_sha256") is None:
            item["image_sha256"] = image_sha256(item.get("image"))
    # Rebuild the key map after backfilling legacy section fields.
    by_key = {result_key(item): item for item in full.get("results", []) if item.get("question_hint")}
    for item in results:
        key = result_key(item)
        previous = by_key.get(key)
        # A transient empty/truncated retry is diagnostic only.  It must not
        # erase an earlier provider-backed E1/E2 result for the same immutable
        # image; the most recent *passed* result wins.
        if previous is None or is_passed(item) or not is_passed(previous):
            by_key[key] = item
    merged_rows = list(by_key.values())
    diagnostic_rows = [
        *full.get("diagnostic_results", []),
        *(item for item in merged_rows if not is_passed(item)),
    ]
    diagnostics_by_key = {result_key(item): item for item in diagnostic_rows if item.get("question_hint")}
    full["diagnostic_results"] = list(diagnostics_by_key.values())
    full["results"] = [item for item in merged_rows if is_passed(item)]
    full["status"] = "passed" if full["results"] else "unverified"
    write(full_path, full)

    verified = [
        {
            "question_hint": item.get("question_hint"),
            "section": item.get("section"),
            "image": item.get("image"),
            "image_sha256": item.get("image_sha256"),
            "model": item.get("model"),
            "confidence": item.get("confidence"),
            "structured": item.get("structured"),
            "source_provenance": item.get("source_provenance"),
        }
        for item in full["results"]
        if item.get("status") == "passed" and item.get("confidence") in {"E1", "E2"} and item.get("structured")
    ]
    providers = sorted({str(item.get("model") or "unknown") for item in verified})
    live_path = ROOT / "data" / "vision_live_evidence.json"
    previous_live = read(live_path) if live_path.exists() else {}
    source_probes = set(previous_live.get("source_probes", []))
    source_probes.update({str(probe_path), "data/vision_live_probe_2.json", "data/vision_probe_b4.json"})
    evidence = {
        "schema_version": "7.1",
        "status": "passed" if verified else "unverified",
        "provider": "mixed verified visual providers: " + ", ".join(providers),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verified_count": len(verified),
        "results": verified,
        "structured": verified[0]["structured"] if verified else None,
        "source_probes": sorted(source_probes),
        "consumer_guard": "Only complete E1/E2 structured results may enter packets; all other images remain blocked.",
    }
    write(live_path, evidence)
    print(json.dumps({"merged": [item["question_hint"] for item in results], "verified_count": len(verified), "full_status": full["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
