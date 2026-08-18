# LUNA-CH12-03 证据记录

## 任务边界

- task_id: LUNA-CH12-03
- assigned section: 1.4
- expected items: 37
- model contract: combo/protect-luna, reasoning effort max, declared context window 1000000
- unique write directory: reports/ch12_luna_sections/LUNA-CH12-03
- source boundary: only Downloads\\课程合集 allowed course corpus, mathematical 8.5/8.5课程 requirement evidence, real textbook, current PaddleOCR AI Studio output, and current Luna image observations.
- excluded from learner context: 老人版课程、8.5g、数学摄像头、答案册及旧 sidecar 结论。

## Initial source snapshot

READY is present at the contract path reports/luna_dispatch/READY.json and reports status=ready. The task-specific assignment is reports/ch12_luna_dispatch/assignments.json; its task record is the authority for this recovery task.

| source | sha256 |
|---|---|
| reports/luna_dispatch/READY.json | f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267 |
| reports/ch12_luna_dispatch/assignments.json | 6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc |
| reports/all_chapters/packet-build-current.json | 848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884 |
| data/all_chapters_course_catalog.json | fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048 |
| chapter1_manifest.json | d4f276a026ddfd35d69795ed5c589cdbf8f3f8e98ad3fe73ef814d672a1541c5 |
| data/packets/1.4/packet.json | c323cb7e45c37e10c83d9078f3aa4ee057255aba7dabbcad498d9ccdd3e8b3dc |
| data/packets/1.4/learning_packet.json | a7eca3ef6d38e20c7241243aa768665d403d63d4bc96b28d03cff4ab9b58fb81 |
| data/packets/1.4/student_packet.json | e730b075a89a1b59feda6c6d7968533b92935e9b11c2779a2be531c8853daa5f |
| data/packets/1.4/student_learning_items.json | c52de4938607e34db72d03e00062646b2b48bb6d6041ce53a582b132b417d56d |
| assignment-bound skill contract | 08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0 |
| live SKILL.md | fe2a01562f4c9f801c36b0a5874b509aed8d1ef1387dec37487430efe6a4ef03 |
| live references/ocr-vision-crosscheck.md | dfcbedfdd74269f59eb7e4991e32e30128daf7cfe3231ccd34ab243b3e0ad4d8 |

The four direct contracts were read in full before delivery work: workflow-contract.md, output-schema.md, simulation-gates.md, and ocr-vision-crosscheck.md.

## Approved 1.1 workflow reference

Read-only references used only for workflow/schema shape:

- reports/ch12_luna_sections/LUNA-CH12-01/delivery.json sha256 7410d6f049142d8b364f103344cd5b6440d76f4aa2a7877b81fa069874149b17
- reports/ch12_luna_sections/LUNA-CH12-01/learning_path_without_questions.md sha256 85a4ede8749f9b1a107e053a9d820e72b59482797f76f30ae187d4c37c48755f
- reports/ch12_luna_sections/LUNA-CH12-01/ocr_vision_crosscheck.json sha256 a47134ef6bffcf4975a9a253f5770971bd6a6e4eb51d2a48fe09dd6d6f1cbc31

No 1.1 mathematical item, question, answer, or route text is being copied into section 1.4.

## Canonical inventory snapshot

Live packet and manifest agree on section 1.4, label 第3节 空间向量的应用, and counts 22 worked examples + 3 direct variants + 12 A/B/C exercises = 37. The textbook order is preserved by the packet cycles: direction/normal-vector foundations; vector applications; parallel/perpendicular proof types; spatial angles; distances; point/line-in-plane judgment; folding and existence synthesis.

The packet is structurally VERIFIED; the chapter manifest remains PARTIAL_UNVERIFIED because current transcripts do not contain dedicated courses for folding conservation and dynamic dihedral-angle trigonometric parameterization. Those gaps are recorded as shared-source defects and must not be silently marked as course coverage.

## Current visual fallback

The current luna_worker host returned the explicit image-input blocker: image content omitted because current luna_worker host does not support image input. The required build_paddle_glm_crosscheck.py command was executed first and stopped at 1.4 A2 because the packet exercise image has no source_docs entry. Shared packet files were not edited. A task-local repair run then resolved PaddleOCR documents by exact image filename, checked the assignment-bound sidecar SHA and original image SHA, and produced the same v1 fallback schema.

- fallback mode: paddle_glm_crosscheck
- Luna status: blocked; the original blocker text is preserved in the delivery and every record
- visual status: passed using exact-SHA READY-bound GLM-4.6V-Flash structured observations plus PaddleOCR artifacts
- visual evidence file: reports/ch12_luna_sections/LUNA-CH12-03/ocr_vision_crosscheck.json
- visual evidence SHA256: 236e57f9a184db1891a4fe0e51ba0b7f54e0d000fcf5987da28d1686fc7a9f9f
- records: 22, unique image SHA values: 22
- temporary repair_fallback.py: deleted after generation

## Work log

- [x] Read skill and four direct contracts.
- [x] Read task assignment and approved 1.1 reference artifacts.
- [x] Verified READY, packet-build, catalog, manifest, 1.4 packet, and learner packet hashes.
- [x] Created this evidence file before downstream artifacts.
- [x] Reconcile every 1.4 canonical item bidirectionally.
- [x] Read all bound course transcripts and map exact course calls.
- [x] Attempted the current Luna image capability probe; host returned the explicit image-input blocker.
- [x] Generated exact-SHA Paddle/GLM fallback cross-check records for all 22 bound images; Luna remains blocked.
- [x] Run five rounds with five stable personas, preserving actual attempt text.
- [x] Export answer-free Markdown and HTML.
- [x] Run the specified validate_section_delivery.py command after delivery export.

## States at evidence initialization

- proxy_simulation: passed
- independent_acceptance: not_run
- human_acceptance: not_run
- cold_24h_retest: not_run
- validator: passed

## Final delivery evidence

### Course transcript bindings

The following legal course transcript SHA values were consumed and mapped to the real MP4 named in the learner route:

- coordinate_ops: 88343b0159aeb40c6fc0b28c66fe626358e91963fe13ab2bb04c72482475636e
- coplanar: 968ae0a27d2627b307951e3d537fde7d5bc00cd45066ae86151d31bf7282a325
- direction_normal: d0ec9c67e89b5b7506aebe5aaa477553790cbc98b64eed43cb0fb63c8cde276c
- distance: a476ddac1a574d6a287f789a2fd29600be72a04c67330998e26888dedc96d410
- line_line_angle: 0be63e83adac131e7f4e0cf99d0424f23b1981ee3a446d5b2fa6029733311147
- line_plane_angle: 635245d9a4e1d53dd30ed409b7c8937636bfeae6901f599d72c2b38068138cf8
- moving_point: da8ca5e664bf4438ef4a559263240bdf12e0494e1f67ab699ea7902293df3976
- parallel_perpendicular: 94c0581735e82edeb9613c4adfa25230e22ca40b1d563b007099c54c0ee2a0bc
- plane_equation_lower: 361496fd36e353ab29fed41acc0a6642c023bee9e8cfbd25aab463a0296d7412
- plane_equation_upper: 54de6ddd1117713ce8a28e33374ad3cb7c868b4c74f36dc99fd65b67727c2f0a
- plane_plane_angle: 5a01b37ad36ed0c8aed759b8b3f58ca2dbf7beb9c0aa1f9de4ee8b42f9afe23b

### Image bindings

Every image SHA bound by delivery.json appears once below and once in ocr_vision_crosscheck.json records:

- 008987a6d646465e5269bc47abafefa8147fdf5bdd2746f12f834e1935382863
- 0920f7b8980cf8cf4a9cdee4eaf6dba9e2074e85a56a10cd7c2324f9e5f41c91
- 188839eb8c3ecd50372539b3b0affebfbc569eb6fe481c5012ca27f2ba2b32c2
- 34903c45a8282d1d387f953e3186d4cd9059444f78847e67c0cd37316d1a3672
- 4274aa2691444a6341642521bc7952666e50480a85c4bbcd789744d6a987f1ec
- 4bd9c2809300d1e6f7de4925d996270d5d2bdcae43fa2be530f47ca94f159b08
- 4f72deff759fe90b3bcef3bf221ffa4494bbc2275f05f4bea830fa6692b4815b
- 5bf19e031edf5bff20122e2023aa615c7c4a20b12aab33f07c17ccf72d183593
- 65c773278b5de0c868bf52682d7ffc1e9a2b45d7e5e6651be470287276151e8a
- 6610dd44d09e96294229e4f3bb603e571838873260d24e5a99dced6838e23ea8
- 66fee4503a25f8d7803ac95c879be8dec9ed66cb230ddd2e890de22c32128e16
- 76fc9199f1783b0d73d25414b386e5a51b0ad09466a0bdddfbdd7821e514a86d
- 88262d02c7a74fd4b1b662ccc52e45eeae82229e5d649a4ebe7fd3db9c5e209f
- 8c901a0abedad0a569ef2ab5d792cc95bafa4bdc24401e6685eda89cc91ede37
- 9e3c71574df508bba8e1e1dc18de39c6fdc44c26254a9646f31bbae87f9d239c
- c09e41cc475cb8810754adbeee86eefaf54481b2c69a5693a85f8681d27bcb26
- c487b6528512e8ce8a24d76bf2505d3fcdcac23db2b756e2bc26a055b70b34e9
- e028e49fb9240af2c72fc50b6f90d0acf4b54d7a9baa58d530a52130161b886c
- e5498a7ed5c84a7c517b431a3535532c49cfe59180774081db8eb219303c7518
- fc55bb596c7b5a6696d06695cc7dfb378458abaa05916022af32086bf74f6cce
- fd176ced53ca004fc95233b8848774d227fb57275973938fe7db1d84c799b7eb
- fe23eb0a2cb7d392546b03a28ba60f5c9d2c684f875c6a26e91fa06ca2ca73dd

### Coverage and simulation

- Canonical coverage: 22 worked examples, 3 direct variants, 12 A/B/C exercises, 37/37 unique, 0 duplicates, 0 missing, 0 unexpected.
- Route versions: v1 superseded, v2 final; final route hash 77b3a163c8ca313c593f3d5f0163c94a476840d6d80b91d43072e26d8ffc7b2d.
- Protocol: five-round-five-persona-v2; 5 rounds, 5 stable personas per round, 37 items per persona, 25 actual attempts per item, 925 attempts total.
- Round 1 failed item set: C9, C10, C11, C12 due to missing explicit bridge; repair changed method_model to add the required bridge and R2-R5 all passed with failed_item_keys empty.
- Proxy simulation: passed. This is not human acceptance or a 24-hour cold retest.

### Commands and validator

- Required fallback command was run first and stopped honestly at 1.4 A2 because exercise image source_docs was empty.
- Task-local exact-image filename repair generated the fallback evidence; the repair script was deleted afterward.
- Final validator command:
  python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-03 --delivery reports\ch12_luna_sections\LUNA-CH12-03\delivery.json
- Validator result: passed; errors=[]

### Final states

- visual: passed through paddle_glm_crosscheck; visual_model=glm-4.6v-flash; Luna remains blocked with the exact host blocker text.
- proxy_simulation: passed
- independent_acceptance: not_run
- human_acceptance: not_run
- cold_24h_retest: not_run
- shared unresolved: no dedicated current MP4 was found for folding conservation or dynamic dihedral-angle trigonometric parameterization; route v2 contains explicit bridges and the gap is recorded in shared_defects.json.
