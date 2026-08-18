# LUNA-CH12-04 evidence

状态：passed（当前 assignment 允许的 PaddleOCR + GLM fallback 路径）。

## 任务绑定

- task_id：LUNA-CH12-04
- section：micro专题1
- expected/delivered：16/16
- model contract：combo/protect-luna / max / context 1000000
- unique write directory：reports/ch12_luna_sections/LUNA-CH12-04
- updated skill_contract_sha256：08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0

## Source hashes

| 文件 | SHA-256 |
|---|---|
| reports/luna_dispatch/READY.json | f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267 |
| reports/all_chapters/packet-build-current.json | 848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884 |
| data/all_chapters_course_catalog.json | fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048 |
| data/vision_sidecar_all_chapters.json | ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc |
| reports/ch12_luna_dispatch/assignments.json | 6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc |
| data/packets/micro专题1/packet.json | 5f9f63878dfd8189b32e9d609dd01d6e7ed2eb20c8139075af846e88fb31c041 |
| data/packets/micro专题1/learning_packet.json | 5d403ed590effb0cd3664426621fe81791fdf8262ccf89759e02a8a54d3b05d1 |
| reports/ch12_luna_sections/LUNA-CH12-04/ocr_vision_crosscheck.json | 3a419c40b6f600dd708fde00190f6f830ca9237dd5ece3ac7dbcd4dc0d213e3a |

## Commands

1. Read current SKILL.md, workflow-contract.md, output-schema.md, simulation-gates.md and ocr-vision-crosscheck.md.
2. Read current reports/ch12_luna_dispatch/assignments.json.
3. Requested shared fallback command stopped because exercise rows expose source_anchor.ocr_doc while the shared builder reads source_docs.
4. A task-local wrapper repaired only that source-doc lookup and generated the same ybt-ocr-vision-crosscheck-v1 schema.
5. Route/export generator wrote delivery.json, learning_path_without_questions.md and learning_path_without_questions.html.
6. Strict validator result is appended below.

## Canonical and route

- 7 worked examples + 1 direct variant + 8 B/C exercises = 16.
- Bidirectional canonical order: each key appears once in delivery.json; no duplicate, missing or unexpected keys.
- Six cycles preserve type example -> direct variant -> B/C exercise order from the current learning packet.
- Used transcript files: 8 exact catalog-bound transcripts; learner-facing exports show Chinese course names and real MP4 basenames.
- Route version: 1; final route hash: dd344b2f3161aad431e27578a3c1a25b1422c3b7e7bdf02ac055614906bfbf0f.

## Visual

- ocr_vision_crosscheck.json records: 10 exact source-image SHA records.
- PaddleOCR: passed; GLM fallback: passed; visual_status: passed; visual_model: glm-4.6v-flash.
- Luna status: blocked.
- Luna blocker: image content omitted because current luna_worker host does not support image input
- No GLM row is labeled as Luna. The route uses the fallback visual structure only as answer-free diagram evidence.

## Five-round-five-persona-v2

- Protocol: five-round-five-persona-v2.
- Rounds/personas: 5/5.
- Attempts: 25 per item, 400 total.
- failed_item_keys: empty in every round; route repairs: none required after current route mapping.
- Round 5 binds final route hash dd344b2f3161aad431e27578a3c1a25b1422c3b7e7bdf02ac055614906bfbf0f.
- Proxy simulation: passed.
- Independent acceptance: not_run; human acceptance: not_run; cold 24h retest: not_run.

## Validator

- Command: python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-04 --delivery reports\ch12_luna_sections\LUNA-CH12-04\delivery.json
- Result: passed; errors: []

## Final artifacts

- delivery.json SHA-256: 9c6f4e14ab10caa606ba8f02601852e4692f5e043ca4acdfc6a40e9a5fa5170c
- learning_path_without_questions.md SHA-256: 607042763038020c9dcf44b2d586f799b07db7c138ea8f2f727dfa24351db8ed
- learning_path_without_questions.html SHA-256: 2b4438a5ad9e4b01a2fad3668dfe982438d486704e46c2c3f75ecb3d484eafa6
- ocr_vision_crosscheck.json SHA-256: 3a419c40b6f600dd708fde00190f6f830ca9237dd5ece3ac7dbcd4dc0d213e3a
- evidence.md SHA-256 after this write: recompute from the filesystem.

Generated at: 2026-08-17T10:51:05.855182+00:00
