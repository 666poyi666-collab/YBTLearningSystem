# Math Learning Cloud MCP

这是一本通数学学习系统主仓库内的 Cloudflare 远程 MCP，不是独立项目。

## 能力

- 读取教材/题目索引、课程映射、网课方法和时间片。
- 读取真实用户当前任务与学习状态。
- 幂等记录课程学习、作答、疑问、提示使用、题目通过、循环完成和进度快照。
- D1 保存查询索引和学习事件；R2 保存版本化题包、题图和课程转写。

## 安全边界

- `math:read` 与 `math:write` 分离。
- `math_mark_item_passed` 必须有冻结证据哈希、baseVersion 和用户确认。
- 内部模拟进度不得进入真实用户状态。
- 第二章缺少时间轴的课程返回 `null` 时间，不做推测。
- `OAUTH_RS_CLIENT_SECRET` 只通过 Cloudflare secret 配置。

## 当前状态

代码、D1 schema、私有 R2、共享 OAuth audience/scopes 和独立资源服务器凭据均已建立。远端迁移、内容导入、生产部署和未授权访问验收已通过；`/healthz`、`/readyz` 与 protected-resource 元数据均为 200，无令牌 `/mcp` 为 401。

当前内容快照为 `v1-946594dec80d0b04`：第一、二章共 11 节、401 个教材项目、37 门必修课程、1,365 条项目-课程映射和 2,038 个转写查询片段；R2 另保存 11 个节次题包、1 个课程转写包和 1 个题图包（72 张引用题图）。导入计划由 `scripts/import_content.mjs` 生成，默认 dry-run，可用 `npm run import:dry` 重建；远程导入使用 `npm run import:remote`。

学习者安全的读取工具包括：`math_get_section_overview`（完整节次大纲与项目索引）、`math_get_item_content`（完整题面与题图，不返回答案侧车）和 `math_get_course_transcript`（完整老师文稿及可靠时间轴）。第二章课程没有可验证的逐句时间轴时，返回 `timelineAvailable=false` 和空时间轴，不作估算。当前生产 Worker 为 `https://math-learning-mcp.focuslink-poyi-6465e9.workers.dev`，部署版本 `98671c0a-75c3-4ff9-95e9-280730567d3b`。

ChatGPT 网页端“数学一本通学习”开发模式 App 已完成 OAuth 授权，并在项目“数学选择性必修一”中完成真实只读调用验收：ChatGPT 读取了系统状态、第一章第一节概览、第一道题题面和第一门课程全文；系统返回 2 章、11 节、401 个项目、37 门课程、2,038 个转写片段，学习事件仍为 0。本次验收未写入学习进度。
