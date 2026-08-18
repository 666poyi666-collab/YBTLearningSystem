# 一本通 v7 真实用户观察协议（Real-User Observation Protocol）

版本：7.3 · 适用：五名真实零基础用户的基线、听课、逐题作答、知识点复述与冷复测证据采集。

## 1. 边界声明（先读）

- 本协议只服务**真实人类观察**。simulation.py 的 10 条代理轨迹、任何把 synthetic proxy 改名为“真实用户”的做法、任何凭空生成的 participant_id，一律不得进入本协议对应的记录存储。
- 观察记录只能证明**观察到的行为**（听了、做了、复述了、重做了），不自动证明掌握。掌握主张必须由主线状态层（state.py 的 FULL_PASS / near_transfer / delayed_recall）依据独立过程另行判定。
- 本协议不携带最终答案：任何事件出现 final_answer / answer_text / solution / answer_content 字段即被拒绝。答案内容只存在于 answer_sidecar.json。
- 记录文件按追加式 JSONL 保存；artifact 只进不出（复制并哈希，不修改原件）。

## 2. 五名用户与五个槽位

| 槽位 | 要求 |
| --- | --- |
| real-user-01 … real-user-05 | 每槽一名真实零基础用户；participant_id 由本人自选（如 同学甲-0814），注册时必须提交 consent artifact（本人手写化名+日期的照片/扫描件），否则拒绝注册 |

一个真人不能占多槽；一个槽位只能注册一次，覆盖即拒绝。

## 3. 可审计证据定义

### 3.1 身份证据
- identity.json：participant_id、注册时间、consent artifact 的 SHA-256。

### 3.2 听课证据（课程顺序第一环）
- 对每节 must_listen_courses 的每个 course_key：course_listened 事件，字段含 course_key、role、batch_id、occurred_at。
- artifact 必须提供：播放器画面/设备屏幕截图（含时间）、转写日志文件、或带时间戳的听课记录照片。事件与 artifact 时间应一致。

### 3.3 逐知识点与例题证据
- 每个知识点：knowledge_point_study 事件（knowledge_point_id 必须属于该节计划），并附学习记录 artifact。
- 每个知识点至少一次右侧例题作答：example_solved 事件（example_labels 必须来自该知识点 examples），并附作答 artifact。
- 每个类型题标签：type_training 事件，并附训练记录 artifact。

### 3.4 逐题作答证据
- 按 exercise_order（A → B → C，题号升序）逐题提交 question_attempt：
  - result ∈ {correct, incorrect, partial, guess}；independent 必须如实标注；
  - 每题必须附 artifact：手写作答照片/扫描件；
  - 视觉题（coverage 中 visual_status=VISION_VERIFIED）：必须附加**当次**图形证据（作答时看到的图截图/照片或该题 packet 图像引用），否则该题证据不完整。
- verify 会机器检查首次作答时间是否遵守 A/B/C 顺序；顺序偏离会记录为可审计事实并导致该槽未通过。

### 3.5 小节完成后的复述与冷复测
- recap：全节最后一题作答之后，进行不看答案的知识点复述；artifact 为录音/录像/照片，事件恒为 answer_free。
- cold_review：至少一题在首次作答 ≥24 小时后冷重做（gap_hours 由 harness 计算），answer_free，附手写重做 artifact。同日重做请用 review 事件，不计入冷复测门槛。

### 3.6 事件顺序
每个槽位先记录一次 `baseline_check`（`baseline_status=zero_base`，附不含答案的抽样证据），再开始第一节。每节事件顺序 = 听课 → 知识点讲解 → 右侧例题 → 类型题 → A/B/C 习题 → 复述 → 冷复测；节序按 1.1 → 1.2+1.3 → 1.4 → micro专题1。五个槽位都必须覆盖这四节，单独记录 1.1、只完成部分章节或只填代理轨迹均不能通过；harness 记录实际 occurred_at，verify 检查注册时间、事件时间、哈希链、跨事件阶段和跨章节顺序。

## 4. 采集与验证命令

    python scripts/real_user_collect.py register --slot real-user-01 --participant-id <本人化名> --consent-artifact <手写化名照片>
    python scripts/real_user_collect.py record --slot real-user-01 --observed-by <本人化名> --section 1.1 --kind baseline_check --baseline-status zero_base --details '{"answer_free":true,"sample_question_keys":["A1","A2"]}' --artifact <基线抽样照片>
    python scripts/real_user_collect.py record --slot real-user-01 --observed-by <本人化名> --section 1.1 --kind course_listened --course-key space_vector_ops --artifact <听课截图>
    python scripts/real_user_collect.py record --slot real-user-01 --observed-by <本人化名> --section 1.1 --kind question_attempt --question-key A1 --result correct --independent --process-verified --artifact <手写作答照片> --visual-evidence <当次图证据>
    python scripts/real_user_collect.py record --slot real-user-01 --observed-by <本人化名> --section 1.1 --kind recap --artifact <复述录音>
    python scripts/real_user_collect.py record --slot real-user-01 --observed-by <本人化名> --section 1.1 --kind cold_review --question-key A1 --result correct --artifact <冷重做照片> --at 2026-08-16T09:00:00+08:00
    python scripts/real_user_collect.py verify --all
    python scripts/real_user_collect.py export
    python scripts/real_user_collect.py self-test

record 的详细字段也可用 --details 一次传入 JSON 对象；--kind 对应的必填字段定义见 data/real_user_schema.json。

## 5. verify 门禁（全部机器检查）

1. 身份：participant_id 非空；consent artifact 存在且 SHA-256 一致。
2. 每节：must_listen 课程全部有 course_listened。
3. 每节：全部知识点有 knowledge_point_study；每知识点至少一个 example_solved；全部类型题标签有 type_training。
4. 每节：exercise_order 内全部题目有 question_attempt；首次作答时间按 A/B/C 升序；视觉题有当次图形证据。
5. 每节：全部作答完成后有 answer_free 的 recap。
6. 每节：至少一题 cold_review，间隔 ≥ 24 小时。
7. 全量事件：无 forbidden 字段；规定事件必须有 artifact，artifact 文件存在且哈希一致；cold_review 的 gap_hours 由 verify 重新计算并核对。
8. 五槽全部通过后 data/real_user_observations.json 的 status 才为 passed；否则保持 not_run / in_progress。

## 6. 与现有层的关系

- 观察存储（本协议，data/real_user_records/）：真人行为证据链。
- 事件采用 `prev_event_hash`/`event_hash` 追加链；篡改、删除、插入或重排事件会被 verify 拒绝。视觉题的 `visual_evidence_present` 只是派生标志，唯一权威是事件中实际存在且哈希一致的 `visual_evidence` artifact。
- 主线状态（ybt_learning/state.py + CLI record-attempt / review-item）：奖励与掌握账本。两者互相独立；观察记录满足后，再由真人/操作者把逐题结果如实录入状态层。
- 模拟矩阵（reports/simulation_matrix_current.json）：合成代理轨迹，与本协议无交集，禁止互相填充。
- 验收报告（reports/final-acceptance.json）读取 data/real_user_observations.json；export 只从真实事件同步该契约文件，报告不会因此误读为真人已通过。
