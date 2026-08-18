from __future__ import annotations

from pathlib import Path

from .common import load_json


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_manifest(path: str | Path | None = None) -> dict:
    manifest_path = Path(path or project_root() / "chapter1_manifest.json")
    manifest = load_json(manifest_path)
    # bridge_micro_lessons.json is the canonical answer-free curriculum
    # registry.  Project its global target keys into every section so the
    # raw manifest, generated plan, coverage ledger and DeepSeek contexts do
    # not drift apart again.
    bridge_path = manifest_path.parent / "data" / "bridge_micro_lessons.json"
    bridge_catalog = load_json(bridge_path) if bridge_path.exists() else None
    if manifest and bridge_catalog:
        for section in manifest.get("sections", []):
            section_id = section.get("id")
            projected = []
            for unit in bridge_catalog.get("units", []):
                if section_id not in unit.get("sections", []):
                    continue
                item = dict(unit)
                global_targets = list(item.get("target_questions", []))
                prefix = f"{section_id}-"
                item["target_question_keys"] = global_targets
                item["target_questions"] = [key[len(prefix):] for key in global_targets if key.startswith(prefix)]
                item["source_status"] = item.get("status", "UNKNOWN")
                item["release_status"] = item.get("status", "UNKNOWN")
                projected.append(item)
            section["bridge_units"] = projected
        manifest.setdefault("source_evidence", {})["bridge_source_of_truth"] = "data/bridge_micro_lessons.json"
    return manifest


def section_map(manifest: dict) -> dict[str, dict]:
    return {item["id"]: item for item in manifest["sections"]}
