# LUNA-YBT-06 证据

## 当前状态

- 任务状态：`passed`。
- 代理模拟：`passed`；每节 5 轮 × 5 人格，每题 25 次尝试；Round 5 绑定最终 route hash。
- 独立验收：`not_run`。
- 真人验收：`not_run`。
- 24 小时冷复测：`not_run`。

## 来源哈希

- READY：C:\开发\小工具\一本通学习系统_v7\reports\luna_dispatch\READY.json
  - SHA256: f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267
  - status: ready; visual_gate=127/127; post_build_unbound_items=0
- assignments.json SHA256: d9136bd27b2bf2e660e70c2ea34a044dd4225b2afa46b871700a429ac5c4cb8a
- packet-build-current.json SHA256: 848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884
- all_chapters_course_catalog.json SHA256: fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048
- vision_sidecar_all_chapters.json SHA256: ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc
- visual-inventory-source-question-only.json SHA256: 6a74378730c450904fa22221df46560c99022b94eee7161b16f2cda67ae21ebf

## 分节覆盖

- ch3.s1：45 项；packet=56b0f3858ac3d5129ac0a2eda4125ef8260d236131e472c7f4040d3ab5eb3ca5；learning_packet=16816116f836f7f8dc79b3be9dfe42f57b6f73d6a2b8e1e6da02303a3eab45be；manifest=e294b0a63b15c3f3f7254c80e286332a6db4df77ff9c312ce9dbb8a297fceee8
  - 图形状态库存：2 个图片 SHA；题项视觉状态按 JSON 逐项绑定。
  - route v1=493d9f06ae6171287373b280ddcb18d54e3e1d8ff893977a5caa6b49dc55c4ae；route v2/final=e9ed9948d89d1716e65c2e8a0ed677d603e990d0220ddc1e0c72d32c62faeb8f
  - transcript SHA 数量：6
- 1.4：37 项；packet=c323cb7e45c37e10c83d9078f3aa4ee057255aba7dabbcad498d9ccdd3e8b3dc；learning_packet=a7eca3ef6d38e20c7241243aa768665d403d63d4bc96b28d03cff4ab9b58fb81；manifest=d4f276a026ddfd35d69795ed5c589cdbf8f3f8e98ad3fe73ef814d672a1541c5
  - 图形状态库存：22 个图片 SHA；题项视觉状态按 JSON 逐项绑定。
  - route v1=48881c1edad6605291227f98914155cae4a9006e92c4c0f2ffca0278d3185ed7；route v2/final=53d903178b4890fa17364147c49752a33913a32370b8505aad6d4ceaa5fce650
  - transcript SHA 数量：11
- ch3.s3：30 项；packet=3eb853eb174fffd005e509e91bdfa307a1dff87e13fad78375d2933f163ffeeb；learning_packet=6e439c0253b12cf6cd07fca51c7c817db5b302b63d52709def82c7abc2010be0；manifest=e294b0a63b15c3f3f7254c80e286332a6db4df77ff9c312ce9dbb8a297fceee8
  - 图形状态库存：1 个图片 SHA；题项视觉状态按 JSON 逐项绑定。
  - route v1=d9c343bf3950ccf108f9ec8786d401d771caea8c2744d96fd1da860db30535e4；route v2/final=211e536097f93e67d9188a00ce143f7e1863f587eab43b3a3b036372ae2ce6af
  - transcript SHA 数量：7
- 4.6：9 项；packet=4b5f4d7a311476853a98c484adeae5e5fb1f9278835a92eb4a6cdef07bef1bea；learning_packet=c80971c0f21d80d87dd2e686d48d9e4a81d4e2ca9127573168d6d9022f35f4e2；manifest=104f4cbd00e13b567235d3dc77c7d6589e926852f262bf179160d608277c9308
  - 图形状态库存：0 个图片 SHA；题项视觉状态按 JSON 逐项绑定。
  - route v1=5d82ce2959e2bc4d3d7870d29b4bafd073ccea10527d405a86dae43340bc93fd；route v2/final=d27b7d4c98b5b7b3a3c758cd4c8656b0294e056411d8820dec41a3cdcc172f76
  - transcript SHA 数量：2

## 课程转写

课程来源限定为 Downloads\课程合集及其当前目录；本任务实际调用的 transcript SHA 去重后共 22 个。课程目录声明排除老人版课程、8.5g、数学摄像头。

## 运行命令

```powershell
python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py `
  --project-root C:\开发\小工具\一本通学习系统_v7 `
  --assignment reports\luna_dispatch\assignments.json `
  --task-id LUNA-YBT-06 `
  --delivery reports\luna_sections\LUNA-YBT-06\delivery.json
```

validator_result: `passed`；实际输出：`{"status":"passed","task_id":"LUNA-YBT-06","errors":[]}`。

## 共享源问题

未发现需要写入 shared_defects.json 的共享源缺陷；未创建该文件。

## 边界

学习者 Markdown/HTML 不含题面、解答、选项结论、答案侧车、内部 item key、哈希或模型指令。
