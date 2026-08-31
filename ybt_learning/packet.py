from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from .common import clean_text, delimiter_errors, normalize_math, save_json, stable_id
from .answers import build_answer_index, merge_answer_indexes
from .vision import structured_answer_leaks, structured_visual_errors


QUESTION_RE = re.compile(r"(?m)^(?:#{1,6}\s*)?(?P<number>\d{1,2})\s*(?:\\?[.．、]|(?=（)|(?=\())\s*(?:（[^\n]{0,80}）|\([^\n]{0,80}\)|[^\n]*)")
GROUP_RE = re.compile(r"(?i)(?:^|\n)\s*(?:#{1,6}\s*)?(?P<group>[ABC])\s*组")
ANSWER_MARKER_RE = re.compile(r"(?im)^\s*(?:答案|解答|解析|点评|反思)\s*[：:]?")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
STUDENT_SOLUTION_MARKER_RE = re.compile(r"(?im)(?:^|\n)\s*(?:解法\s*[一二两12]|证明|解答|解析|答案|故答案|最终答案|所以(?:其|余弦|得到)|因此(?:得到|可得)|故(?:得|为|其))\s*[：:：]?")
# OCR from answer books can leave a bare option on its own line, for example
# ``### 1. B``.  It is not a normal student question and must never cross the
# student/context boundary.  Keep this exact-line rule narrow to avoid
# deleting legitimate option text such as ``A. B``.
BARE_ANSWER_LINE_RE = re.compile(r"(?im)^\s*#{0,6}\s*\d{1,2}\s*[.．、]\s*[A-D]\s*$")
CHOICE_JUDGEMENT_LINE_RE = re.compile(
    r"(?im)^.*(?:故\s*[A-D]\s*项(?:正确|错误)|正确选项|故选\s*[A-D]).*$"
)
HTML_IMAGE_MARKUP_RE = re.compile(r"(?is)<(?:div|img|/div|figure|/figure|p|/p)\b[^>]*>")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PacketError(ValueError):
    pass


def _portable_source_identity(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.name


def _portable_artifact_paths(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _portable_artifact_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable_artifact_paths(item) for item in value]
    if isinstance(value, tuple):
        return [_portable_artifact_paths(item) for item in value]
    if not isinstance(value, str) or not value:
        return value
    try:
        path = Path(value)
        if not path.is_absolute():
            return value
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except (OSError, ValueError):
        return value


def _sha256_file(path: Path) -> str | None:
    """Return a content identity for an image, when the file is available.

    OCR runs can materialize the same cropped figure under different roots.
    Path equality is therefore not enough to bind a visual sidecar to a
    question; the hash is the second, content-based identity.
    """
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _usable_vision_sidecar(sidecar: dict[str, Any] | None) -> bool:
    """Accept only a real, non-degraded visual result."""
    if not isinstance(sidecar, dict) or sidecar.get("status") != "passed":
        return False
    if sidecar.get("confidence") not in {"E1", "E2"}:
        return False
    structured = sidecar.get("structured")
    if not isinstance(structured, dict):
        structured = sidecar.get("vision")
    if not isinstance(structured, dict):
        return False
    if any("```" in str(value) for value in structured.values()):
        return False
    if any("视觉模型未返回结构化JSON" in str(value) for value in structured.values()):
        return False
    if any(
        marker in json.dumps(structured, ensure_ascii=False).lower()
        for marker in ("答案册", "answer_book", "answer-book", "answerbook")
    ):
        return False
    if structured_answer_leaks(structured):
        return False
    if structured_visual_errors(structured, item_id=str(sidecar.get("item_id") or "")):
        return False
    meaningful = any(value not in (None, "", [], {}) for key in ("objects", "relations", "coordinates", "ranges", "text") for value in [structured.get(key)])
    if structured.get("confidence") == "E2|E1|E0":
        return False
    return bool(meaningful)


def _is_answer_book_path(value: Any) -> bool:
    """Student packets may never bind a figure or provenance to an answer book."""
    text = str(value or "").lower()
    chinese_answer_book = "答案册" in text and "无答案册" not in text
    return chinese_answer_book or any(marker in text for marker in ("answer_book", "answer-book", "answerbook"))


def _split_answer(text: str) -> tuple[str, str]:
    match = ANSWER_MARKER_RE.search(text)
    if not match:
        return text.strip(), ""
    return text[: match.start()].strip(), text[match.start() :].strip()


def _trim_question_tail(text: str) -> str:
    """Remove the next exercise-group header accidentally captured by a page-ending question."""
    match = re.search(r"(?im)^\s*(?:#{1,6}\s*)?(?:一\s*数.*|[ABC]\s*组\s+(?:夯实基础|强化能力|拓展提升).*)$", text)
    return text[: match.start()].rstrip() if match else text.strip()


def _redact_answer_sections(text: str) -> str:
    """保留知识点/题干，移除页内答案与解析直到下一个标题或例题。"""
    marker = re.compile(r"(?ims)(?:^|\n)\s*(?:答案|解析|解答|点评|反思)\s*[：:]?.*?(?=\n\s*(?:#{1,6}\s|【(?:例|变式)|\d{1,2}\s*\\?[.．、])|\Z)")
    text = marker.sub("\n", text)
    # 对 OCR 把标记粘到正文行中的情况再做一次确定性清除。
    text = re.sub(r"(?im)^\s*(?:答案|解析|解答|点评|反思)\s*[：:].*$", "", text)
    return text


def _redact_student_text(text: str) -> str:
    """学生包只保留知识点/题面；方法册中的完整解法、答案和收尾结论全部隔离。"""
    text = _redact_answer_sections(text)
    # 例题区的“解/证明/解法/解析”通常一路持续到下一例题、类型标题或页尾。
    block = re.compile(r"(?ims)(?:^|\n)\s*(?:解法\s*[一二两12]|证明|证明过程|解答|解析|答案)\s*[：:：]?.*?(?=\n\s*(?:#{1,6}\s|【(?:例|变式)|##\s*类型|类型[一二三四五六IVXⅠⅡⅢⅣⅤⅥ]|##\s*(?:A|B|C)\s*组|\Z))")
    text = block.sub("\n", text)
    # OCR 有时把“证明：”接在题干/选项同一行，无法依赖行首；从该标记到下一个结构标题均隔离。
    inline = re.compile(r"(?ims)^(?!\s*[（(]\s*\d+\s*[）)])\s*(?:证明|证明过程)\s*[：:]?.*?(?=\n\s*(?:#{1,6}\s|【(?:例|变式)|##\s*类型|类型[一二三四五六IVXⅠⅡⅢⅣⅤⅥ]|##\s*(?:A|B|C)\s*组)|\Z)")
    text = inline.sub("\n", text)
    # OCR 常把“最终答案是/故答案为”嵌在行中，仍需清除该行及其后的明确结论。
    text = re.sub(r"(?im)^.*(?:最终答案|故答案|答案为|所以其余弦值|因此得到|故得|故为).*$", "", text)
    # Some method-book OCR drops the explicit "解析：" heading and appends a
    # full option-by-option judgement directly after the last choice.  The
    # first judgement line is an unambiguous solution boundary; discard it and
    # everything after it while preserving the A-D question stem above.
    choice_judgement = CHOICE_JUDGEMENT_LINE_RE.search(text)
    if choice_judgement:
        text = text[: choice_judgement.start()]
    text = re.sub(r"(?im)^\s*【反思】.*$", "", text)
    # The image reference has already been extracted into image_refs.  Remove
    # the HTML shell from the pure-text field so a text-only worker does not
    # mistake markup for mathematical content.
    text = HTML_IMAGE_MARKUP_RE.sub("", text)
    # Answer-book OCR sometimes appends a standalone choice after the actual
    # question.  Remove it in the student view and leave the answer sidecar
    # untouched.
    text = BARE_ANSWER_LINE_RE.sub("", text)
    return text


def _student_page_text(text: str) -> str:
    """页级文本也必须走同一套答案/解法隔离，防止 DeepSeek 从 pages 绕过题目隔离。"""
    return _redact_student_text(text)


EXERCISE_HEADING_RE = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?(?:知识点|内容纲要|强化训练|A\s*组|B\s*组|C\s*组|类型\s*[一二三四五六IVXⅠⅡⅢⅣⅤⅥ])"
)
LESSON_EXAMPLE_RE = re.compile(r"(?im)^\s*(?:【(?:例|变式)[^】]*】|例\s*\d+|变式\s*\d*)")
LEARNING_ITEM_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?【\s*(?P<kind>例|变式)\s*(?P<label>[^】]*)】"
)
LEARNING_STRUCTURE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:知识点|类型|内容纲要|强化训练|[ABC]\s*组)"
)
LEARNING_SOLUTION_RE = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?(?:【\s*(?:解|解析|证明|答案|点评|反思)\s*】|"
    r"(?:解|解析|证明|答案|解法\s*(?:[一二两三四五六七八九十百\d]+)?|"
    r"证法\s*[一二两三四五六七八九十百\d]*)\s*[：:])"
)
INLINE_LEARNING_ITEM_RE = re.compile(r"(?=【\s*(?:例|变式)\s*[^】]*】)")


def _student_lesson_free_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """学生尝试包不携带讲义例题解法；例题完整内容另存 lesson_packet 供听课阶段使用。"""
    example_mode = False
    result: list[dict[str, Any]] = []
    for page in pages:
        kept: list[str] = []
        for line in page.get("text", "").splitlines():
            if example_mode:
                if EXERCISE_HEADING_RE.match(line):
                    example_mode = False
                    kept.append(line)
                else:
                    continue
            else:
                if LESSON_EXAMPLE_RE.match(line):
                    example_mode = True
                    continue
                kept.append(line)
        text = _student_page_text("\n".join(kept))
        if not text.strip() and str(page.get("text", "")).strip():
            text = (
                f"（ocr_doc {page.get('ocr_doc')} 为方法册教学续页；"
                "完整教学内容已进入 learning_packet.json，独立作答上下文仅保留此中性锚点。）"
            )
        result.append({**page, "text": text, "image_refs": _image_refs(text, Path(page.get("source_path", ".")).parent), "math_errors": delimiter_errors(text)})
    return result


def _learning_solution_boundary(text: str) -> int | None:
    boundaries = [
        match.start()
        for pattern in (LEARNING_SOLUTION_RE, CHOICE_JUDGEMENT_LINE_RE)
        if (match := pattern.search(text)) is not None
    ]
    return min(boundaries) if boundaries else None


def _split_learning_solution(text: str) -> tuple[str, str]:
    """Split a worked item without treating the example solution as exercise evidence."""
    boundary = _learning_solution_boundary(text)
    if boundary is None:
        return _redact_student_text(text).strip(), ""
    return _redact_student_text(text[:boundary]).strip(), text[boundary:].strip()


def _example_number(label: str) -> int | None:
    match = re.search(r"\d+", label)
    return int(match.group()) if match else None


def _learning_role(section: dict[str, Any], number: int | None) -> tuple[str, str | None]:
    if number is None:
        return "worked_example", None
    first_chapter_sections = {"1.1", "1.2+1.3", "1.4", "micro专题1"}
    if str(section.get("id")) not in first_chapter_sections:
        # OCR knowledge spans can include later type examples. Prefer the
        # explicit type heading in the generic chapter 2-5 extraction.
        for item in section.get("type_training", []):
            if number in item.get("example_numbers", []):
                return "type_example", item.get("type")
    for point in section.get("knowledge_points", []):
        examples = {str(item).replace(" ", "") for item in point.get("examples", [])}
        if f"例{number}" in examples:
            return "knowledge_example", point.get("id")
    for item in section.get("type_training", []):
        if number in item.get("example_numbers", []):
            return "type_example", item.get("type")
    return "worked_example", None


def _repair_learning_item_layout(section_id: str, items: list[dict[str, Any]], pages: list[dict[str, Any]]) -> None:
    """Repair source-verified two-column continuations after OCR linearization."""
    page_text = {page.get("ocr_doc"): str(page.get("text", "")) for page in pages}
    examples = {item.get("example_number"): item for item in items if item.get("kind") == "example"}

    if section_id == "ch3.s1":
        example3 = examples.get(3)
        if example3:
            question = (
                r"【例3】若椭圆 \(\frac{x^{2}}{25}+y^{2}=1\) 上一点 \(P\) 到椭圆一个焦点的距离为 3，"
                r"则 \(P\) 到另一个焦点的距离为 ___。"
            )
            solution = (
                r"解析：由椭圆方程 \(\frac{x^{2}}{25}+y^{2}=1\) 可知 \(a=5\)，"
                r"所以点 \(P\) 到两焦点的距离之和为 \(2a=10\)，"
                r"所以 \(P\) 到另一个焦点的距离为 \(10-3=7\)。" + "\n\n答案：7"
            )
            example3["teaching_text"] = question + "\n\n" + solution
            example3["question_text"] = question
            example3["solution_present"] = True
            example3["source_layout_repair"] = {
                "status": "SOURCE_PDF_VISUALLY_VERIFIED",
                "source_pdf_sha256": "d5fd328c1937e8695f8527a16bfd6916849401eabe474ba3f4c0a9c185bf3af7",
                "pdf_pages": [1, 2],
                "reason": "例3题干跨双栏页尾与下一页页首，OCR把左栏知识正文插入题干。",
            }

        example6 = examples.get(6)
        if example6:
            question = (
                r"【例6】若点 \(A(\sqrt{2},m)\) 在椭圆 \(\frac{x^2}{4}+y^2=1\) 的内部，"
                r"则实数 \(m\) 的取值范围是 ___。"
            )
            solution = (
                r"解析：由题意，点 \(A\) 在椭圆的内部，所以 "
                r"\(\frac{(\sqrt{2})^2}{4}+m^2<1\)，解得 "
                r"\(-\frac{\sqrt{2}}{2}<m<\frac{\sqrt{2}}{2}\)。" + "\n\n"
                r"答案：\(\left(-\frac{\sqrt{2}}{2},\frac{\sqrt{2}}{2}\right)\)"
            )
            example6["teaching_text"] = question + "\n\n" + solution
            example6["question_text"] = question
            example6["solution_present"] = True
            example6["source_layout_repair"] = {
                "status": "SOURCE_PDF_VISUALLY_VERIFIED",
                "source_pdf_sha256": "d5fd328c1937e8695f8527a16bfd6916849401eabe474ba3f4c0a9c185bf3af7",
                "pdf_pages": [2, 3],
                "reason": "例6位于右栏，左栏特征三角形与焦点三角形正文被OCR插入题干和解析之间。",
            }

        for item in items:
            if (
                item.get("kind") == "direct_variant"
                and "\\angle F_1PF_2" in str(item.get("question_text") or "")
            ):
                item["image_refs"] = []
                item["visual_status"] = "READY_TEXT_ONLY"
                item["source_layout_repair"] = {
                    "status": "SOURCE_PDF_VISUALLY_VERIFIED",
                    "source_pdf_sha256": "d5fd328c1937e8695f8527a16bfd6916849401eabe474ba3f4c0a9c185bf3af7",
                    "pdf_page": 9,
                    "reason": "OCR绑定的M/N圆图属于上一道变式1解析；变式2自己的P点示意图位于答案解析区，不进入独立作答题面。",
                }
        return

    if section_id == "ch3.s12":
        example2 = examples.get(2)
        if example2:
            question = (
                r"【例2】设抛物线 \(y^2=4x\) 的焦点为 \(F\)，\(O\) 是坐标原点，\(M(4,0)\)，"
                r"过点 \(F\) 的直线与抛物线交于 \(A,B\) 两点，延长 \(AM,BM\) 分别交抛物线于 "
                r"\(C,D\) 两点，\(P,Q\) 分别是 \(AB,CD\) 的中点。" + "\n"
                r"（1）求直线 \(OP\) 的斜率的取值范围；" + "\n"
                r"（2）求 \(\cos\angle POQ\) 的最小值。"
            )
            teaching = str(example2.get("teaching_text") or "")
            solution_start = teaching.find("由题意，\\(F(1,0)\\)")
            if solution_start < 0:
                raise PacketError("ch3.s12 例2 source-verified solution boundary is missing")
            example2["teaching_text"] = question + "\n\n解：（1）" + teaching[solution_start:]
            example2["question_text"] = question
            example2["solution_present"] = True
            example2["source_layout_repair"] = {
                "status": "SOURCE_PDF_VISUALLY_VERIFIED",
                "source_pdf_sha256": "4060e78273b1d002bc484a186f69df8b1acfaa643b332a75926ea10964b1de86",
                "pdf_pages": [3, 4],
                "reason": "OCR遗漏蓝色提示后的“解：（1）”标记，导致整段解答进入question_text。",
            }
        return

    if section_id == "4.4":
        example6 = examples.get(6)
        continuation = page_text.get(53, "")
        if example6 and continuation:
            start = continuation.find("解析：由")
            end = continuation.find("## 知识点5", start)
            if start < 0 or end <= start:
                raise PacketError("4.4 例6 source-verified cross-page solution is missing")
            example6["teaching_text"] = (
                str(example6.get("teaching_text") or "").rstrip()
                + "\n\n"
                + continuation[start:end].strip()
            )
            example6["source_docs"] = sorted(set([*example6.get("source_docs", []), 53]))
            question_text, solution_text = _split_learning_solution(example6["teaching_text"])
            example6["question_text"] = question_text
            example6["solution_present"] = bool(solution_text)
            example6["source_layout_repair"] = {
                "status": "SOURCE_PDF_VISUALLY_VERIFIED",
                "source_pdf_sha256": "e32b88dc4c34007ae8ec16ee0faed3a2949ae1952235d1b9a8e5aea5f2d59f5c",
                "pdf_pages": [53, 54],
                "reason": "例6题干在第53页右栏，解析位于第54页右栏且被OCR排到下一知识点标题之后。",
            }
        return

    if section_id == "2.1":
        example5 = examples.get(5)
        if example5:
            question = (
                r"【例5】已知直线 \(l\) 的倾斜角 \(\alpha\) 满足 "
                r"\(\frac{\pi}{3}<\alpha\leq\frac{3\pi}{4}\)，则 \(l\) 的斜率 \(k\) 的取值范围是（ ）" + "\n"
                r"A. \([-1,\sqrt{3})\)  B. \([-\sqrt{3},1]\)" + "\n"
                r"C. \(( -\infty,-1]\cup(\sqrt{3},+\infty)\)  "
                r"D. \(( -\infty,-\sqrt{3}]\cup(-1,+\infty)\)"
            )
            solution = (
                r"解析：正切函数 \(k=\tan\alpha\) 在 \(\left[0,\frac{\pi}{2}\right)\) 和 "
                r"\(\left(\frac{\pi}{2},\pi\right)\) 上分别单调递增。"
                r"当 \(\frac{\pi}{3}<\alpha<\frac{\pi}{2}\) 时，\(k>\sqrt{3}\)；"
                r"当 \(\alpha=\frac{\pi}{2}\) 时斜率不存在；"
                r"当 \(\frac{\pi}{2}<\alpha\leq\frac{3\pi}{4}\) 时，\(k\leq-1\)。"
                r"所以 \(k\in(-\infty,-1]\cup(\sqrt{3},+\infty)\)。" + "\n\n答案：C"
            )
            example5["teaching_text"] = question + "\n\n" + solution
            example5["question_text"] = question
            example5["solution_present"] = True
            example5["source_layout_repair"] = {
                "status": "SOURCE_PDF_VISUALLY_VERIFIED",
                "pdf_pages": [2, 3],
                "reason": "右栏例5跨页，OCR把下一知识点左栏正文插入题干与解析之间。",
            }

        example7 = examples.get(7)
        if example7:
            question = (
                r"【例7】若直线 \(l\) 的一个方向向量 \(\vec n=(1,-\sqrt{3})\)，则 \(l\) 的倾斜角为（ ）" + "\n"
                r"A. \(30^\circ\)  B. \(60^\circ\)  C. \(120^\circ\)  D. \(150^\circ\)"
            )
            solution = (
                r"解析：设直线 \(l\) 的斜率为 \(k\)，倾斜角为 \(\alpha\)。"
                r"由题意，\(k=\frac{-\sqrt{3}}{1}=-\sqrt{3}\)，故 \(\tan\alpha=-\sqrt{3}\)。"
                r"结合 \(0^\circ\leq\alpha<180^\circ\) 可得 \(\alpha=120^\circ\)。" + "\n\n答案：C"
            )
            example7["teaching_text"] = question + "\n\n" + solution
            example7["question_text"] = question
            example7["solution_present"] = True
            example7["source_layout_repair"] = {
                "status": "SOURCE_PDF_VISUALLY_VERIFIED",
                "pdf_pages": [3, 4],
                "reason": "右栏例7跨页，OCR把左栏平行垂直知识正文插入题干与选项之间。",
            }
        return

    if section_id == "2.2":
        for item in items:
            if item.get("kind") == "direct_variant" and "垂直平分线" in str(item.get("question_text") or ""):
                text = str(item.get("question_text") or "")
                boundary = text.find("\n设 ")
                if boundary < 0:
                    raise PacketError("2.2 变式2 source-verified solution boundary is missing")
                item["question_text"] = text[:boundary].strip()
                item["source_layout_repair"] = {
                    "status": "SOURCE_PDF_TEXT_VERIFIED",
                    "source_docs": [16],
                    "reason": "根据源页边界，从“设AB中点”起隔离后续教学过程。",
                }
        return

    if section_id == "4.5":
        for item in items:
            if item.get("kind") == "direct_variant" and "S_9+8S_3" in str(item.get("question_text") or ""):
                text = str(item.get("question_text") or "")
                boundary = text.find("\n设等比数列")
                if boundary < 0:
                    raise PacketError("4.5 例4变式2 source-verified solution boundary is missing")
                item["question_text"] = text[:boundary].strip()
                item["source_layout_repair"] = {
                    "status": "SOURCE_PDF_TEXT_VERIFIED",
                    "source_docs": [66, 67],
                    "reason": "根据源页边界，从“设等比数列”起隔离后续教学过程。",
                }
        return

    if section_id == "5.2":
        for item in items:
            if item.get("kind") == "direct_variant" and "切线也是" in str(item.get("question_text") or ""):
                text = str(item.get("question_text") or "")
                boundary = text.find("\n由题意")
                if boundary < 0:
                    raise PacketError("5.2 例8变式3 source-verified solution boundary is missing")
                item["question_text"] = text[:boundary].strip()
                item["source_layout_repair"] = {
                    "status": "SOURCE_PDF_TEXT_VERIFIED",
                    "source_docs": [13],
                    "reason": "根据源页边界，从“由题意”起隔离后续教学过程。",
                }
        return

    if section_id == "5.4":
        for item in items:
            if item.get("kind") == "direct_variant" and item.get("label") == "变式2" and "证明不等式" in str(item.get("question_text") or ""):
                item["question_text"] = (
                    r"【变式2】证明不等式：\(\left(1-\frac{2}{x}\right)\ln x>-\frac{1}{2}\)（\(x>0\)）。"
                )
                item["source_layout_repair"] = {
                    "status": "SOURCE_PDF_VISUALLY_VERIFIED",
                    "source_pdf_sha256": "205282fd79c60a2539cd231044a6d06c5f78a44845a9879d931766851789fa25",
                    "pdf_page": 52,
                    "reason": "OCR漏掉“证明不等式：”后的整条公式，原页公式已逐字恢复；证法1起隔离为解答。",
                }
        return

    if section_id == "1.2+1.3":
        example3 = examples.get(3)
        source20 = page_text.get(20, "")
        if example3 and "的射影来寻找向量" in source20 and "## 知识点3" in source20:
            base = example3["teaching_text"]
            contamination_start = base.find("面，依次交x轴")
            if contamination_start >= 0:
                base = base[:contamination_start].rstrip()
            continuation = source20[source20.index("的射影来寻找向量"):source20.index("## 知识点3")].strip()
            example3["teaching_text"] = base + continuation
            question_text, solution_text = _split_learning_solution(example3["teaching_text"])
            example3["question_text"] = question_text
            example3["solution_present"] = bool(solution_text)
        return

    if section_id == "1.4":
        example9 = examples.get(9)
        if example9:
            question = (
                r"【例9】在空间直角坐标系中，已知平面 \(\alpha\)，\(\beta\) 的一个法向量分别为 "
                r"\(\boldsymbol m=(0,-1,-1)\)，\(\boldsymbol n=(-2,1,2)\)，则 \(\alpha\) 与 \(\beta\) "
                r"的夹角的余弦值为（ ）" + "\n"
                r"A. \(\frac{2}{3}\)  B. \(\frac{\sqrt{2}}{3}\)  "
                r"C. \(-\frac{\sqrt{2}}{2}\)  D. \(\frac{\sqrt{2}}{2}\)"
            )
            solution = (
                r"解析：设两平面的夹角为 \(\theta\)，则 "
                r"\(\cos\theta=\frac{|\boldsymbol m\cdot\boldsymbol n|}{|\boldsymbol m|\,|\boldsymbol n|}"
                r"=\frac{|0\times(-2)+(-1)\times1+(-1)\times2|}{\sqrt{2}\times3}"
                r"=\frac{\sqrt{2}}{2}\)。" + "\n\n答案：D"
            )
            example9["teaching_text"] = question + "\n\n" + solution
            example9["question_text"] = question
            example9["solution_present"] = True
            example9["source_layout_repair"] = {
                "status": "SOURCE_PDF_VISUALLY_VERIFIED",
                "pdf_pages": [4, 5],
                "reason": "例9题干和法向量坐标跨页，OCR将左栏三类空间角知识正文插入题干。",
            }

        example7 = examples.get(7)
        if example7:
            example7["teaching_text"] = re.sub(r"(?m)^答案：C\s*\n+", "", example7["teaching_text"], count=1)

        example16 = examples.get(16)
        if example16 and "解：" in example16["teaching_text"]:
            clean_question = (
                r"【例16】（2021·天津卷（节选））如图，在棱长为2的正方体 "
                r"\(ABCD-A_1B_1C_1D_1\) 中，\(E\)，\(F\) 分别为棱 "
                r"\(BC\)，\(CD\) 的中点，求直线 \(AC_1\) 与平面 "
                r"\(A_1EC_1\) 所成角的正弦值。"
            )
            solution = "解：" + example16["teaching_text"].split("解：", 1)[1]
            example16["teaching_text"] = clean_question + "\n\n" + solution

        example18 = examples.get(18)
        if example18:
            text = example18["teaching_text"]
            start = text.find("所以由点到直线的距离公式")
            end = text.find("答案：1", start)
            if start >= 0 and end > start:
                calculation = (
                    r"所以由点到直线的距离公式，点 \(A\) 到直线 \(l\) 的距离 "
                    r"\(d=\sqrt{|\overrightarrow{AB}|^2-(\overrightarrow{AB}\cdot\boldsymbol{u})^2}"
                    r"=\sqrt{3-2}=1\)。" + "\n\n"
                )
                text = text[:start] + calculation + text[end:]
            reflection = text.find("【反思】")
            if reflection >= 0:
                text = text[:reflection] + (
                    r"【反思】设 \(A\) 为直线 \(l\) 外一点，\(B\) 为直线 \(l\) 上任意一点，"
                    r"\(u\) 为直线 \(l\) 的一个单位方向向量，则点 \(A\) 到直线 \(l\) 的距离 "
                    r"\(d=\sqrt{|\overrightarrow{AB}|^2-(\overrightarrow{AB}\cdot u)^2}\)。"
                )
            example18["teaching_text"] = text

        example22 = examples.get(22)
        if example22:
            example22["teaching_text"] = example22["teaching_text"].replace(
                r"平面 \(CDC\) 的一个法向量", r"平面 \(CDC_1\) 的一个法向量"
            )

        for item in (example9, example7, example16, example18, example22):
            if not item:
                continue
            question_text, solution_text = _split_learning_solution(item["teaching_text"])
            item["question_text"] = question_text
            item["solution_present"] = bool(solution_text)
        return

    if section_id == "micro专题1":
        example2 = examples.get(2)
        if example2:
            example2["teaching_text"] = example2["teaching_text"].replace(r"A_1EG\) 为平行四边形", r"A_1EGF\) 为平行四边形")
            example2["teaching_text"] = example2["teaching_text"].replace(r"A_1EG\) 为矩形", r"A_1EGF\) 为矩形")

        example5 = examples.get(5)
        if example5:
            text = example5["teaching_text"].replace(
                r"P\left(1,1,\frac{1}{2}\right)", r"P\left(1,1,\frac{1}{3}\right)"
            ).replace(r"\overrightarrow{DQ} // m", r"\overrightarrow{D_1Q}\parallel m")
            marker = "求上式的最值需要先分析"
            first = text.find(marker)
            second = text.find(marker, first + len(marker)) if first >= 0 else -1
            if first >= 0 and second > first:
                text = text[:first] + text[second:]
            example5["teaching_text"] = text

        example7 = examples.get(7)
        if example7:
            text = example7["teaching_text"]
            bad_start = text.find("连接 AC 交 BD 于点 G")
            clean_start = text.find("又 M 是 OA 中点", bad_start + 1)
            if bad_start >= 0 and clean_start > bad_start:
                text = text[:bad_start] + text[clean_start:]
            formula_start = text.find(r"\[\begin{aligned}")
            conclusion_start = text.find("因为平面 BDM", formula_start)
            if formula_start >= 0 and conclusion_start > formula_start:
                formula = (
                    r"由两平面的法向量可得 "
                    r"\(\left|\cos\langle\boldsymbol{m},\boldsymbol{n}\rangle\right|"
                    r"=\frac{\sin\theta}{\sqrt{\sin^2\theta+8}}\)。" + "\n\n"
                )
                text = text[:formula_start] + formula + text[conclusion_start:]
            text = text.replace(r"二面角 A-EF-D 的大小为  \(\frac{\pi}{7}\)", r"二面角 A-EF-D 的大小为 \(\frac{\pi}{2}\)")
            example7["teaching_text"] = text

        for item in (example2, example5, example7):
            if not item:
                continue
            question_text, solution_text = _split_learning_solution(item["teaching_text"])
            item["question_text"] = question_text
            item["solution_present"] = bool(solution_text)
        return

    if section_id != "1.1":
        return

    example2 = examples.get(2)
    if example2:
        continuation = (
            r"法则，\(\overrightarrow{AB}+\overrightarrow{AD}=\overrightarrow{AC}\)，" + "\n\n"
            r"所以\(\overrightarrow{AB}+\overrightarrow{AD}+\overrightarrow{CC_1}"
            r"=\overrightarrow{AC}+\overrightarrow{CC_1}=\overrightarrow{AC_1}\)。" + "\n\n"
            "答案：C"
        )
        example2["teaching_text"] = example2["teaching_text"].rstrip() + "\n" + continuation

    example4 = examples.get(4)
    source2 = page_text.get(2, "")
    if example4 and "共线，" in source2 and "【例5】" in source2:
        table_end = source2.rfind("</table>", 0, source2.index("【例5】"))
        start = table_end + len("</table>") if table_end >= 0 else source2.index("共线，")
        continuation = source2[start:source2.index("【例5】")].strip()
        example4["teaching_text"] = example4["teaching_text"].rstrip() + " " + continuation

    example5 = examples.get(5)
    source3 = page_text.get(3, "")
    if example5 and "分析一下理由，" in source3 and "## 知识点4" in source3:
        base = example5["teaching_text"]
        table_start = base.find("<table")
        if table_start >= 0:
            base = base[:table_start].rstrip()
        continuation = source3[source3.index("分析一下理由，"):source3.index("## 知识点4")].strip()
        example5["teaching_text"] = base + "\n\n" + continuation

    example7 = examples.get(7)
    if example7:
        text = example7["teaching_text"]
        contamination_start = text.find("(iii)")
        continuation_start = text.find("因为", contamination_start)
        if contamination_start >= 0 and continuation_start > contamination_start:
            example7["teaching_text"] = text[:contamination_start].rstrip() + "\n\n" + text[continuation_start:]

    for item in (example2, example4, example5, example7):
        if not item:
            continue
        question_text, solution_text = _split_learning_solution(item["teaching_text"])
        item["question_text"] = question_text
        item["solution_present"] = bool(solution_text)


def _apply_clean_learner_question_stems(
    section_id: str,
    items: list[dict[str, Any]],
    clean_stems: list[dict[str, Any]],
) -> None:
    """Replace reviewed learner text exactly, while retaining teaching solutions separately."""
    relevant = [row for row in clean_stems if str(row.get("section")) == section_id]
    if not relevant:
        return
    by_id = {str(item.get("item_id")): item for item in items}
    missing: list[str] = []
    for row in relevant:
        item_id = str(row.get("item_id") or "")
        item = by_id.get(item_id)
        if item is None:
            missing.append(item_id)
            continue
        clean_question_text = str(row.get("clean_question_text") or "")
        expected_sha256 = str(row.get("new_text_sha256") or "").lower()
        actual_sha256 = hashlib.sha256(clean_question_text.encode("utf-8")).hexdigest()
        if not clean_question_text or actual_sha256 != expected_sha256:
            raise PacketError(f"{section_id} invalid clean learner stem: {item_id}")
        if str(item.get("label") or "") != str(row.get("label") or ""):
            raise PacketError(f"{section_id} clean learner stem label mismatch: {item_id}")
        previous_text = str(item.get("question_text") or "")
        item["question_text"] = clean_question_text
        item["source_question_stem_review"] = {
            "status": "SOURCE_REVIEWED_ANSWER_FREE",
            "review_path": row.get("review_path"),
            "review_sha256": row.get("review_sha256"),
            "old_reported_question_text_sha256": row.get("old_text_sha256"),
            "pre_override_question_text_sha256": hashlib.sha256(previous_text.encode("utf-8")).hexdigest(),
            "question_text_sha256": expected_sha256,
            "confidence": row.get("confidence"),
            "boundary_basis": row.get("boundary_basis"),
            "source": row.get("source"),
        }
    if missing:
        raise PacketError(f"{section_id} clean learner stems did not bind: {missing}")


def _extract_learning_items(
    pages: list[dict[str, Any]],
    section: dict[str, Any],
    clean_stems: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Extract examples for teaching and answer-free variants for transfer."""
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_example: int | None = None

    def finish() -> None:
        nonlocal current
        if not current:
            return
        raw_text = "\n".join(current.pop("lines")).strip()
        question_text, solution_text = _split_learning_solution(raw_text)
        current["question_text"] = question_text
        boundary = _learning_solution_boundary(raw_text)
        question_source = raw_text if boundary is None else raw_text[:boundary]
        current["image_refs"] = _image_refs(
            question_source,
            Path(pages[0].get("source_path", ".")).parent,
        )
        current["visual_status"] = "READY_TEXT_ONLY" if not current["image_refs"] else "NEEDS_VISION_SIDECAR"
        if current["kind"] == "example":
            current["teaching_text"] = raw_text
            current["solution_present"] = bool(solution_text)
        else:
            current["solution_isolated"] = True
        items.append(current)
        current = None

    for page in pages:
        doc = page.get("ocr_doc")
        source_lines = [
            fragment
            for raw_line in page.get("text", "").splitlines()
            for fragment in INLINE_LEARNING_ITEM_RE.split(raw_line)
            if fragment
        ]
        for line in source_lines:
            match = LEARNING_ITEM_RE.match(line)
            if match:
                finish()
                kind = "example" if match.group("kind") == "例" else "direct_variant"
                label = match.group("label").strip()
                number = _example_number(label) if kind == "example" else None
                if number is not None:
                    current_example = number
                role_number = number if kind == "example" else current_example
                role, role_ref = _learning_role(section, role_number)
                current = {
                    "item_id": stable_id(section["id"], kind, doc, len(items), label),
                    "kind": kind,
                    "label": f"例{number}" if number is not None else (f"变式{label}" if label else "变式"),
                    "example_number": number,
                    "parent_example_number": current_example if kind == "direct_variant" else None,
                    "role": role if kind == "example" else "direct_variant",
                    "role_ref": role_ref,
                    "source_docs": [doc],
                    "lines": [line],
                }
                continue
            if current and LEARNING_STRUCTURE_RE.match(line):
                finish()
            if current:
                if doc not in current["source_docs"]:
                    current["source_docs"].append(doc)
                current["lines"].append(line)
    finish()

    _repair_learning_item_layout(section["id"], items, pages)
    _apply_clean_learner_question_stems(section["id"], items, clean_stems or [])

    deduplicated: list[dict[str, Any]] = []
    unique: dict[tuple[str, int | None, str], dict[str, Any]] = {}
    for item in items:
        canonical = (
            re.sub(r"\s+", "", str(item.get("question_text", "")))
            .replace("。", ".")
            .rstrip(".")
        )
        parent = item.get("example_number") if item.get("kind") == "example" else item.get("parent_example_number")
        key = (str(item.get("kind")), parent, canonical)
        previous = unique.get(key)
        if not canonical or previous is None:
            unique[key] = item
            continue
        selected = item if len(str(item.get("teaching_text") or item.get("question_text") or "")) > len(
            str(previous.get("teaching_text") or previous.get("question_text") or "")
        ) else previous
        other = previous if selected is item else item
        selected["source_docs"] = sorted(
            set([*selected.get("source_docs", []), *other.get("source_docs", [])])
        )
        refs: dict[str, dict[str, Any]] = {}
        for ref in [*selected.get("image_refs", []), *other.get("image_refs", [])]:
            ref_key = str(ref.get("path") or ref.get("ref") or "")
            if ref_key:
                refs[ref_key] = ref
        selected["image_refs"] = list(refs.values())
        unique[key] = selected
        deduplicated.append(
            {
                "kind": item.get("kind"),
                "parent_example_number": parent,
                "kept_item_id": selected.get("item_id"),
                "removed_item_id": other.get("item_id"),
                "source_docs": selected.get("source_docs", []),
                "reason": "same_parent_and_normalized_question_text",
            }
        )
    items = list(unique.values())

    examples = [item for item in items if item["kind"] == "example"]
    variants = [item for item in items if item["kind"] == "direct_variant"]
    return {
        "worked_examples": examples,
        "direct_variants": variants,
        "counts": {"worked_examples": len(examples), "direct_variants": len(variants)},
        "deduplicated_items": deduplicated,
    }


def _materialize_learning_cycles(
    section: dict[str, Any],
    learning_items: dict[str, Any],
    exercise_questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Bind the explicit course/method cycle plan to current packet items."""
    specs = section.get("learning_cycles") or []
    if not specs:
        return []

    examples = {item.get("example_number"): item for item in learning_items["worked_examples"]}
    variants_by_parent: dict[int, list[dict[str, Any]]] = {}
    for item in learning_items["direct_variants"]:
        variants_by_parent.setdefault(item.get("parent_example_number"), []).append(item)
    exercises = {f"{item.get('group')}{item.get('number')}": item for item in exercise_questions}
    known_course_keys = set(section.get("required_course_keys", [])) | set(section.get("support_course_keys", []))
    known_knowledge_refs = {item.get("id") for item in section.get("knowledge_points", [])}

    seen_examples: set[int] = set()
    seen_variants: set[str] = set()
    seen_exercises: set[str] = set()
    cycles: list[dict[str, Any]] = []
    for index, spec in enumerate(specs, start=1):
        course_keys = list(spec.get("course_keys", []))
        prerequisite_course_keys = list(spec.get("prerequisite_course_keys", []))
        optional_course_keys = list(spec.get("optional_course_keys", []))
        unknown_courses = (
            set(course_keys) | set(prerequisite_course_keys) | set(optional_course_keys)
        ) - known_course_keys
        if unknown_courses:
            raise PacketError(f"{section['id']} learning cycle has unknown course keys: {sorted(unknown_courses)}")
        knowledge_refs = list(spec.get("knowledge_refs", []))
        prerequisite_knowledge_refs = list(spec.get("prerequisite_knowledge_refs", []))
        unknown_knowledge = (set(knowledge_refs) | set(prerequisite_knowledge_refs)) - known_knowledge_refs
        if unknown_knowledge:
            raise PacketError(f"{section['id']} learning cycle has unknown knowledge refs: {sorted(unknown_knowledge)}")

        method_checkpoints = list(spec.get("method_checkpoints", []))
        for checkpoint in method_checkpoints:
            if not checkpoint.get("id") or not str(checkpoint.get("question_text", "")).strip():
                raise PacketError(f"{section['id']} learning cycle has malformed method checkpoint")
            if re.search(r"答案\s*[：:]|解析\s*[：:]|解答\s*[：:]", str(checkpoint.get("question_text", ""))):
                raise PacketError(f"{section['id']} method checkpoint leaks an answer")

        example_numbers = list(spec.get("example_numbers", []))
        cycle_examples = []
        cycle_variants = []
        for number in example_numbers:
            if number in seen_examples:
                raise PacketError(f"{section['id']} example {number} appears in multiple learning cycles")
            if number not in examples:
                raise PacketError(f"{section['id']} learning cycle references missing example {number}")
            seen_examples.add(number)
            cycle_examples.append(examples[number])
            for variant in variants_by_parent.get(number, []):
                item_id = str(variant.get("item_id"))
                if item_id in seen_variants:
                    raise PacketError(f"{section['id']} variant {item_id} appears in multiple learning cycles")
                seen_variants.add(item_id)
                cycle_variants.append(variant)

        exercise_keys = list(spec.get("exercise_keys", []))
        cycle_exercises = []
        for key in exercise_keys:
            if key in seen_exercises:
                raise PacketError(f"{section['id']} exercise {key} appears in multiple learning cycles")
            if key not in exercises:
                raise PacketError(f"{section['id']} learning cycle references missing exercise {key}")
            seen_exercises.add(key)
            cycle_exercises.append(exercises[key])

        action_order = ["watch_current_courses"] if course_keys else []
        if cycle_examples:
            action_order.append("learn_each_current_example_then_attempt_its_direct_variants")
        if method_checkpoints:
            action_order.append("attempt_current_method_checkpoints_without_answers")
        if cycle_exercises:
            action_order.append("attempt_current_abc_exercises_without_answers")
        action_order.append("assess_current_cycle")

        cycles.append({
            "cycle_id": spec.get("id") or f"{section['id']}-cycle-{index}",
            "sequence": index,
            "title": spec.get("title") or f"方法循环 {index}",
            "course_keys": course_keys,
            "prerequisite_course_keys": prerequisite_course_keys,
            "optional_course_keys": optional_course_keys,
            "knowledge_refs": knowledge_refs,
            "prerequisite_knowledge_refs": prerequisite_knowledge_refs,
            "type_refs": list(spec.get("type_refs", [])),
            "bridge_unit_ids": list(spec.get("bridge_unit_ids", [])),
            "method_checkpoints": method_checkpoints,
            "worked_examples": cycle_examples,
            "direct_variants": cycle_variants,
            "exercise_questions": cycle_exercises,
            "action_order": action_order,
            "advance_gate": "本批例题理解、直属变式、对应习题和独立复测证据齐全后才可进入下一批；提示或看答案的题必须以未见题或延迟闭卷复测补证。",
            "failure_rule": "只报告第一处断点并给最小提示；不得提前展示下一批或当前题答案。",
        })

    expected_examples = set(examples)
    expected_variants = {str(item.get("item_id")) for item in learning_items["direct_variants"]}
    expected_exercises = set(exercises)
    if seen_examples != expected_examples:
        raise PacketError(f"{section['id']} learning cycles do not cover examples exactly: missing={sorted(expected_examples - seen_examples)}")
    if seen_variants != expected_variants:
        raise PacketError(f"{section['id']} learning cycles do not cover variants exactly: missing={sorted(expected_variants - seen_variants)}")
    if seen_exercises != expected_exercises:
        raise PacketError(f"{section['id']} learning cycles do not cover exercises exactly: missing={sorted(expected_exercises - seen_exercises)}")
    return cycles


def _learning_item_vision_hint(section_id: str, item: dict[str, Any]) -> str:
    """Return a stable sidecar key without exposing an answer-bearing label."""
    item_id = str(item.get("item_id") or "")
    if not item_id:
        raise PacketError(f"{section_id} learning item is missing item_id")
    return f"{section_id}-LI{item_id}"


def _student_vision_structured(value: Any) -> dict[str, Any] | None:
    """Project only answer-free visual facts into the student item packet."""
    if not isinstance(value, dict):
        return None
    structured = value.get("structured") if isinstance(value.get("structured"), dict) else value
    return {
        key: deepcopy(structured[key])
        for key in ("objects", "relations", "coordinates", "ranges", "text", "uncertainties", "confidence")
        if key in structured
    }


def _student_learning_item(item: dict[str, Any]) -> dict[str, Any]:
    """Build an answer-free view of one worked example or direct variant.

    The teaching text and solution flags intentionally never cross this
    boundary.  Visual sidecars are reduced to structured geometry facts and
    their confidence; source provenance and any accidental answer-bearing
    metadata stay in the lesson/diagnostic artifacts.
    """
    projected: dict[str, Any] = {}
    for key in (
        "item_id",
        "kind",
        "label",
        "example_number",
        "parent_example_number",
        "role",
        "role_ref",
        "source_docs",
        "vision_hint",
    ):
        if key in item:
            projected[key] = deepcopy(item[key])
    projected["question_text"] = _redact_student_text(str(item.get("question_text", ""))).strip()
    projected["image_refs"] = [
        {
            key: deepcopy(ref[key])
            for key in ("ref", "path", "exists")
            if key in ref
        }
        for ref in item.get("image_refs", [])
        if isinstance(ref, dict)
    ]
    projected["visual_status"] = item.get("visual_status")
    sidecars = []
    for sidecar in item.get("vision_sidecars", []) or []:
        if not isinstance(sidecar, dict):
            continue
        structured = _student_vision_structured(sidecar)
        if structured is None:
            continue
        sidecars.append({
            "image_sha256": sidecar.get("image_sha256"),
            "confidence": sidecar.get("confidence"),
            "structured": structured,
        })
    if sidecars:
        projected["vision_sidecars"] = sidecars
    structured = _student_vision_structured(item.get("vision_sidecar"))
    if structured is not None:
        projected["vision_sidecar"] = structured
    projected["evidence"] = deepcopy(item.get("evidence", []))
    return projected


def _student_learning_item_packet(
    section: dict[str, Any],
    packet: dict[str, Any],
    learning_items: dict[str, Any],
) -> dict[str, Any]:
    """Persist the answer-free example/variant input used by DeepSeek."""
    worked_examples = [_student_learning_item(item) for item in learning_items["worked_examples"]]
    direct_variants = [_student_learning_item(item) for item in learning_items["direct_variants"]]
    return {
        "schema_version": "7.1",
        "packet_type": "DEEPSEEK_STUDENT_LEARNING_ITEMS",
        "section": section["id"],
        "status": packet["status"],
        "source": packet["source"],
        "consumer_guard": "Student/DeepSeek input only; teaching text, solutions and answer sidecars are excluded.",
        "worked_examples": worked_examples,
        "direct_variants": direct_variants,
        "counts": {
            "worked_examples": len(worked_examples),
            "direct_variants": len(direct_variants),
            "total": len(worked_examples) + len(direct_variants),
        },
        "answer_policy": {
            "worked_examples": "question only; complete teaching remains in learning_packet.json",
            "direct_variants": "question only; solution isolated in answer-free build boundary",
        },
    }


def _extract_instruction_pages(pages: list[dict[str, Any]], section_id: str = "") -> list[dict[str, Any]]:
    """Reuse answer-checked redaction for the instruction prefix only.

    A source page may contain the end of the method book and the beginning of
    A/B/C exercises.  Preserve the instruction prefix instead of discarding
    that whole page when an exercise heading is present.
    """
    instruction_pages: list[dict[str, Any]] = []
    end_re = re.compile(r"(?im)^\s*(?:#{1,6}\s*)?(?:强化训练|[ABC]\s*组(?:\s|$))")
    for page in pages:
        raw_text = str(page.get("text", ""))
        match = end_re.search(raw_text)
        prefix = raw_text[: match.start()] if match else raw_text
        if prefix.strip():
            instruction_pages.append({**page, "text": prefix})
        if match:
            break

    safe_pages = _student_lesson_free_pages(instruction_pages)
    result: list[dict[str, Any]] = []
    for safe in safe_pages:
        safe_text = str(safe.get("text", "")).strip()
        if section_id == "1.1" and safe.get("ocr_doc") == 1:
            safe_text = re.sub(r"(?ms)^法则，.*?^所以\s+.*?\。\s*$", "", safe_text, count=1).strip()
            safe_text = safe_text.replace(r"\n \(u+v=AD+BC=AC\)", "")
        elif section_id == "1.1" and safe.get("ocr_doc") == 2:
            table_end = safe_text.rfind("</table>")
            if table_end >= 0:
                safe_text = safe_text[: table_end + len("</table>")].strip()
            safe_text += (
                "\n\n" + r"推论补全：若 \(O,A,B\) 不共线，且 "
                r"\(\overrightarrow{OP}=x\overrightarrow{OA}+y\overrightarrow{OB}\)，"
                r"则 \(A,P,B\) 共线当且仅当 \(x+y=1\)。若 \(O,A,B,C\) 不共面，且 "
                r"\(\overrightarrow{OP}=x\overrightarrow{OA}+y\overrightarrow{OB}+z\overrightarrow{OC}\)，"
                r"则 \(P,A,B,C\) 共面当且仅当 \(x+y+z=1\)。"
            )
        elif section_id == "1.1" and safe.get("ocr_doc") == 3:
            safe_text = re.sub(
                r"(?ms)^分析一下理由，.*?(?=^\s*##\s*知识点4\s*$)",
                "",
                safe_text,
                count=1,
            ).strip()
            safe_text = safe_text.replace(
                r"\(a \cdot b = b \cdot c \neq a = c\)",
                r"\(a \cdot b=b \cdot c\) 不能推出 \(a=c\)",
            )
            safe_text = re.sub(r"(?ms)^\s*##\s*类型\s*I\s*：.*\Z", "", safe_text).strip()
        elif section_id == "1.4" and safe.get("ocr_doc") == 34:
            safe_text = re.sub(r"(?ms)^则式①可改写为.*\Z", "", safe_text, count=1).strip()
        elif section_id == "1.4" and safe.get("ocr_doc") == 35:
            safe_text = re.sub(r"(?m)^\s*\\\(\\alpha \\parallel \\beta\\\)，则k=（\s*）\s*$", "", safe_text)
            safe_text = re.sub(r"\\\((?:\\alpha|\\beta) \\nparallel .*?\\\)", "", safe_text)
        if safe_text.startswith("（ocr_doc ") and "为方法册教学续页" in safe_text:
            continue
        if safe_text:
            result.append({
                "ocr_doc": safe.get("ocr_doc"),
                "text": safe_text,
                "image_refs": safe.get("image_refs", []),
                "math_errors": safe.get("math_errors", []),
            })
            if section_id == "1.1" and safe.get("ocr_doc") == 3:
                continuation = next((item for item in pages if item.get("ocr_doc") == 4), None)
                if continuation:
                    continuation_text = str(continuation.get("text", ""))
                    end = continuation_text.find("\n因为")
                    if end >= 0:
                        continuation_text = continuation_text[:end].strip()
                    if continuation_text:
                        result.append({
                            "ocr_doc": 4,
                            "text": continuation_text,
                            "image_refs": continuation.get("image_refs", []),
                            "math_errors": continuation.get("math_errors", []),
                        })
    return result


def _extract_knowledge_blocks(instruction_pages: list[dict[str, Any]], section: dict[str, Any]) -> list[dict[str, Any]]:
    """Split the answer-free left-column knowledge notes into named blocks."""
    points = section.get("knowledge_points", [])
    if not points:
        return []
    corpus = "\n\n".join(str(page.get("text", "")) for page in instruction_pages)
    corpus = re.sub(
        r"(?m)(?<!^)(知识点\s*\d+\s*[：:])",
        r"\n## \1",
        corpus,
    )
    heading_re = re.compile(r"(?im)^(?:##\s*)?知识点\s*(\d+)\s*[:：][^\n]*$")
    matches = list(heading_re.finditer(corpus))
    if len(matches) < len(points):
        fallback_re = re.compile(r"(?im)^##\s*知识点\s*\d+\s*$")
        fallback_matches = list(fallback_re.finditer(corpus))
        if len(fallback_matches) >= len(points):
            matches = fallback_matches
    if len(matches) < len(points):
        raise PacketError(f"{section['id']} has {len(points)} knowledge points but only {len(matches)} left-column blocks")
    blocks: list[dict[str, Any]] = []
    for match_index, point in enumerate(points):
        match = matches[match_index]
        end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(corpus)
        text = corpus[match.start():end]
        text = re.sub(r"(?im)^##\s*知识点\s*\d+\s*$", "", text).strip()
        blocks.append({
            "id": point["id"],
            "label": point.get("label", point["id"]),
            "example_labels": list(point.get("examples", [])),
            "text": text,
            "answer_free": True,
        })
    return blocks


def _derived_formula_corrections(section_id: str, page: dict[str, Any]) -> list[dict[str, str]]:
    """Return only source-anchored, visually confirmed corrections.

    Original OCR remains untouched on disk. The correction is an explicit derived
    layer so a worker never consumes a known-wrong formula silently.
    """
    if section_id == "ch3.s1" and page.get("ocr_doc") == 0:
        return [{
            "from": r"（即\)|F_1F_2|$）",
            "to": r"（即\(|F_1F_2|\)）",
            "reason": "source doc_0 line 11 closes the focal-distance absolute value; Paddle delimiter drift moved the dollar marker",
        }]
    if section_id == "4.4" and page.get("ocr_doc") == 53:
        return [{
            "from": r"②下标和性质：若  \(m+n=p+q\)， \((m,n,p,q \in \mathbb{N}^*\) \(，则\) a_m a_n = a_p a_q $；",
            "to": r"②下标和性质：若 \(m+n=p+q\)，\((m,n,p,q \in \mathbb{N}^*\)），则 \(a_m a_n = a_p a_q\)；",
            "reason": "source doc_53 line 7 has one parenthesized index condition and one formula; Paddle emitted an extra dollar marker",
        }]
    if section_id == "4.5" and page.get("ocr_doc") == 73:
        return [{
            "from": r"\(\{a_{n+1}\)}$",
            "to": r"\(\{a_{n+1}\}\)",
            "reason": "source doc_73 line 35 closes the sequence braces before the inline-math delimiter",
        }]
    if section_id == "5.5" and page.get("ocr_doc") == 67:
        return [{
            "from": r"=2(x_{1}-x_{2})-a\ln\frac{x_{1}}{x_{2}}=\left(2-\frac{a}{x_{1}-x_{2}}\ln\frac{x_{1}}{x_{2}}\right)(x_{1}-x_{2}), 所以\frac{f(x_{1})-f(x_{2})}{x_{1}-x_{2}}=2-\frac{a}{x_{1}-x_{2}}\ln\frac{x_{1}}{x_{2}} $，",
            "to": r"\(=2(x_{1}-x_{2})-a\ln\frac{x_{1}}{x_{2}}=\left(2-\frac{a}{x_{1}-x_{2}}\ln\frac{x_{1}}{x_{2}}\right)(x_{1}-x_{2})\)，所以 \(\frac{f(x_{1})-f(x_{2})}{x_{1}-x_{2}}=2-\frac{a}{x_{1}-x_{2}}\ln\frac{x_{1}}{x_{2}}\)，",
            "reason": "source doc_67 starts with the continuation of a displayed derivation; bind its two formulas separately around the Chinese connector",
        }]
    if section_id == "5.6" and page.get("ocr_doc") == 80:
        return [{
            "from": r"\frac{x^2 + 1}{x^2}",
            "to": r"\frac{x^2 + 1}{\mathrm{e}^x}",
            "reason": "source merged PDF page 81 shows the same quotient by e^x before and after the monotonicity argument",
        }]
    if section_id == "micro专题1" and page.get("ocr_doc") == 57:
        return [{
            "from": r"\sqrt{1 - \left( \frac{4}{\pi} \right)^2} = \frac{3}{\pi}",
            "to": r"\sqrt{1 - \left( \frac{4}{5} \right)^2} = \frac{3}{5}",
            "reason": "layout_det_res_57.jpg visual review E1; same page establishes sin(theta)=4/5",
        }]
    if section_id == "micro专题1" and page.get("ocr_doc") == 65:
        return [{
            "from": "设直线 EM 与平面 PBD 交于 O",
            "to": "设直线 AM 与平面 PBD 交于 O",
            "reason": "primary figure img_in_image_box_904_1063_1093_1270.jpg shows A, O, M collinear and no point E",
        }]
    if section_id == "1.1" and page.get("ocr_doc") == 12:
        return [{
            "from": "新疆巴音郭楞斯坦",
            "to": "新疆巴音郭楞期末",
            "reason": "primary page visual review E1; OCR fused the location and exam-type text",
        }]
    if section_id == "1.1" and page.get("ocr_doc") == 16:
        return [{
            "from": r"\(\overrightarrow{OA}\)" + "\n\n " + r"\(a - 2b + c\)",
            "to": r"\(\overrightarrow{OA} = a - 2b + c\)",
            "reason": "layout_det_res_16.jpg visual review E1 shows the equals sign in Q13",
        }]
    if section_id == "1.2+1.3" and page.get("ocr_doc") == 24:
        return [{
            "from": "【变式 1】",
            "to": "【变式1】",
            "reason": "layout_det_res_24.jpg visual review E1; replace the detector-garbled givens with a direct transcription",
        }]
    if section_id == "1.2+1.3" and page.get("ocr_doc") == 29:
        return [{
            "from": "如图，在三棱锥",
            "to": "5.（2025·广东清远期末）\n\n如图，在三棱锥",
            "reason": "source section PDF page 12 visual review E1; restore B5 provenance and remove the running footer",
        }]
    if section_id == "1.2+1.3" and page.get("ocr_doc") == 30:
        return [{
            "from": "如图，M 是三棱锥",
            "to": "9.（2025·安徽阜阳期末）\n\n如图，M 是三棱锥",
            "reason": "source section PDF page 13 visual review E1; restore B9 and B11 printed provenance",
        }]
    if section_id == "1.1" and page.get("ocr_doc") == 1:
        return [{
            "from": r"\)}}=\frac{1}{8}",
            "to": r"=\frac{1}{8}",
            "reason": "doc_1 OCR delimiter repair; visual formula closes after the midpoint expression",
        }]
    if section_id == "1.4" and page.get("ocr_doc") == 40:
        return [{
            "from": "由图可知，",
            "to": "由图可知，",
            "reason": "doc_40 visual review anchor; the OCR expansion below is replaced by a transcribed dot-product derivation",
        }]
    if section_id == "1.4" and page.get("ocr_doc") == 34:
        return [{
            "from": "，若",
            "to": "，若",
            "reason": "source PDF pages 35-36 visual review E1; example 4 continues in the right column of the next printed page",
        }]
    if section_id == "1.4" and page.get("ocr_doc") == 35:
        return [{
            "from": r"\( \alpha \parallel \beta \)，则k=（ ）",
            "to": "",
            "reason": "source PDF page 36 visual review E1; remove example 4 right-column fragments after restoring them to doc 34",
        }]
    if section_id == "1.4" and page.get("ocr_doc") == 50:
        return [{
            "from": "中，AB=",
            "to": "中，AB=",
            "reason": "source PDF page 51 visual review E1; rejoin the B5 equality split across OCR lines",
        }]
    if section_id == "1.4" and page.get("ocr_doc") == 51:
        return [{
            "from": "（2024·安徽合肥二模）数·高中数学一本通",
            "to": "（2024·安徽合肥二模）",
            "reason": "source PDF page 52 visual review E1; remove the running header fused into B7",
        }]
    if section_id == "micro专题1" and page.get("ocr_doc") == 67:
        return [{
            "from": "（2025·陕西模拟）数·高中数学一本通",
            "to": "（2025·陕西模拟）",
            "reason": "source PDF page 68 visual review E1; remove running header and bind the C7 figure branch",
        }]
    return []


def _apply_derived_formula_corrections(section_id: str, page: dict[str, Any]) -> dict[str, Any]:
    corrections = _derived_formula_corrections(section_id, page)
    if not corrections:
        return page
    updated = dict(page)
    text = updated.get("text", "")
    applied: list[dict[str, str]] = []
    for correction in corrections:
        if section_id == "1.2+1.3" and page.get("ocr_doc") == 24:
            start = text.find("【变式 1】")
            end = text.find("（1）证明", start) if start >= 0 else -1
            if start >= 0 and end > start:
                replacement = (
                    r"【变式1】如图，三棱柱 \(ABC-A_1B_1C_1\) 中，"
                    r"\(CC_1\perp\)平面 \(ABC\)，\(AC\perp BC\)，"
                    r"\(AC=BC=2\)，\(CC_1=3\)。点 \(D\)，\(E\) 分别在棱 "
                    r"\(AA_1\) 和 \(CC_1\) 上，\(AD=1\)，\(CE=2\)，"
                    r"\(M\) 为棱 \(A_1B_1\) 的中点。" + "\n\n"
                )
                text = text[:start] + replacement + text[end:]
                applied.append(correction)
        elif section_id == "1.2+1.3" and page.get("ocr_doc") == 29:
            original = text
            text = text.replace("如图，在三棱锥", "5.（2025·广东清远期末）\n\n如图，在三棱锥", 1)
            text = re.sub(r"(?m)^\s*一数·高中数学一本通\s*$", "", text)
            if text != original:
                applied.append(correction)
        elif section_id == "1.2+1.3" and page.get("ocr_doc") == 30:
            original = text
            text = text.replace("如图，\\(M\\) 是三棱锥", "9.（2025·安徽阜阳期末）\n\n如图，\\(M\\) 是三棱锥", 1)
            text = text.replace("三棱锥 A-BCD 中", "11.（2025·河北廊坊期末）\n\n三棱锥 A-BCD 中", 1)
            if text != original:
                applied.append(correction)
        elif section_id == "1.4" and page.get("ocr_doc") == 40:
            marker = "由图可知，"
            start = text.find(marker)
            end = text.find("从而", start + len(marker)) if start >= 0 else -1
            if start >= 0 and end > start:
                replacement = (
                    "由图可知，\\(\\overrightarrow{CA_1}=\\overrightarrow{CB}+\\overrightarrow{CD}+\\overrightarrow{CC_1}\\)，"
                    "\\(\\overrightarrow{BC_1}=\\overrightarrow{CC_1}-\\overrightarrow{CB}\\)，"
                    "\\(\\overrightarrow{BD}=\\overrightarrow{CD}-\\overrightarrow{CB}\\)。"
                    "因此\\(\\overrightarrow{CA_1}\\cdot\\overrightarrow{BC_1}"
                    "=(\\overrightarrow{CB}+\\overrightarrow{CD}+\\overrightarrow{CC_1})"
                    "\\cdot(\\overrightarrow{CC_1}-\\overrightarrow{CB})"
                    "=|\\overrightarrow{CC_1}|^2-|\\overrightarrow{CB}|^2"
                    "+\\overrightarrow{CD}\\cdot\\overrightarrow{CC_1}"
                    "-\\overrightarrow{CD}\\cdot\\overrightarrow{CB}"
                    "=2^2-2^2+2\\times2\\times\\cos60^\\circ"
                    "-2\\times2\\times\\cos60^\\circ=0\\)；"
                    "\\(\\overrightarrow{CA_1}\\cdot\\overrightarrow{BD}"
                    "=(\\overrightarrow{CB}+\\overrightarrow{CD}+\\overrightarrow{CC_1})"
                    "\\cdot(\\overrightarrow{CD}-\\overrightarrow{CB})"
                    "=|\\overrightarrow{CD}|^2-|\\overrightarrow{CB}|^2"
                    "+\\overrightarrow{CC_1}\\cdot\\overrightarrow{CD}"
                    "-\\overrightarrow{CC_1}\\cdot\\overrightarrow{CB}"
                    "=2^2-2^2+2\\times2\\times\\cos60^\\circ"
                    "-2\\times2\\times\\cos60^\\circ=0\\)。"
                )
                text = text[:start] + replacement + text[end:]
                applied.append(correction)
        elif section_id == "1.4" and page.get("ocr_doc") == 34:
            suffix = "，若"
            if text.rstrip().endswith(suffix):
                continuation = (
                    r" \(\alpha\parallel\beta\)，则 \(k=\)（ ）" + "\n\n"
                    "A. 4  B. -4\n\nC. 10  D. -10\n\n"
                    r"解析：因为 \(\alpha\parallel\beta\)，所以 \(m\parallel n\)，"
                    r"故 \(\frac{1}{-2}=\frac{2}{k}=\frac{-3}{6}\)，解得：\(k=-4\)。" + "\n\n"
                    "答案：B"
                )
                text = text.rstrip()[:-len(suffix)] + "，若" + continuation
                applied.append(correction)
        elif section_id == "1.4" and page.get("ocr_doc") == 35:
            original = text
            orphan_lines = (
                r"(?m)^\s*\$\s*\\alpha\s*\\parallel\s*\\beta\s*\$，则k=（\s*）\s*$",
                r"(?m)^\s*A\.\s*4\s+B\.\s*-4\s*$",
                r"(?m)^\s*C\.\s*10\s+D\.\s*-10\s*$",
                r"(?m)^\s*解析：因为\s*\$\s*\\alpha\s*\\parallel\s*\\beta\s*\$，所以\s*\$\s*m\s*\\parallel\s*n\s*\$，\s*$",
                r"(?m)^\s*故\s*\$\s*\\frac\{1\}\{-2\}\s*=\s*\\frac\{2\}\{k\}\s*=\s*\\frac\{-3\}\{6\}\s*\$，解得：k\s*=\s*-4。\s*$",
                r"(?m)^\s*答案：B\s*$",
            )
            for pattern in orphan_lines:
                text = re.sub(pattern, "", text)
            if text != original:
                applied.append(correction)
        elif section_id == "1.4" and page.get("ocr_doc") == 50:
            original = text
            text = re.sub(
                r"中，AB=\s*\\\[AD=AA_\{1\}=1，\\angle",
                lambda _: r"中，\(AB=AD=AA_{1}=1，\angle",
                text,
                count=1,
            )
            text = text.replace(r"60^{\circ}．\]", r"60^{\circ}\)．")
            if text != original:
                applied.append(correction)
        elif correction["from"] in text:
            text = text.replace(correction["from"], correction["to"])
            applied.append(correction)
    if section_id == "1.1" and page.get("ocr_doc") == 1 and applied:
        text = text.replace(r"-\overrightarrow{AD}$。", r"-\overrightarrow{AD}\)。")
    if applied:
        updated["text"] = text
        updated["math_errors"] = delimiter_errors(text)
        updated["derived_corrections"] = applied
    return updated


def _apply_derived_question_corrections(
    section_id: str,
    page: dict[str, Any],
    corrections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply source-verified question-line fixes without changing raw OCR files."""
    relevant = [
        item
        for item in corrections
        if item.get("section") == section_id and item.get("source_doc") == page.get("ocr_doc")
    ]
    if not relevant:
        return page

    updated = deepcopy(page)
    lines = str(updated.get("text", "")).splitlines()
    applied: list[dict[str, Any]] = []
    for correction in relevant:
        match_text = str(correction.get("match_text", "")).strip()
        match_prefix = str(correction.get("match_prefix", "")).strip()
        action = correction.get("action")
        expected_matches = int(correction.get("expected_matches", 1))
        if bool(match_text) == bool(match_prefix) or action not in {"replace_line", "remove_line"}:
            raise PacketError(f"{section_id} has malformed derived question correction")
        indexes = [
            index
            for index, line in enumerate(lines)
            if (
                line.strip() == match_text
                if match_text
                else line.strip().startswith(match_prefix)
            )
        ]
        if len(indexes) != expected_matches:
            raise PacketError(
                f"{section_id} doc_{page.get('ocr_doc')} correction match count "
                f"{len(indexes)} != {expected_matches}: {correction.get('id')}"
            )
        if action == "replace_line":
            replacement = str(correction.get("replacement", "")).strip()
            if not replacement:
                raise PacketError(f"{section_id} correction replacement is empty: {correction.get('id')}")
            for index in indexes:
                lines[index] = replacement
        else:
            for index in reversed(indexes):
                del lines[index]
        applied.append(
            {
                "id": correction.get("id"),
                "action": action,
                "evidence": correction.get("evidence"),
                "reason": correction.get("reason"),
            }
        )

    text = "\n".join(lines)
    updated["text"] = text
    updated["math_errors"] = delimiter_errors(text)
    updated["derived_question_corrections"] = applied
    return updated


def _question_spans(text: str) -> list[re.Match[str]]:
    return list(QUESTION_RE.finditer(text))


def _group_at(text: str, offset: int, current: str | None) -> str | None:
    for match in GROUP_RE.finditer(text[:offset]):
        current = match.group("group").upper()
    return current


def _image_refs(text: str, root: Path) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for match in IMAGE_RE.findall(text):
        raw = next((x for x in match if x), "")
        relative = raw.split("#", 1)[0]
        path = (root / relative).resolve()
        refs.append({"ref": raw, "path": str(path), "exists": path.exists()})
    return refs


def _expected_numbers(group_ranges: dict[str, list[int]]) -> set[tuple[str, int]]:
    return {(group, n) for group, bounds in group_ranges.items() for n in range(bounds[0], bounds[1] + 1)}


class PacketBuilder:
    def __init__(self, *, ocr_root: str | Path, output_root: str | Path):
        self.ocr_root = Path(ocr_root)
        self.output_root = Path(output_root)

    def _recovery_question(self, section: dict[str, Any], group: str, number: int, recovery: dict[str, Any], answer_root: str | Path | None) -> dict[str, Any] | None:
        """Recover an OCR-missing question only from an explicitly anchored source.

        The recovery is fail-closed: a manifest entry must name the source kind and
        document. It never guesses a question from an arbitrary neighboring page.
        """
        source_kind = recovery.get("source_kind")
        source_doc = recovery.get("source_doc")
        if source_kind == "primary_ocr":
            source_root = self.ocr_root
        else:
            # Answer OCR is an answer-book source.  It may populate the
            # isolated answer sidecar, but it is never allowed to recover a
            # student question or its figure.
            return None
        if not isinstance(source_doc, int):
            return None
        source = source_root / f"doc_{source_doc}.md"
        if not source.exists():
            return None
        # Match against raw OCR so manifest anchors may refer to the source's
        # literal `$...$` form; normalize only the recovered payload afterward.
        text = clean_text(source.read_text(encoding="utf-8", errors="replace"))
        start_re = recovery.get("start_regex")
        end_re = recovery.get("end_regex")
        if not start_re:
            return None
        start_match = next((m for m in re.finditer(start_re, text, flags=re.M)), None)
        if not start_match:
            return None
        end_match = re.search(end_re, text[start_match.end():], flags=re.M) if end_re else None
        end = start_match.end() + end_match.start() if end_match else len(text)
        recovered_text = normalize_math(text[start_match.start():end].strip())
        if not recovered_text or len(recovered_text) < 20:
            return None
        images = _image_refs(recovered_text, source.parent)
        return {
            "qid": "Q-" + stable_id(str(source_root), source_doc, section["id"], group, number),
            "section": section["id"], "group": group, "number": number, "kind": f"{group}组",
            "source_anchor": {
                "ocr_doc": source_doc,
                "pdf_page": recovery.get("pdf_page"),
                "file": str(source),
                "recovery": recovery.get("evidence"),
                "recovery_source_kind": source_kind,
            },
            "question_text": recovered_text, "answer_text": "", "answer_isolated": True,
            "image_refs": images, "visual_status": "NEEDS_VISION_SIDECAR" if images else "READY_TEXT_ONLY",
            "math_errors": delimiter_errors(recovered_text), "evidence": ["E1", recovery.get("evidence", "explicit_recovery")],
            "recovery_reason": recovery.get("reason"),
        }

    def _read_page(self, number: int) -> tuple[Path, str]:
        path = self.ocr_root / f"doc_{number}.md"
        if not path.exists():
            raise PacketError(f"missing OCR page: {path}")
        return path, clean_text(path.read_text(encoding="utf-8", errors="replace"))

    @staticmethod
    def _attach_visual_sidecar(item: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """Attach one usable, identity-bound result for every figure.

        A question can contain more than one image.  A single matching result
        must never make that question consumable because the text-only worker
        would then silently miss the remaining figure.
        """
        images = item.get("image_refs", [])
        if not images:
            return item
        matched: list[dict[str, Any]] = []
        used: set[int] = set()
        for image in images:
            found_index = next(
                (
                    index
                    for index, candidate in enumerate(candidates)
                    if index not in used
                    and _usable_vision_sidecar(candidate)
                    and PacketBuilder._sidecar_matches_question(candidate, [image])
                ),
                None,
            )
            if found_index is None:
                return item
            used.add(found_index)
            matched.append(candidates[found_index])

        if len(matched) == len(images):
            item["visual_status"] = "VISION_VERIFIED"
            item["vision_sidecars"] = [
                {
                    "image": sidecar.get("image"),
                    "image_sha256": sidecar.get("image_sha256"),
                    "confidence": sidecar.get("confidence"),
                    "structured": sidecar.get("structured") or sidecar.get("vision") or {},
                    "source_provenance": sidecar.get("source_provenance"),
                }
                for sidecar in matched
            ]
            # Keep the original field for older consumers; the complete list
            # above is the authoritative payload for multi-image questions.
            item["vision_sidecar"] = item["vision_sidecars"][0]["structured"]
            item["vision_source_provenance"] = [
                sidecar.get("source_provenance") for sidecar in matched if sidecar.get("source_provenance")
            ]
            weakest = "E1" if any(sidecar.get("confidence") == "E1" for sidecar in matched) else "E2"
            item["evidence"] = ["E1", weakest]
        return item

    @staticmethod
    def _apply_image_attachment_overrides(
        section_id: str,
        items: list[dict[str, Any]],
        overrides: list[dict[str, Any]],
        target_kinds: set[str],
    ) -> None:
        by_id = {
            str(item.get("item_id") or item.get("qid") or ""): item
            for item in items
        }
        for override in overrides:
            if str(override.get("section") or "") != section_id:
                continue
            if str(override.get("kind") or "") not in target_kinds:
                continue
            item_id = str(override.get("item_id") or "")
            item = by_id.get(item_id)
            if item is None:
                raise PacketError(f"{section_id} image attachment override item missing: {item_id}")
            drop = override.get("drop") or {}
            drop_ref = str(drop.get("ref") or "")
            drop_hash = str(drop.get("image_sha256") or "")
            refs = list(item.get("image_refs", []))
            matches = [ref for ref in refs if str(ref.get("ref") or "") == drop_ref]
            if len(matches) != 1:
                raise PacketError(f"{section_id} image attachment drop match mismatch: {override.get('id')}")
            drop_path = Path(str(matches[0].get("path") or ""))
            if not drop_path.is_file() or _sha256_file(drop_path) != drop_hash:
                raise PacketError(f"{section_id} image attachment drop hash mismatch: {override.get('id')}")
            retained = [ref for ref in refs if ref is not matches[0]]
            retained_by_ref = {str(ref.get("ref") or ""): ref for ref in retained}
            for expected in override.get("keep", []):
                ref = retained_by_ref.get(str(expected.get("ref") or ""))
                path = Path(str((ref or {}).get("path") or ""))
                if ref is None or not path.is_file() or _sha256_file(path) != expected.get("image_sha256"):
                    raise PacketError(f"{section_id} image attachment keep binding mismatch: {override.get('id')}")
            item["image_refs"] = retained
            item["visual_status"] = "NEEDS_VISION_SIDECAR" if retained else "READY_TEXT_ONLY"
            for field in ("vision_sidecar", "vision_sidecars", "vision_source_provenance"):
                item.pop(field, None)
            item["evidence"] = [value for value in item.get("evidence", []) if value not in {"E1", "E2"}] or ["E1"]
            item.setdefault("source_repairs", []).append({
                "id": override.get("id"),
                "kind": "image_attachment",
                "reason": override.get("reason"),
                "review_ref": override.get("review_ref"),
            })

    def build_section(self, section: dict[str, Any], *, visual_sidecar: dict[str, Any] | None = None, answer_root: str | Path | None = None) -> dict[str, Any]:
        start, end = section["ocr_docs"]
        pages: list[dict[str, Any]] = []
        questions: list[dict[str, Any]] = []
        observed: set[tuple[str, int]] = set()
        source_rel = _portable_source_identity(self.ocr_root)
        current_group: str | None = None
        sidecar_by_hint: dict[str, list[dict[str, Any]]] = {}
        for entry in (visual_sidecar or {}).get("results", []):
            hint = entry.get("question_hint")
            if hint:
                sidecar_by_hint.setdefault(hint, []).append(entry)
        known_recoveries = [
            item for item in (visual_sidecar or {}).get("known_visual_recoveries", [])
            if item.get("section") == section["id"]
        ]
        question_corrections = [
            item for item in (visual_sidecar or {}).get("derived_question_corrections", [])
            if item.get("section") == section["id"]
        ]
        canonical_qids: dict[tuple[str, int], dict[str, Any]] = {}
        for correction in question_corrections:
            canonical_qid = str(correction.get("canonical_qid") or "")
            if not canonical_qid:
                continue
            group = str(correction.get("group") or "")
            number = correction.get("number")
            if not re.fullmatch(r"Q-[0-9a-f]{16}", canonical_qid) or not isinstance(number, int):
                raise PacketError(f"{section['id']} malformed canonical QID binding: {correction.get('id')}")
            key = (group, number)
            if key in canonical_qids and canonical_qids[key]["canonical_qid"] != canonical_qid:
                raise PacketError(f"{section['id']} conflicting canonical QID binding: {key}")
            canonical_qids[key] = correction
        for page_number in range(start, end + 1):
            path, raw = self._read_page(page_number)
            normalized = normalize_math(raw)
            page = {
                "ocr_doc": page_number,
                "source_path": str(path),
                "text": normalized,
                "text_sha256": stable_id(normalized, length=64),
                "image_refs": _image_refs(normalized, self.ocr_root),
                "math_errors": delimiter_errors(normalized),
            }
            page = _apply_derived_formula_corrections(section["id"], page)
            page = _apply_derived_question_corrections(section["id"], page, question_corrections)
            pages.append(page)
            normalized = page["text"]
            spans = _question_spans(normalized)
            # 组标题可能出现在同一页的题目之后（例如 B4 后紧接 C 组），
            # 不能先把“本页最后一个组”写入 current_group，否则前面的题会被错分。
            # 按每个题号相对组标题的位置计算组别，并把最后一个标题带到下一页。
            page_start_group = current_group
            page_groups = list(GROUP_RE.finditer(normalized))
            for index, match in enumerate(spans):
                group_for_match = page_start_group
                for group_match in page_groups:
                    if group_match.start() < match.start():
                        group_for_match = group_match.group("group").upper()
                    else:
                        break
                # “强化训练/无 A 组”页的 B 组标题有时在上一页，且题1只剩
                # 日期括号；微专题的固定页锚允许继续沿用 B 组状态。
                if group_for_match is None and section.get("id") == "micro专题1" and page_number in {55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65}:
                    group_for_match = "B"
                current_group = group_for_match
                number = int(match.group("number"))
                end_offset = spans[index + 1].start() if index + 1 < len(spans) else len(normalized)
                chunk = normalized[match.start() : end_offset].strip()
                # A printed question number can be absent from OCR, so the
                # next numbered question is not necessarily the next span.
                # Use only an explicit manifest recovery anchor to cut the
                # unnumbered tail out of the preceding question.
                for recovery in known_recoveries:
                    if recovery.get("source_kind") != "primary_ocr" or recovery.get("source_doc") != page_number:
                        continue
                    recovery_group = str(recovery.get("group", ""))
                    recovery_number = int(recovery.get("number", -1))
                    if recovery_group != str(group_for_match or "") or recovery_number <= number or not recovery.get("start_regex"):
                        continue
                    anchor = re.search(str(recovery["start_regex"]), chunk, flags=re.M)
                    if anchor and anchor.start() > 0:
                        chunk = chunk[:anchor.start()].rstrip()
                        break
                # OCR 常把“### 4. 省份”标题和正文“4. 省份”各识别一次。
                # 标题没有题干/选项，直接丢弃，不建立第二个 QID。
                first_line = chunk.splitlines()[0].strip() if chunk.splitlines() else ""
                same_number_line = any(re.match(rf"^\s*{number}\s*[.．、]", line) for line in chunk.splitlines()[1:5])
                nonempty_lines = [line for line in chunk.splitlines() if line.strip()]
                if (first_line.startswith("###") or first_line.startswith("##")) and (same_number_line or len(nonempty_lines) <= 1):
                    continue
                question_text, answer_text = _split_answer(chunk)
                question_text = _trim_question_tail(question_text)
                images = _image_refs(question_text, path.parent)
                qid_binding = canonical_qids.get((str(group_for_match or ""), number))
                qid = (
                    str(qid_binding["canonical_qid"])
                    if qid_binding
                    else "Q-" + stable_id(source_rel, page_number, current_group or "?", number)
                )
                item = {
                    "qid": qid,
                    "section": section["id"],
                    "group": group_for_match,
                    "number": number,
                    "kind": f"{group_for_match or '?'}组",
                    "source_anchor": {"ocr_doc": page_number, "pdf_page": page_number + 1, "file": str(path)},
                    "question_text": question_text,
                    "answer_text": answer_text,
                    "answer_isolated": not bool(answer_text and answer_text in question_text),
                    "image_refs": images,
                    "visual_status": "READY_TEXT_ONLY" if not images else "NEEDS_VISION_SIDECAR",
                    "math_errors": delimiter_errors(question_text),
                    "evidence": ["E1"],
                }
                if qid_binding:
                    item["canonical_qid_binding"] = {
                        "status": "PRESERVED_ACROSS_SOURCE_TEXT_REPAIR",
                        "correction_id": qid_binding.get("id"),
                        "evidence": qid_binding.get("evidence"),
                    }
                sidecar_candidates = sidecar_by_hint.get(f"{section['id']}-{group_for_match}{number}", [])
                self._attach_visual_sidecar(item, sidecar_candidates)
                questions.append(item)
                if group_for_match:
                    observed.add((group_for_match, number))
            if page_groups:
                current_group = page_groups[-1].group("group").upper()

        # 只把 A/B/C 习题区的题目纳入“题包”；方法册例题仍保留在 pages 中，
        # 由 chapter1_manifest 的 knowledge_points/examples 负责索引，避免题数膨胀。
        questions = [q for q in questions if q.get("group") in section["question_groups"]]
        # 同一题的 Markdown 标题和正文可能各自命中正则；保留信息量最高的一条。
        deduped: dict[tuple[str, int], dict[str, Any]] = {}
        visual_rank = {"VISION_VERIFIED": 2, "READY_TEXT_ONLY": 1, "NEEDS_VISION_SIDECAR": 0}
        for item in questions:
            key = (item["group"], item["number"])
            previous = deduped.get(key)
            if previous is None:
                deduped[key] = item
                continue
            # OCR can emit a heading/body pair for the same question.  Keep
            # the richer text, but never throw away a verified sidecar that
            # was attached to the other duplicate.  Unioning figure refs is
            # safe here because the question key is already identical and the
            # sidecar matcher still requires an exact path or image hash.
            selected = item if len(item.get("question_text", "")) > len(previous.get("question_text", "")) else previous
            other = previous if selected is item else item
            refs: list[dict[str, Any]] = []
            seen_refs: set[str] = set()
            for ref in [*selected.get("image_refs", []), *other.get("image_refs", [])]:
                ref_key = str(ref.get("path") or ref.get("ref") or "")
                if ref_key and ref_key not in seen_refs:
                    refs.append(ref)
                    seen_refs.add(ref_key)
            if refs:
                selected["image_refs"] = refs
            if visual_rank.get(other.get("visual_status", ""), 0) > visual_rank.get(selected.get("visual_status", ""), 0):
                for field in ("visual_status", "vision_sidecar", "vision_sidecars", "vision_source_provenance", "evidence"):
                    if field in other:
                        selected[field] = other[field]
            deduped[key] = selected
        questions = list(deduped.values())
        expected = _expected_numbers(section["question_groups"])
        recovered = {
            (entry["group"], entry["number"]): entry
            for entry in (visual_sidecar or {}).get("known_visual_recoveries", [])
            if entry.get("section") == section["id"]
        }
        missing = sorted(expected - observed)
        for group, number in missing:
            recovery = recovered.get((group, number))
            recovered_item = self._recovery_question(section, group, number, recovery or {}, answer_root) if recovery else None
            if recovered_item:
                hint = f"{section['id']}-{group}{number}"
                self._attach_visual_sidecar(recovered_item, sidecar_by_hint.get(hint, []))
                questions.append(recovered_item)
                observed.add((group, number))
                continue
            questions.append({
                "qid": "Q-" + stable_id(source_rel, section["id"], group, number),
                "section": section["id"],
                "group": group,
                "number": number,
                "kind": f"{group}组",
                "source_anchor": {"ocr_doc": None, "pdf_page": None, "file": None},
                "question_text": "",
                "answer_text": "",
                "answer_isolated": True,
                "image_refs": [],
                "visual_status": "NEEDS_PAGE_VISUAL" if recovery else "MISSING_OCR_ANCHOR",
                "math_errors": [],
                "evidence": ["E0"],
                "recovery_reason": (recovery or {}).get("reason") if recovery else "题号未在 OCR 文本中出现",
            })

        # Recovery questions are appended above.  Recompute the missing set
        # before deriving the release status; otherwise a successfully
        # recovered, fully evidenced question leaves a stale pre-recovery
        # marker and the packet remains falsely UNVERIFIED.
        missing = sorted(expected - observed)

        self._apply_image_attachment_overrides(
            str(section["id"]),
            questions,
            list((visual_sidecar or {}).get("item_image_attachment_overrides", [])),
            {"abc_exercise"},
        )

        unresolved = []
        for page in pages:
            unresolved.extend(f"doc_{page['ocr_doc']}:{err}" for err in page["math_errors"])
            unresolved.extend(f"doc_{page['ocr_doc']}:missing_image:{ref['ref']}" for ref in page["image_refs"] if not ref["exists"])
        for item in questions:
            unresolved.extend(f"{item['qid']}:{err}" for err in item["math_errors"])
            if item["visual_status"] in {"NEEDS_PAGE_VISUAL", "MISSING_OCR_ANCHOR", "NEEDS_VISION_SIDECAR"}:
                unresolved.append(f"{item['qid']}:{item['visual_status']}")
        if section.get("id") == "micro专题1" and any(p.get("ocr_doc") == 57 and not p.get("derived_corrections") for p in pages):
            unresolved.append("doc_57:suspicious_fraction_denominator_pi_manual_review")
        status = "VERIFIED" if not unresolved and len(pages) == end - start + 1 and not missing else "UNVERIFIED"
        sorted_questions = sorted(questions, key=lambda x: (x.get("group") or "Z", x["number"], x["qid"]))
        for item in sorted_questions:
            anchor = item.get("source_anchor")
            if isinstance(anchor, dict) and isinstance(anchor.get("ocr_doc"), int) and anchor.get("pdf_page") is None:
                anchor["pdf_page"] = anchor["ocr_doc"] + 1
        student_questions = []
        answer_index = build_answer_index(answer_root, section["question_groups"]) if answer_root else {}
        answer_sidecar = []
        for item in sorted_questions:
            student = {k: v for k, v in item.items() if k not in {"answer_text", "answer_isolated"}}
            student["question_text"] = _redact_student_text(student.get("question_text", ""))
            student_questions.append(student)
            answer = answer_index.get((item.get("group"), item.get("number")))
            fallback_answer = item.get("answer_text", "") if answer_root is None else ""
            answer_sidecar.append({"qid": item["qid"], "section": item["section"], "group": item["group"], "number": item["number"], "answer_text": (answer or {}).get("text", fallback_answer), "answer_isolated": True, "source": (answer or {}).get("source"), "answer_kind": (answer or {}).get("kind", "source_packet" if fallback_answer else None), "answer_evidence": "E2" if answer and (answer or {}).get("kind") == "answer_marker" else ("E1" if answer or fallback_answer else "E0")})
        packet = {
            "schema_version": "7.1",
            "packet_type": "DEEPSEEK_TEXT_PACKET",
            "section": section["id"],
            "label": section["label"],
            "source": {"ocr_root": str(self.ocr_root), "ocr_docs": [start, end], "source_file": section.get("source_file")},
            "manifest": {
                "page_count": len(pages),
                "question_count": len(questions),
                "expected_question_count": sum(b[1] - b[0] + 1 for b in section["question_groups"].values()),
                "expected_groups": section["question_groups"],
                "derived_question_correction_count": sum(
                    len(page.get("derived_question_corrections", [])) for page in pages
                ),
            },
            "status": status,
            "consumer_guard": "Only consume when status=VERIFIED; UNVERIFIED packets are diagnostic evidence only.",
            "pages": pages,
            "questions": student_questions,
            "unresolved": sorted(set(unresolved)),
        }
        out = self.output_root / section["id"].replace("+", "_")
        save_json(out / "packet.json", _portable_artifact_paths(packet))
        lesson_packet = dict(packet)
        lesson_packet["packet_type"] = "DEEPSEEK_LESSON_PACKET"
        lesson_packet["consumer_guard"] = "Lesson-only context: may include worked examples; never use for independent attempt or reward judgement."
        save_json(out / "lesson_packet.json", _portable_artifact_paths(lesson_packet))
        learning_items = _extract_learning_items(
            pages,
            section,
            (visual_sidecar or {}).get("clean_learner_question_stems", []),
        )
        self._apply_image_attachment_overrides(
            str(section["id"]),
            [*learning_items["worked_examples"], *learning_items["direct_variants"]],
            list((visual_sidecar or {}).get("item_image_attachment_overrides", [])),
            {"worked_example", "direct_variant"},
        )
        for item in [*learning_items["worked_examples"], *learning_items["direct_variants"]]:
            hint = _learning_item_vision_hint(section["id"], item)
            item["vision_hint"] = hint
            self._attach_visual_sidecar(item, sidecar_by_hint.get(hint, []))
        learning_visual_unresolved = [
            f"{item.get('vision_hint')}:{item.get('visual_status')}"
            for item in [*learning_items["worked_examples"], *learning_items["direct_variants"]]
            if item.get("image_refs") and item.get("visual_status") != "VISION_VERIFIED"
        ]
        learning_text_unresolved = [
            f"{item.get('item_id')}:EMPTY_QUESTION_TEXT"
            for item in [*learning_items["worked_examples"], *learning_items["direct_variants"]]
            if not str(item.get("question_text", "")).strip()
        ]
        learning_unresolved = sorted(
            set([*packet["unresolved"], *learning_visual_unresolved, *learning_text_unresolved])
        )
        learning_status = "VERIFIED" if packet["status"] == "VERIFIED" and not learning_unresolved else "UNVERIFIED"
        instruction_pages = _extract_instruction_pages(pages, section["id"])
        knowledge_blocks = _extract_knowledge_blocks(instruction_pages, section)
        learning_cycles = _materialize_learning_cycles(section, learning_items, student_questions)
        knowledge_by_id = {item["id"]: item for item in knowledge_blocks}
        for cycle in learning_cycles:
            cycle["knowledge_blocks"] = [knowledge_by_id[ref] for ref in cycle.get("knowledge_refs", [])]
            cycle["prerequisite_knowledge_blocks"] = [knowledge_by_id[ref] for ref in cycle.get("prerequisite_knowledge_refs", [])]
        learning_packet = {
            "schema_version": "7.4",
            "packet_type": "DEEPSEEK_SEQUENTIAL_LEARNING_PACKET",
            "section": section["id"],
            "status": learning_status,
            "source": packet["source"],
            "workflow_order": [
                "repeat_each_learning_cycle_in_order",
                "watch_current_courses",
                "learn_each_current_example_then_attempt_its_direct_variants",
                "attempt_current_abc_exercises_without_answers",
                "assess_current_cycle_before_advancing",
                "unseen_near_transfer",
                "delayed_closed_book_review",
            ],
            "learning_cycles": learning_cycles,
            "knowledge_and_type_pages": instruction_pages,
            "knowledge_blocks": knowledge_blocks,
            "worked_examples": learning_items["worked_examples"],
            "direct_variants": learning_items["direct_variants"],
            "deduplicated_learning_items": learning_items.get("deduplicated_items", []),
            "exercise_questions": student_questions,
            "counts": {
                **learning_items["counts"],
                "abc_exercises": len(student_questions),
                "total_numbered_learning_items": (
                    learning_items["counts"]["worked_examples"]
                    + learning_items["counts"]["direct_variants"]
                    + len(student_questions)
                ),
            },
            "answer_policy": {
                "worked_examples": "teaching solutions allowed",
                "direct_variants": "question only; solution isolated",
                "abc_exercises": "question only; answer sidecar forbidden",
            },
            "unresolved": learning_unresolved,
        }
        save_json(out / "learning_packet.json", _portable_artifact_paths(learning_packet))
        save_json(
            out / "student_learning_items.json",
            _portable_artifact_paths(_student_learning_item_packet(
                section,
                {**packet, "status": learning_status},
                learning_items,
            )),
        )
        student_packet = dict(packet)
        student_packet["packet_type"] = "DEEPSEEK_STUDENT_PACKET"
        student_packet["answer_sidecar"] = None
        student_packet["consumer_guard"] = "Student/DeepSeek context: no answers. Consume only when status=VERIFIED."
        student_packet["pages"] = _student_lesson_free_pages(pages)
        student_packet["student_page_text_redacted"] = True
        save_json(out / "student_packet.json", _portable_artifact_paths(student_packet))
        answer_sidecar_path = out / "answer_sidecar.json"
        existing_answer_sidecar: dict[str, Any] | None = None
        if answer_sidecar_path.is_file():
            try:
                candidate = json.loads(answer_sidecar_path.read_text(encoding="utf-8-sig"))
                if isinstance(candidate, dict) and candidate.get("schema_version") == "ybt-answer-sidecar-v3":
                    existing_answer_sidecar = candidate
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                existing_answer_sidecar = None
        if existing_answer_sidecar is not None:
            current_qids = {str(item.get("qid") or "") for item in student_questions}
            answer_qids = {
                str(item.get("qid") or "")
                for item in existing_answer_sidecar.get("answers", [])
                if isinstance(item, dict)
            }
            if answer_qids != current_qids:
                raise PacketError(
                    f"{section['id']} verified answer sidecar QID drift: "
                    f"missing={sorted(current_qids - answer_qids)} "
                    f"stale={sorted(answer_qids - current_qids)}"
                )
        else:
            save_json(answer_sidecar_path, _portable_artifact_paths({"schema_version": "7.1", "section": section["id"], "answers": answer_sidecar, "consumer_guard": "Never pass this file to a student diagnosis context."}))
        save_json(
            out / "manifest.json",
            {
                "status": status,
                "learning_status": learning_status,
                "section": section["id"],
                "page_count": len(pages),
                "question_count": len(questions),
                "unresolved_count": len(packet["unresolved"]),
                "learning_unresolved_count": len(learning_unresolved),
                "consumer_guard": packet["consumer_guard"],
            },
        )
        (out / "packet.md").write_text(self.to_markdown(packet), encoding="utf-8")
        return _portable_artifact_paths(packet)

    @staticmethod
    def _sidecar_matches_question(sidecar: dict[str, Any], images: list[dict[str, Any]]) -> bool:
        """Require a sidecar image to be one of this question's actual figures.

        Prefer exact path equality, then accept an explicit content hash match
        for the same crop copied by a different OCR run.  A question hint alone
        is never sufficient, which prevents multi-image questions from being
        silently cross-bound.
        """
        if not isinstance(sidecar, dict):
            return False
        if not images:
            return False
        project_root = Path(__file__).resolve().parents[1]

        def resolve_image_reference(value: Any) -> Path:
            reference = Path(str(value or ""))
            if reference.is_file() or _is_answer_book_path(str(reference)):
                return reference
            current_roots = (
                "first_chapter_69",
                "second_chapter_109",
                "third_chapter_180",
                "chapter4_100",
                "chapter5_95",
            )
            candidates = (
                *(
                    project_root / "data" / "ocr_live_current" / root / folder / reference.name
                    for root in current_roots
                    for folder in ("imgs", "")
                ),
                project_root / "data" / "ocr_live_full" / "imgs" / reference.name,
                project_root / "reports" / "source_visuals2" / reference.name,
                project_root / "reports" / "source_visuals" / reference.name,
            )
            return next((candidate for candidate in candidates if candidate.is_file()), reference)

        sidecar_image = Path(str(sidecar.get("image", "")))
        if not sidecar_image.is_file():
            # Evidence produced on the old device may retain an absolute OCR
            # path.  Resolve only the basename into the current repository
            # snapshot; the content hash check below remains authoritative.
            if _is_answer_book_path(str(sidecar_image)):
                return False
            sidecar_image = resolve_image_reference(sidecar_image)
        if not sidecar_image.is_file():
            return False
        provenance = sidecar.get("source_provenance")
        if isinstance(provenance, dict) and _is_answer_book_path(provenance.get("source_pdf")):
            return False
        sidecar_resolved = sidecar_image.resolve()
        actual_sidecar_hash = _sha256_file(sidecar_image)
        if not actual_sidecar_hash:
            return False
        declared_hash = sidecar.get("image_sha256")
        if declared_hash and declared_hash != actual_sidecar_hash:
            return False
        resolved_images = [(ref, resolve_image_reference(ref.get("path"))) for ref in images]
        if any(reference.resolve() == sidecar_resolved for _, reference in resolved_images if reference.is_file()):
            return True
        if any(
            actual_sidecar_hash == (ref.get("sha256") or _sha256_file(reference))
            for ref, reference in resolved_images
        ):
            return True

        # A high-resolution crop from the authoritative source PDF is allowed
        # to replace a lower-resolution OCR crop only with an explicit,
        # content-bound provenance record.  A question hint alone is never a
        # binding key.
        if not isinstance(provenance, dict) or provenance.get("source_kind") != "high_resolution_source_pdf_crop":
            return False
        source_pdf = Path(str(provenance.get("source_pdf", "")))
        if not source_pdf.is_file():
            # The original source PDF may live on the old device.  The
            # derived crop and its current OCR image hash still provide a
            # verifiable content binding, so accept that portable fallback
            # without pretending the old PDF path is available.
            derived_hash = provenance.get("derived_from_image_sha256")
            derived_path = resolve_image_reference(provenance.get("derived_from_image_path"))
            if (
                isinstance(derived_hash, str)
                and re.fullmatch(r"[0-9a-f]{64}", derived_hash)
                and derived_path.is_file()
                and _sha256_file(derived_path) == derived_hash
                and any(derived_hash == (ref.get("sha256") or _sha256_file(reference)) for ref, reference in resolved_images)
            ):
                return True
            return False
        source_pdf_sha256 = provenance.get("source_pdf_sha256")
        if not isinstance(source_pdf_sha256, str) or source_pdf_sha256 != _sha256_file(source_pdf):
            return False
        if not isinstance(provenance.get("pdf_page"), int) or provenance["pdf_page"] < 1:
            return False
        crop_rect = provenance.get("crop_rect")
        if (
            not isinstance(crop_rect, list)
            or len(crop_rect) != 4
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in crop_rect)
            or crop_rect[0] >= crop_rect[2]
            or crop_rect[1] >= crop_rect[3]
        ):
            return False
        derived_hash = provenance.get("derived_from_image_sha256")
        if not isinstance(derived_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", derived_hash):
            return False
        derived_path = provenance.get("derived_from_image_path")
        if derived_path:
            derived_resolved = resolve_image_reference(derived_path).resolve()
            if not any(reference.resolve() == derived_resolved for _, reference in resolved_images if reference.is_file()):
                # The same immutable OCR crop can live under the historical
                # worker root or the current live root.  Exact path equality
                # is unnecessary when the declared derived path exists and
                # its content hash matches the declared identity.
                if not derived_resolved.is_file() or _sha256_file(derived_resolved) != derived_hash:
                    return False
        return any(
            derived_hash == (ref.get("sha256") or _sha256_file(Path(str(ref.get("path", ""))).resolve()))
            for ref in images
        )

    @staticmethod
    def to_markdown(packet: dict[str, Any]) -> str:
        lines = [f"# {packet['label']}", "", f"状态：`{packet['status']}`", f"页数：{packet['manifest']['page_count']}", f"题目记录：{packet['manifest']['question_count']}", "", "## 题目索引", ""]
        for item in packet["questions"]:
            anchor = item["source_anchor"].get("pdf_page") or "?"
            text = re.sub(r"\s+", " ", item.get("question_text", ""))[:180].rstrip()
            lines.append(f"- {item['group'] or '?'}{item['number']} / `{item['qid']}` / PDF页 {anchor} / {item['visual_status']} / {text}")
        if packet["unresolved"]:
            lines.extend(["", "## 未解决", ""])
            lines.extend(f"- {x}" for x in packet["unresolved"])
        return "\n".join(lines) + "\n"


def verify_packet(path: str | Path) -> dict[str, Any]:
    import json

    packet = json.loads(Path(path).read_text(encoding="utf-8"))
    errors: list[str] = []
    if packet.get("status") != "VERIFIED":
        errors.append("packet_status_not_verified")
    if packet.get("manifest", {}).get("page_count") != len(packet.get("pages", [])):
        errors.append("page_count_mismatch")
    if packet.get("manifest", {}).get("question_count") != len(packet.get("questions", [])):
        errors.append("question_count_mismatch")
    if packet.get("unresolved"):
        errors.append("unresolved_items")
    for page in packet.get("pages", []):
        errors.extend(f"{page.get('ocr_doc')}:{x}" for x in page.get("math_errors", []))
    for item in packet.get("questions", []):
        source_anchor = item.get("source_anchor") or {}
        if source_anchor.get("recovery_source_kind") == "answer_ocr":
            errors.append(f"{item.get('qid')}:answer_ocr_recovery_forbidden")
        for ref in item.get("image_refs", []):
            if _is_answer_book_path(ref.get("path")):
                errors.append(f"{item.get('qid')}:answer_book_image_reference")
        if item.get("answer_text") and item["answer_text"] in item.get("question_text", ""):
            errors.append(f"{item.get('qid')}:answer_leak")
        if re.search(r"(?m)^\s*(?:最终答案|故答案|答案为|所以其余弦值|因此得到|故得|故为|解法\s*[一二两12]|证明|证明过程)\s*[：:]?", item.get("question_text", ""), flags=re.I):
            errors.append(f"{item.get('qid')}:solution_marker_leak")
        if BARE_ANSWER_LINE_RE.search(item.get("question_text", "")):
            errors.append(f"{item.get('qid')}:bare_answer_line_leak")
        if item.get("visual_status") == "VISION_VERIFIED":
            sidecars = item.get("vision_sidecars")
            if sidecars is not None:
                if not isinstance(sidecars, list) or len(sidecars) != len(item.get("image_refs", [])):
                    errors.append(f"{item.get('qid')}:incomplete_vision_sidecars")
                elif any(
                    not isinstance(sidecar, dict)
                    or not _usable_vision_sidecar({
                        "status": "passed",
                        "confidence": sidecar.get("confidence"),
                        "structured": sidecar.get("structured"),
                    })
                    for sidecar in sidecars
                ):
                    errors.append(f"{item.get('qid')}:invalid_vision_sidecar")
                else:
                    for sidecar in sidecars:
                        if _is_answer_book_path((sidecar.get("source_provenance") or {}).get("source_pdf")):
                            errors.append(f"{item.get('qid')}:answer_book_visual_provenance")
                        if not PacketBuilder._sidecar_matches_question(sidecar, item.get("image_refs", [])):
                            errors.append(f"{item.get('qid')}:visual_sidecar_not_bound")
            elif len(item.get("image_refs", [])) > 1:
                errors.append(f"{item.get('qid')}:incomplete_vision_sidecars")
            if not _usable_vision_sidecar({"status": "passed", "confidence": (item.get("evidence") or [None, None])[-1], "structured": item.get("vision_sidecar")}):
                errors.append(f"{item.get('qid')}:invalid_vision_sidecar")
    if packet.get("packet_type") == "DEEPSEEK_STUDENT_PACKET":
        if packet.get("answer_sidecar") is not None:
            errors.append("answer_sidecar_present")
        page_leak = re.compile(r"(?im)^\s*(?:解法\s*[一二两12]|证明|证明过程|解答|解析|答案)\s*[：:：]?")
        for page in packet.get("pages", []):
            if page_leak.search(page.get("text", "")):
                errors.append(f"{page.get('ocr_doc')}:page_solution_marker_leak")
            if BARE_ANSWER_LINE_RE.search(page.get("text", "")):
                errors.append(f"{page.get('ocr_doc')}:page_bare_answer_line_leak")
        for item in packet.get("questions", []):
            if not item.get("question_text", "").strip():
                errors.append(f"{item.get('qid')}:empty_question_text")
            if item.get("visual_status") not in {"READY_TEXT_ONLY", "VISION_VERIFIED"}:
                errors.append(f"{item.get('qid')}:visual_not_consumable")
    return {"status": "passed" if not errors else "failed", "errors": sorted(set(errors)), "path": str(path)}
