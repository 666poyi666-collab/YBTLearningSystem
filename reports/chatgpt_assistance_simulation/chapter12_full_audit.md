# 第一、二章 ChatGPT 完整资料核验

## 本地哈希审计

- 节次：11/11
- 教材项目：401/401
- 题面内容：`all_question_content_complete=true`
- 课程转写：`all_teacher_transcripts_ready=true`
- 课程目录与转写：170/170
- 第一章：15 门课程、124 项、`not_started`
- 第二章：22 门课程、277 项、`not_started`

## Edge 中 ChatGPT 项目复核

项目：数学选择性必修一

ChatGPT 通过 `@GitHub` 重新读取提交 `ec04712` 后确认：

1. `data/chatgpt_context/chapter12_complete_audit.json` 的 summary 与本地审计一致。
2. `data/learner_progress/chapter1.json` 和 `data/learner_progress/chapter2.json` 均存在，课程数、项目数和未开始状态一致。
3. 例题与直属变式从对应节次的 `student_learning_items.json` 读取。
4. A/B/C 练习从对应节次的 `student_packet.json` 读取。
5. 教师讲解必须读取绑定 `course_refs` 对应的 `data/course_transcripts/*.json` 的 `full_text`，采用网课老师的定义、术语、识别方式和方法顺序。
6. 浏览器实时进度不自动同步 GitHub，必须使用网页“复制进度”快照。

## 结论

第一、二章的静态教材、题面、循环、课程映射和课程转写已经完整可读取。真实用户和持续学习者的学习状态仍是未开始，这是进度状态，不是资料缺失。

