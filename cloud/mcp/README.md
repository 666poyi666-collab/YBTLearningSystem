# Math Learning Cloud MCP

这是一本通数学学习系统主仓库内的 Cloudflare 远程 MCP，不是独立项目。

## 能力

- 读取教材/题目索引、课程映射、网课方法和时间片。
- 搜索两本配套《高二数学精讲精练》，按课程定位候选页并返回原页图核对。
- 搜索并按课程/循环解锁《2026版高中必刷题数学·选择性必修第一册》，返回书内印刷页、PDF 页、题号和原页图。
- 读取真实用户当前任务与学习状态。
- 幂等记录课程学习、作答、疑问、提示使用、题目通过、循环完成和进度快照。
- 实时记录错题和题型分类，并按最新云端状态生成错题整理文档。
- 记录必刷题作答与手写逐行分析，保留第一处分歧和前错导致的下游污染。
- D1 保存查询索引和学习事件；R2 保存版本化题包、题图和课程转写。

## 安全边界

- `math:read` 与 `math:write` 分离。
- `math_mark_item_passed` 必须有冻结证据哈希、baseVersion 和用户确认。
- 内部模拟进度不得进入真实用户状态。
- 讲义 OCR 只用于检索；公式、图形和题面必须以返回的原页图为核对依据。
- 必刷题源 PDF 不含答案；课程优先入口才会解锁基础题，节次综合和章节检测后置。
- 第二章缺少时间轴的课程返回 `null` 时间，不做推测。
- `OAUTH_RS_CLIENT_SECRET` 只通过 Cloudflare secret 配置。

## 当前状态

代码、D1 schema、私有 R2、共享 OAuth audience/scopes 和独立资源服务器凭据均已建立。远端迁移、内容导入、生产部署和未授权访问验收已通过；`/healthz`、`/readyz` 与 protected-resource 元数据均为 200，无令牌 `/mcp` 为 401。

当前内容快照为版本化导入计划：选择性必修 1 第一至第五章共 38 节、1,209 个教材项目、全部 170 门课程目录中的实际映射课程、课程转写和可用答案来源；R2 保存节次题包、课程转写包和题图包。导入计划由 `scripts/import_content.mjs` 生成，默认 dry-run，可用 `npm run import:dry` 重建；远程导入使用 `npm run import:remote`。学习路径仍只针对第一、二章。

补充练习库版本化导入计划由 `scripts/import_practice_book.mjs` 生成，索引器为仓库根目录 `scripts/build_practice_book_index.py`。当前书源为 106 页、727 个唯一题目；第一章 194 题、第二章 230 题、第三章 269 题，另有 34 道模块综合题。生产版本 `practice-v1-914d4950e9156882` 已写入 D1/R2，题面 OCR 是搜索辅助，原页图是题面权威；源 PDF 本身没有答案。

学习者安全的读取工具包括：`math_get_section_overview`（完整节次大纲与项目索引）、`math_get_item_content`（完整题面与题图，不返回答案侧车）、`math_get_course_transcript`（完整老师文稿及可靠时间轴）、三项讲义检索/原页工具、课程优先学习包、必刷题路由/原页工具、手写逐行分析和 `math_get_answer_sources`（已导入的一本通原书答案来源）。模型自己的解法不写入原书答案表，必须由 ChatGPT 单独标记为 `model_solution` 并给出推荐理由。没有可验证逐句时间轴时，返回 `timelineAvailable=false` 和空时间轴，不作估算。当前生产 Worker 为 `https://math-learning-mcp.focuslink-poyi-6465e9.workers.dev`，最新部署版本为 `efa887d6-017f-4f9d-8a14-c35e14350ea0`。

ChatGPT 网页端“数学一本通学习”开发模式 App 已完成 OAuth 授权，并在项目“数学选择性必修一”中完成真实只读调用验收：ChatGPT 读取了系统状态、第一章第一节概览、第一道题题面和第一门课程全文；系统返回 2 章、11 节、401 个项目、37 门课程、2,038 个转写片段，学习事件仍为 0。本次验收未写入学习进度。
