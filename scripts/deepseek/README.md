# 第一章全章 DeepSeek 独立消费探针

本目录只包含全章探针的新文件，不修改仓库其它文件。

## 为什么需要它

scripts/run_deepseek_http_probe.py 只探 1.1 一节（context 路径硬编码）。
全章探针把同一套门禁与理解校验推广到第一章四个批次，但门禁不降级：
只有通过 validate_context 的节才会派发 HTTP；被拦下的节只记录缺口。

## 四条设计约束

1. 不泄露答案：发给模型的投影只含 qid / 组 / 题号 / 前80字符题面 /
   视觉状态 / 图片数，以及课程、知识点、类型题、A/B/C 顺序等路由元数据；
   不含页 OCR 全文、答案侧车和任何答案字段。发送前还会做一次防泄漏扫描。
2. 逐题绑定：模型必须回显 context_sha256、canary、probe_tokens，
   并逐题回显 question_key / group / number / question_text_prefix /
   visual_status，全部由 verify_worker_understanding 校验。
3. 课程/知识点/类型题/A-B-C 顺序：understanding_summary 必须返回
   must_listen_course_keys、knowledge_point_ids、type_training（有序）、
   exercise_order（A/B/C 分组有序）、expected_groups，且
   mastery_not_assessed=true。
4. 不扩大 1.1 结果：汇总 chapter_consumption_ready 只有在四个节全部
   通过时才为 true；任一节被门禁拦截都会让全章状态保持 blocked。

## 运行

    python scripts/deepseek/chapter_probe.py

输出到 scripts/deepseek/out/：

- chapter_probe_latest.json：固定路径聚合报告（含每节 gate / transport /
  verification / 缺口明细）
- chapter_probe_<utc>.json：时间戳副本
- raw_<section>.json：实际派发节的原始 HTTP 响应

退出码 0 表示全章可消费，1 表示存在缺口。

## 与 1.1 探针的关系

全章探针直接复用 run_deepseek_http_probe.py 的 PROMPT、请求、解析、归一化
与 ybt_learning/deepseek_context.py 的 validate_context /
verify_worker_understanding，行为与单节探针完全一致，只是逐节编排并做
聚合汇总。1.1 通过只代表 1.1 一节可消费。
