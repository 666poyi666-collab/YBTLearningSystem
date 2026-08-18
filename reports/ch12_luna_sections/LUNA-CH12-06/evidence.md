# LUNA-CH12-06 evidence

## Intake and scope

- task_id: LUNA-CH12-06
- assigned section: 2.3（第3节 直线的交点坐标与距离公式）
- expected/delivered canonical items: 45/45
- model contract: fixed luna_worker, combo/protect-luna, max, context declaration 1000000
- recovery reason: previous run stopped at Luna upstream 503 no available targets; no previous content was inherited
- current assignment status: ready
- write boundary: only reports/ch12_luna_sections/LUNA-CH12-06; no shared source or other task directory was modified

## Current source snapshot

| file | SHA256 | state |
|---|---|---|
| reports/luna_dispatch/READY.json | f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267 | ready |
| reports/ch12_luna_dispatch/assignments.json | 6f7abf010749227f718026e2231b69e742c68505563caa2973ca9ac151daffdc | current rebound assignment |
| reports/all_chapters/packet-build-current.json | 848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884 | passed; section 2.3 total=45 |
| data/all_chapters_course_catalog.json | fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048 | current catalog |
| Skill contract tree | 08736c8e05e7815106339585f37f69bc171d3343a226839a653863064d03d7c0 | current bundle hash |
| data/vision_sidecar_all_chapters.json | ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc | READY-bound GLM fallback source |
| chapter2_manifest.json | 5584c68a130fc8cf40c5bdfa666552378c05cb9fde6d7ea09727badb76c58f08 | current manifest |
| data/packets/2.3/packet.json | 0c505a8b150cf44ef107dcb42b8c6cb6a520f4b67065e5672c7f246e10dbf654 | current packet |
| data/packets/2.3/learning_packet.json | 6adc3f0358eed0e55dca74cc25ca4c856537f48e74962a46c7c29f5671e839b9 | VERIFIED |

The Skill tree hash is the deterministic sha256_tree binding used by build_scoped_assignment.py, not the SHA of SKILL.md alone. The current ocr-vision-crosscheck.md and the four direct contracts were reread after the assignment upgrade.

## Source and course mapping

The route reads the actual in-scope course transcriptions and uses these catalog entries in first-use order:

| course key | learner-facing course name | transcript SHA256 |
|---|---|---|
| line_five_forms | 直线的五种表示形式及其应用 | 2ef5c5aec4a90cc70571223bf71a57dda04b5b8887ff736173c4a9a7e0501922 |
| line_equation_application | 直线方程的应用 | f83ea2f5ece2e4feaeab2638df73aedb07ec98a5406c3f4d0193a36f607dd068 |
| point_line_distance | 点到直线以及平行直线距离公式 | f7c3476688d9b1cefeaf7bb1b26a9795cae56340dd11fa481c0ce1d3a04b2b57 |
| line_parallel_perpendicular | 直线间的位置关系：平行与垂直 | 3b46fa4a9dc9ee83b68c439688f5f5025b94815946b4902a0aeff244e1e6848e |
| line_family_fixed_point | 过定点的直线系与曲线系 | bed2ae00832196b4573532519c10d2989c40101b40f52e778fab98a0d43d5648 |
| slope_angle_relation | 直线倾斜角与斜率的关系 | ccfa982a3349407ffc888e423cd0a45d5615310ebd25c383bb29aa03a5e1a155 |
| circle_determination | 圆的确定 | c892b166703fb0c953f01c848c6d8b6adccc4fff836cf44131095e195ed7f9f4 |

The ordered route is knowledge point -> adjacent worked example -> direct variant -> type consolidation -> A/B/C exercises. The current packet's nine direct variants are reused exactly once under parents 6, 8, 9, 10, 11, and 12; no item 46 or other new canonical item was created.

## Visual/OCR evidence

Command run:

python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\build_paddle_glm_crosscheck.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-06 --output reports\ch12_luna_sections\LUNA-CH12-06\ocr_vision_crosscheck.json --luna-blocker "image content omitted because current luna_worker host does not support image input"

- evidence file: ocr_vision_crosscheck.json
- evidence SHA256: 1741a6e9564e836f7f6289d8eb603fdb46c652f4489442fefb2f697967bd017b
- mode: paddle_glm_crosscheck
- section visual status: passed
- Paddle status: passed
- visual model: glm-4.6v-flash
- Luna status: blocked
- Luna blocker: image content omitted because current luna_worker host does not support image input
- bound visual items: 1 (例11); image SHA256 9f060fdbb6c15360043bc80731ad21db63a376932a0674dfed0b81e2bf168de7
- Paddle artifact: data/ocr_live_current/second_chapter_109/doc_34.md, SHA256 efb4dfe9e9ed1be5ef1cef90f8817b49a8f1d344db4623ef3c65f99e195aa178
- remaining 44 canonical items have no image_refs and remain READY_TEXT_ONLY
- formal cross-check conflict list: empty; the GLM row is not relabeled as Luna

## Five-round-five-persona-v2

The delivery stores actual course_call, recognition_statement, first_line_attempt, continuation_attempt, and self_check_attempt for every persona/item/round.

| round | route version | failed item keys | field-level repairs |
|---:|---:|---:|---:|
| 1 | 1 | 39 | 39 |
| 2 | 2 | 0 | 0 |
| 3 | 2 | 0 | 0 |
| 4 | 2 | 0 | 0 |
| 5 | 2 | 0 | 0 |

- personas per round: 5 stable profiles
- attempts per canonical item: 25
- total attempt rows: 1125
- route v1 hash: 1d5752f9d0bd4d578a09e4a950a2e25b1dfd12e225ccf2cb1f604155d1f76738 (superseded)
- final route v2 hash: f2007a0ed1672c60945ee60afd9e661f3b98e8d56425ca6eb93c697ac44afd01
- round 5 unresolved item keys: empty
- proxy simulation: passed

## Export and validation

Generated files and final SHA256:

| file | SHA256 |
|---|---|
| delivery.json | 6cdf100255ce013c3c72e6d6281046ca2dc55ad74476175eaa591612c1047cb3 |
| learning_path_without_questions.md | a4e7cac12090c4680c31aa28a0c7fe46e8cde0e904f8a7bdf5d98c9995e122e2 |
| learning_path_without_questions.html | 0e068e4fee44a915baedf3a592286fbe18dadbd7ec9f0eb29bb3669c727f653d |
| ocr_vision_crosscheck.json | 1741a6e9564e836f7f6289d8eb603fdb46c652f4489442fefb2f697967bd017b |

Learner-facing Markdown/HTML static scan: no question_text, teaching_text, answer sidecar, answer/result field, internal item key, LI: key, or Q: key found. JSON parse checks passed.

Strict validator command:

python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\ch12_luna_dispatch\assignments.json --task-id LUNA-CH12-06 --delivery reports\ch12_luna_sections\LUNA-CH12-06\delivery.json

Validator output: status=passed, errors=[].

Independent acceptance: not_run
Human acceptance: not_run
24-hour cold retest: not_run

## Real unresolved state

The route, fallback visual gate, exports, and strict validator are passed. The Luna host image-input capability remains genuinely blocked under the exact blocker above; GLM fallback evidence is transparently labeled and is not claimed as Luna evidence. No shared defect file was required by the current fallback gate.
