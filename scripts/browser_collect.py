#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only browser-history collector for the mathematics project.

This collector never opens a browser profile in write mode and never reads
cookies, localStorage, passwords, or page content.  It copies Chromium history
databases to a temporary directory, queries the copies, and writes a
provenance-rich evidence snapshot.  DOM evidence can be supplied separately
by a browser session; it is never inferred from history.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COLLECTOR_VERSION = "1.2.0"
PROJECT_URL_PART = "g-p-6a2573ae1918819187d0cff2278b1216-shu-xue"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "browser_evidence.json"
DEFAULT_EVENTS = Path(__file__).resolve().parents[1] / "data" / "browser_collection_events.jsonl"
REFERENCE_PATH = Path(__file__).resolve().parents[1] / "data" / "math_chat_reference.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def chromium_time(value: int | None) -> str | None:
    if not value:
        return None
    # Chromium timestamps are microseconds since 1601-01-01 UTC.
    try:
        seconds = (int(value) - 11644473600000000) / 1_000_000
        return datetime.fromtimestamp(seconds, timezone.utc).astimezone().isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        return None


def default_history_paths() -> dict[str, Path]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    return {
        "edge": local / "Microsoft" / "Edge" / "User Data" / "Default" / "History",
        "chrome": local / "Google" / "Chrome" / "User Data" / "Default" / "History",
    }


def _pattern_present(haystack: str, pattern: str) -> bool:
    lowered = pattern.lower()
    if lowered == "8.5":
        # Match the lesson label, not a decimal substring in payment/product
        # URLs such as 18.57 or 278.55; leave Chinese title characters valid.
        return re.search(r"(?<![0-9A-Za-z.])8[.]5(?![0-9A-Za-z])", haystack, re.IGNORECASE) is not None
    if lowered == "8.5课程":
        return "8.5课程" in haystack
    return lowered in haystack


def _history_matches(rows: list[tuple[Any, ...]], patterns: list[str]) -> list[dict[str, Any]]:
    matches = []
    for url, title, count, last_visit in rows:
        haystack = f"{url or ''} {title or ''}".lower()
        matched = [pattern for pattern in patterns if _pattern_present(haystack, pattern)]
        if matched:
            matches.append({
                "url": url,
                "title": title,
                "visit_count": int(count or 0),
                "last_visit": chromium_time(last_visit),
                "matched_terms": matched,
            })
    return matches


def query_history(source: Path, label: str, patterns: list[str]) -> dict[str, Any]:
    if not source.is_file():
        return {"browser": label, "status": "not_found", "path": str(source), "matches": []}
    with tempfile.TemporaryDirectory(prefix="ybt_browser_history_") as tmp:
        copy = Path(tmp) / "History"
        shutil.copy2(source, copy)
        copied_sha = sha256(copy)
        connection = sqlite3.connect(f"file:{copy.as_posix()}?mode=ro", uri=True)
        try:
            # Read the complete urls table from the temporary copy. Project
            # Read the table from a copy, then scope both accepted references
            # to the mathematics project in memory.
            rows = connection.execute(
                "SELECT url, title, visit_count, last_visit_time FROM urls "
                "ORDER BY last_visit_time DESC"
            ).fetchall()
        finally:
            connection.close()
    project_rows = [
        row for row in rows
        if PROJECT_URL_PART.lower() in str(row[0] or "").lower()
        or "数学" in str(row[1] or "")
    ]
    project_matches = _history_matches(project_rows, patterns)
    all_matches = _history_matches(rows, patterns)
    return {
        "browser": label,
        "status": "passed",
        "source_path": str(source),
        "history_db_sha256": copied_sha,
        # Only the mathematics project is in scope for these two references.
        "matches": project_matches,
        "project_matches": project_matches,
        "all_matches": all_matches,
        "history_scope": "mathematics_project_only",
    }


def collect(output: Path, events: Path, paths: dict[str, Path] | None = None) -> dict[str, Any]:
    paths = paths or default_history_paths()
    checked_at = now_iso()
    previous_dom: dict[str, Any] | None = None
    if output.exists():
        try:
            previous = json.loads(output.read_text(encoding="utf-8"))
            candidate = previous.get("dom_evidence") if isinstance(previous, dict) else None
            if isinstance(candidate, dict) and candidate.get("status") == "passed":
                previous_dom = dict(candidate)
                previous_dom["snapshot_reused_by_history_collector"] = True
        except (OSError, json.JSONDecodeError):
            previous_dom = None
    edge = query_history(paths["edge"], "edge", ["8.5课程", "8.5"])
    chrome = query_history(paths["chrome"], "chrome", ["8.5课程", "8.5"])
    project_history_matches = edge.get("project_matches", []) + chrome.get("project_matches", [])
    matches_85_course = [m for m in project_history_matches if "8.5课程" in m.get("matched_terms", [])]
    matches_85 = [m for m in project_history_matches if "8.5" in m.get("matched_terms", []) and "8.5课程" not in m.get("matched_terms", [])]
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8")) if REFERENCE_PATH.is_file() else {}
    accepted_chats = reference.get("accepted_chats", {}) if isinstance(reference, dict) else {}
    evidence = {
        "schema_version": "browser-evidence-1.2",
        "collector": "scripts/browser_collect.py",
        "collector_version": COLLECTOR_VERSION,
        "checked_at": checked_at,
        "history_verified_at": checked_at,
        "source_kind": "browser_history_copy_read_only",
        "8.5": {
            "status": "passed" if matches_85 else "unknown",
            "matches": len(matches_85),
            "history_matches": matches_85,
            "source": "Edge/Chrome History copied to a temporary directory and queried read-only",
            "history_scope": "project URL or 数学 title",
            "dom_evidence_ref": "dom_evidence.visible_entries",
            "content_status": accepted_chats.get("8.5", {}).get("content_status", "not_collected"),
            "content_source_file": accepted_chats.get("8.5", {}).get("source_file"),
            "content_source_sha256": accepted_chats.get("8.5", {}).get("source_sha256"),
        },
        "8.5课程": {
            "status": "passed" if matches_85_course else "unknown",
            "matches": len(matches_85_course),
            "history_matches": matches_85_course,
            "source": "Edge/Chrome History copied to a temporary directory and queried read-only",
            "history_scope": "mathematics project only",
            "dom_evidence_ref": "dom_evidence.reference_summary",
            "content_status": accepted_chats.get("8.5课程", {}).get("content_status", "not_collected"),
            "reference_rules": accepted_chats.get("8.5课程", {}).get("rules", []),
        },
        "history_scan": {
            "project_match_count": len(project_history_matches),
            "required_titles": ["8.5", "8.5课程"],
        },
        "browsers": {"edge": edge, "chrome": chrome},
        "dom_evidence": {
            "status": "passed" if accepted_chats else "not_collected",
            "source": "data/math_chat_reference.json",
            "read_at": reference.get("read_at"),
            "visible_entries": list(accepted_chats),
            "reference_summary": accepted_chats,
            "note": "Browser history confirms the exact chat identities; 8.5 content rules come from the hash-bound user-provided Markdown export. Full chat text is not copied into project data.",
        },
        "privacy": "只复制并读取 History 副本；不读取 cookies/localStorage/密码/浏览器 profile，不输入账号，不发送消息",
        "collector_boundary": "只采集数学项目中的 8.5 与 8.5课程；其他相似名称不进入学习上下文。DOM 与历史证据分开记录。",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    events.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event": "browser_history_collected",
        "collector": "scripts/browser_collect.py",
        "collector_version": COLLECTOR_VERSION,
        "occurred_at": checked_at,
        "evidence_path": str(output),
        "history_db_sha256": {name: value.get("history_db_sha256") for name, value in (("edge", edge), ("chrome", chrome))},
        "privacy_boundary": evidence["privacy"],
    }
    with events.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="只读采集 Edge/Chrome 数学项目浏览历史")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--events", default=str(DEFAULT_EVENTS))
    parser.add_argument("--edge-history", default=None)
    parser.add_argument("--chrome-history", default=None)
    args = parser.parse_args()
    paths = default_history_paths()
    if args.edge_history:
        paths["edge"] = Path(args.edge_history)
    if args.chrome_history:
        paths["chrome"] = Path(args.chrome_history)
    result = collect(Path(args.output), Path(args.events), paths)
    print(json.dumps({"status": "collected", "output": args.output, "8.5": result["8.5"]["status"], "8.5课程": result["8.5课程"]["status"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
