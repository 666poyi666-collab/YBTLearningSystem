from __future__ import annotations

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "codex-skill" / "ybt-all-chapters-learning-path" / "scripts" / "render_compact_chapter_learning.py"
SPEC = importlib.util.spec_from_file_location("ybt_compact_renderer", SCRIPT)
assert SPEC and SPEC.loader
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


class CompactChapterRendererTests(unittest.TestCase):
    def test_chapter1_output_is_complete_compact_and_answer_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = RENDERER.render_chapter(ROOT, 1, Path(temporary))
            markdown = (Path(temporary) / "chapter1.md").read_text(encoding="utf-8")
            html = (Path(temporary) / "chapter1.html").read_text(encoding="utf-8")
        self.assertEqual(124, report["canonical_items"])
        self.assertEqual(15, report["required_courses"])
        self.assertEqual(4, report["sections"])
        self.assertEqual(124, html.count('class="item-detail"'))
        self.assertEqual(124, html.count('class="mapping-row"'))
        self.assertEqual(4, html.count('class="section-panel"'))
        self.assertEqual(4, html.count('class="section-tab"'))
        self.assertIn('class="course-dialog"', html)
        self.assertIn('data-cycle-panel="outline"', html)
        self.assertIn("空间向量的相关概念", html)
        self.assertIn("类型Ⅰ 线性运算", html)
        self.assertIn("3.1.1.1 空间向量的运算", html)
        self.assertGreater(html.find("3.1.4.6.b"), html.find("3.1.4.6.a"))
        self.assertIn("标记已听完", html)
        self.assertIn("data-star-item=", html)
        self.assertIn("data-cycle-question=", html)
        self.assertIn("复制给 ChatGPT", html)
        self.assertIn("请优先使用已连接的“数学一本通学习” MCP", html)
        self.assertIn("只有 MCP 不可用时，才使用 @GitHub", html)
        self.assertIn("不直接公布结果", html)
        self.assertIn('data-chapter="1"', html)
        self.assertIn('class="chapter-dashboard"', html)
        self.assertIn('class="section-course-head"', html)
        self.assertIn('class="route-marker"', html)
        self.assertIn('class="back-to-route"', html)
        self.assertNotIn('class="cycle-tab"', html)
        self.assertIn('class="next-step"', html)
        self.assertIn('data-next-title', html)
        self.assertIn('data-copy-progress', html)
        self.assertIn('chapter12_complete_audit.json', html)
        self.assertIn("课程编号", html)
        self.assertIn("课程名称", html)
        self.assertIn("data-pass-item=", html)
        self.assertIn('class="section-course-head"', html)
        self.assertIn('class="chapter-dashboard"', html)
        self.assertNotIn("课程覆盖项目", html)
        self.assertNotIn("模拟已学课程", html)
        self.assertNotIn("真实用户", html)
        self.assertEqual(124, markdown.count('<details class="item-detail">'))
        self.assertIn("| 例1 | 空间向量的相关概念 | 知识点右侧例题 | 图形已核验 |", markdown)
        self.assertIn("| 例9 | 类型Ⅰ 线性运算 | 类型题 | 文本可用 |", markdown)
        self.assertIn('<meta name="viewport"', html)
        self.assertNotRegex(markdown + html, re.compile(r"LI:|Q:Q-|答案\s*[：:]|正确选项"))

    def test_chapter2_output_keeps_all_sections_and_items(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = RENDERER.render_chapter(ROOT, 2, Path(temporary))
            html = (Path(temporary) / "chapter2.html").read_text(encoding="utf-8")
        self.assertEqual(277, report["canonical_items"])
        self.assertEqual(22, report["required_courses"])
        self.assertEqual(7, report["sections"])
        self.assertEqual(277, html.count('class="item-detail"'))
        self.assertEqual(277, html.count('class="mapping-row"'))
        self.assertEqual(7, html.count('class="section-panel"'))
        self.assertEqual(7, html.count('class="section-tab"'))


if __name__ == "__main__":
    unittest.main()
