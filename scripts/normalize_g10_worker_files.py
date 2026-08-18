#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G-10 worker 分片机械归一化（只改顶层/枚举/题号标识，不改任何内容与判定）。

背景：5 个 G-10 worker 输出在顶层 schema 约定（section/worker_status/布尔边界）、
hint_level 枚举（0/NONE）、教材习题 item_id（Q-* / 1.1-B8 前缀）上与合并契约不一致。
本脚本做确定性映射并输出归一化日志，随后由 merge_structured_zero_base_simulation.py
的严格校验兜底（题项闭包、哈希、边界、必填字段全部仍会被检查）。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATION = "G-20260816-10"
HINT_MAP = {"0": "none", "1": "minimal", "2": "full", "NONE": "none", "MINIMAL": "minimal", "FULL": "full"}
# 教材习题 item_id 映射：qid/带前缀标识 -> 契约题号（label 作为附加字段保留）
EXERCISE_ID_MAP = {
    "Q-65729f8347757586": "B12",
    "Q-a5a0d0efe5d430ca": "B6",
    "Q-c541e3eee1efc530": "B7",
    "1.1-B8": "B8",
    "1.1-C13": "C13",
    "1.1-C14": "C14",
}


def derive_worker_status(item_results: list[dict]) -> str:
    verdicts = {str(i.get("verdict", "")).upper() for i in item_results}
    if verdicts <= {"PASS"}:
        return "PASS"
    if verdicts <= {"BLOCKED"}:
        return "BLOCKED"
    if "FAIL" in verdicts:
        return "FAIL"
    return "PARTIAL"


def fix_item(item: dict) -> dict:
    out = dict(item)
    hint = out.get("hint_level")
    if isinstance(hint, int):
        hint = str(hint)
    if isinstance(hint, str) and hint in HINT_MAP:
        out["hint_level"] = HINT_MAP[hint]
    verdict = out.get("verdict")
    if isinstance(verdict, str):
        out["verdict"] = verdict.upper()
    iid = str(out.get("item_id", ""))
    if iid in EXERCISE_ID_MAP:
        out["item_id"] = EXERCISE_ID_MAP[iid]
    elif iid.startswith("1.1-") and iid in EXERCISE_ID_MAP:
        out["item_id"] = EXERCISE_ID_MAP[iid]
    for flag in ("answer_sidecar_read", "human_acceptance_not_proven"):
        v = out.get(flag)
        if isinstance(v, str):
            out[flag] = v.strip().lower() == "true"
    return out


def fix_method_check(m: dict) -> dict:
    out = dict(m)
    hint = out.get("hint_level")
    if isinstance(hint, int):
        hint = str(hint)
    if isinstance(hint, str) and hint in HINT_MAP:
        out["hint_level"] = HINT_MAP[hint]
    verdict = out.get("verdict")
    if isinstance(verdict, str):
        out["verdict"] = verdict.upper()
    for flag in ("answer_sidecar_read", "human_acceptance_not_proven"):
        v = out.get(flag)
        if isinstance(v, str):
            out[flag] = v.strip().lower() == "true"
    return out


def main() -> int:
    changes: list[dict] = []
    for n in range(1, 6):
        path = ROOT / "reports" / "zero_base_cycles" / f"1.1-structured-worker-{n}-g10.json"
        if not path.is_file():
            print(f"missing {path.name}")
            return 2
        data = json.loads(path.read_text(encoding="utf-8"))
        before = json.dumps(data, ensure_ascii=False, sort_keys=True)
        # 顶层
        if data.get("section") != "1.1":
            data["section"] = "1.1"
            changes.append({"worker": n, "field": "section", "value": "1.1"})
        if data.get("schema_version") not in ("1.1",):
            data["schema_version"] = "1.1"
            changes.append({"worker": n, "field": "schema_version", "value": "1.1"})
        for flag in ("answer_sidecar_read", "human_acceptance_not_proven"):
            v = data.get(flag)
            if isinstance(v, str):
                data[flag] = v.strip().lower() == "true"
                changes.append({"worker": n, "field": flag, "value": data[flag]})
        if data.get("worker_status") not in {"PASS", "PARTIAL", "BLOCKED", "FAIL"}:
            old = data.get("worker_status")
            data["worker_status"] = derive_worker_status(data.get("item_results", []))
            changes.append({"worker": n, "field": "worker_status", "from": old, "value": data["worker_status"]})
        # 题项与方法检查
        items = [fix_item(i) for i in data.get("item_results", [])]
        checks = [fix_method_check(m) for m in data.get("method_check_results", [])]
        data["item_results"] = items
        data["method_check_results"] = checks
        after = json.dumps(data, ensure_ascii=False, sort_keys=True)
        if after != before:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changes.append({"worker": n, "rewritten": True})
    log = ROOT / "reports" / "builds" / "g10-normalization-notes.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(
        {"purpose": "机械归一化 G-10 worker 分片顶层约定/枚举/教材习题 item_id；内容与 verdict 未改动；严格合并校验仍全部生效",
         "generation": GENERATION, "changes": changes}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(changes, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
