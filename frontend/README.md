# Frontend Ownership

本目录定义 learner-facing Markdown/HTML 的未来前端所有权边界。当前渲染实现仍位于 `scripts/export_learning_preview_html.py` 和现有合并脚本中，本轮不复制或迁移代码。

当前紧凑章节样式位于 `codex-skill/ybt-all-chapters-learning-path/assets/chapter-report.css`，渲染入口是同一 Skill 下的 `scripts/render_compact_chapter_learning.py`。后续前端工作应优先解决章节课程账本、节次导航、教材循环、未通过项和移动端可读性。压力测试轨迹、哈希和内部 ID 不属于学习页面。

当前 HTML 信息架构为：紧凑章节进度栏 → 左侧节次导航 → 中间纵向学习路线 → 右侧课程队列；循环详情独占工作区。移动端改为当前节次选择器 → 课程队列 → 学习路线。不要恢复横向循环标签条或把课程编号、课程名称、题目顺序合并成一个文本块。

路线首屏必须有动态“下一步”区域；它从本地循环状态推导当前应学循环和题序。循环路线使用连续编号时间线表达，不使用横向 tab 导航。
