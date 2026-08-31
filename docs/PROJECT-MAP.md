# 项目总览

## 这个产品做什么

本项目把《一本通》选择性必修 1、170 门网课文稿、原书答案、选做必刷题、讲义和真实学习进度组织成一个学习助手。静态学习路线覆盖五章、38 节、1,209 个教材项目；真实用户进度由 Cloudflare 数学 MCP 保存，不能由本地模拟代写。

## 一条学习数据怎样流动

```text
原书/OCR/题图 + 网课全文
        |
        v
chapter1-5_manifest.json       章节、节次、课程、循环和题型清单
        |
        v
data/packets/<节次>/
  student_learning_items.json  例题/变式纯题干
  student_packet.json          A/B/C 纯题干
  learning_packet.json         教师侧完整学习包，含例题解析
  answer_sidecar.json          判卷侧原书答案证据
        |
        +--> 无答案 Markdown/HTML 学习路线
        |
        +--> 题干隔离审计 --> 冻结路线尝试 --> 冻结后路线评估
        |
        +--> Cloudflare R2/D1 --> ChatGPT 数学 MCP
```

关键边界是：学生或模拟人格只能读取两个 `student_*` 题包、无答案路线和课程正文。`learning_packet.json`、原始 `packet.json` 与 `answer_sidecar.json` 只能在作答冻结后由教师/评估侧读取。

## 主要目录

- `chapter1_manifest.json` 至 `chapter5_manifest.json`：五章 canonical 结构与课程/题型映射。
- `data/course_transcripts/`：170 门课的转写正文；课程标题不能替代正文覆盖证据。
- `data/packets/`：38 节学生题包、教师学习包、答案侧车和 learner-facing 路线。
- `data/answer_evidence/`：扫描版答案册的逐页 OCR、页图和 SHA 证据。
- `ybt_learning/`：题包、状态机、视觉、完整性与答案隔离运行层。
- `scripts/`：全书构建、审计、路线导出、题型合并和 Cloud 内容验证入口。
- `codex-skill/ybt-all-chapters-learning-path/`：以后智能体执行同一学习流程时必须遵守的 Skill。
- `cloud/mcp/`：同仓的 Cloudflare Worker、D1/R2 导入器、OAuth 保护和 MCP 工具。
- `reports/`：机器审计、版本化路线运行、真实验收与历史证据；报告不是源数据。

## 三种“进度”不能混在一起

1. 浏览器本地：星标、循环听完、单题通过和疑问，存于页面 `localStorage`。
2. 仓库代理：`primary-user-proxy` 的合成路线证据，只用于找路线缺口。
3. 真实用户云端：D1 中的学习事件、错题、题型、记忆点和当前任务；只有成功 MCP 写入才算同步。

浏览器复制快照或聊天中的一句“完成了”都不会自动成为云端进度。真实用户完成、代理路线可执行和 24 小时冷复测是三个状态。

## 五人格与持续代理

五人格每节运行五轮，共 25 次/项目，用于压力测试字面入口、题型识别、代数边界、图形翻译和自检。它们写的是方法路线，不是最终数学答案，因此输出只能叫“路线评估”。

`primary-user-proxy` 是一个跨节、跨运行保存历史的代理。文稿文件存在或被加载不等于课程学完；没有最终作答和独立判分时，代理学习状态保持 `not_run_no_final_learner_answers`，也不会更新真实用户进度。

## 发布与 current

全书审计写入 `reports/deep_simulation_runs/<run-id>/`。只有以下条件同时满足，才原子更新 `reports/deep_section_simulations/current.json`：

- 38 节、1,209 项恰好覆盖一次；
- learner 题干隔离为 1,209/1,209；
- 每项 25 条冻结尝试，合计 30,225 条且 ID 全局唯一；
- 答案只在冻结后进入路线评估；
- 源题、视觉、题型和课程阻断为空；
- 没有数学正确、代理掌握或真人完成的越权声明。

中途失败的版本目录保留为诊断证据，但不会替换 current。

## ChatGPT 怎样读取

ChatGPT 默认通过远程数学 MCP 读取：当前任务 -> 节次概览 -> 当前无答案题面/题图 -> 绑定课程全文 -> 真实进度。GitHub 是静态事实和审计回退。讲义与必刷题 OCR 只负责定位，公式、图形和完整题面必须看原页图。

原书解法和模型独立解法必须分栏。低置信 OCR 或仅有原页证据时，ChatGPT 要说明需要核页，不能自动判分。

## 常用验收

```powershell
python scripts/audit_student_question_isolation.py
python scripts/build_all_answer_evidence.py --reuse-page-ocr
python scripts/deep_simulate_all_sections.py
python -m unittest discover -s tests -v
```

每次变更的非代码说明记录在 `docs/DEVLOG.md`；仍未解决的限制记录在 `docs/KNOWN-ISSUES.md`。
