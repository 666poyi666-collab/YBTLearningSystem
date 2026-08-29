# ChatGPT 辅助学习配置

这套项目不需要每次把 GitHub 仓库下载下来，也不需要把整个仓库上传到 ChatGPT 项目。

## 推荐连接方式

1. 在 ChatGPT 项目“数学选择性必修一”中使用已经授权的“数学一本通学习”远程 MCP。
2. 新建聊天后发送 `prompts/math_project_bootstrap.md`，让 ChatGPT 先读取 MCP 系统状态、当前任务和第一章第一节概览。
3. MCP 不可用时，才在 ChatGPT 的 `设置 → Apps → GitHub` 连接 GitHub，并只授权仓库 `666poyi666-collab/ybt-learning-system-v7`，作为静态回退。
4. 将 `C:\Users\16408\Downloads\数学_必修二_-_8.5.md` 作为可选项目参考文件上传一次。它是旧对话参考，不是本节教材事实，也不应提交到公开 GitHub。

GitHub 负责读取仓库事实：教材题包、题图、课程转写、课程覆盖、学习路径和项目规则。8.5 文件只负责提供过去对话的辅助形式和用户卡点案例。当前节次的真实内容必须以仓库题包、题图和课程转写为准。

用户提供的两份《高二数学精讲精练》讲义已建立 562 页云端索引和原页图包。ChatGPT 可用 `math_search_handout` 搜索文字、用 `math_get_course_handout` 定位课程候选页，再用 `math_get_handout_page` 读取原页图。OCR 只用于定位，公式、图形和题面必须以原页图核对；候选课程映射不得冒充已视觉核验映射。

资料库范围与学习路径范围分开：MCP 资料库覆盖选择性必修 1 的第一至第五章；当前学习路径和持续学习者只推进第一、二章。讲题核对答案时，`math_get_answer_sources` 返回已导入的一本通答案来源；ChatGPT 必须把原书答案和自己的 `model_solution` 分开，给出推荐方案和理由，不能把模型答案冒充原书答案。

## 不要上传的内容

- 不要上传整个仓库压缩包；GitHub 连接已经承担仓库读取。
- 不要上传答案侧车、内部模拟 JSON 或整份生成 HTML。
- 不要把 8.5 对话提交到公开仓库，除非以后明确决定公开它。

## 一次性项目提示词

将 [math_project_bootstrap.md](../prompts/math_project_bootstrap.md) 发送到项目“数学选择性必修一”的新聊天。发送后先让 ChatGPT 只做“第一章第一节循环 1”的资料核验，不要直接开始整章长篇输出。

## 每次卡住时

网页循环详情中的“复制给 ChatGPT”会生成当前循环上下文。复制后粘贴到项目聊天，并补充自己的题目尝试或截图。不要只说“这题不会”，要保留自己的第一步，这样画像才有证据。

章节页顶部的“复制进度”只生成当前浏览器实时进度快照。它不会自动写入 Cloudflare D1，也不会因为 ChatGPT 读到了快照就产生云端学习事件。开始新聊天或跨设备继续时，应先复制这份进度；当用户明确确认某个真实动作已经发生后，ChatGPT 才调用对应的写工具（听完课、题目通过、循环完成或疑问记录），并使用幂等 `requestId` 和当前 `baseVersion`。需要把当天快照写入云端时，明确说“同步今天进度”，再调用 `math_sync_progress_snapshot`。

用户确认做错、卡住或依赖提示后，ChatGPT 应立即调用 `math_record_wrong_question`，同时保存错因和题型归类。用户说“整理当前错题”时，调用 `math_export_wrong_questions` 即时生成包含最新循环、错题状态、题型、记忆重点和复测动作的 Markdown；不得只凭聊天记忆临时拼接。用户明确跳过某循环时调用 `math_defer_cycle`，状态必须是“暂缓”，不能冒充“完成”。

《2026版 高中必刷题数学 选择性必修第一册 RJA》是独立补充题库。请先调用 `math_get_course_first_route` 查看课程编号顺序，完成对应《一本通》项目后，再用 `math_get_practice_route` 查看当前已解锁的基础题。需要看题时调用 `math_get_practice_page`；回复中同时写明书内印刷页、PDF 页和题号。源 PDF 没有答案，不能把模型推导或其他答案册冒充原书答案。

用户上传手写图时，先用视觉能力逐行转写并核对原题，再调用 `math_record_handwriting_analysis` 保存 `firstWrongStep`、每行状态、错误原因、下游污染、归一化框坐标和 LaTeX。根据返回的 `annotationSpec` 输出 HTML：原图作为底图，透明无填充 SVG 叠加，首错红框、下游橙色虚线框、正确绿色框，右侧显示行号、解释和 LaTeX/MathJax。只有用户确认“确实错了/按这个记录”后，才调用 `math_record_wrong_question` 写入正式错题和题型；不确定就保留为 `needs_clarification`。

若图片模糊、字迹/符号有歧义、原题没核对或模型置信度低，必须先在回答和 HTML 中单列“仍不确定，需用户确认”，写明具体行和需要补拍的区域；同时向 `math_record_handwriting_analysis` 提交 `uncertainties` 与 `clarificationRequest`。没有披露不确定性时，云端写入会拒绝。

标准流程：

```text
网页选择当前循环
→ 听对应课程
→ 按题序完成教材项目
→ 在疑问框写卡点
→ 复制给 ChatGPT
→ 提交自己的第一步或过程
→ 接收一个最小提示
→ 修改后再提交
→ 标记循环听完、项目通过或保留星标
```

## GitHub 与 MCP 的边界

GitHub App + 项目提示词仍是静态仓库事实的回退路径；数学远程 MCP 已部署并保存第一至第五章的版本化题包、题图、课程全文、答案来源和学习状态索引。连接完成后，ChatGPT 应优先使用 MCP 获取实时内容和进度，GitHub 用于核对源文件、审计包和提示词。学习路径仍只推进第一、二章。

MCP 不是资料上传工具，也不能替代项目提示词和学习状态模型。ChatGPT 网页端已完成 `https://math-learning-mcp.focuslink-poyi-6465e9.workers.dev/mcp` 的 OAuth 自定义 App 授权，并在项目“数学选择性必修一”中完成真实只读调用。资料库现已包含选择性必修 1 五章全部 38 节；学习路径仍只推进第一、二章。写回工具仍只在用户明确确认后使用，网页 `localStorage` 本身不代表云端已同步。
