from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


def image_blocks(page: fitz.Page) -> list[dict]:
    blocks = []
    for index, block in enumerate(page.get_text("dict").get("blocks", [])):
        if block.get("type") != 1 or not block.get("image"):
            continue
        blocks.append({
            "index": index,
            "bbox": block.get("bbox"),
            "width": block.get("width"),
            "height": block.get("height"),
            "ext": block.get("ext", "png"),
            "bytes": block.get("image"),
        })
    return blocks


def render_page(doc: fitz.Document, page_index: int, out_dir: Path, label: str) -> list[dict]:
    page = doc[page_index]
    matrix = fitz.Matrix(3.0, 3.0)
    full_path = out_dir / f"{label}_page_{page_index + 1:03d}_full.png"
    page.get_pixmap(matrix=matrix, alpha=False).save(full_path)
    records = [{"kind": "full_page", "path": str(full_path), "page": page_index + 1}]
    for item in image_blocks(page):
        ext = item.pop("ext")
        raw = item.pop("bytes")
        image_path = out_dir / f"{label}_page_{page_index + 1:03d}_image_{item['index']:02d}.{ext}"
        image_path.write_bytes(raw)
        item["kind"] = "embedded_image"
        item["path"] = str(image_path)
        item["page"] = page_index + 1
        records.append(item)
    return records


def render_crop(doc: fitz.Document, page_index: int, rect: tuple[float, float, float, float], out_dir: Path, label: str) -> dict:
    page = doc[page_index]
    clip = fitz.Rect(*rect)
    path = out_dir / f"{label}_page_{page_index + 1:03d}_crop.png"
    page.get_pixmap(matrix=fitz.Matrix(4.0, 4.0), clip=clip, alpha=False).save(path)
    return {"kind": "source_crop", "path": str(path), "page": page_index + 1, "rect": list(rect)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter-pdf", required=True)
    parser.add_argument("--answer-pdf", required=False, help="兼容旧命令；学生视觉源不再读取答案册")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    with fitz.open(args.chapter_pdf) as chapter:
        for page_number, label in ((30, "b5_source"), (32, "b13_source"), (51, "pyramid_b4_source"), (65, "micro_b1_source"), (67, "micro_b4_source")):
            records.extend(render_page(chapter, page_number - 1, out_dir, label))
        records.extend([
            render_crop(chapter, 29, (250, 145, 370, 300), out_dir, "b5_source"),
            render_crop(chapter, 31, (420, 360, 595, 530), out_dir, "b13_source"),
            render_crop(chapter, 50, (420, 145, 595, 390), out_dir, "pyramid_b4_source"),
            # B1 is on the chapter's merged no-answer PDF page 65.  The
            # crop contains only the printed figure, never the answer-book
            # coordinate sketch or solution text.
            render_crop(chapter, 64, (450, 500, 595, 650), out_dir, "micro_b1_source"),
            render_crop(chapter, 66, (405, 135, 595, 360), out_dir, "micro_b4_source"),
        ])
    # Answer-book PDF rendering was deliberately removed.  Answer OCR/PDF
    # material belongs to answer_sidecar only and must never enter a student
    # packet's visual evidence.
    (out_dir / "manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out_dir), "records": records}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
