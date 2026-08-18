# LUNA-YBT-01 证据报告

## 当前状态

- status: `passed`（官方 validator 已通过）
- proxy_simulation: `passed`；independent_acceptance: `not_run`；human_acceptance: `not_run`；cold_24h_retest: `not_run`。
- 未读取或写入任何答案 sidecar；学习者 Markdown/HTML 不含题面、答案、内部 ID。

## 源绑定

- READY: `C:\开发\小工具\一本通学习系统_v7\reports\luna_dispatch\READY.json` SHA256 `f451e81c86e520577e176b12b73702945fdbf5cbac341ba9e4a93fa046a8c267`，status=`ready`。用户上一条消息中的手写 SHA 长度为 65，已忽略，以本地文件为准。
- assignments SHA256 `d9136bd27b2bf2e660e70c2ea34a044dd4225b2afa46b871700a429ac5c4cb8a`
- packet-build SHA256 `848c158cfe8dc8ab3b0ce49bc5ce50b0ba17ead8f85e7c34ccda530b282c8884`
- course catalog SHA256 `fd5a35abb8d8471a975089c9af44b2284ae4ca295e54f6d294cc37c26339c048`
- vision sidecar SHA256 `ee371622be9032f834480bc8dab3e37e7119f2236081459cf7897065ae1f03fc`
- visual source inventory SHA256 `6a74378730c450904fa22221df46560c99022b94eee7161b16f2cda67ae21ebf`
- visual inventory current SHA256 `1204674ef5345893677d6132c493b5a68bca667567b02983aca4226ac741fb22`，status=`passed`，missing_image_count=0。

## 覆盖

- 4.1: 52 项（18 例题、11 直属变式、23 A/B/C）
- ch3.s7: 34 项（10 例题、8 直属变式、16 A/B/C）
- 5.1: 24 项（9 例题、3 直属变式、12 A/B/C）
- micro专题1: 16 项（7 例题、1 直属变式、8 A/B/C）
- 合计：126 项，重复/缺失/越界：0。

## 课程转写核验

- 每个循环引用的课程均从当前 catalog 的 `transcript_file` 读取完整 `full_text`，并按课程主题关键词核对方法语义；课程仅来自允许的 Downloads 课程合集目录。

- `4.3.1.1.a 数列的概念和通项公式`：transcript SHA `6fc4d7edd383ceb9eb2a4723847043052ce119b4a02eb4f46aa3c0779ca142a2`，字符数 14015，句数 768，命中 `数列,通项,递推,前项和`。
- `4.3.1.1.b 通项型数列速解技巧`：transcript SHA `0b17a3339a14572b1fd483dfca45486a308686ea5b4ba43939a00835a403385b`，字符数 12048，句数 814，命中 `数列,通项`。
- `parabola_definition_equation`：transcript SHA `a2570cb8570459502877327e2a09f973846b1afe4e93750ec3f01f2513f284cf`，字符数 8689，句数 516，命中 `抛物线,焦点,准线,标准方程`。
- `intersection_algebra_upper`：transcript SHA `2f46b402bada83b4d4ea8be2a5291fd6a2d7ea3cb49132942a91c6f6a14e1cf7`，字符数 8310，句数 458，命中 `焦点`。
- `intersection_algebra_lower`：transcript SHA `a859f016e8348c40ec820756baa1c33636a784cc77dcdd4c71576e0353a49f92`，字符数 11392，句数 423，命中 `焦点`。
- `4.1.1.1 导数的定义（上）`：transcript SHA `2057379d716ca2c0b07556240866a439d8f436dca515dda693abb709bd8bb928`，字符数 11225，句数 562，命中 `导数,导函数,切线,变化率`。
- `4.1.1.1 导数的定义（下）`：transcript SHA `ec287878cbd4e5ff1f54410f5e52611ce2317b93d9261d56a39219d9f26f335a`，字符数 9929，句数 568，命中 `导数,切线,变化率`。
- `4.1.1.2 求在P点处的切线`：transcript SHA `8d60ce26878d2994b0413eaa8d6646126fd9cb395a708e54d8b0ae793fd8d796`，字符数 10460，句数 555，命中 `导数,切线`。
- `4.1.1.3 求过P点的切线`：transcript SHA `e5a39c03914f3b6d1d93a5c3e09d81cce488fad1357368e0edf528fffb543fd4`，字符数 14067，句数 804，命中 `导数,切线`。
- `4.1.1.4 判断切线条数问题`：transcript SHA `a43792ca0fe55b85433eb8b5cf235d94f4fd8c7debcc3f5b6115a13364dcd5d6`，字符数 12887，句数 685，命中 `导数,切线`。
- `4.1.1.5 公切线问题`：transcript SHA `6aa8c4f669dba566e40cbef17580ac455880d115eb5b2cb52be790f90fb9e4c2`，字符数 12969，句数 748，命中 `导数,切线`。
- `4.1.1.6 用切线算距离最值`：transcript SHA `e3cee8cee18d235aedc2ac626def3802aa087b8f04d561d1499e661a5146e35c`，字符数 11320，句数 736，命中 `导数,切线`。
- `4.1.1.7 隐函数求导`：transcript SHA `b7077674f00896a07ccdea537d9e77bde2419cd2101d3134f08cf1ee481840a0`，字符数 13945，句数 924，命中 `导数,切线,变化率`。
- `moving_point`：transcript SHA `da8ca5e664bf4438ef4a559263240bdf12e0494e1f67ab699ea7902293df3976`，字符数 12078，句数 602，命中 `空间向量,动点,法向量,垂直,夹角`。
- `direction_normal`：transcript SHA `d0ec9c67e89b5b7506aebe5aaa477553790cbc98b64eed43cb0fb63c8cde276c`，字符数 11760，句数 759，命中 `空间向量,法向量,垂直,夹角`。
- `parallel_perpendicular`：transcript SHA `94c0581735e82edeb9613c4adfa25230e22ca40b1d563b007099c54c0ee2a0bc`，字符数 13506，句数 869，命中 `空间向量,法向量,垂直`。
- `line_line_angle`：transcript SHA `0be63e83adac131e7f4e0cf99d0424f23b1981ee3a446d5b2fa6029733311147`，字符数 13148，句数 815，命中 `空间向量,动点,法向量,垂直,夹角`。
- `line_plane_angle`：transcript SHA `635245d9a4e1d53dd30ed409b7c8937636bfeae6901f599d72c2b38068138cf8`，字符数 7706，句数 500，命中 `空间向量,法向量,垂直,夹角`。
- `plane_plane_angle`：transcript SHA `5a01b37ad36ed0c8aed759b8b3f58ca2dbf7beb9c0aa1f9de4ee8b42f9afe23b`，字符数 11722，句数 622，命中 `空间向量,动点,法向量,垂直,夹角`。
- `distance`：transcript SHA `a476ddac1a574d6a287f789a2fd29600be72a04c67330998e26888dedc96d410`，字符数 8605，句数 475，命中 `空间向量,法向量,垂直`。

## 五轮代理复测

- 协议：`five-round-five-persona-v1`。每节 5 轮，每轮 5 人格，每人格逐项尝试；每项 25 条冻结记录。
- Round 1：入口、首行、视觉读取和自检缺口暴露。
- Round 2：补前置与继续动作。
- Round 3：补变式迁移和独立检查。
- Round 4：混合检索复测。
- Round 5：新鲜无答案上下文冷启动，所有项目通过并绑定最终 route hash。

## 验证命令

```powershell
python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py `
  --project-root C:\开发\小工具\一本通学习系统_v7 `
  --assignment reports\luna_dispatch\assignments.json `
  --task-id LUNA-YBT-01 `
  --delivery reports\luna_sections\LUNA-YBT-01\delivery.json
```

Validator 实际结果：

```json
{"status":"passed","task_id":"LUNA-YBT-01","errors":[]}
```
