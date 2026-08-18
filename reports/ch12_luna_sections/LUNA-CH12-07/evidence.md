# LUNA-CH12-07 evidence

状态：passed（任务交付）；独立验收、人类学习、24 小时冷复测均保持 not_run。

## 范围与模型

- task_id：LUNA-CH12-07
- 唯一章节：2.4
- canonical：5 个例题、8 个直属变式、15 个 A/B/C，共 28 项
- 唯一写目录：reports/ch12_luna_sections/LUNA-CH12-07
- 模型合同：combo/protect-luna，max，上下文窗口 1000000
- 未修改共享源、READY、packet-build、课程目录/转写、manifest、packets、OCR、Skill、测试、旧交付或其他任务目录

## 当前绑定

| 文件/绑定 | SHA-256 |
|---|---|
| reports/ch12_luna_dispatch/assignments.json | 6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc |
| reports/luna_dispatch/READY.json | f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267 |
| reports/all_chapters/packet-build-current.json | 848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884 |
| data/all_chapters_course_catalog.json | fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048 |
| data/vision_sidecar_all_chapters.json | ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc |
| data/packets/2.4/packet.json | 321a5615a2276f1615c6cd17c11fdc887f802795f7a8163fa6ede2231d5415cf |
| data/packets/2.4/learning_packet.json | 125536fb080f102be6929f66510152bf9a5baa1585a528c47be79b1e05812209 |
| data/packets/2.4/student_packet.json | 52e1821997faf893dac66d11b8294513501387f2ddf198f7f46b776083d8e60a |
| data/packets/2.4/student_learning_items.json | 522e6afdda18b23ef952002c4e949e97aab503c5ed43f31e153f1acd0deb3643 |
| assignment skill_contract_sha256 | 08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0 |

课程转写已按当前 catalog 绑定并读取：

- 3.2.3.2.a 点线对称（上）.json：3e69e7cdc025cd54579f86ca4fd75f3d4c0fbbc25e2d5ac5e73b58a9222d9c78
- 3.2.3.2.b 点线对称（下）.json：089da60a397500e097a38c1379e0139c632adc4c7bb523afb35cb414752d4096
- 3.2.3.3.a 线线对称（上）.json：49c14b5ce0f923e6f5f0511ac39f02debfeac7dcafcdabfef945e012a694c222
- 3.2.3.3.b 线线对称（下）.json：78bd06387662dc6b02df1e644515efef5164408e3b788572173f9013d44fbeba
- 3.2.3.4 过定点的直线系与曲线系.json：bed2ae00832196b4573532519c10d2989c40101b40f52e778fab98a0d43d5648

2.4 OCR 页 doc_44.md 至 doc_55.md 均已读取；当前页 SHA 依次为：

8aef29e23f04f08318e6ae7456d2e38e4988d09408fb0ed4062b57e736f3b60a，7894a0240add6f21b87258330678a98d8b3b9f421a84ce26fd5b6df075bb16cb，e932706193918e09584ddd9acd6ea2c71b58feb12942bc74547423db7d664b7e，5d55e290a6756357d01cf2e3fa200d14b048df7d18eced766244de50b07866da，ceef12311a865cb933825e01d7aee302376205b83076677272a950dc90edbf03，5b7f5225d9328e6db0645ccaf0c912d332d8dc00d554479cd94e3f6555679181，700c04156eb978dd4ee29cb84f3a5707ad5f11932e7bb9011b1f3947799b34c7，74edc9a0786c1f1930cd9a0ceb39462360f9e62e8a56d6490c906f0687a31fde，b0bbede97282e8e521b4772988a26e2b1a821301a9d8006183908f1d27ef8968，5f7b3f42dfd98ebbc313014a37f3a961b3faa7d3963185a7dc9ed3fdef28af9d，1c50168905c4f49db9e8803b136c20553b13c7ae2ae3d3725d5fac11f249c7bf，b5374f46b12facd80dd766a6b5fa91ba04f52f0a33c726ccb11f10e1fb357b30。

## 视觉回退

当前 luna_worker 宿主的实际 image payload 能力探测失败，未声称 Luna 读图。使用当前 Skill 允许的确定性回退：

mode=paddle_glm_crosscheck；luna_status=blocked；luna_blocker=image content omitted because current luna_worker host does not support image input；paddle_status=passed；visual_status=passed；visual_model=glm-4.6v-flash。

三张绑定图各一条记录，均为当前原图 SHA：

- A4：9e14d20fdf569d4fa2e4930c0395ab37a9f2f89a20433a50a926d3db775c9f4d
- C14：34b11ecd93de016ebba5dadb6c1877a44acb16ea04975031688878ad251b21b2
- C15：54a176aec67f7a8a97fade2edcbf05c30d37dc2044b2c4c537788d0524ad6059

证据文件 ocr_vision_crosscheck.json，SHA-256 0fdec37e2ed718c75fc9ae4cd1d42fb806ba9bde302d8950c0bafb472a5a5bb8。旧 GLM sidecar 仅作 READY-bound 定位和结构化回退来源，未改名为 Luna。

## 路线与覆盖

- 8 个学习循环，顺序为五类知识/例题/直属变式，再到 A、B、C 组。
- 所有 28 个 canonical item 恰好一次：duplicate_items=[]、missing_items=[]、unexpected_items=[]。
- 每项均写入 course refs、中文课程调用对应的实际 mp4 文件名、识别入口、方法模型、符号化首行、继续动作、首断点、最小提示、独立自检和视觉状态。
- learner-facing MD/HTML 不含题面、内部 item key、答案或解题末值。
- route v1：a8e0fed347314f669c780a3ed51c230d138a9f3c0d14367e52b494bdceb25152
- route v2：b06b960f1d10b473294389c12284df096be985705d492b546d86a07b0ba0b32c

## five-round-five-persona-v2

- 5 轮 × 5 persona × 28 项 = 700 条实际 attempt records。
- 每项恰好 25 次，actual_attempts_per_item 全部为 25。
- Round 1：18 个 item 首断点，18 条字段级 repair；失败列表与结果一致。
- Round 2：应用 repair 后全量重跑。
- Round 3：继续与迁移重跑；Round 4：混合检索重跑；Round 5：冷 proxy 重跑。
- Round 5 failed_item_keys=[]，unresolved_item_keys=[]，simulation passed。
- persona 固定为 literal-zero-base、recognition-weak、algebra-weak、visual-weak、self-check-weak；每题均保存 course_call、recognition_statement、first_line_attempt、continuation_attempt、self_check_attempt。

## 命令与结果

1. 直接执行 Skill 指定的 build_paddle_glm_crosscheck.py：failed，错误为 missing PaddleOCR doc: 2.4 34b11ecd93de016ebba5dadb6c1877a44acb16ea04975031688878ad251b21b2。
2. 原因和影响写入 shared_defects.json；未修改共享源。使用一次性隔离输入副本补齐已有 source_anchor.ocr_doc 后，调用未修改的 Skill 脚本生成任务本地三条回退记录；临时生成器随后删除。
3. 生成 delivery.json、learning_path_without_questions.md、learning_path_without_questions.html。
4. 严格 validator：

~~~text
python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-07 --delivery reports\ch12_luna_sections\LUNA-CH12-07\delivery.json
{
  "status": "passed",
  "task_id": "LUNA-CH12-07",
  "errors": []
}
~~~

最终文件 SHA：

- delivery.json：7f703a17b53a670d533d8b71b1fd7b3cf66f3b7132daaff2837441c70d1c9dd8
- learning_path_without_questions.md：9542483b23d958ccfc3c9ef0fe60525007fc86517afdb9464fd8667b5d5470fc
- learning_path_without_questions.html：35abded747e481c19a242ba80d20075d8a4628e2ef866191d2c5e850ef4ff271

真实未闭合项：Luna 图像输入被宿主阻断；共享 fallback 脚本与 2.4 source_anchor.ocr_doc 绑定缺陷仍待主控修复。独立验收、人类学习、24 小时冷复测未运行。
