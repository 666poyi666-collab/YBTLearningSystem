from __future__ import annotations

import os
import argparse
import re
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATHJAX_SCRIPT = ROOT / "data" / "assets" / "mathjax" / "3.2.2" / "es5" / "tex-chtml.js"

_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<body>.+?)\s*$")
_LIST_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>(?:\d+[.)]|[-+*]))[ \t]+(?P<body>.*)$"
)
_UNSAFE_HTML_RE = re.compile(r"<\s*(?:script|style|iframe|img|svg|object|embed)\b", re.IGNORECASE)


def render_inline(text: str) -> str:
    """Escape Markdown text while preserving the few inline constructs used here."""
    protected: list[str] = []

    def protect(markup: str) -> str:
        token = f"\x00{len(protected)}\x00"
        protected.append(markup)
        return token

    text = re.sub(
        r"`([^`\n]+)`",
        lambda match: protect(f"<code>{escape(match.group(1), quote=False)}</code>"),
        text,
    )
    rendered = escape(text, quote=False)
    rendered = re.sub(r"\*\*([^\n]+?)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", rendered)
    rendered = rendered.replace("  \n", "<br>\n")
    for index, markup in enumerate(protected):
        rendered = rendered.replace(f"\x00{index}\x00", markup)
    return rendered


def _indent_width(value: str) -> int:
    return len(value.expandtabs(4))


def _render_list_item_body(body: str) -> str:
    checkbox = re.match(r"^\[([ xX])\]\s+(.*)$", body)
    if checkbox:
        checked = " checked" if checkbox.group(1).lower() == "x" else ""
        return (
            '<span class="task-item"><input type="checkbox" disabled'
            f"{checked}> <span>{render_inline(checkbox.group(2))}</span></span>"
        )
    return render_inline(body)


def _render_list(lines: list[str], index: int, base_indent: int) -> tuple[str, int]:
    first = _LIST_RE.match(lines[index])
    if first is None:
        raise ValueError("list renderer called without a list item")

    ordered = first.group("marker")[0].isdigit()
    tag = "ol" if ordered else "ul"
    items: list[str] = []
    cursor = index

    while cursor < len(lines):
        match = _LIST_RE.match(lines[cursor])
        if match is None:
            break
        indent = _indent_width(match.group("indent"))
        current_ordered = match.group("marker")[0].isdigit()
        if indent < base_indent or indent > base_indent or current_ordered != ordered:
            break

        body = _render_list_item_body(match.group("body"))
        cursor += 1
        nested = ""
        if cursor < len(lines):
            nested_match = _LIST_RE.match(lines[cursor])
            if nested_match is not None:
                nested_indent = _indent_width(nested_match.group("indent"))
                if nested_indent > base_indent:
                    nested, cursor = _render_list(lines, cursor, nested_indent)
        task_item = re.match(r"^`任务\s+\d+`", match.group("body").strip()) is not None
        if task_item:
            body = f'<div class="task-main">{body}</div>'
        class_attr = ' class="task-card"' if task_item else ""
        items.append(f"<li{class_attr}>{body}{nested}</li>")

    return f"<{tag}>" + "".join(items) + f"</{tag}>", cursor


def _render_table(table_html: str) -> str:
    if _UNSAFE_HTML_RE.search(table_html):
        raise ValueError("unsafe HTML is not allowed in the learning preview")
    return f'<div class="table-wrap">{table_html}</div>'


def _mathjax_script_src(output_path: Path) -> str:
    if not MATHJAX_SCRIPT.is_file():
        return ""
    return Path(os.path.relpath(MATHJAX_SCRIPT, output_path.parent)).as_posix()


def render_markdown(text: str) -> str:
    """Render the generated packet Markdown without a third-party dependency.

    The exporter intentionally emits raw knowledge tables. They are recognized as
    trusted table blocks; every other HTML-looking input is escaped as text.
    """
    lines = text.splitlines()
    blocks: list[str] = []
    cursor = 0

    def is_special(line: str) -> bool:
        stripped = line.strip()
        return bool(
            _HEADING_RE.match(line)
            or _LIST_RE.match(line)
            or line.lstrip().startswith(">")
            or stripped == "---"
            or re.match(r"^\s*<table\b", line, re.IGNORECASE)
        )

    while cursor < len(lines):
        line = lines[cursor]
        if not line.strip():
            cursor += 1
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            level = len(heading.group("marks"))
            heading_body = heading.group("body").strip()
            heading_class = ""
            heading_id = ""
            if level == 2 and heading_body == "一眼总览":
                heading_class = ' class="overview-heading"'
                heading_id = ' id="overview"'
            elif level == 2 and heading_body.startswith("循环 "):
                cycle_match = re.match(r"循环\s+(\d+)", heading_body)
                heading_class = ' class="cycle-heading"'
                if cycle_match:
                    heading_id = f' id="cycle-{cycle_match.group(1)}"'
            blocks.append(
                f"<h{level}{heading_class}{heading_id}>{render_inline(heading_body)}</h{level}>"
            )
            cursor += 1
            continue

        if line.strip() == "---":
            blocks.append("<hr>")
            cursor += 1
            continue

        if line.lstrip().startswith(">"):
            quote_lines: list[str] = []
            while cursor < len(lines) and lines[cursor].lstrip().startswith(">"):
                quote_lines.append(re.sub(r"^\s*>\s?", "", lines[cursor]))
                cursor += 1
            blocks.append(f"<blockquote>{render_markdown(chr(10).join(quote_lines))}</blockquote>")
            continue

        if re.match(r"^\s*<table\b", line, re.IGNORECASE):
            table_lines = [line.strip()]
            cursor += 1
            while not re.search(r"</table\s*>", table_lines[-1], re.IGNORECASE):
                if cursor >= len(lines):
                    raise ValueError("unterminated table in learning preview source")
                table_lines.append(lines[cursor].strip())
                cursor += 1
            blocks.append(_render_table("\n".join(table_lines)))
            continue

        if _LIST_RE.match(line):
            base_indent = _indent_width(_LIST_RE.match(line).group("indent"))
            rendered_list, cursor = _render_list(lines, cursor, base_indent)
            blocks.append(rendered_list)
            continue

        paragraph_lines = [line]
        cursor += 1
        while cursor < len(lines) and lines[cursor].strip() and not is_special(lines[cursor]):
            paragraph_lines.append(lines[cursor])
            cursor += 1
        blocks.append(f"<p>{render_inline(chr(10).join(paragraph_lines))}</p>")

    return "\n".join(blocks)


def export_preview(markdown_path: Path, output_path: Path) -> None:
    text = markdown_path.read_text(encoding="utf-8-sig")
    title = text.splitlines()[0].lstrip("# ").strip() or "学习路线预览"
    rendered = render_markdown(text)
    mathjax_src = _mathjax_script_src(output_path)
    mathjax_tag = (
        f'<script defer data-mathjax-version="3.2.2" src="{escape(mathjax_src, quote=True)}"></script>'
        if mathjax_src
        else '<meta name="mathjax-status" content="missing-local-resource">'
    )
    document = (
        "<!doctype html>\n"
        "<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{escape(title)}</title>"
        "<style>"
        ":root{color-scheme:light;--ink:#1f2933;--muted:#52606d;--navy:#243b53;--teal:#0f766e;--teal-soft:#e7f5f2;--amber:#b45309;--amber-soft:#fff7e6;--line:#d9e2ec;--paper:#ffffff;--page:#eef2f4;}"
        "*{box-sizing:border-box;}"
        "html{scroll-behavior:smooth;}"
        "body{margin:0;background:var(--page);color:var(--ink);font:16px/1.7 system-ui,'Microsoft YaHei',sans-serif;}"
        "main.report-page{max-width:1180px;margin:0 auto;padding:36px 34px 72px;background:var(--paper);min-height:100vh;box-shadow:0 0 0 1px rgba(36,59,83,.06);}" 
        "h1{margin:0 0 1.2rem;padding-bottom:1.1rem;border-bottom:3px solid var(--teal);color:var(--navy);font-size:2rem;line-height:1.3;}"
        "h2{margin:2.7rem 0 1rem;padding-top:1.25rem;border-top:1px solid var(--line);color:var(--navy);font-size:1.42rem;line-height:1.4;scroll-margin-top:1rem;}"
        "h2.overview-heading{margin-top:1.1rem;padding-top:.6rem;border-top:0;color:var(--teal);}"
        "h2.cycle-heading{border-top:0;border-left:5px solid var(--teal);padding:.55rem 0 .55rem .85rem;background:var(--teal-soft);}" 
        "h3{margin:1.75rem 0 .7rem;color:#315c67;font-size:1.15rem;line-height:1.45;}"
        "h4{margin:1.25rem 0 .55rem;color:#486581;font-size:1rem;line-height:1.45;}"
        "p{margin:.7rem 0;word-break:break-word;}"
        "blockquote{margin:1rem 0;padding:.85rem 1rem;border-left:4px solid var(--amber);background:var(--amber-soft);color:var(--muted);}"
        "blockquote p{margin:.15rem 0;}"
        "ul,ol{margin:.55rem 0 1rem;padding-left:2rem;}"
        "li{margin:.25rem 0;word-break:break-word;}"
        "li>ul,li>ol{margin:.15rem 0 .35rem;}"
        "code{padding:.12rem .35rem;border:1px solid var(--line);border-radius:4px;background:#f4f7f8;color:#315c67;font:.92em ui-monospace,SFMono-Regular,Consolas,monospace;word-break:break-word;}"
        "hr{margin:2.2rem 0;border:0;border-top:1px solid var(--line);}"
        ".table-wrap{max-width:100%;margin:1.2rem 0;overflow-x:auto;border:1px solid var(--line);border-radius:6px;}"
        "table{width:100%;border-collapse:collapse;color:var(--navy);font-size:.94rem;line-height:1.55;}"
        "td,th{border:1px solid var(--line);padding:.6rem .7rem;vertical-align:top;word-break:break-word;}"
        "th{background:#f4f7f8;font-weight:700;text-align:left;}"
        "td[style*='text-align: center'],th[style*='text-align: center']{text-align:center;}"
        ".overview-table{min-width:760px;}"
        ".overview-table thead th{background:var(--teal);color:#fff;border-color:#0b625c;}"
        ".overview-table tbody tr:nth-child(even) td,.overview-table tbody tr:nth-child(even) th{background:#fbfcfc;}"
        ".overview-table tbody th{width:18%;color:var(--navy);}"
        ".overview-table thead th:last-child,.overview-table tbody td:last-child{width:12%;min-width:112px;white-space:nowrap;}"
        "li.task-card{margin:.7rem 0;padding:.75rem .9rem;border:1px solid var(--line);border-left:4px solid var(--teal);border-radius:5px;background:#fbfdfd;list-style-position:outside;}"
        ".task-main{font-weight:600;color:var(--navy);}"
        "li.task-card>ul{margin:.55rem 0 .05rem;padding-left:1.4rem;color:var(--muted);font-size:.94rem;}"
        "li.task-card>ul>li{margin:.28rem 0;}"
        ".task-item{display:inline-flex;align-items:flex-start;gap:.4rem;}"
        ".task-item input{width:1rem;height:1rem;margin-top:.35rem;flex:0 0 auto;}"
        "@media (max-width:720px){body{font-size:15px;}main.report-page{padding:24px 16px 52px;}h1{font-size:1.55rem;}h2{font-size:1.25rem;margin-top:2.1rem;}h3{font-size:1.06rem;}table{min-width:620px;}.overview-table{min-width:760px;}li.task-card{padding:.65rem .7rem;}}"
        "@media print{body{background:#fff;}main.report-page{max-width:none;padding:0;box-shadow:none;}h2.cycle-heading{break-before:page;}li.task-card{break-inside:avoid;}}"
        "</style>"
        "<script>window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']],displayMath:[['\\\\[','\\\\]']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre','code']}};</script>"
        f"{mathjax_tag}"
        "</head><body><main class=\"report-page\">"
        f"{rendered}"
        "</main></body></html>\n"
    )
    output_path.write_text(document, encoding="utf-8", newline="\r\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a browser preview with an explicit UTF-8 charset")
    parser.add_argument("--section", default="1.1")
    parser.add_argument("--output")
    args = parser.parse_args()
    packet_dir = ROOT / "data" / "packets" / args.section.replace("+", "_")
    markdown_path = packet_dir / "learning_path_without_questions.md"
    output_path = Path(args.output) if args.output else packet_dir / "learning_path_without_questions.html"
    export_preview(markdown_path, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
