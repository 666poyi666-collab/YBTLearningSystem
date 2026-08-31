# Math Learning Cloud MCP

这是一本通数学学习系统主仓库内的 Cloudflare 远程 MCP，不是独立项目。

## 能力

- 读取教材/题目索引、课程映射、网课方法和时间片。
- 搜索两本配套《高二数学精讲精练》，按课程定位候选页并返回原页图核对。
- 搜索并按课程/循环解锁《2026版高中必刷题数学·选择性必修第一册》，返回书内印刷页、PDF 页、题号和原页图。
- 读取真实用户当前任务与学习状态。
- 幂等记录课程学习、作答、疑问、提示使用、题目通过、循环完成和进度快照。
- 实时记录错题和题型分类，并按最新云端状态生成错题整理文档。
- 记录可选必刷题作答与手写逐行分析，保留第一处分歧、透明 HTML 标注规格和前错导致的下游污染。
- D1 保存查询索引和学习事件；R2 保存版本化题包、题图和课程转写。
- 全书原书答案按题保存证据类型、置信度、复核与自动判分权限，并绑定原 PDF SHA、PDF 页码、页图 SHA 和版本化 R2 原页包。

## 安全边界

- `math:read` 与 `math:write` 分离。
- `math_mark_item_passed` 必须有冻结证据哈希、baseVersion 和用户确认。
- 内部模拟进度不得进入真实用户状态。
- 讲义 OCR 只用于检索；公式、图形和题面必须以返回的原页图为核对依据。
- 必刷题源 PDF 不含答案；它是可选增强，不阻塞课程、一本通、节次或章节完成。课程优先入口只决定推荐/可选解锁，节次综合和章节检测后置。
- 第二章缺少时间轴的课程返回 `null` 时间，不做推测。
- 答案证据默认 fail-closed：只有 `parsed_answer_text + high + review_required=false + automatic_grading_allowed=true` 可用于自动判分。低置信 OCR 和仅原页证据会强制禁止自动判分；需复核时 `math_get_answer_sources` 返回经 SHA 验证的 MCP image block。
- `model_solution` 不写入 `answer_sources`，必须在对话中与原书答案分列，不得反向冒充原书证据。
- `OAUTH_RS_CLIENT_SECRET` 只通过 Cloudflare secret 配置。

## 当前状态

代码、D1 schema、私有 R2、共享 OAuth audience/scopes 和独立资源服务器凭据均已建立。远端迁移、内容导入、生产部署和未授权访问验收已通过；`/healthz`、`/readyz` 与 protected-resource 元数据均为 200，无令牌 `/mcp` 为 401。

当前生产内容版本为 `v1-82aac1d4dce375de`，绑定提交 `d2eb9e1a754b6cbd206dfb3af1bb8eb3fda1e207`：选择性必修 1 第一至第五章共 38 节、1,209 个教材项目、5,097 条唯一项目-课程链接、170 门课程、19,234 个转写片段和 546 条当前原书答案。答案分为 473 条自动可用、51 条文本待原页复核和 22 条仅原页证据；R2 保存 38 个答案页包和 326 张唯一页图。78/78 个当前版本对象已逐个下载验 SHA。

补充练习库版本化导入计划由 `scripts/import_practice_book.mjs` 生成，索引器为仓库根目录 `scripts/build_practice_book_index.py`。当前书源为 106 页、727 个唯一题目；第一章 194 题、第二章 230 题、第三章 269 题，另有 34 道模块综合题。最新候选路由版本为 `practice-v1-f55a4c6c3bbfd761`，包含 3,020 条候选链接；题面 OCR 是搜索辅助，原页图是题面权威，跨节综合页不生成伪精确 cycle 绑定。源 PDF 本身没有答案，必刷题始终选做且不阻塞主线。

学习者安全的读取工具包括：`math_get_section_overview`（完整节次大纲与项目索引）、`math_get_item_content`（完整题面与题图，不返回答案侧车）、`math_get_course_transcript`（完整老师文稿及可靠时间轴）、三项讲义检索/原页工具、课程优先学习包、必刷题路由/原页工具、手写逐行分析和 `math_get_answer_sources`（已导入的一本通原书答案来源）。模型自己的解法不写入原书答案表，必须由 ChatGPT 单独标记为 `model_solution` 并给出推荐理由。没有可验证逐句时间轴时，返回 `timelineAvailable=false` 和空时间轴，不作估算。当前生产 Worker 为 `https://math-learning-mcp.focuslink-poyi-6465e9.workers.dev`，最新部署版本为 `0f7f29b2-01e3-4d36-8f43-b375c329a939`。

`0006_answer_evidence_contract.sql` 是纯增量迁移，不重建或删除任何用户表，已应用到生产 D1。旧答案行自动降级为 `legacy_unreviewed`，默认禁止自动判分；工具默认按来源类型返回最新内容版本，旧记录只在显式 `includeHistory=true` 时可见。

ChatGPT 网页端“数学一本通学习”开发模式 App 已完成 OAuth 授权。当前 D1 保留 7 条用户确认学习事件、3 条诊断、3 条题型分类和 3 条记忆点；内容/练习重导入没有覆盖这些记录。`/healthz`、`/readyz` 均为 200，无令牌 `/mcp` 为 401。
