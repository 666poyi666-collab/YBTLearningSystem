# -*- coding: utf-8 -*-
"""Bounded retry loop for the 5 residual visual-crop probes (read-only collector).

Targets: 1.2+1.3-B13, 1.4-B4, micro专题1-B1 (2 images), micro专题1-B4.

Usage (from project root):
    python -X utf8 reports/vision_retry_loop.py --rounds 2 --out reports/vision_retry_round.json

Behaviour:
  - Skips (hint, image) pairs that already have a passed E1/E2 result in
    data/vision_sidecar_full.json.
  - Calls GLM-4.6V-Flash (deepseek-eyes describe.py) with backoff between
    rounds. Provider quota is consumed; nothing else is mutated.
  - Writes only its own probe output file (--out), same schema as
    sidecar_for_question_images. Merge with the existing pipeline:
        python scripts/merge_vision_probe.py reports/vision_retry_round.json
        python -m ybt_learning.cli build-chapter1
  - Never invents results: only provider returned E1/E2 structured payloads
    count as passed.
"""
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ybt_learning.vision import VISION_PROMPT, describe_image  # noqa: E402

def load(rel):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

TARGETS = [
    ("1.2+1.3-B13", r"data\ocr_live_full\imgs\img_in_image_box_897_830_1094_1011.jpg"),
    ("1.4-B4", r"data\ocr_live_full\imgs\img_in_image_box_896_353_1093_566.jpg"),
    ("micro专题1-B1", r"C:\开发\小工具\一本通DeepSeek迭代\worker-02-solutions\ocr\section-04\imgs\img_in_image_box_905_452_1094_632.jpg"),
    ("micro专题1-B1", r"C:\开发\小工具\一本通DeepSeek迭代\worker-02-solutions\ocr\section-04\imgs\img_in_image_box_521_1010_695_1178.jpg"),
    ("micro专题1-B4", r"data\ocr_live_full\imgs\img_in_image_box_832_343_1093_610.jpg"),
]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--out", default="reports/vision_retry_round.json")
    ap.add_argument("--backoff-sec", type=int, default=30)
    args = ap.parse_args()

    full = load("data/vision_sidecar_full.json") or {"results": []}
    already = {(r.get("question_hint"), r.get("image")) for r in full.get("results", [])
               if r.get("status") == "passed" and r.get("confidence") in {"E1", "E2"}}
    pending = [(h, str(ROOT / p) if not Path(p).is_absolute() else p) for h, p in TARGETS]
    pending = [(h, p) for h, p in pending if (h, p) not in already]
    print("already_passed=", len(TARGETS) - len(pending), "pending=", len(pending))
    if not pending:
        print("nothing pending")
        return 0

    collected = []
    for rnd in range(1, args.rounds + 1):
        print("--- round", rnd, "/", args.rounds, "---")
        for hint, path in list(pending):
            if not Path(path).is_file():
                print("SKIP missing image:", path)
                pending.remove((hint, path))
                continue
            result = describe_image(path, prompt=VISION_PROMPT, max_tokens=1536)
            conf = result.get("confidence") or (result.get("structured") or {}).get("confidence", "E0")
            item = {"status": result.get("status"), "question_hint": hint, "image": str(path),
                    "confidence": conf, "model": result.get("model"), "elapsed_ms": result.get("elapsed_ms"),
                    "section": hint.rsplit("-", 1)[0]}
            if result.get("structured"):
                item["structured"] = result["structured"]
            if result.get("error"):
                item["error"] = result["error"]
            collected.append(item)
            ok = item["status"] == "passed" and item["confidence"] in {"E1", "E2"}
            print("  " + hint, Path(path).name, "status=" + str(item["status"]), "confidence=" + str(item["confidence"]), "error=" + str((item.get("error") or "")[:60]))
            if ok:
                pending.remove((hint, path))
        if not pending:
            break
        if rnd < args.rounds:
            print("backoff", args.backoff_sec, "s")
            time.sleep(args.backoff_sec)

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "7.1",
               "status": "passed" if collected and all(r.get("status") == "passed" and r.get("confidence") in {"E1", "E2"} for r in collected) else "unverified",
               "provider": "GLM-4.6V-Flash via deepseek-eyes", "results": collected}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    passed = [r for r in collected if r.get("status") == "passed" and r.get("confidence") in {"E1", "E2"}]
    print("written=", out, "passed=", len(passed), "of", len(collected))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
