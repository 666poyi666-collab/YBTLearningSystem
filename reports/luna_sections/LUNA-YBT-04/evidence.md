# LUNA-YBT-04 Evidence

状态：bundled validator 已通过。

## Scope

- 分节：2.6、4.4、ch3.s8、4.8
- canonical items：50 + 36 + 23 + 17 = 126
- 每节 route versions：1 -> 5
- 每项代理尝试：25
- independent_acceptance：not_run
- human_acceptance：not_run
- cold_24h_retest：not_run

## Source Hashes

- READY.json SHA256: f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267
- assignments.json SHA256: d9136bd27b2bf2e660e70c2ea34a044dd4225b2afa46b871700a429ac5c4cb8a
- packet-build-current.json SHA256: 848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884
- all_chapters_course_catalog.json SHA256: fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048
- vision_sidecar_all_chapters.json SHA256: ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc
- visual-inventory-source-question-only.json SHA256: 6a74378730c450904fa22221df46560c99022b94eee7161b16f2cda67ae21ebf

## Section Hashes

### 2.6
- packet.json SHA256: 5e961444ae31a7376300e0d9f40de93e4db467e2ed18f8f3431b5b9686176c5e
- learning_packet.json SHA256: 47d26e5b95122ffc843b77a1341410ca074e7a0d7ac5f0a04c59f01dea878e00
- transcript count: 6
- visual image hashes: 0
- final route hash: 7b19f2dc27adf65e49e7bbb8c5381737e2a560a8109a41cd86ac14ef97a7f754

### 4.4
- packet.json SHA256: fbfc97ac3bf8ce6701faceba997d9fbaea36a5c4ec82c0fca99ce3be9fdd84b3
- learning_packet.json SHA256: 17432ce726da95f9921d698c13a771a4dd39208b84b5e8c64a1a265fb7019514
- transcript count: 4
- visual image hashes: 0
- final route hash: 7c0c4b148082914c1e6f6fd00599ddf6e8ff3f438b229681a5b2f5d23f46b985

### ch3.s8
- packet.json SHA256: 2ccd320e8096bb8f6f888cd0c21f591d4dba4e73e5768207f6109476959b1e72
- learning_packet.json SHA256: 65e8ebbed7a38fb8549d85aa213d90483f4b4fdc0ea8f9060e1b7a55eff1f650
- transcript count: 3
- visual image hashes: 0
- final route hash: ef4ef2fa68d8085e4c682e428285a4f416085d86d5f8e257201a45ef7f527afb

### 4.8
- packet.json SHA256: 0321125200dfec44dd2ffc20d39ae68ae6a7f9847adb770ea581d13781691cc6
- learning_packet.json SHA256: b54a71e4fd8ccc9ddec830d2494fa3fb335dc8a00476efaa65ae8bc45f0faf31
- transcript count: 15
- visual image hashes: 0
- final route hash: 424757c81b129f75b79621c917ac82ad7fb654b206775f3ce8b01f4943c5d34c

## Commands

python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\luna_dispatch\assignments.json --task-id LUNA-YBT-04 --delivery reports\luna_sections\LUNA-YBT-04\delivery.json

Validator result: passed. JSON status: passed. Errors: [].

## Simulation

- Protocol: five-round-five-persona-v1
- Rounds: 5
- Personas per round: 5
- Attempts per item: 25
- Round 5: all four boolean gates true and final route hash bound
- Proxy simulation: passed

## Shared Defects

未发现共享源缺陷；未写入 shared_defects.json。
