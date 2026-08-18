# LUNA-CH12-08 最终阶段证据

## 任务边界

- `task_id`: `LUNA-CH12-08`；唯一章节：`2.5`；预期 canonical：`39`。
- 唯一写入目录：`reports/ch12_luna_sections/LUNA-CH12-08/`。未修改 READY、packet-build、课程目录/转写、manifest、packets、OCR、Skill、测试、旧交付或其他任务目录。
- 课程来源限定为 `Downloads\课程合集\3.2 直线与圆的方程`；未将老人版、`8.5g`、数学摄像头或答案册放入学习者上下文。
- assignment 当前状态：`ready`；当前 Skill contract SHA 与 assignment 绑定为 `08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0`。

## 源哈希

| 来源 | SHA-256 |
|---|---|
| `reports/luna_dispatch/READY.json` | `f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267` |
| `reports/ch12_luna_dispatch/assignments.json` | `6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc` |
| `reports/all_chapters/packet-build-current.json` | `848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884` |
| `data/all_chapters_course_catalog.json` | `fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048` |
| `data/vision_sidecar_all_chapters.json` | `ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc` |
| `data/packets/2.5/packet.json` | `f4c582aa51e9ca35ba07870f7b9d9ad68c5c441fd52801be49a47216f617a83a` |
| `data/packets/2.5/learning_packet.json` | `3d201c8c837bae004343df19169b67ff19a9b1635bf222664dde455f6cf4b0e0` |
| `data/course_transcripts/3.2.4.1 圆的标准方程和一般方程.json` | `7e780a6671a38b037d3a4bbe32088da3c9cae4f83d61ac4405645be56201bb12` |
| `data/course_transcripts/3.2.4.2 圆的确定.json` | `c892b166703fb0c953f01c848c6d8b6adccc4fff836cf44131095e195ed7f9f4` |
| `data/course_transcripts/3.2.5.8 圆的等价模型（代数）.json` | `cd083e520457da1f1e78eb37024886cf33235a6963d198fc1e20a05a44747a27` |
| `data/course_transcripts/3.2.5.9 圆的等价模型（几何）.json` | `e5f7cdff3878fc9661d05ccef55e7aade019cb5d90bc673a281ec0004acc58a6` |
| 唯一绑定原图 | `66d4828aba05c0fd47ef219de64f8a3b33c9ef814aca35d3caa40aaa5e2a865b` |

## 视觉回退

- Luna Max 当前宿主已由实际 payload 证明不支持图像输入，原文 blocker：`image content omitted because current luna_worker host does not support image input`。delivery 保留 `luna_status=blocked`，没有把 GLM 观察改名为 Luna。
- 按新 `ocr-vision-crosscheck.md` 执行确定性回退命令：

```powershell
python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\build_paddle_glm_crosscheck.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-08 --output reports\ch12_luna_sections\LUNA-CH12-08\ocr_vision_crosscheck.json --luna-blocker "image content omitted because current luna_worker host does not support image input"
```

- 脚本结果：`status=passed`，`records=1`；crosscheck SHA：`d8107b717277b3b0d2328c1974575ef1b3b605e240dbc796610a7224e3fcfa4e`。
- section visual contract：`mode=paddle_glm_crosscheck`、`luna_status=blocked`、`paddle_status=passed`、`visual_status=passed`、`visual_model=glm-4.6v-flash`、冲突 `0`。

## 覆盖与路线

- canonical 双向清点：`39/39`，教学例题 `11`，直属变式 `12`，A/B/C `16`，每项恰好一次；6 个循环。
- route version：`1`；final route hash：`dd9070ebb6b04079577ce79917397106625e33ef0e4ac1b7ae536b700b8adb24`。
- 课程调用按真实转写绑定：圆的标准方程和一般方程、圆的确定、圆的等价模型（代数）、圆的等价模型（几何）；学习者文件显示中文课程名和真实 mp4 文件名。
- learner Markdown/HTML 已移除内部 key、题面、答案、解答和模型指令；静态检查通过，HTML 含 UTF-8 meta，Markdown 未使用未配对 `$`。

## Five-round-five-persona-v2

- protocol：`five-round-five-persona-v2`。
- 5 轮 × 5 人格 × 39 项 = `975` 条实际 attempt；每项恰好 `25` 条。
- Round 1-5：`failed_item_keys=[]`、`route_repairs=[]`、`unresolved_item_keys=[]`；Round 5 绑定 final route hash。
- proxy simulation：`passed`；independent acceptance：`not_run`；human acceptance：`not_run`；cold 24h retest：`not_run`。

## 交付与验证

| 文件 | SHA-256 |
|---|---|
| `delivery.json` | `c7b831718e486ddc97aa245829e0c31844fb421bdecce4643e08c35c927b901d` |
| `learning_path_without_questions.md` | `6e5328e54a411478c62dcac91ffbb907fbf939e6125f7a42277bbfbbcabf7617` |
| `learning_path_without_questions.html` | `36df981b6209d6f189fa4bb32022f03145296820f340dbdb217d37eb7e0e4246` |
| `ocr_vision_crosscheck.json` | `d8107b717277b3b0d2328c1974575ef1b3b605e240dbc796610a7224e3fcfa4e` |

严格命令：

```powershell
python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-08 --delivery reports\ch12_luna_sections\LUNA-CH12-08\delivery.json
```

validator：`status=passed`，`errors=[]`。临时 `_build_delivery.py` 已删除。
真实未闭合项：Luna 原生图像读取仍为 `blocked`；本次视觉放行为当前合同允许的 exact-SHA Paddle + GLM fallback，不是 Luna 读图通过。
