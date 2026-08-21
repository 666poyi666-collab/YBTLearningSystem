from __future__ import annotations

import argparse
import html
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = ROOT / "data" / "ocr_live_current" / "first_chapter_69"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "第一章_空间向量与立体几何_电子重建版.pdf"

CHAPTER_TITLE = "第一章 空间向量与立体几何"


def normalize_dashes(value: str) -> str:
    for dash in "\u2010\u2011\u2012\u2013\u2014\u2212\ufe58\ufe63\uff0d":
        value = value.replace(dash, "-")
    return value


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = normalize_dashes(value)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"(\*\*|__|`)", "", value)
    # OCR keeps inline formula commands as literal LaTeX.  Convert the
    # common commands to readable Unicode/text so the rebuilt PDF is useful
    # without requiring a LaTeX renderer.
    value = re.sub(
        r"\\(overrightarrow|vec)\{([^{}]*)\}",
        lambda match: "→" + match.group(2),
        value,
    )
    value = re.sub(
        r"\\(boldsymbol|mathbf|mathrm|text)\{([^{}]*)\}",
        lambda match: match.group(2),
        value,
    )
    value = re.sub(
        r"\\frac\{([^{}]*)\}\{([^{}]*)\}",
        lambda match: f"({match.group(1)})/({match.group(2)})",
        value,
    )
    value = re.sub(r"\\sqrt\{([^{}]*)\}", lambda match: "√(" + match.group(1) + ")", value)
    value = value.replace("\\left", "").replace("\\right", "")
    value = value.replace("\\!", "")
    formula_symbols = {
        "\\pm": "±",
        "\\mp": "∓",
        "\\times": "×",
        "\\cdot": "·",
        "\\cdots": "⋯",
        "\\ldots": "…",
        "\\Leftrightarrow": "⇔",
        "\\Longleftrightarrow": "⇔",
        "\\Rightarrow": "⇒",
        "\\Longrightarrow": "⇒",
        "\\Leftarrow": "⇐",
        "\\parallel": "∥",
        "\\perp": "⊥",
        "\\neq": "≠",
        "\\le": "≤",
        "\\leq": "≤",
        "\\ge": "≥",
        "\\geq": "≥",
        "\\in": "∈",
        "\\notin": "∉",
        "\\alpha": "α",
        "\\beta": "β",
        "\\gamma": "γ",
        "\\delta": "δ",
        "\\lambda": "λ",
        "\\mu": "μ",
        "\\pi": "π",
        "\\theta": "θ",
        "\\varphi": "φ",
        "\\phi": "φ",
        "\\mathbf": "",
    }
    for source, target in formula_symbols.items():
        value = value.replace(source, target)
    # Handle vector commands whose subscript contains a nested brace, e.g.
    # ``\\overrightarrow{AA_{1}}``.  The fallback keeps the base notation
    # readable even when OCR produced malformed braces.
    value = value.replace("\\overrightarrow{", "→").replace("\\vec{", "→")
    value = value.replace("\\boldsymbol{", "").replace("\\mathbf{", "")
    value = value.replace("\\mathrm{", "").replace("\\text{", "")
    value = value.replace("$", "")
    value = value.replace("\\", "")
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def para_text(value: str) -> str:
    return escape(clean_text(value), {"'": "'", '"': '"'})


class TableParser(HTMLParser):
    """Parse the small HTML tables emitted by the OCR pipeline."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
            self._in_cell = True
        elif tag == "br" and self._in_cell and self._cell is not None:
            self._cell.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._in_cell and self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._in_cell and self._row is not None:
            self._row.append(clean_text("".join(self._cell or [])))
            self._cell = None
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def extract_table(table_html: str) -> list[list[str]]:
    parser = TableParser()
    parser.feed(table_html)
    return parser.rows


def extract_images_and_replace(text: str) -> tuple[str, list[str]]:
    images: list[str] = []

    def replace(match: re.Match[str]) -> str:
        src = html.unescape(match.group(1)).replace("\\", "/")
        name = Path(src).name
        images.append(name)
        return ""

    text = re.sub(r"<img\b[^>]*?src=[\"']([^\"']+)[\"'][^>]*?/?>", replace, text, flags=re.IGNORECASE)
    text = re.sub(r"</?div\b[^>]*>", "", text, flags=re.IGNORECASE)
    return text, images


def replace_tables(text: str) -> tuple[str, list[list[list[str]]]]:
    tables: list[list[list[str]]] = []

    def replace(match: re.Match[str]) -> str:
        rows = extract_table(match.group(0))
        if rows:
            tables.append(rows)
            return f"\n@@TABLE_{len(tables) - 1}@@\n"
        return "\n"

    text = re.sub(r"<table\b.*?</table>", replace, text, flags=re.IGNORECASE | re.DOTALL)
    return text, tables


def find_font() -> Path | None:
    candidates = [
        Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def register_chinese_font() -> str:
    path = find_font()
    if path is None:
        return "STSong-Light"
    try:
        pdfmetrics.registerFont(TTFont("ChapterChinese", str(path)))
        return "ChapterChinese"
    except Exception:
        return "STSong-Light"


def make_styles(font_name: str):
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitleCN",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=26,
            leading=34,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324D"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSubCN",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=11,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#506070"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="PageMarkCN",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=8,
            leading=11,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#7A8793"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1CN",
            parent=styles["Heading1"],
            fontName=font_name,
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#17324D"),
            spaceBefore=7,
            spaceAfter=8,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2CN",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=12.5,
            leading=18,
            textColor=colors.HexColor("#1E5977"),
            spaceBefore=6,
            spaceAfter=5,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H3CN",
            parent=styles["Heading3"],
            fontName=font_name,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#38586C"),
            spaceBefore=4,
            spaceAfter=3,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCN",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=9.2,
            leading=14.5,
            textColor=colors.HexColor("#202A33"),
            spaceAfter=4,
            wordWrap="CJK",
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallCN",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=8.2,
            leading=12,
            textColor=colors.HexColor("#465564"),
            spaceAfter=3,
            wordWrap="CJK",
        )
    )
    styles.add(
        ParagraphStyle(
            name="NoteCN",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=8.6,
            leading=13.5,
            textColor=colors.HexColor("#526170"),
            backColor=colors.HexColor("#F2F6F8"),
            borderColor=colors.HexColor("#D6E1E7"),
            borderWidth=0.6,
            borderPadding=7,
            spaceBefore=7,
            spaceAfter=9,
            wordWrap="CJK",
        )
    )
    return styles


def make_table(rows: list[list[str]], font_name: str, available_width: float):
    if not rows:
        return None
    columns = max(len(row) for row in rows)
    normalized = [row + [""] * (columns - len(row)) for row in rows]
    cell_style = ParagraphStyle(
        "TableCellCN",
        fontName=font_name,
        fontSize=7.2 if columns >= 4 else 7.8,
        leading=10.2 if columns >= 4 else 11.2,
        textColor=colors.HexColor("#23313B"),
        wordWrap="CJK",
    )
    data = [[Paragraph(para_text(cell), cell_style) for cell in row] for row in normalized]
    widths = [available_width / columns] * columns
    table = Table(data, colWidths=widths, repeatRows=1, splitByRow=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C7CF")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2F5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def add_image_flowables(story: list, image_names: Iterable[str], styles, image_root: Path, available_width: float):
    image_names = list(dict.fromkeys(image_names))
    if not image_names:
        return
    story.append(Paragraph("本页图示", styles["H3CN"]))
    for index, name in enumerate(image_names, start=1):
        path = image_root / name
        if not path.is_file():
            story.append(Paragraph(f"图示 {index} 缺失：{para_text(name)}", styles["SmallCN"]))
            continue
        try:
            image = Image(str(path))
            image._restrictSize(available_width, 63 * mm)
            story.append(Paragraph(f"图示 {index}", styles["SmallCN"]))
            story.append(image)
            story.append(Spacer(1, 3))
        except Exception as exc:
            story.append(Paragraph(f"图示 {index} 无法载入：{para_text(str(exc))}", styles["SmallCN"]))


def add_doc(story: list, doc_path: Path, doc_index: int, styles, font_name: str, available_width: float):
    raw = doc_path.read_text(encoding="utf-8", errors="replace")
    raw, image_names = extract_images_and_replace(raw)
    raw, tables = replace_tables(raw)

    if story:
        story.append(PageBreak())
    story.append(Paragraph(f"教材页 {doc_index + 1} / 69", styles["PageMarkCN"]))

    table_index = 0
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("@@TABLE_") and line.endswith("@@"):
            table = make_table(tables[table_index], font_name, available_width)
            table_index += 1
            if table is not None:
                story.append(Spacer(1, 3))
                story.append(table)
                story.append(Spacer(1, 5))
            continue
        if re.fullmatch(r"[-*_]{3,}", line):
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            style = styles["H1CN"] if level <= 2 else styles["H2CN"] if level == 3 else styles["H3CN"]
            story.append(Paragraph(para_text(heading.group(2)), style))
            continue
        line = re.sub(r"^\s*[-*+]\s+", "• ", line)
        line = re.sub(r"^\s*\d+[.)]\s+", lambda m: m.group(0).strip() + " ", line)
        if line.startswith("注：") or line.startswith("注:"):
            story.append(Paragraph(para_text(line), styles["NoteCN"]))
        elif line.startswith("答案：") or line.startswith("答案:"):
            story.append(Paragraph(para_text(line), styles["SmallCN"]))
        else:
            story.append(Paragraph(para_text(line), styles["BodyCN"]))

    add_image_flowables(story, image_names, styles, OCR_ROOT / "imgs", available_width)


def draw_page(canvas, document):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#D8E2E8"))
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont(document._chapter_font, 7.5)
    canvas.setFillColor(colors.HexColor("#73818C"))
    canvas.drawString(18 * mm, 9 * mm, "第一章 空间向量与立体几何 - OCR 重建电子版")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"{document.page}")
    canvas.restoreState()


def build(output: Path) -> dict:
    if not OCR_ROOT.is_dir():
        raise FileNotFoundError(f"OCR root not found: {OCR_ROOT}")
    docs = sorted(OCR_ROOT.glob("doc_*.md"), key=lambda path: int(re.search(r"(\d+)$", path.stem).group(1)))
    if len(docs) != 69:
        raise ValueError(f"expected 69 OCR pages, found {len(docs)}")
    output.parent.mkdir(parents=True, exist_ok=True)

    font_name = register_chinese_font()
    styles = make_styles(font_name)
    margin = 18 * mm
    available_width = A4[0] - 2 * margin
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=17 * mm,
        bottomMargin=19 * mm,
        title=CHAPTER_TITLE + "（电子重建版）",
        author="一本通学习系统",
        subject="空间向量与立体几何第一章",
    )
    document._chapter_font = font_name
    story: list = []
    story.append(Spacer(1, 34 * mm))
    story.append(Paragraph(CHAPTER_TITLE, styles["CoverTitleCN"]))
    story.append(Paragraph("电子重建版 · 共 69 个教材页单元", styles["CoverSubCN"]))
    story.append(Spacer(1, 12 * mm))
    story.append(
        Paragraph(
            "本文件由仓库中保留的 69 份逐页 OCR 文稿和 151 张教材图示重建，正文、例题、变式和强化训练按原教材页序整理。原始 PDF 二进制未随当前仓库保留，因此本文件是可搜索的内容重建版，版式与原 PDF 可能不同。",
            styles["NoteCN"],
        )
    )
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("内容目录", styles["H1CN"]))
    toc = [
        ["第 1 节", "空间向量及其运算", "教材页 1-18"],
        ["第 2 节", "空间向量基本定理、空间向量及其运算的坐标表示", "教材页 19-40"],
        ["第 3 节", "空间向量的应用", "教材页 41-55"],
        ["微专题", "空间向量与立体几何综合训练", "教材页 56-69"],
    ]
    toc_data = [[Paragraph(para_text(cell), styles["BodyCN"]) for cell in row] for row in toc]
    toc_table = Table(toc_data, colWidths=[25 * mm, 93 * mm, 32 * mm], hAlign="LEFT")
    toc_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C7CF")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF2F5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(toc_table)

    for index, doc in enumerate(docs):
        add_doc(story, doc, index, styles, font_name, available_width)

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return {"output": str(output), "ocr_pages": len(docs), "font": font_name, "size": output.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a searchable Chapter 1 PDF from the preserved OCR packet.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(build(args.output))


if __name__ == "__main__":
    main()
