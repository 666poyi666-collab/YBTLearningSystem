from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_preview_exporter():
    path = ROOT / "scripts" / "export_learning_preview_html.py"
    spec = importlib.util.spec_from_file_location("ybt_preview_exporter_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PreviewHtmlTests(unittest.TestCase):
    def test_markdown_blocks_are_rendered_and_tables_are_not_escaped(self) -> None:
        exporter = _load_preview_exporter()
        source = (
            "# 标题\n\n"
            "> 说明  \n"
            "> 第二行\n\n"
            "## 一眼总览\n\n"
            "<table class=\"overview-table\"><tr><td>总览</td></tr></table>\n\n"
            "## 循环 1/1\n\n"
            "- `任务 01` 教材例1\n"
            "  - **思考入口：** 先识别方法\n"
            "  - **书写骨架：** 逐步写出\n"
            "  - **检查点：** 回代核对\n\n"
            "- 视频\n"
            "  - 文件：课程.mp4\n\n"
            "1. 第一步\n"
            "2. 第二步\n\n"
            "<table border=1><tr><td>知识点</td></tr></table>\n"
        )

        rendered = exporter.render_markdown(source)

        self.assertIn("<h1>标题</h1>", rendered)
        self.assertIn("<blockquote>", rendered)
        self.assertIn('<h2 class="overview-heading" id="overview">一眼总览</h2>', rendered)
        self.assertIn('<h2 class="cycle-heading" id="cycle-1">循环 1/1</h2>', rendered)
        self.assertIn('<li class="task-card"><div class="task-main"><code>任务 01</code> 教材例1</div>', rendered)
        self.assertIn("<ul><li><strong>思考入口：</strong> 先识别方法</li>", rendered)
        self.assertIn("<ul><li>视频<ul><li>文件：课程.mp4</li></ul></li></ul>", rendered)
        self.assertIn("<ol><li>第一步</li><li>第二步</li></ol>", rendered)
        self.assertIn("<table border=1>", rendered)
        self.assertNotIn("&lt;table", rendered)
        self.assertNotIn("<pre>", rendered)

    def test_export_preview_has_utf8_document_shell_and_no_question_media(self) -> None:
        exporter = _load_preview_exporter()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            markdown_path = root / "learning_path_without_questions.md"
            output_path = root / "learning_path_without_questions.html"
            markdown_path.write_text(
                "# 无题目预览\n\n- [ ] 只保留路线\n\n<table><tr><td>知识点</td></tr></table>\n",
                encoding="utf-8-sig",
            )

            exporter.export_preview(markdown_path, output_path)
            html = output_path.read_text(encoding="utf-8")

        self.assertIn('<meta charset="utf-8">', html)
        self.assertIn('<main class="report-page"><h1>无题目预览</h1>', html)
        self.assertIn("main.report-page", html)
        self.assertIn('type="checkbox" disabled', html)
        self.assertIn("<table>", html)
        self.assertIn('data-mathjax-version="3.2.2"', html)
        self.assertNotIn("cdn.jsdelivr.net", html)
        self.assertNotIn("<pre>", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("&lt;table", html)

    def test_local_mathjax_asset_is_pinned(self) -> None:
        exporter = _load_preview_exporter()
        self.assertTrue(exporter.MATHJAX_SCRIPT.is_file())
        self.assertIn("3.2.2", str(exporter.MATHJAX_SCRIPT))


if __name__ == "__main__":
    unittest.main()
