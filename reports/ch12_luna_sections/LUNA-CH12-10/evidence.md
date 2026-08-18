# LUNA-CH12-10 evidence

## Scope and contract

- Task: LUNA-CH12-10
- Section: 2.7 only
- Canonical scope: 10 worked examples, 10 direct variants, 19 A/B/C exercises, 39 items
- Assignment: reports/ch12_luna_dispatch/assignments.json
- Current assignment SHA256: 6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc
- New skill_contract_sha256: 08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0
- Model contract: combo/protect-luna, reasoning_effort=max, context_window=1000000
- Write scope: reports/ch12_luna_sections/LUNA-CH12-10 only
- No shared source, manifest, packet, catalog, OCR, sidecar, test, or other task directory was modified.

## Source snapshot and hashes

- READY: reports/luna_dispatch/READY.json; status=ready; SHA256=f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267
- Packet build: reports/all_chapters/packet-build-current.json; status=passed; SHA256=848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884
- Course catalog: data/all_chapters_course_catalog.json; SHA256=fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048
- Vision sidecar: data/vision_sidecar_all_chapters.json; SHA256=ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc
- Section manifest: data/packets/2.7/manifest.json; status=VERIFIED; SHA256=8e4d163af5058d0b7df912287116d8978249c53907ab7919a289b5af14129fca
- Section packet: data/packets/2.7/packet.json; SHA256=f6dbe7f92f62b78f11f45ed1fcedcaf6af13aaac0b38f083744af52e8c46a8b2
- Learning packet: data/packets/2.7/learning_packet.json; status=VERIFIED; SHA256=d3f48dfb3805f4b6b785c6a68fa5be2d9e5e7eecd56dda53b9bd6b32f45bbb28

## Course transcript evidence

All calls are catalog-bound and use the real MP4 names shown in the learner route. The consumed transcript SHA256 values are:

- 3.2.5.6 圆与圆的五种位置关系判定.json: 38914e67202e946d5ec5671fc3d7d0e558d7eb9c5ef480689e0c7f204125f785
- 3.2.5.7 配极与切点弦模型.json: e1f2e50e0dd7d2b5d8c53e2ca4b943c7e84a713008ae760368bd9319f0151fae
- 3.2.5.8 圆的等价模型（代数）.json: cd083e520457da1f1e78eb37024886cf33235a6963d198fc1e20a05a44747a27
- 3.2.5.9 圆的等价模型（几何）.json: e5f7cdff3878fc9661d05ccef55e7aade019cb5d90bc673a281ec0004acc58a6
- 3.2.5.2 相切与求切线.json: abe9ff932d7cf2b10f4e683a95a0ee96c95e4e2aad8f95751f250ced6bc5b3eb
- 3.2.5.3 弦长与垂径定理.json: e5e0c0ed5eef1d8f4b8d34fecd6f9f1da16ff5724c754d90ad01d770a4f028f3
- 3.2.5.5 线圆相离的最值模型.json: a14b5c2d75e47953888e6561d6d368dd222f95c06e30c46ee9afbfa0cd2c473b
- 3.2.4.2 圆的确定.json: c892b166703fb0c953f01c848c6d8b6adccc4fff836cf44131095e195ed7f9f4
- 3.2.4.1 圆的标准方程和一般方程.json: 7e780a6671a38b037d3a4bbe32088da3c9cae4f83d61ac4405645be56201bb12

## Visual fallback

Command executed exactly:

    python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\build_paddle_glm_crosscheck.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-10 --output reports\ch12_luna_sections\LUNA-CH12-10\ocr_vision_crosscheck.json --luna-blocker "image content omitted because current luna_worker host does not support image input"

Result: status=passed, records=0.

- Evidence file: reports/ch12_luna_sections/LUNA-CH12-10/ocr_vision_crosscheck.json
- Evidence SHA256: eec59e97c05084f2d3cf736ea8b1f80ec6e1a56fc4fd70bff761d314713a3dc7
- mode=paddle_glm_crosscheck
- luna_capability.status=blocked
- luna_capability.blocker=image content omitted because current luna_worker host does not support image input
- fallback visual model=glm-4.6v-flash
- Paddle status=passed; section visual_status=passed
- The 2.7 learning packet has no bound image references: all 39 item visual states are READY_TEXT_ONLY and image_sha256 is empty. Therefore there are no per-image records to invent; the fallback file honestly contains zero records.
- No Luna image read is claimed. No old GLM sidecar was renamed as Luna.

## Coverage and route

- Bidirectional canonical check: 39 unique delivery keys, ordinals 1-39 exactly once; 10 worked examples, 10 direct variants, 19 A/B/C exercises.
- Final route version: 2
- Route version 1 SHA: 4242770a9e3d14d4e6a18decc190cf23b68e0ed64695da405feaaded50114bde
- Final route version 2 SHA: 8288a6e3245c67e3d5d4b17dfc5d6d3919be4251da293008643b7e9f950d61d3
- Textbook order preserved: knowledge point -> adjacent worked example -> direct variant -> type/example route -> A/B/C -> cycle acceptance.
- Learner-facing files contain Chinese course names and real MP4 filenames; no internal item keys, question text, answers, solution fields, or answer-sidecar content.

## five-round-five-persona-v2

- Protocol: five-round-five-persona-v2
- Personas per round: 5
- Rounds: 5
- Attempts per canonical item: 25
- Total attempt records: 975
- Round 1: route_version=1, failed_item_keys=29, concrete field-level repairs=29
- Round 2: route_version=2, failed_item_keys=0
- Round 3: route_version=2, failed_item_keys=0
- Round 4: route_version=2, failed_item_keys=0
- Round 5: route_version=2, failed_item_keys=0 and final route hash bound
- Every attempt stores course_call, recognition_statement, first_line_attempt, continuation_attempt, self_check_attempt, booleans, first blocker, correction field and verdict. Round 5 is fully passed with no unresolved item keys.

## Commands and outputs

- Current assignment/contract reread: passed
- Deterministic Paddle/GLM fallback: passed
- Temporary delivery generator: ran successfully and was deleted after artifact generation
- Markdown export: passed; UTF-8 without BOM
- HTML export: passed; UTF-8 without BOM and responsive CSS for narrow/desktop widths
- Learner artifact forbidden-key scan: 0 hits for internal IDs, question_text, solution_text, correct_option, final_answer, answer_sidecar, or teaching text
- Final delivery SHA256: 6b8e56a72d3e02ed3c0a3921978ed1982a3c4ee835781a5d699712bcfdb4dfd4
- Markdown SHA256: 5e330b149c189a9b590db931209110d39f1320f5956186c7f2a77cd319142cb7
- HTML SHA256: 1b56768ffa7ad708b63627358c865763b3d98047a863d5d9ba8aa785710e9a6d

Strict validator command:

    python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-10 --delivery reports\ch12_luna_sections\LUNA-CH12-10\delivery.json

Validator result: passed; errors=[]

## Acceptance states

- proxy_simulation: passed
- independent_acceptance: not_run
- human_acceptance: not_run
- cold_24h_retest: not_run
- unresolved source/visual/route items: none in the validator gate; Luna image capability remains explicitly blocked as recorded above.
