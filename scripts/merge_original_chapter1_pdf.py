from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    import pymupdf
except ImportError:  # pragma: no cover - compatibility with older PyMuPDF releases
    import fitz as pymupdf


DEFAULT_OUTPUT = Path("output/pdf/第一章_空间向量与立体几何_原书_方法册习题册.pdf")


def section_number(path: Path) -> int:
    match = re.match(r"^第(\d+)节", path.name)
    if not match:
        raise ValueError(f"cannot read section number from {path.name}")
    return int(match.group(1))


def merge(source_root: Path, output: Path) -> dict:
    source_root = source_root.resolve()
    candidates = list(source_root.glob("第*节*（方法册+习题册）.pdf"))
    files = sorted(candidates, key=section_number)
    if len(files) != 4 or [section_number(path) for path in files] != [1, 2, 3, 4]:
        names = ", ".join(path.name for path in files)
        raise ValueError(f"expected one method+exercise PDF for sections 1-4; found: {names}")

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    merged = pymupdf.open()
    counts: list[int] = []
    for path in files:
        source = pymupdf.open(str(path))
        counts.append(len(source))
        merged.insert_pdf(source)
        source.close()

    merged.set_metadata(
        {
            "title": "第一章 空间向量与立体几何",
            "author": "一本通",
            "subject": "2025-2025版选择性必修第1册",
            "keywords": "空间向量, 立体几何, 一本通",
        }
    )
    merged.save(str(output), garbage=3, deflate=True, clean=True)
    merged.close()

    check = pymupdf.open(str(output))
    page_count = len(check)
    check.close()
    expected = sum(counts)
    if page_count != expected:
        raise RuntimeError(f"merged page count mismatch: expected {expected}, got {page_count}")
    return {
        "output": str(output),
        "source_files": [path.name for path in files],
        "source_page_counts": counts,
        "pages": page_count,
        "bytes": output.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge the original Chapter 1 method+exercise PDFs without OCR or reflow.")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(merge(args.source_root, args.output))


if __name__ == "__main__":
    main()
