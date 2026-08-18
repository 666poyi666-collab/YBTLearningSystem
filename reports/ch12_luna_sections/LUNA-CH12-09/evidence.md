# LUNA-CH12-09 证据记录

- task_id: `LUNA-CH12-09`
- assigned section: `2.6`
- expected items: `50`
- model contract: `combo/protect-luna`, reasoning effort `max`, fixed `luna_worker`
- output scope: `reports/ch12_luna_sections/LUNA-CH12-09`
- run start: `2026-08-17`
- status: `in_progress`

## Authority and source boundary

本任务只消费当前 assignment、共享 READY/packet-build/catalog、2.6 章节 packet、允许课程合集转写、真实教材 OCR/原图、当前 Luna/Paddle 交叉证据，以及只读的 1.1 母版流程/schema。不得读取答案册进入学习者上下文；不得修改 READY、packet-build、课程目录/转写、manifest、packets、OCR、Skill、测试、旧交付或其他任务目录。

## Initial snapshot

- assignment: `reports/ch12_luna_dispatch/assignments.json`
- shared READY: `reports/luna_dispatch/READY.json`
- packet-build: `reports/all_chapters/packet-build-current.json`
- course catalog: `data/all_chapters_course_catalog.json`
- section packet: `data/packets/2.6/packet.json`
- learning packet: `data/packets/2.6/learning_packet.json`
- approved 1.1 delivery: `reports/ch12_luna_sections/LUNA-CH12-01/delivery.json`
- approved 1.1 learner route: `reports/ch12_luna_sections/LUNA-CH12-01/learning_path_without_questions.md`
- approved 1.1 vision cross-check: `reports/ch12_luna_sections/LUNA-CH12-01/ocr_vision_crosscheck.json`

## Commands and results

1. Read the full Skill v2 contract and its direct references: `workflow-contract.md`, `output-schema.md`, `simulation-gates.md`, `ocr-vision-crosscheck.md`. Result: read successfully; required schema and gates loaded.
2. Read assignment and shared READY. Result: assignment is `ready`; shared READY is `ready`.
3. Read packet-build. Result: whole-book build is `passed`; section `2.6` is `VERIFIED`, with 12 worked examples, 19 direct variants, 19 A/B/C exercises, total 50.
4. Created this evidence file before route/export artifacts.

## Pending gates

- source snapshot hashes: `not_run`
- canonical bidirectional coverage audit: `not_run`
- assigned transcript/content mapping: `not_run`
- per-image current Luna/Paddle cross-check: `not_run`
- five-round-five-persona-v2 actual attempt records: `not_run`
- answer-free Markdown/HTML export: `not_run`
- strict validator: `not_run`
- independent acceptance: `not_run`
- human acceptance: `not_run`
- cold 24h retest: `not_run`

This file is append-only for the current task run; later entries will record exact hashes, commands, outputs, and unresolved states.

## Refreshed binding and visual fallback

- current assignment status: `ready`
- assignment skill_contract_sha256: `08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0`
- ready_sha256: `f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267`
- packet_build_sha256: `848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884`
- course_catalog_sha256: `fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048`
- vision_sidecar_sha256: `ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc`
- current 2.6 packet_sha256: `5e961444ae31a7376300e0d9f40de93e4db467e2ed18f8f3431b5b9686176c5e`
- current 2.6 learning_packet_sha256: `47d26e5b95122ffc843b77a1341410ca074e7a0d7ac5f0a04c59f01dea878e00`
- assignment source binding equals delivery top-level binding: `passed`

Official deterministic fallback command executed exactly as assigned:

```text
python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\build_paddle_glm_crosscheck.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-09 --output reports\ch12_luna_sections\LUNA-CH12-09\ocr_vision_crosscheck.json --luna-blocker "image content omitted because current luna_worker host does not support image input"
result: blocked by shared packet defect: missing PaddleOCR doc for image SHA `83bfaa8774a949a6022ea2b57b988ff15ccd051f48a6d785228065714450c99b`.
```

The affected exercise has `source_anchor.ocr_doc=88` and `data/ocr_live_current/second_chapter_109/doc_88.md` exists. A task-local generator used the same exact-SHA Paddle+READY-bound GLM logic and only fell back to that existing source anchor; no shared source was edited. The defect is recorded in `shared_defects.json`.

Task-local fallback result:

```text
status=passed; items=50; image_records=2; route_versions=5; attempts_per_item=[25]; round5_failed=[]
```

Visual evidence output: `ocr_vision_crosscheck.json`, SHA256 `20cf965651792f704eca7f0feeb1b7b7857bb7138f06d38414c63f347662ca4d`.

The section summary is explicitly `mode=paddle_glm_crosscheck`, `luna_status=blocked`, `luna_blocker=image content omitted because current luna_worker host does not support image input`, `paddle_status=passed`, `visual_status=passed`, `visual_model=glm-4.6v-flash`. The two image SHA records are:

- `2a09a14774dad0006055a939404b9c62e9e688bd333169cc5f8ff4f05e399b49`
- `83bfaa8774a949a6022ea2b57b988ff15ccd051f48a6d785228065714450c99b`

## Route and simulation

- reused and re-bound the existing 2.6 method scaffold to the current canonical packet; no 1.1 mathematical content was copied
- canonical coverage: 12 worked examples + 19 direct variants + 19 A/B/C exercises = 50; duplicate/missing/unexpected = 0
- textbook cycle order preserved: knowledge/example -> direct variants -> A/B/C groups -> cycle acceptance
- course calls: `line_circle_position`, `tangent`, `pole_polar_chord`, `chord_length`, `longest_shortest_chord`, `line_circle_extreme`; all six real mp4 files and current transcript files exist, with catalog transcript hashes bound in delivery
- protocol: `five-round-five-persona-v2`; 5 rounds x 5 personas x 50 items = 1,250 frozen attempt records
- round failures and repairs: R1=5, R2=4, R3=3, R4=2; each failed key has a field-level repair; R5=0
- every attempt stores actual `course_call`, `recognition_statement`, `first_line_attempt`, `continuation_attempt`, and `self_check_attempt`; no boolean-only rows
- round 5 attempts: 250; `recognized_method=false` 0, `first_line_written=false` 0, `continuation_complete=false` 0, `self_check_complete=false` 0; verdicts `passed=236`, `passed_after_self_correction=14`; `failed_item_keys=[]`
- `actual_attempts_per_item`: 25 for every item; `unresolved_item_keys=[]`; final route hash: `02fdd7960afed8d25dbe2c5fdd603f1e4ff6c53a5057eb8699e2e10fb5dbcc77`

## Export and strict validation

- learner Markdown and HTML exported; both have 0 internal-ID hits, 0 answer-term hits, 0 unescaped dollar delimiters, and balanced MathJax delimiters 135/135
- required output files present: `delivery.json`, `learning_path_without_questions.md`, `learning_path_without_questions.html`, `evidence.md`, `ocr_vision_crosscheck.json`; `shared_defects.json` is present because the official fallback script exposed the shared packet defect
- strict validator command:

```text
python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-09 --delivery reports\ch12_luna_sections\LUNA-CH12-09\delivery.json
result: status=passed; errors=[]
```

## Final states

- proxy_simulation: `passed`
- independent_acceptance: `not_run`
- human_acceptance: `not_run`
- cold_24h_retest: `not_run`
- current unresolved item keys: none
- real shared-source defect: `data/packets/2.6/learning_packet.json` missing `source_docs` for `Q:Q-dfa5d1d45a2d1637`; handled by source-anchor fallback and reported without modifying shared files
