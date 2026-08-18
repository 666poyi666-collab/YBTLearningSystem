# LUNA-YBT-10 证据

生成时间：2026-08-17T06:36:57.861311+00:00

## 当前源快照

- READY path: C:\开发\小工具\一本通学习系统_v7\reports\luna_dispatch\READY.json
- READY status: ready
- READY SHA-256: f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267
- assignments SHA-256: d9136bd27b2bf2e660e70c2ea34a044dd4225b2afa46b871700a429ac5c4cb8a
- packet-build SHA-256: 848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884
- course catalog SHA-256: fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048
- vision sidecar SHA-256: ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc
- visual source inventory SHA-256: 6a74378730c450904fa22221df46560c99022b94eee7161b16f2cda67ae21ebf
- supervisor context hash: 570bbb3694b492279c0d396bc6b0f5c5ab9b20c60397791a7a5afedfbca31e48

## 分节覆盖

- ch3.s5: 40 items; packet=a1f64502a46db16be8afd188286f9703c305a149a57f22a2013ba742c5ab1f0f; learning=41f310616997d419de44524845485936613a50f2237134b9b7e980e67babd778
- 2.5: 39 items; packet=f4c582aa51e9ca35ba07870f7b9d9ad68c5c441fd52801be49a47216f617a83a; learning=3d201c8c837bae004343df19169b67ff19a9b1635bf222664dde455f6cf4b0e0
- 4.5: 33 items; packet=11be12bef6403499995255eea48fb08cab8940dcb11e2596b4b0822571f29c81; learning=7a0a02076b0ebb7dc48cef33e79698b3ee5a5a69351a7f92606f05fb93af38d4
- total: 112; duplicate=0; missing=0; unexpected=0.

## 模拟与状态

- protocol: five-round-five-persona-v1.
- each section: 5 rounds x 5 personas x every item; 25 attempts per item.
- route versions: 1 -> 2 -> 3; round 5 binds final route hash.
- proxy simulation: passed.
- independent acceptance: not_run.
- human acceptance: not_run.
- cold 24h retest: not_run.

## 共享源缺陷

- shared_defects.json records the visual inventory status mismatch; shared files were not modified.

## 校验

- command: python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py --project-root C:\开发\小工具\一本通学习系统_v7 --assignment reports\luna_dispatch\assignments.json --task-id LUNA-YBT-10 --delivery reports\luna_sections\LUNA-YBT-10\delivery.json
- validator output: {"status":"passed","task_id":"LUNA-YBT-10","errors":[]}; process exit code 0.
