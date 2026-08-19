# ChatGPT 辅助全流程模拟记录

## 测试范围

- 项目：ChatGPT 项目“数学选择性必修一”
- 仓库：`666poyi666-collab/ybt-learning-system-v7`
- 目标：第一章第一节，循环 1
- 用户画像：持续成长学习者，初始按零基础处理
- 参考对话：8.5 文件未上传；只作为可选交互参考，不影响 GitHub 事实核验

## 实际流程

1. 在 Edge 已登录 ChatGPT 项目中发送带 `@GitHub` 的项目初始化提示词。
2. ChatGPT 读取并核对：`chapter1_manifest.json`、`data/packets/1.1/manifest.json`、`data/packets/1.1/learning_packet.json`、`data/packets/1.1/learning_packet.md`、`data/packets/1.1/student_learning_items.json`、`data/question_coverage.json`、`data/course_catalog.json` 和课程转写。
3. ChatGPT 确认课程 `3.1.1.1`《空间向量的运算》覆盖循环 1。
4. ChatGPT 给出教材顺序：例 1、例 2、例 3、例 9、例 10、A1—A3，并要求先做例 1。
5. 模拟用户提交：只看长度相同的棱，不确定平行是否足够。
6. ChatGPT 判断卡点为概念判断，给出最小提示：相等向量需要长度相等且方向相同；要求用户说明箭头方向。
7. 模拟用户订正：说明长度相等、方向相同，相反向量需要反向。
8. ChatGPT 判断例 1 的概念要求已掌握，但还没有完成全部列举；下一步仍限定为例 1 第（1）问逐条检查。

## 验收结论

- GitHub 仓库读取：通过。
- 当前循环定位：通过。
- 课程与题序：通过。
- 零基础画像启动：通过。
- 卡点分类：通过。
- 最小提示：通过。
- 等待用户尝试再推进：通过。
- 过早给出完整结果：未发生。
- 8.5 项目文件上传：来源页文件选择器未响应，未上传；不阻塞 GitHub 主链路。

