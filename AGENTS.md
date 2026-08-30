# 一本通学习系统协作说明

## 当前产品范围

- 当前交付范围是选择性必修 1 全五章、38 个 canonical 节次；每节都必须生成教材顺序、课程调用、循环、题目清单和验收动作。
- 第一章第一节是持续回归样板，需要继续吸收真实对话中的课程顺序、语音识别纠错、手写首错定位和最小提示反馈；它不再阻止其他节次并行完成。
- 当前用户表述高于历史报告、旧聊天、生成稿和模型自述。
- 接到某一节后，先读完整教材版面和题包，再判断知识点、右侧例题、类型题、变式与强化训练的真实关系；不得先套固定模板。

## 学习与模拟边界

- 课程“覆盖”表示转写内容足以教授教材项目；课程“学完”必须有对应学习者的消费记录。两者不得混写。
- 五个固定零基础人格是内部路线压力测试，不代表当前用户。
- `primary-user-proxy` 是持续成长的用户模拟智能体。它按教材顺序跨节运行，画像只能由已冻结的作答、卡点、提示和自检证据更新。
- 代理通过、真实用户通过和 24 小时冷复测必须保持为不同状态。
- 默认执行节奏是一节一天；循环是当天的短执行单元，不得把一个循环自动解释为一天。
- 语音转写可能破坏选项、上下标或符号。只有在题面与用户表达均核对后才能记错题；存在歧义时先确认，不得把识别错误写入画像。

## 输出要求

- 机器 JSON 保留逐题、逐尝试和哈希证据。
- 面向用户的 Markdown/HTML 只保留课程顺序、教材结构、共享方法、题目清单、例外提示和验收状态；不得展开压力测试流水账。
- learner-facing 文件不得包含答案、正确选项、内部题目 ID 或实现说明。

## 工程边界

- `ybt_learning/` 是现有核心 Python 实现，`scripts/` 是构建与验收入口。
- `frontend/` 和 `backend/` 记录未来所有权边界；本轮不搬迁现有模块。
- 禁止新增用户目录或旧设备绝对路径。路径应从项目根、参数或显式配置解析。
- 需求、架构、配置、数据模型或输出合同变更时，同步更新 `docs/` 和 `docs/DEVLOG.md`。

## 基础验证

```powershell
python -m unittest discover -s tests -v
python codex-skill/ybt-all-chapters-learning-path/scripts/test_validate_section_delivery.py -v
python codex-skill/ybt-all-chapters-learning-path/scripts/validate_chapter_learning_progress.py --project-root . --progress data/learner_progress/chapter1.json
python codex-skill/ybt-all-chapters-learning-path/scripts/validate_chapter_learning_progress.py --project-root . --progress data/learner_progress/chapter2.json
```
