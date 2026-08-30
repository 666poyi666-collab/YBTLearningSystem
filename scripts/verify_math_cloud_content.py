#!/usr/bin/env python3
"""Download and hash every R2 object in a generated math content version."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUCKET = "math-learning-content"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(row: dict[str, Any], npx: str) -> dict[str, Any]:
    key = str(row["key"])
    source = Path(str(row["path"]))
    expected = sha256_file(source)
    process = subprocess.run(
        [npx, "wrangler", "r2", "object", "get", f"{BUCKET}/{key}", "--pipe", "--remote"],
        cwd=ROOT / "cloud/mcp",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    actual = sha256_bytes(process.stdout) if process.returncode == 0 else None
    return {
        "key": key,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "status": "passed" if actual == expected else "failed",
        "error": None if process.returncode == 0 else process.stderr.decode("utf-8", errors="replace")[-500:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    plan_path = ROOT / "tmp/math-cloud-import" / args.version / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        raise SystemExit("npx is missing")
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 8))) as pool:
        rows = list(pool.map(lambda row: verify(row, npx), plan["r2"]))
    failed = [row for row in rows if row["status"] != "passed"]
    report = {
        "schema_version": "ybt-math-cloud-r2-verification-v1",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "source_version": args.version,
        "git_commit": plan["currentCommit"],
        "objects": len(rows),
        "passed": len(rows) - len(failed),
        "failed": failed,
        "rows": rows,
    }
    output = ROOT / "reports/all_chapters/cloud-r2-verification.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("source_version", "objects", "passed", "failed")}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
