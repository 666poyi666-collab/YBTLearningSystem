# 一本通学习系统 v7

这是《一本通》教材、课程覆盖、学习路径和验收证据仓库。当前产品范围是选择性必修 1 全五章、38 节：每节都有无答案学习路线，五个固定零基础人格承担合成路线压力审计，`primary-user-proxy` 按教材顺序维护跨运行的预测画像。路线审计不提交最终数学答案，因此不证明正确或掌握；第一章第一节继续作为真实对话驱动的回归样板。

第一次接触项目先看 `docs/PROJECT-MAP.md`；产品合同见 `docs/PRODUCT-REQUIREMENTS.md`，工程规则见 `docs/PROJECT-STANDARDS.md`。

云端 MCP 已部署在 `https://math-learning-mcp.focuslink-poyi-6465e9.workers.dev`，资料库和学习路线覆盖选择性必修 1 第一至第五章。两本《高二数学精讲精练》共 562 页已建立 OCR 检索与原页图核对链路；《2026版高中必刷题数学·选择性必修第一册》106 页、727 题作为独立选做题库。ChatGPT OAuth 已完成真实调用验收；没有可靠时间轴的课程会明确返回无时间轴状态。错题、题型、手写分析、练习作答和进度实时写入 D1；原书答案和 ChatGPT 自己的模型解法必须分开显示。

## 运行

在本目录执行：

```powershell
python -m ybt_learning.cli build-chapter1
python -m ybt_learning.cli answer-status
python -m ybt_learning.cli deepseek-status
python scripts/run_deepseek_http_probe.py
python scripts/verify_saved_deepseek_http_probe.py
python -m ybt_learning.cli simulate-five
python -m ybt_learning.cli verify-packet --packet data/packets/1.1/student_packet.json
python -m unittest discover -s tests -v
python scripts/export_all_section_routes.py
python scripts/audit_student_question_isolation.py
python scripts/deep_simulate_all_sections.py
python scripts/simulate_all_section_routes.py
python scripts/audit_all_section_learning_contracts.py --sol-review-status completed_requested_scope_with_findings
python scripts/audit_all_chapters_sources.py --book-root <一本通原书目录>
python codex-skill/ybt-all-chapters-learning-path/scripts/validate_chapter_learning_progress.py --project-root . --progress data/learner_progress/chapter1.json
python codex-skill/ybt-all-chapters-learning-path/scripts/validate_chapter_learning_progress.py --project-root . --progress data/learner_progress/chapter2.json
python codex-skill/ybt-all-chapters-learning-path/scripts/render_compact_chapter_learning.py --project-root .
```

当前静态路线覆盖 5 章、38 节、1,209 个 canonical 项目。五人格审计只证明路线合同可执行，`primary-user-proxy` 在没有最终数学答案时保持 `simulated_learning_status=not_run_no_final_learner_answers`，两者均保持 `mastery_claimed=false`。全量审计先写版本目录，只有 38 节全部通过才更新 `reports/deep_section_simulations/current.json`。真实课程消费、逐题作答和 MCP 写回证据闭合后，才能标记真人节次或章节完成。

生产状态入口：先用 `init-state --state <路径> --section 1.1` 建立目标状态；原题作答用 `record-attempt`，独立近变式用 `record-near-variant --item-id <原题ID> --variant-item-id <新题ID>`，到期复测用 `review-item`，小节完成用 `complete-section`。`VISION_VERIFIED` 必须同时提供 `--source-anchor-json '{"visual_evidence":"E1或E2"}'`，否则拒绝入账。

`build-chapter1` 会：

1. 扫描 Downloads 下第一章课程和字幕；
2. 读取无答案合并 PDF 的 OCR 产物，生成按页、题号、图引用和答案隔离的数据包；
3. 输出四节学习顺序、必听课程、知识点/例题/类型题/A-B-C 题号；
4. 初始化 MAIN 状态与奖励账本。

## 硬规则

- `coverage`、`mastery`、`unlock`、`exposure` 分开保存；积分奖励仅保留为旧状态机兼容能力，不参与当前学习流程验收。
- 听完课、猜中、看答案、提示后答对都不会给独立完成奖励。
- `FULL_PASS` 必须有独立过程；`U5` 必须是未污染近迁移；`U6` 必须是到期后的冷重做。
- 原题 `FULL_PASS` 与近变式 `near_transfer` 必须是两个独立事件和两个题目 ID；同一次作答不能同时刷两档奖励。
- OCR 题号、公式、图片、答案分离任一失败，题包不能标记 `VERIFIED`。
- 页面图像没有视觉侧车时，DeepSeek 只能看到 `READY_TEXT_ONLY`，不得假称完全看懂图形。
- 对话参考只允许数学项目中的 `8.5` 与 `8.5课程`。用户提供的 `C:\Users\poyi\Downloads\数学_-_8.5.md` 是 `8.5` 的完整导出，提供从一本通倒推课程和按课程逐批做题的原始路线；`8.5课程` 提供实际听课交互、纠错和掌握判定规则。`scripts/browser_collect.py` 只读核对这两个精确标题，不采集其他相似对话。
- OCR 唯一入口是项目已配置的 PaddleOCR AI Studio API。当前 fresh live 证据在 `data/ocr_live_current_evidence.json`；构建和验收都要求 `active_provider=paddle_ai_studio` 且 `active_provider_live_verified=true`。
- 第一章按书上编号共有 124 个学习题项：58 道教学例题、16 道无答案直接变式、50 道 A/B/C 习题。`50` 只表示末尾习题，不是整章题量。
- `data/packets/*/learning_packet.json` 按“知识页 -> 完整例题教学 -> 隐藏解答的直接变式 -> 无答案 A/B/C 习题”分层；独立作答阶段不得重新读取例题解法。
- 答案册已独立核验：全五章 546/546 道 A/B/C 习题绑定原书 PDF、页码、页面图与 OCR 哈希；473 道可自动使用，73 道低置信文本或原页视觉证据必须复核。答案内容只能进入 `answer_sidecar.json` 和冻结后的评估侧，不能进入学生或人格上下文。
- `simulate-five` 运行 5 个零基础学生代理的当前工件预检；1.1 的代际证据入口是 `reports/zero_base_cycles/1.1-current-agent-simulation.json`。旧 `zero_base_agent_simulation.json`、旧五轮汇总和旧教师判卷只能作为历史存在性记录，不能回退覆盖当前结论。每个当前代题项都必须有 `item_results`、课程调用、第一行/第二行/继续动作/独立自检、首断点、提示等级和源哈希；代理不能假装观看过视频，且代理模拟不等于真人观察。
- `scripts/deep_simulate_all_sections.py` 是当前全书路线审计入口：冻结前只读取白名单化学生题包和无答案路线，冻结后才加载教师解析/答案证据；输出叫 `route_assessments`，没有最终答案时固定为 `mathematical_correctness=not_evaluated_no_final_answer`。
- 整章的 1.2+1.3、1.4、micro专题1 另有 86 个学习项门禁：`scripts/merge_chapter_zero_base_simulations.py` 只接受当前 context 哈希、完整 packet 闭包、DeepSeek worker 合同和无答案边界；`reports/zero_base_cycles/chapter1-current-simulation-status.json` 是三节当前证据状态账本。`chapter_probe` 只证明上下文可消费，不证明逐题模拟或掌握。
- `scripts/run_deepseek_http_probe.py` 通过本机 10100 Chat Completions 独立消费 1.1 学生上下文；它要求 DeepSeek 回显 14 道题、课程、知识点、类型题和 A/B/C 顺序，并由 `verify_worker_understanding` 做上下文哈希、canary、逐题和答案泄漏校验。`scripts/deepseek/chapter_probe.py` 另对四节逐节真实 dispatch，当前 4/4 gate、4/4 consumption 通过；两者都证明独立路由消费能力，不替代学生 mastery。
- `data/real_user_observations.json` 是五名真实零基础用户观察的空契约；代理轨迹不能填充它。实际观察必须记录听课、逐题作答、知识点复述和冷复测证据。

## 目录

- `chapter1_manifest.json`：第一章四节和课程映射的权威静态清单。
- `ybt_learning/packet.py`：OCR 页包、题号、公式、图片和答案隔离。
- `ybt_learning/isolated_simulation.py`：1,209 项题干投影、冻结尝试、路线评估、版本化运行和持续代理快照。
- `ybt_learning/state.py`：MAIN/COURSE_LOCAL、状态迁移、幂等合并、奖励和复测。
- `ybt_learning/catalog.py`：Downloads 视频/字幕清单和按节课程计划。
- `ybt_learning/coverage.py`：50 道题的课程直接覆盖、方法桥接、视觉状态和阻断原因账本。
- `data/bridge_micro_lessons.json`：13 个桥接微单元；原书方法证据与无答案补充专项课分开标记，均不携带答案。
- `data/packets/*/student_learning_items.json`：例题和直属变式的无答案题面投影；只保留题面、编号、方法角色和视觉侧车，不含 `teaching_text`、解法或答案字段。
- `reports/deep_simulation/student-question-isolation.json`：全书 learner 题干 SHA 与污染门禁；非 1,209/1,209 通过时禁止发布路线审计。
- `data/contexts/*.json`：DeepSeek 独立作答上下文；绑定同节 `learning_packet.json` 的路线和 `student_learning_items.json` 的完整题面，先完成教学和直接变式阶段，只有 `VERIFIED` 才能进入 A/B/C 独立做题。
- `scripts/generate_acceptance_report.py`：从当前 CLI、题包、浏览器、奖励和当前代模拟生成 UTF-8 验收报告，不复用旧数量或旧 5/5 结论；报告会校验当前模拟的 generation、worker 契约、逐题闭合、答案隔离和源文件哈希。当前运行 sidecar 为 `reports/runtime-evidence-sidecar-current.json`，旧 `runtime-evidence-sidecar.json` 仅作 superseded 历史快照。
- `data/`：运行产物，不提交凭据或浏览器 profile。

视觉侧车必须使用 `vision.py` 生成的结构化结果；旧版空 caption、围栏原文、模板置信度和 429 结果均不会放行。当前主册无答案 PDF 的源图探针已覆盖 5 个关键图形，四节构建为 50/50 可消费（31 `VISION_VERIFIED` + 19 `READY_TEXT_ONLY`）；仍以当前 `build-chapter1`、`verify-packet` 和实时视觉门禁为准，不能把视觉覆盖扩大解释为学生 mastery。doc_57 的 4/π、3/π 已用源图 E1 证据在派生题包层修正为 4/5、3/5，原始 OCR 保留不覆盖。
