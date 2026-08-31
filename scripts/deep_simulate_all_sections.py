#!/usr/bin/env python3
"""Run the answer-isolated five-round route stress simulation."""

from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ybt_learning.isolated_simulation import run_all


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-proxy-history", action="store_true")
    args = parser.parse_args()
    summary = run_all(ROOT, reset_proxy_history=args.reset_proxy_history)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
