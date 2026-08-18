# LUNA-CH12-02 源与覆盖证据

状态：进行中。该目录只属于 LUNA-CH12-02；本次恢复不继承上次 503 的任何内容进度。

## 任务与合同

- task_id：LUNA-CH12-02
- 唯一章节：1.2+1.3
- expected_items：33
- 模型合同：combo/protect-luna，max
- Skill：ybt-luna-section-delivery-v2
- 写目录：reports/ch12_luna_sections/LUNA-CH12-02
- assignment：reports/ch12_luna_dispatch/assignments.json，SHA-256 6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc
- 当前 skill_contract_sha256：08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0

## 源快照

| 文件 | SHA-256 | 用途 |
|---|---|---|
| reports/luna_dispatch/READY.json | f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267 | READY 门禁，status=ready |
| reports/all_chapters/packet-build-current.json | 848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884 | 全书包构建与本节计数 |
| data/all_chapters_course_catalog.json | fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048 | 课程键、中文名、真实 mp4、转写 |
| chapter1_manifest.json | d4f276a026ddfd35d69795ed5c589cdbf8f3f8e98ad3fe73ef814d672a1541c5 | 章节布局、桥接和来源边界 |
| data/packets/1.2_1.3/manifest.json | 1f1a721e41b6af472cb0b269d35f64eae9334d937a33e85788bc5521b60a846d | packet=VERIFIED、learning=VERIFIED |
| data/packets/1.2_1.3/packet.json | 15dd99d3510126ef76222287c4230034b39162c08a9991ce08fcec9317692693 | 结构包 |
| data/packets/1.2_1.3/learning_packet.json | 784cdb8e77a3b23a22c26a0cb37d85a8f9ec576f82e5f2aeb8b8062029b00f9f | canonical、课程映射、视觉绑定 |
| data/packets/1.2_1.3/student_packet.json | 60310a0b0ff1ac02afb9c26958000a86660c3faca697ef1e9849f281cdeb46f0 | 仅核对学生包结构；不读取答案册 |
| data/packets/1.2_1.3/student_learning_items.json | b53b34bbbcb0203188af46c4b4258477a808ed07ad754149e6c4f024f8044bd5 | 学习者条目结构 |
| data/vision_sidecar_all_chapters.json | ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc | 只作旧 sidecar 定位索引，不作当前 Luna 证据 |
| 当前 Skill 合同绑定 | 08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0 | assignment 当前 source binding |

课程转写和真实视频均来自允许目录 Downloads/课程合集/3.1 空间向量与立体几何，本节使用的 catalog key 为：

- space_vector_ops：空间向量的运算；
- decomposition：空间向量拆分法；
- equal_surface：空间向量等值面法；
- coordinate_system：空间直角坐标系；
- coordinate_ops：空间向量运算的坐标表示。

原始 OCR 页范围为 doc_18.md 至 doc_32.md，来自 data/ocr_live_current/first_chapter_69。答案册 OCR、老人版、8.5g、数学摄像头均未进入学习者上下文。

## Canonical 双向覆盖

packet -> delivery 的目标键（按教材例题、直属变式、A/B/C 顺序）：

1. 例1 LI:fcfa77372aee59c2
2. 例2 LI:cfccea517f624ccf
3. 例3 LI:9069871239ce9982
4. 例4 LI:ced7480896c3ecc3
5. 例5 LI:85160af783cfe7ee
6. 例6 LI:8398d10a7994f7f5
7. 例7 LI:1a9c42257c66649e
8. 例8 LI:c77cbbb7b8837fc7
9. 例9 LI:a463b65df011512d
10. 例10 LI:0cc4d4ebec2bcaeb
11. 例11 LI:94d4c82f6d2171e2
12. 例12 LI:590da6bc5e5f4e4b
13. 例13 LI:57b57c8f53fc2c69
14. 例5直属变式 LI:cf037999c56eca66
15. 例10直属变式1 LI:bcfdff63c5c01bf4
16. 例10直属变式2 LI:d085ad01a858870d
17. 例12直属变式 LI:0b28bb0d2da57497
18. A1 Q:Q-6ed7e46c02ea0cbe
19. A2 Q:Q-9dc59a76b39b51c2
20. A3 Q:Q-8937bea007e341dc
21. A4 Q:Q-e3eea135920d1de5
22. B5 Q:Q-ca47ddb3109b2aa7
23. B6 Q:Q-a0ac3d3dec067140
24. B7 Q:Q-c0fa068ea13aa8b0
25. B8 Q:Q-491d3349a231a63f
26. B9 Q:Q-0e25875e8ce0e2b0
27. B10 Q:Q-4cc4fab641617085
28. B11 Q:Q-bba50604ebcccacf
29. B12 Q:Q-16e242b54c60a9aa
30. B13 Q:Q-3b98ee5668cad691
31. C14 Q:Q-8bc83f44a0a18ca0
32. C15 Q:Q-3e85a8a45c48effa
33. C16 Q:Q-9e0354161f002565

双向清点初始结果：worked_examples=13、direct_variants=4、abc_exercises=16、total=33；重复=0、缺失=0、越界=0。路线循环为 10 个，保持“知识点 → 紧邻例题 → 直属变式 → 类型题 → A/B/C → 循环验收”。

## 门状态（初始）

- source snapshot：passed
- canonical coverage：passed
- PaddleOCR 全页读取：not_run
- 当前 Luna 原图能力探针：not_run
- 逐图 Luna/Paddle 交叉：not_run
- five-round-five-persona-v2：not_run
- answer-free Markdown/HTML：not_run
- strict validator：not_run
- independent_acceptance：not_run
- human_acceptance：not_run
- cold_24h_retest：not_run

视觉阻塞证据：本运行暴露工具只有 view_image；调用绑定原图时返回 “view_image is not allowed because you do not support image inputs”。因此未把旧 GLM sidecar（model=glm-4.6v-flash）升级或冒充为当前 Luna 观察。依合同，视觉状态只能保持 blocked，不能写成 passed。

## 已运行命令

- Get-FileHash -Algorithm SHA256：源快照与包文件哈希核对。
- PowerShell JSON 解析：assignment、READY、chapter1 manifest、packet、learning_packet、student 包和课程 catalog。
- validate_section_delivery.py --assignment-only：当前任务分配校验 passed。

后续命令和结果在本文件末尾追加；不写共享源、READY、packet-build、课程目录、转写、manifest、packets、OCR、Skill 或其他任务目录。

## 最终执行结果

- 当前 assignments：重新读取，status=ready；文件 SHA-256 为 6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc。
- 当前 OCR/视觉合同：已重新读取；透明回退证据模式为 paddle_glm_crosscheck。
- 官方回退命令第一次执行结果：failed，原因是 build_paddle_glm_crosscheck.py 只读取 exercise.source_docs，而本包 exercise 使用 source_anchor.ocr_doc；未修改共享脚本。
- 兼容执行：任务目录临时包装向临时 packet 副本补入已有 OCR doc 编号，再调用官方 build_paddle_glm_crosscheck.py；输出 7 条记录，完成后已删除包装和 staging。
- ocr_vision_crosscheck.json：SHA-256 2fec95c3e6bcbec4a56503204b3989184ab0050281819a1c27631b7e80451097；mode=paddle_glm_crosscheck；luna_status=blocked；luna_blocker 原文为 image content omitted because current luna_worker host does not support image input；paddle_status=passed；visual_status=passed；visual_model=glm-4.6v-flash。
- 视觉覆盖：7 张绑定原图，当前 image SHA 与 READY-bound GLM row 一一对应；不声称 Luna 读图。
- canonical 覆盖：worked_examples=13、direct_variants=4、abc_exercises=16、total=33；重复=0、缺失=0、越界=0。
- 路线：10 个循环，final_route_hash=fb0492056610736237e76c5f8aa588dda539b71ed0c537f1ae487f562495a060。
- five-round-five-persona-v2：5 轮、每轮 5 人格、每人格 33 项；每项 25 条，合计 825 条；simulation=passed；unresolved_item_keys=[]。
- delivery.json：SHA-256 05df0aeaf3294cf9d2a218992145f63020d49060241dd82328caf12c4b4256ac。
- learning_path_without_questions.md：SHA-256 099215aaca4045d3552ada265071910b071906beb74a006093a921af10c69025。
- learning_path_without_questions.html：SHA-256 98d85d71fdc768e115e9d23c62ba7690bb9d246241e94bf09a1851b2f4e0dc88。
- shared_defects.json：SHA-256 f91472e6616f832475a502c11d9cb2a578f5713bc4678b1551076cecbac7b1d3；记录 C15/C16 课程缺口和 fallback builder 字段缺陷。

## 最终门状态

- proxy_simulation：passed
- independent_acceptance：not_run
- human_acceptance：not_run
- cold_24h_retest：not_run
- strict validator：passed，status=passed，errors=[]
- 真实未闭合项：当前 luna_worker 宿主不支持图像输入，Luna 视觉能力保持 blocked；视觉通过的是透明 GLM/Paddle fallback，不是 Luna 读图。C15/C16 没有专门现成视频，路线以显式桥接补足，未宣称专门课程覆盖。
