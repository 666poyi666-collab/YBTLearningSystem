#!/usr/bin/env python3
"""Classify every previously unclassified A/B/C item against section type prototypes."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/item_type_classification.json"
REPORT = ROOT / "reports/deep_simulation/type-classification.json"

DOMAIN_TERMS = (
    "斜率", "倾斜角", "方向向量", "直线方程", "平行", "垂直", "交点", "距离", "对称", "轨迹", "圆心", "半径",
    "切线", "弦", "最值", "位置关系", "椭圆", "双曲线", "抛物线", "焦点", "离心率", "准线", "中点弦", "定点",
    "定值", "面积", "长度", "角度", "数列", "递推", "通项", "等差", "等比", "前n项和", "求和", "裂项", "错位相减",
    "归纳", "单调", "周期", "放缩", "导数", "切点", "复合函数", "原函数", "极值", "零点", "参数", "恒成立", "不等式",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def section_folder(section_id: str) -> str:
    return section_id.replace("+", "_")


def normalized(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()


def features(text: str) -> Counter[str]:
    compact = normalized(text)
    result: Counter[str] = Counter()
    for size, weight in ((2, 1), (3, 2), (4, 3)):
        for index in range(max(0, len(compact) - size + 1)):
            result[compact[index:index + size]] += weight
    for term in DOMAIN_TERMS:
        if term in text:
            result[f"TERM:{term}"] += 12
    for symbol in re.findall(r"[A-Za-z]+|\d+|[=<>]", text):
        result[f"SYM:{symbol.lower()}"] += 2
    return result


def cosine(left: Counter[str], right: Counter[str]) -> float:
    common = set(left) & set(right)
    numerator = sum(left[key] * right[key] for key in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def item_key(item: dict[str, Any]) -> str:
    return f"{item.get('group')}{item.get('number')}"


def main() -> int:
    rows: list[dict[str, Any]] = []
    section_summaries: list[dict[str, Any]] = []
    expected_pending = 0

    for chapter in range(1, 6):
        manifest_path = ROOT / f"chapter{chapter}_manifest.json"
        manifest = load(manifest_path)
        manifest_changed = False
        for section in manifest.get("sections", []):
            section_id = str(section["id"])
            if section_id == "1.1":
                continue
            packet = load(ROOT / "data/packets" / section_folder(section_id) / "learning_packet.json")
            packet_cycles = {str(cycle["cycle_id"]): cycle for cycle in packet.get("learning_cycles", [])}
            manifest_cycles = {str(cycle["id"]): cycle for cycle in section.get("learning_cycles", [])}
            prototypes: dict[str, Counter[str]] = {}
            prototype_evidence: dict[str, list[str]] = {}
            for cycle in packet.get("learning_cycles", []):
                manifest_cycle = manifest_cycles.get(str(cycle["cycle_id"]), {})
                if str(manifest_cycle.get("type_mapping_status") or "").startswith(("MACHINE_", "MULTI_AGENT_")):
                    continue
                type_refs = [str(value) for value in cycle.get("type_refs", []) if str(value).strip()]
                if not type_refs:
                    continue
                text_parts = [str(cycle.get("title") or ""), *type_refs]
                labels = []
                for item in [*cycle.get("worked_examples", []), *cycle.get("direct_variants", []), *cycle.get("exercise_questions", [])]:
                    text_parts.append(str(item.get("question_text") or ""))
                    labels.append(str(item.get("label") or item_key(item)))
                joined = "\n".join(text_parts)
                for type_ref in type_refs:
                    prototypes[type_ref] = features(joined)
                    prototype_evidence[type_ref] = labels
            if not prototypes:
                for label in section.get("type_labels", []):
                    prototypes[str(label)] = features(str(label))
                    prototype_evidence[str(label)] = []

            section_rows = []
            for cycle_id, cycle in packet_cycles.items():
                manifest_cycle = manifest_cycles.get(cycle_id)
                if not manifest_cycle:
                    continue
                status = str(manifest_cycle.get("type_mapping_status") or "")
                needs_classification = status == "PENDING_ITEM_LEVEL_CLASSIFICATION" or status.startswith("MACHINE_SEMANTIC_CLASSIFIED") or (
                    chapter == 1 and bool(cycle.get("exercise_questions")) and not cycle.get("type_refs")
                )
                if not needs_classification:
                    continue
                items = cycle.get("exercise_questions", [])
                expected_pending += len(items)
                assignments = []
                for item in items:
                    text = str(item.get("question_text") or "")
                    item_features = features(text)
                    scored = sorted(
                        ((cosine(item_features, prototype), label) for label, prototype in prototypes.items()),
                        reverse=True,
                    )
                    best_score, best_label = scored[0]
                    second_score = scored[1][0] if len(scored) > 1 else 0.0
                    margin = max(0.0, best_score - second_score)
                    confidence = "high" if best_score >= 0.26 and margin >= 0.04 else "medium" if best_score >= 0.12 else "low"
                    matched_terms = [term for term in DOMAIN_TERMS if term in text and term in best_label]
                    record = {
                        "chapter": chapter,
                        "section": section_id,
                        "cycle_id": cycle_id,
                        "item_id": item.get("qid"),
                        "item_label": item_key(item),
                        "type_title": best_label,
                        "score": round(best_score, 6),
                        "runner_up_score": round(second_score, 6),
                        "margin": round(margin, 6),
                        "confidence": confidence,
                        "matched_terms": matched_terms,
                        "question_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        "prototype_item_labels": prototype_evidence.get(best_label, []),
                        "classification_method": "character_ngram_plus_domain_terms",
                        "review_status": "awaiting_multi_agent_semantic_review",
                    }
                    assignments.append({
                        "item_id": item.get("qid"),
                        "item_label": item_key(item),
                        "type_title": best_label,
                        "confidence": confidence,
                        "evidence_ref": f"data/item_type_classification.json#{item.get('qid')}",
                    })
                    rows.append(record)
                    section_rows.append(record)
                manifest_cycle["item_type_assignments"] = assignments
                manifest_cycle["type_refs"] = list(dict.fromkeys(row["type_title"] for row in assignments))
                manifest_cycle["type_mapping_status"] = "MACHINE_SEMANTIC_CLASSIFIED_AWAITING_MULTI_AGENT_REVIEW"
                manifest_cycle.pop("unclassified_item_ids", None)
                manifest_changed = True

            if section_rows:
                section_summaries.append({
                    "chapter": chapter,
                    "section": section_id,
                    "items": len(section_rows),
                    "high": sum(row["confidence"] == "high" for row in section_rows),
                    "medium": sum(row["confidence"] == "medium" for row in section_rows),
                    "low": sum(row["confidence"] == "low" for row in section_rows),
                })
        if manifest_changed:
            save(manifest_path, manifest)

    if expected_pending != 512 or len(rows) != 512:
        raise ValueError(f"classification coverage mismatch: expected_pending={expected_pending}, rows={len(rows)}")
    payload = {
        "schema_version": "ybt-item-type-classification-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": len(rows),
        "status": "awaiting_multi_agent_semantic_review",
        "rows": rows,
    }
    save(OUTPUT, payload)
    report = {
        "schema_version": "ybt-item-type-classification-report-v1",
        "generated_at": payload["generated_at"],
        "items": len(rows),
        "sections": len(section_summaries),
        "confidence": {
            "high": sum(row["confidence"] == "high" for row in rows),
            "medium": sum(row["confidence"] == "medium" for row in rows),
            "low": sum(row["confidence"] == "low" for row in rows),
        },
        "section_summaries": section_summaries,
        "status": "awaiting_multi_agent_semantic_review",
    }
    save(REPORT, report)
    print(json.dumps({"items": len(rows), "sections": len(section_summaries), "confidence": report["confidence"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
