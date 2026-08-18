from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ybt_learning.vision import describe_image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "source_visual_probe.json"
TARGETS = [
    ("1.2+1.3-B5", ROOT / "reports/source_visuals2/b5_source_page_030_crop.png"),
    ("1.2+1.3-B13", ROOT / "reports/source_visuals2/b13_source_page_032_crop.png"),
    ("1.4-B4", ROOT / "reports/source_visuals2/pyramid_b4_source_page_051_crop.png"),
    # B1 is one figure from the merged no-answer chapter PDF.  The old
    # answer-book coordinate crop is intentionally excluded.
    ("micro专题1-B1", ROOT / "reports/source_visuals2/micro_b1_source_page_065_crop.png"),
    ("micro专题1-B4", ROOT / "reports/source_visuals2/micro_b4_source_page_067_crop.png"),
]
PROMPT = """你是高中数学教材图形核验器。只输出一个合法 JSON 对象，不要 Markdown，不要解释，不要答案。字段固定为 objects、relations、coordinates、ranges、text、uncertainties、confidence。只记录图中明确看见的点、线、面、虚实线和位置关系；不要从题干推断图中没有的内容；每个数组最多 12 项；confidence 只能是 E2、E1 或 E0。"""


def main() -> int:
    rows = []
    for hint, path in TARGETS:
        result = describe_image(path, prompt=PROMPT, max_tokens=2048, timeout_ms=180000)
        row = {
            "question_hint": hint,
            "image": str(path),
            "status": result.get("status"),
            "confidence": result.get("confidence") or (result.get("structured") or {}).get("confidence", "E0"),
            "model": result.get("model"),
            "elapsed_ms": result.get("elapsed_ms"),
            "structured": result.get("structured"),
            "error": result.get("error"),
        }
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("question_hint", "status", "confidence", "error")}, ensure_ascii=False))
    payload = {
        "schema_version": "7.2",
        "status": "passed" if rows and all(row["status"] == "passed" and row["confidence"] in {"E1", "E2"} for row in rows) else "unverified",
        "provider": "GLM-4.6V-Flash via deepseek-eyes",
        "source_kind": "high_resolution_source_pdf_crop",
        "results": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(OUT), "status": payload["status"], "passed": sum(row["status"] == "passed" and row["confidence"] in {"E1", "E2"} for row in rows), "total": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
