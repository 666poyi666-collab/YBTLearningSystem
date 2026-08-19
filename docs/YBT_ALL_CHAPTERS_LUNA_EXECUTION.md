# 《一本通》第 1-5 章 Luna Max 并行执行与验收文档

> 历史执行方案：本文记录 2026-08-17 的五章并行构建方式，不再是当前产品合同。自 2026-08-18 起，活动范围收敛到第一章和第二章；五人格仅作为内部路线压力测试，章节主模拟改为持续成长的 `primary-user-proxy`。当前需求以 [PRODUCT-REQUIREMENTS.md](PRODUCT-REQUIREMENTS.md) 为准，工程规则以 [PROJECT-STANDARDS.md](PROJECT-STANDARDS.md) 为准。

## 1. 目标

以下内容保留用于解释历史工件，不授权继续生成第三至第五章新交付。

为现有《一本通》第 1-5 章全部 38 节建立最终可用的零基础高效学习路径。每节必须从真实教材版面和允许课程出发，按“知识点 -> 右侧例题 -> 直属变式 -> 类型题 -> A/B/C”推进；每个编号学习项都要明确听哪门课、如何识别、第一行怎么写、后面怎么继续、容易卡在哪里、如何纠错和如何独立自检。

本工程不是一次性生成报告。每节要经过 5 轮、每轮 5 个零基础人格的逐题代理模拟；任何题出现方法入口、首行、继续动作或自检缺口，就修订路线并在下一轮重测。

## 2. 当前权威基线

- 项目：`C:\开发\小工具\一本通学习系统_v7`
- 总需求：`REQ-20260817-YBT-ALL-CHAPTERS-001`
- 总任务：`TASK-20260817-YBT-ALL-CHAPTERS-001`
- 章节：5
- 分节：38
- 教学例题：379
- 直属变式：284
- A/B/C 习题：546
- 编号学习项总数：1,209
- 允许课程：170 门，必须以当前课程目录和哈希为准

旧报告中的 1,210 已失效。2.3 中同一直属变式的 OCR 重复已经源页核对并去重，当前权威总数是 1,209。

## 3. 用户要求的硬边界

允许来源：

- `C:\Users\poyi\Downloads\课程合集` 下的 8 个指定课程目录。
- 数学 `8.5` 与 `8.5课程` 仅作为需求和课程映射证据。
- 真实《一本通》教材。
- PaddleOCR AI Studio 当前 OCR。
- 当前图片 SHA 绑定的 E1/E2 视觉侧车。

禁止来源：

- 老人版课程。
- `8.5g`。
- 数学摄像头。
- 相邻项目、旧聊天的完成声明和未绑定当前哈希的旧结果。
- 学生上下文中的答案册、答案侧车、目标题完整解答和正确选项。

## 4. Skill

所有 Luna 任务必须先读取并遵守：

- `C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\SKILL.md`
- `C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\references\workflow-contract.md`
- `C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\references\output-schema.md`
- `C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\references\simulation-gates.md`

机器校验器：

`C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py`

## 5. 模型与任务方式

- 不调用子智能体。
- 使用 10 个独立 Codex 任务。
- 每个任务固定 `gpt-5.6-luna`。
- 每个任务固定 `reasoning_effort=max`。
- 每个任务使用 Codex 保存项目“`小工具`”的本地环境。
- 每个任务只写 `reports/luna_sections/<task-id>/`。
- 共享 manifests、OCR、packets、course catalog、视觉侧车和构建脚本只有主控能改。

官方模型能力基线：GPT-5.6 Luna 支持 `max` 推理，105 万上下文，最大输入约 92.2 万，最大输出 12.8 万。任务仍需控制上下文，只读取当前分片必需文件。

## 6. 10 路均衡分工

| 任务 | 分节 | 学习项 |
|---|---|---:|
| LUNA-YBT-01 | 4.1、ch3.s7、5.1、micro专题1 | 126 |
| LUNA-YBT-02 | 5.6、2.1、ch3.s9、4.7 | 125 |
| LUNA-YBT-03 | 5.3、5.4、5.5、ch3.s10 | 123 |
| LUNA-YBT-04 | 2.6、4.4、ch3.s8、4.8 | 126 |
| LUNA-YBT-05 | 2.3、1.1、ch3.s6、ch3.s11 | 122 |
| LUNA-YBT-06 | ch3.s1、1.4、ch3.s3、4.6 | 121 |
| LUNA-YBT-07 | 4.3、ch3.s4、2.4、ch3.s12 | 121 |
| LUNA-YBT-08 | ch3.s2、2.7、5.2、ch3.s13 | 121 |
| LUNA-YBT-09 | 4.2、2.2、1.2+1.3 | 112 |
| LUNA-YBT-10 | ch3.s5、2.5、4.5 | 112 |

合计：38 节、1,209 项。任何任务不得自行交换、增加或放弃分节。

## 7. 开工门

新任务启动后先读 Skill 和本文档，但在下面文件出现且 `status=ready` 前不得开始生成最终路线：

`reports/luna_dispatch/READY.json`

READY 必须绑定：

- 全书题包构建报告 SHA。
- 课程目录 SHA。
- 全书视觉侧车 SHA。
- 38 节 packet 与 learning packet SHA。
- 1,209 项计数。
- 视觉库存为 0 个未绑定项。
- 4 个公式定界异常已经消失。

等待 READY 时不得修改共享文件。可以先完整读取 Skill、确认分工、创建自己的输出目录骨架。

## 8. 每节执行流程

1. 校验 READY 和当前分节 SHA。
2. 逐页理解教材布局，不只看 manifest 摘要。
3. 双向核对题号与题项，确保不缺、不重、不串节。
4. 阅读实际课程转写，验证课程真的教授了该方法。
5. 输出开头总览：先听哪门课，后听哪些新课，完成哪些教材题号。
6. 按教材循环排：知识点、右侧例题、直属变式、类型题、A/B/C。
7. 每题写七项学习方法，不复制题面，不泄露答案。
8. 运行五轮、每轮五人格的逐题无答案代理模拟。
9. 对失败项修路线、升版本、下一轮全量回归。
10. 生成 JSON、Markdown、HTML、证据文档并运行机器校验。

## 9. 每题必须有的内容

- 精确课程调用。
- 识别入口。
- 方法模型。
- 第一行书写模板。
- 继续动作。
- 零基础常见卡点。
- 最小纠错提示。
- 独立自检。
- 图形依赖与视觉状态。

“套公式”“结合课程思考”“按定义做”这类泛化句子不能单独作为方法。相邻题目如果题型不同，入口、首行和自检必须能区分。

## 10. 五轮模拟

每节固定五个人格：字面型、识别弱、代数弱、视觉弱、自检弱。每轮五个人格都要覆盖本节全部题项，因此每题最终必须有 25 条当前路线版本绑定的尝试记录。

五轮用途：

1. 基线入口。
2. 前置与入口修复。
3. 继续动作与变式迁移。
4. 混合检索与方法竞争。
5. 新鲜无答案上下文的冷启动代理复测。

第五轮是代理冷启动，不是真人 24 小时冷测。真人掌握和 24 小时冷测必须保持 `not_run`。

## 11. 输出

每个任务只写：

```text
reports/luna_sections/<task-id>/
  delivery.json
  learning_path_without_questions.md
  learning_path_without_questions.html
  evidence.md
  shared_defects.json   # 发现共享源问题时才有
```

JSON 保留内部 ID 用于核账。Markdown/HTML 不显示 `K1`、`LI...`、`Q-...` 等内部 ID，不复制题目正文和答案。

## 12. 主控最终合并

主控在 10 个任务全部结束后：

1. 逐个运行 Skill 校验器。
2. 检查 38 节和 1,209 项集合完全相等。
3. 重新按全书顺序排列分节。
4. 做课程全局首次出现去重；循环内继续保留课程调用。
5. 独立检查方法内容是否过度模板化。
6. 独立复查题号、来源、视觉、答案隔离、UTF-8 和 LaTeX。
7. 在桌面与窄屏检查 HTML。
8. 失败项退回原 Luna 任务修订，不由主控静默粉饰。
9. 生成全书 Markdown、HTML、机器报告和状态汇总。

## 13. 状态裁决

- `passed`：当前哈希对应的机器门已运行并通过。
- `failed`：门已运行且发现问题。
- `blocked`：缺源、缺图、缺权限或依赖不可用。
- `not_run`：要求的动作没有执行。
- `unknown`：证据缺失或无法解释。
- `stale`：结果不属于当前源/路线哈希。

任何任务的“我完成了”都不是总验收。全书只有在 10 份交付、主控独立核验和页面检查都通过后才能进入代理工程验收；真人与 24 小时验收仍按真实状态报告。
