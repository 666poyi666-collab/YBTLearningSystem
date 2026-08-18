# LUNA-CH12-01 阶段证据

## 任务边界

- `task_id`: `LUNA-CH12-01`
- 唯一章节：`1.1`
- 唯一写入目录：`reports/ch12_luna_sections/LUNA-CH12-01/`
- 允许来源：当前 READY、packet-build、课程目录/转写、1.1 manifest/packet/learning_packet/student items、当前 PaddleOCR 原始产物、原始图片和现有视觉索引。
- 禁止来源：老人版课程、`8.5g`、数学摄像头、答案册进入学习者上下文、旧 `reports/luna_sections` 交付物。

## 已核对覆盖

- Canonical 覆盖：`38/38`
- 教学例题：`16`
- 直属变式：`8`
- A/B/C 习题：`14`
- 学习循环：`10`
- 当前绑定原图：`23` 张；当前 luna_worker 图像输入能力为 `blocked`，视觉门由 exact-SHA GLM/Paddle fallback 覆盖 `23/23`
- 当前阶段状态：`completed`
- 五轮五人格模拟：`passed`（5 轮 × 5 人格，38 项/轮）
- 严格 validator：`passed`

## 源哈希

| 来源 | SHA-256 |
|---|---|
| `reports/luna_dispatch/READY.json` | `f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267` |
| `reports/all_chapters/packet-build-current.json` | `848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884` |
| `data/all_chapters_course_catalog.json` | `fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048` |
| `data/vision_sidecar_all_chapters.json` | `ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc` |
| assignment `reports/ch12_luna_dispatch/assignments.json` | `6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc` |
| assignment `skill_contract_sha256` | `08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0` |
| `data/packets/1.1/packet.json` | `4564da9a6081b033188a418d480cef3532b9aa0ed0c56a01f66042229e22df54` |
| `data/packets/1.1/learning_packet.json` | `416990cafa7fabe30dc1c4e04712da47d8ab80ae19e5d6f26b72a46c0814e053` |
| `data/packets/1.1/student_packet.json` | `e4d8a88105b9bc15fbcffa727fe86f217e687f10eb2102e0943f48d9d93bc478` |
| `data/packets/1.1/student_learning_items.json` | `22c1650492b87ff05f6bfabc81875f2f9cdcccb757a30e0cf0bacd87aed38bb` |
| 母版 `data/packets/1.1/learning_path_without_questions.md` | `5a312c1e1760eed1fedc168c5b7a8f4274aa94bf3f5396c46b6bc294c75006e0` |

## Luna 能力探针与证据撤销

- 原图：`data/ocr_live_current/first_chapter_69/imgs/img_in_image_box_781_502_1031_635.jpg`
- 原图 SHA-256：`a2f2e0cccfa97a90474037c4cb6fd3b66287e7d25da041ef13ba2882d4b4f3dd`
- runtime model：`combo/protect-luna`；reasoning effort：`max`
- 当前实际 payload 结果：`image content omitted because current luna_worker host does not support image input`
- 当前探针状态：`blocked`
- 撤销：先前“当前 Luna 已读取首图/23 图”的观察和完成声明不再作为证据；旧 `ocr_vision_crosscheck.json` 已被覆盖。
- 有效视觉证据：READY 绑定的 `glm-4.6v-flash` sidecar（精确原图 SHA）与 PaddleOCR artifact；GLM 证据没有被重命名为 Luna。

## 当前桥接状态

| 目标 | 当前状态 | 事实边界 |
|---|---|---|
| B6 | `passed` | Round1 保留同起点/双垂棱首断点；Round2 五人格完成无题面自造变式、不同垂足平移和三段长度拆分；Round3-5 独立回放、混合检索、fresh 冷启动均通过。 |
| B7 | `passed` | Round1 保留二面角定义首断点；Round2 五人格完成公共棱、同起点、双垂棱、平移和三段长度检查；Round3-5 均无失败。 |
| C14 | `passed` | Round1 首断点为正数条件/平方非负/等号条件/定义域链；Round2 单独失败并做字段级 repair；Round3 完成自造变式、定义域回代、仿射求交和外接球三点等距回代；Round4-5 复测通过。 |

## 23 张绑定原图清单

| 标签 | 文件 | SHA-256 |
|---|---|---|
| 例1 | `img_in_image_box_781_502_1031_635.jpg` | `a2f2e0cccfa97a90474037c4cb6fd3b66287e7d25da041ef13ba2882d4b4f3dd` |
| 例2 | `img_in_image_box_802_1336_1011_1523.jpg` | `6043d5ccdac6e70e0d3de9d1940a95a503b20b3b199a9ed9113489b71c8f113a` |
| 例3 | `img_in_image_box_816_349_993_519.jpg` | `fcdd7ead1de7583f4cce54172b2d6c208d44bb949e9ccac252520935b9d50028` |
| 例6 | `img_in_image_box_809_559_1001_729.jpg` | `4e5a7c0577e0cdbb3caf2b7c2b6a532aed19857b39024f03026935db4a5bba8b` |
| 例8 | `img_in_image_box_789_811_1022_1023.jpg` | `9ebd9874afe31841d8699bd1388b22dae4bdf540180ac6ceadb6bd6d68f0cd27` |
| 例10 | `img_in_image_box_867_654_1095_827.jpg` | `36c6b8ee04859ded84ecb7b64c1722292666d0fa9c8483e5fe88d26c1d5de410` |
| 变式1（例11） | `img_in_image_box_893_538_1093_717.jpg` | `94bb04ba343c34a178938d4696b65f86adb217b5d15add33c27731937eb182e2` |
| 变式2（例11） | `img_in_image_box_892_152_1091_339.jpg` | `356bf8323401605c72e27196b5be610e7e0207d8b8fe491ede592e566c145e8a` |
| 变式（例12） | `img_in_image_box_879_813_1092_1011.jpg` | `405b4cc7cf92a5788a01c97b9ae49565e26ec75a80248208ae7829441b29243e` |
| 变式（例13） | `img_in_image_box_878_574_1093_765.jpg` | `f18572579918966cd43c5ebaf6a597b85d7a008750f32f262fc560182a9d81ac` |
| 变式（例13） | `img_in_image_box_913_257_1092_430.jpg` | `c85f7a603b6d40a9e87e731cd9fc26791af405ecc181c3afe77cb9aea38903e4` |
| 变式1（例15） | `img_in_image_box_895_1378_1092_1572.jpg` | `74481391380a97c010ee10927944da755caa88bf3145272b6cc624352d7278b2` |
| A1 | `img_in_image_box_523_429_694_610.jpg` | `626f9e0d2a7887db60b76f9e4b0b4005cab06f0a447ad99c4c527e40c934f172` |
| A3 | `img_in_image_box_889_1344_1094_1537.jpg` | `9cf1457acd4a93d3d4932b8949bbd20a150970937ad30d4466abcc216cd8f1e2` |
| B4 | `img_in_image_box_517_434_698_617.jpg` | `1193b7af78de73b5943ddc8a5b4bb6a196c1079eb0338864c2233474a5f7ed6b` |
| B5 | `img_in_image_box_507_887_711_1071.jpg` | `c65e123ed4ba3a4e691b3a4866d5a57665e3977c3b98358294cb4ae38bf83ae8` |
| B6 | `img_in_image_box_488_1402_727_1543.jpg` | `d37b92936256451d69e8763df583b58decccce1e987ec456f091f532d644683b` |
| B7 | `img_in_image_box_506_422_710_542.jpg` | `bb777ec8f59e094b9492bc0b92ee97ed7c9af48374778d90316aab85769b5c69` |
| B9 | `img_in_image_box_871_1191_1093_1374.jpg` | `e868adaf97bb30ca1bcd6782025f5709157101a4672fb9be6cf53a2e31b32535` |
| B10 | `img_in_image_box_901_311_1094_497.jpg` | `ee4659a5666446bfecea10a4360acd2489755ee8aec636bb3d3c90fc7531b5a8` |
| B11 | `img_in_image_box_882_1022_1094_1226.jpg` | `94debed05d9a783cd6593ef8936f5b69fe0a43dcdb8c67e783afb61ff2379b49` |
| B12 | `img_in_image_box_885_322_1095_522.jpg` | `9424fcfe19b54fd07a0adc6e994d1b7916136532b0c9c08de84c6e38b0e79f84` |
| C14 | `img_in_image_box_867_546_1093_782.jpg` | `1fd894ced4cd937898585ff2571001f10fea9b67151aa1ade6ab76b95c3a25eb` |

## 阶段命令记录

- 已完成：只读核对、canonical 双向清点、课程目录/转写映射；当前 Luna 图像能力探针明确阻断。
- 已撤销：此前声称 Luna 实际读取 23 张原图的记录。
- 已完成：运行共享 `build_paddle_glm_crosscheck.py`，其因 A/B/C 项使用 `source_anchor.ocr_doc` 而非 `source_docs` 在 B4 fail-closed；随后使用任务目录临时兼容副本生成 23/23 exact-SHA GLM/Paddle 记录，未修改共享 Skill/packet。
- 已完成：修复 `_build_delivery.py` 的 cycle 6 代理重复映射；delivery 为 38 唯一 key、每 key 25 条实际 item_result。
- 已完成：v2 五轮五人格真实迭代、无题面/无解答 Markdown/HTML 导出、严格 validator。
- 已完成：最终 validator 通过后删除 `_build_delivery.py`、任务本地 `_build_paddle_glm_crosscheck.py` 与 `__pycache__`；输出目录无临时脚本/缓存残留。

## 视觉交叉核验结果

- `ocr_vision_crosscheck.json` schema：`ybt-ocr-vision-crosscheck-v1`
- records：`23`；unique image SHA：`23`
- mode：`paddle_glm_crosscheck`
- Luna capability：`blocked`；blocker：`image content omitted because current luna_worker host does not support image input`
- PaddleOCR：`23/23 passed`；visual provider：`glm-4.6v-flash`，`23/23 passed`；conflicts：`0`
- crosscheck SHA-256：`31c8d27768011ac378a88a13c8a5eb09ca976df313d5b7bd9f406cbc054492a3`
- source binding：assignment SHA `6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc`；vision sidecar SHA `ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc`。

## v2 五轮五人格结果

- protocol：`five-round-five-persona-v2`
- 覆盖：`38/38` canonical、`10` 循环、`23` 绑定原图、`950` 条实际尝试；每个 item key 恰好 `25` 条。
- Round1：B6、B7、C14 保留首断点；3 条分别绑定桥接 repair。
- Round2：B6、B7 五人格以 `passed_after_self_correction` 放行；C14 为唯一失败项，绑定 `continuation_actions`/`independent_self_checks` 字段级 repair。
- Round3：C14 完成无题面自造变式、正数条件→平方非负→等号条件→几何定义域回代、仿射求交和外接球三点等距回代；失败项/repair 均为 0。
- Round4：`mixed_retrieval_answer_free`，失败项/repair 均为 0。
- Round5：`fresh_answer_free` 冷启动，失败项/repair 均为 0；`unresolved_item_keys=[]`。
- final route hash：`df32db252e144cf7f9cc7bac4e8d0867c45909e765339d4246af58e5e0563431`

## 交付与严格验收

- delivery schema：`ybt-luna-section-delivery-v2`
- model contract：`combo/protect-luna`；reasoning effort：`max`；context window：`128000`
- delivery status：`passed`；section status：`passed`；proxy simulation：`passed`
- delivery SHA-256：`a4e4b253f28f1e1ba834fa310d7d6e4b38e7ddabb64c50ada7792434aef2660a`
- Markdown SHA-256：`85a4ede8749f9b1a107e053a9d820e72b59482797f76f30ae187d4c37c48755f`
- HTML SHA-256：`1a52523bff481120524358f4077dba606b32ff6c9f7fdc0410a3e02b395cc2eb`
- 严格命令：`python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-01 --delivery reports\ch12_luna_sections\LUNA-CH12-01\delivery.json`
- validator 结果：`status=passed`，`errors=[]`
- 受保护内容哈希保持不变：items `e2d7c35da8c7b11c271607da4da2ecd160c4e616f8b5339173f70b24c2a661dc`；cycles `8b54edfca9c6bac093e29c29e9d501d04675891d14d0c89ee9172e09621ccbb1`；simulation `53260f3a1fc4a91758edfcf17e8291009797e1271debec9c926952331ee29bc6`。
- shared defects：`shared_defects.json` 记录 fallback builder 对 `source_anchor.ocr_doc` 的兼容缺口及当前 Luna host 图像输入阻断。
