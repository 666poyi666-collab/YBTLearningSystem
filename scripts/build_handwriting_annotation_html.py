#!/usr/bin/env python3
"""Render a transparent-overlay HTML review for a handwritten math image.

The image is never painted over.  SVG rectangles and labels are layered above
the original image, while the detailed LaTeX explanation lives in a side panel.
The input JSON is deliberately strict so a generated review cannot silently
claim a first error without a matching line annotation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import mimetypes
from pathlib import Path
from typing import Any


STATUSES = {
    "correct": ("正确", "#16845b"),
    "first_wrong": ("第一处错误", "#c73737"),
    "uncertain": ("待确认", "#a66b00"),
    "downstream_contaminated": ("受前错影响", "#bd6a1b"),
}
ROOT = Path(__file__).resolve().parents[1]


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept either the local schema or a saved MCP response."""
    if payload.get("schema_version") == "math-handwriting-annotation-v1":
        return payload
    spec = payload.get("annotationSpec")
    if not isinstance(spec, dict) or spec.get("schemaVersion") != "math-handwriting-annotation-v1":
        return payload
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    overlays = spec.get("overlays") if isinstance(spec.get("overlays"), list) else []
    first_wrong = next((row.get("line") for row in overlays if isinstance(row, dict) and row.get("status") == "first_wrong"), None)
    return {
        "schema_version": "math-handwriting-annotation-v1",
        "source": {"image_evidence_id": spec.get("imageEvidenceId")},
        "question": {"item_ref": analysis.get("itemRef") or "未绑定题目"},
        "summary": {"first_wrong_line": first_wrong, "analysis_status": analysis.get("analysisStatus") or "proposed"},
        "uncertainties": spec.get("uncertainties") or [],
        "clarification_request": spec.get("clarificationRequest"),
        "lines": [
            {
                "line": row.get("line"),
                "status": row.get("status"),
                "bbox": row.get("bbox"),
                "explanation": row.get("explanation"),
                "latex": row.get("latex"),
            }
            for row in overlays if isinstance(row, dict)
        ],
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_payload(path: Path) -> dict[str, Any]:
    payload = normalize_payload(json.loads(path.read_text(encoding="utf-8")))
    if payload.get("schema_version") != "math-handwriting-annotation-v1":
        raise ValueError("analysis schema must be math-handwriting-annotation-v1")
    source = payload.get("source")
    if not isinstance(source, dict) or not str(source.get("image_evidence_id") or "").strip():
        raise ValueError("source.image_evidence_id is required")
    lines = payload.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValueError("lines must be a non-empty array")
    first_wrong = [row for row in lines if row.get("status") == "first_wrong"]
    summary = payload.get("summary") or {}
    uncertainties = payload.get("uncertainties") or []
    if not isinstance(uncertainties, list) or not all(isinstance(value, str) and value.strip() for value in uncertainties):
        raise ValueError("uncertainties must be an array of non-empty strings")
    if (summary.get("analysis_status") == "needs_clarification" or any(row.get("status") == "uncertain" for row in lines)) and not uncertainties:
        raise ValueError("uncertain analysis must disclose uncertainties to the user")
    if summary.get("analysis_status", "proposed") == "proposed" and len(first_wrong) != 1:
        raise ValueError("proposed analysis must contain exactly one first_wrong line")
    if first_wrong and summary.get("first_wrong_line") != first_wrong[0].get("line"):
        raise ValueError("summary.first_wrong_line must match the first_wrong line")
    for row in lines:
        if not isinstance(row, dict) or not isinstance(row.get("line"), int):
            raise ValueError("every line needs an integer line")
        if row.get("status") not in STATUSES:
            raise ValueError(f"unsupported line status: {row.get('status')}")
        bbox = row.get("bbox")
        if bbox is not None:
            if not isinstance(bbox, list) or len(bbox) != 4 or not all(isinstance(value, (int, float)) for value in bbox):
                raise ValueError("bbox must be [x, y, width, height]")
            if any(value < 0 or value > 1 for value in bbox) or bbox[2] <= 0 or bbox[3] <= 0:
                raise ValueError("bbox must use normalized coordinates in [0, 1]")
            if bbox[0] + bbox[2] > 1 or bbox[1] + bbox[3] > 1:
                raise ValueError("bbox must stay inside the source image")
        if not str(row.get("explanation") or "").strip():
            raise ValueError("every line needs an explanation")
    return payload


def image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def render(payload: dict[str, Any], image: Path, output: Path, mathjax_src: str) -> None:
    image_hash = sha256_file(image)
    source = payload["source"]
    expected_hash = str(source.get("image_sha256") or "")
    if expected_hash and expected_hash != image_hash:
        raise ValueError("source.image_sha256 does not match the supplied image")
    source["image_sha256"] = image_hash
    source["image_file_name"] = image.name

    overlays: list[str] = []
    rows: list[str] = []
    for row in payload["lines"]:
        status = str(row["status"])
        label, color = STATUSES[status]
        line = int(row["line"])
        explanation = html.escape(str(row["explanation"]))
        latex = str(row.get("latex") or "").strip()
        bbox = row.get("bbox")
        if bbox:
            x, y, width, height = [float(value) * 100 for value in bbox]
            overlays.append(
                f'<rect class="overlay overlay-{status}" x="{x:.4f}%" y="{y:.4f}%" width="{width:.4f}%" height="{height:.4f}%" />'
                f'<text class="overlay-label overlay-label-{status}" x="{max(0, x):.4f}%" y="{max(2, y - 0.4):.4f}%">第{line}行 · {html.escape(label)}</text>'
            )
        formula = f'<div class="latex">\\({html.escape(latex)}\\)</div>' if latex else ""
        rows.append(
            f'<article class="line-card line-{status}"><header><span class="line-number">第{line}行</span><span class="line-status">{html.escape(label)}</span></header><p>{explanation}</p>{formula}</article>'
        )

    summary = payload.get("summary") or {}
    first_line = summary.get("first_wrong_line")
    summary_text = "未发现可确认的错误" if first_line is None else f"第一处错误：第 {first_line} 行"
    uncertainty_html = ""
    uncertainties = payload.get("uncertainties") or []
    if uncertainties:
        uncertainty_items = "".join(f"<li>{html.escape(str(value))}</li>" for value in uncertainties)
        clarification = html.escape(str(payload.get("clarification_request") or "请补拍或说明上述位置后再确认。"))
        uncertainty_html = f'<section class="uncertainty"><strong>仍不确定，需用户确认</strong><ul>{uncertainty_items}</ul><p>{clarification}</p></section>'
    image_url = image_data_url(image)
    source_id = html.escape(str(source.get("image_evidence_id")))
    item_ref = html.escape(str((payload.get("question") or {}).get("item_ref") or "未绑定题目"))
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>手写过程批改 · {item_ref}</title>
<style>
:root {{ color-scheme: light; --ink:#1e2824; --muted:#6d7973; --line:#dfe6e2; --paper:#f6f8f6; --panel:#ffffff; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--paper); color:var(--ink); font-family:Inter,"Segoe UI","Microsoft YaHei",sans-serif; line-height:1.65; }}
.shell {{ max-width:1440px; margin:0 auto; padding:28px; }} .top {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-end; margin-bottom:22px; }}
h1 {{ margin:0; font-size:clamp(22px,3vw,34px); letter-spacing:0; }} .meta {{ color:var(--muted); font-size:13px; }}
.summary {{ background:var(--panel); border:1px solid var(--line); border-left:4px solid #c73737; padding:14px 16px; margin-bottom:14px; }} .uncertainty {{ background:#fff8e8; border:1px solid #e4c886; border-left:4px solid #a66b00; padding:14px 16px; margin-bottom:22px; }} .uncertainty ul {{ margin:7px 0; padding-left:20px; }} .uncertainty p {{ margin:0; }}
.workspace {{ display:grid; grid-template-columns:minmax(0,1.35fr) minmax(320px,.65fr); gap:22px; align-items:start; }}
.image-panel {{ background:#fff; border:1px solid var(--line); padding:14px; }} .image-stage {{ position:relative; width:100%; line-height:0; overflow:hidden; }}
.image-stage img {{ display:block; width:100%; height:auto; }} .overlay-layer {{ position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }}
.overlay {{ fill:none; stroke-width:2.4; vector-effect:non-scaling-stroke; }} .overlay-first_wrong {{ stroke:#c73737; }} .overlay-downstream_contaminated {{ stroke:#bd6a1b; stroke-dasharray:8 5; }} .overlay-correct {{ stroke:#16845b; }} .overlay-uncertain {{ stroke:#a66b00; stroke-dasharray:4 4; }}
.overlay-label {{ font:600 14px "Microsoft YaHei",sans-serif; paint-order:stroke; stroke:#fff; stroke-width:4px; stroke-linejoin:round; }} .overlay-label-first_wrong {{ fill:#c73737; }} .overlay-label-downstream_contaminated {{ fill:#bd6a1b; }} .overlay-label-correct {{ fill:#16845b; }} .overlay-label-uncertain {{ fill:#a66b00; }}
.side {{ display:grid; gap:12px; }} .legend, .line-card, .method {{ background:var(--panel); border:1px solid var(--line); padding:14px 16px; }} .legend {{ display:flex; flex-wrap:wrap; gap:8px 14px; font-size:13px; color:var(--muted); }}
.legend span::before {{ content:""; display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; background:currentColor; }} .legend .wrong {{ color:#c73737; }} .legend .downstream {{ color:#bd6a1b; }} .legend .correct {{ color:#16845b; }} .legend .uncertain {{ color:#a66b00; }}
.line-card header {{ display:flex; justify-content:space-between; gap:10px; border-bottom:1px solid var(--line); padding-bottom:7px; margin-bottom:8px; }} .line-number {{ font-weight:700; }} .line-status {{ font-size:12px; font-weight:700; }} .line-first_wrong {{ border-left:4px solid #c73737; }} .line-downstream_contaminated {{ border-left:4px solid #bd6a1b; }} .line-correct {{ border-left:4px solid #16845b; }} .line-uncertain {{ border-left:4px solid #a66b00; }}
.line-card p {{ margin:0; font-size:14px; }} .latex {{ margin-top:8px; padding:8px 10px; background:#f3f6f4; overflow:auto; }} .method {{ color:var(--muted); font-size:13px; }}
@media (max-width:900px) {{ .shell {{ padding:16px; }} .top {{ display:block; }} .meta {{ margin-top:6px; }} .workspace {{ grid-template-columns:1fr; }} }}
</style>
<script defer src="{html.escape(mathjax_src)}"></script>
</head>
<body><main class="shell">
<header class="top"><div><div class="meta">手写过程批改 · 原图保留</div><h1>{item_ref}</h1></div><div class="meta">证据：{source_id}<br>SHA-256：{image_hash}</div></header>
<div class="summary"><strong>{html.escape(summary_text)}</strong><br><span>框线透明无填充；后续步骤仅在确实受首错影响时标记为“受前错影响”。</span></div>{uncertainty_html}
<section class="workspace"><div class="image-panel"><div class="image-stage"><img src="{image_url}" alt="用户手写原图" data-image-sha256="{image_hash}"><svg class="overlay-layer" viewBox="0 0 100 100" preserveAspectRatio="none">{"".join(overlays)}</svg></div></div>
<aside class="side"><div class="legend"><span class="wrong">第一处错误</span><span class="downstream">受前错影响</span><span class="correct">正确</span><span class="uncertain">待确认</span></div>{"".join(rows)}<div class="method">批改规则：先核对题面，再按行检查定义、方向、公式代入、计算和结论；首错之后的连锁错误不重复归因。公式使用 LaTeX/MathJax，原图永远不被覆盖。</div></aside></section>
</main></body></html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mathjax-src", default="")
    args = parser.parse_args()
    if not args.image.is_file() or not args.analysis.is_file():
        raise SystemExit("image and analysis files are required")
    payload = read_payload(args.analysis)
    if args.mathjax_src:
        mathjax_src = args.mathjax_src
    else:
        mathjax_path = ROOT / "data" / "assets" / "mathjax" / "3.2.2" / "es5" / "tex-chtml-full.js"
        if not mathjax_path.is_file():
            raise SystemExit(f"MathJax asset is missing: {mathjax_path}")
        mathjax_src = mathjax_path.as_uri()
    render(payload, args.image, args.out, mathjax_src)
    print(json.dumps({"status": "passed", "output": str(args.out), "image_sha256": sha256_file(args.image)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
