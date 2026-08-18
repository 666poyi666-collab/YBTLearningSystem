from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ybt_learning.vision import VISION_PROMPT, describe_image  # noqa: E402


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_payload(path: Path, rows: list[dict[str, Any]], target_count: int) -> None:
    passed_keys = {
        (row.get("question_hint"), row.get("image_sha256"))
        for row in rows
        if row.get("status") == "passed" and row.get("confidence") in {"E1", "E2"} and row.get("structured")
    }
    payload = {
        "schema_version": "7.1",
        "status": "passed" if len(passed_keys) == target_count else "unverified",
        "provider": "GLM-4.6V-Flash via deepseek-eyes",
        "target_count": target_count,
        "passed_count": len(passed_keys),
        "results": rows,
        "consumer_guard": "Only immutable-image E1/E2 structured rows may enter learning examples or direct variants.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", default="1.1")
    parser.add_argument("--out", default="reports/learning-item-vision-probe.json")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--backoff-sec", type=int, default=30)
    parser.add_argument("--delay-sec", type=int, default=45)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--max-tokens", type=int, default=1536)
    args = parser.parse_args()

    packet_dir = ROOT / "data" / "packets" / args.section.replace("+", "_")
    packet = load(packet_dir / "learning_packet.json")
    full_path = ROOT / "data" / "vision_sidecar_full.json"
    full = load(full_path) if full_path.exists() else {"results": []}
    existing = {
        (row.get("question_hint"), row.get("image_sha256"))
        for row in full.get("results", [])
        if row.get("status") == "passed" and row.get("confidence") in {"E1", "E2"} and row.get("structured")
    }
    out = ROOT / args.out
    previous = load(out) if out.exists() else {"results": []}
    rows: list[dict[str, Any]] = list(previous.get("results", []))
    existing.update({
        (row.get("question_hint"), row.get("image_sha256"))
        for row in rows
        if row.get("status") == "passed" and row.get("confidence") in {"E1", "E2"} and row.get("structured")
    })

    targets: list[tuple[str, Path, str]] = []
    for item in [*packet.get("worked_examples", []), *packet.get("direct_variants", [])]:
        if item.get("visual_status") != "NEEDS_VISION_SIDECAR":
            continue
        hint = str(item.get("vision_hint") or f"{args.section}-LI{item.get('item_id')}")
        for image in item.get("image_refs", []):
            path = Path(str(image.get("path", "")))
            if not path.is_file():
                print(f"missing image: {path}")
                continue
            digest = sha256(path)
            targets.append((hint, path, digest))

    end = None if args.count is None else args.start + args.count
    selected = targets[args.start:end]
    pending = [target for target in selected if (target[0], target[2]) not in existing]
    print(json.dumps({"section": args.section, "targets": len(selected), "already_passed": len(selected) - len(pending), "pending": len(pending), "output": str(out)}, ensure_ascii=False))

    for round_number in range(1, args.rounds + 1):
        for hint, path, digest in list(pending):
            result = describe_image(path, profile=args.profile, prompt=VISION_PROMPT, max_tokens=args.max_tokens)
            confidence = result.get("confidence") or (result.get("structured") or {}).get("confidence", "E0")
            row = {
                "status": result.get("status", "failed"),
                "question_hint": hint,
                "section": args.section,
                "image": str(path),
                "image_sha256": digest,
                "confidence": confidence,
                "model": result.get("model"),
                "elapsed_ms": result.get("elapsed_ms"),
            }
            if result.get("structured"):
                row["structured"] = result["structured"]
            if result.get("error"):
                row["error"] = result["error"]
            rows.append(row)
            ok = row["status"] == "passed" and confidence in {"E1", "E2"} and bool(row.get("structured"))
            print(f"round={round_number} hint={hint} image={path.name} status={row['status']} confidence={confidence}")
            if ok:
                pending.remove((hint, path, digest))
            write_payload(out, rows, len(selected))
            delay = max(args.delay_sec, 90) if row.get("status") != "passed" and "429" in str(row.get("error", "")) else args.delay_sec
            if pending and delay > 0:
                time.sleep(delay)
        if not pending:
            break
        if round_number < args.rounds:
            time.sleep(args.backoff_sec)

    write_payload(out, rows, len(selected))
    return 0 if not pending else 1


if __name__ == "__main__":
    raise SystemExit(main())
