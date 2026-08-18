# DeepSeek 独立上下文协议

纯文本 DeepSeek 的独立做题/掌握判断只接收 `data/packets/<section>/student_packet.json` 生成的 context，不接收 `answer_sidecar.json`，也不接收 `lesson_packet.json`。`lesson_packet.json` 仅供听课阶段讲解例题，不能用于独立正确、近迁移或奖励判定。

运行时必须同时读取同节 `learning_packet.json` 的 `learning_cycles`。`learning_plan` 和完整 Markdown 可以保留整节路线供用户核对；实际执行只认 `route_support.sequential_learning_packet.current_cycle`。首次默认第一个循环，看完后只执行该循环对应的知识点、教学例题、紧跟变式和 A/B/C 题。当前循环验收未通过时，不得在回复中展示或推进后续循环。提示污染后的未见题或延迟闭卷复测仍属于当前循环，补证完成后才允许递增循环序号。

放行条件：

1. `packet_type=DEEPSEEK_STUDENT_PACKET`；
2. `status=VERIFIED`；
3. 页数、题号、公式定界符、图片引用和视觉侧车全部通过；
4. context 中不存在 `answer_text`、答案、解析或答案侧车路径；
5. worker contract 固定为 `opencode-go/deepseek-v4-flash`、`max`、1000000 context。

context 可以独立生成，但只有对应题包 `VERIFIED` 时才会通过消费门禁；当前以 `validate_context` 的实时结果为准：四节当前构建均为 `VERIFIED` 且无 unresolved。这个状态只证明 DeepSeek 能独立消费完整无答案上下文，不签发学生掌握或奖励；若任一节重新出现 `UNVERIFIED` 或 unresolved，只能报告缺口，不能讲题、报答案或签发掌握/奖励。

## 独立消费探针

`scripts/run_deepseek_http_probe.py` 使用本机 `10100/v1/chat/completions` 直接请求上述模型合约，向 DeepSeek 提供当前 1.1 context 的无答案投影。模型必须返回完整的逐题回显、必听课程、知识点、类型题和 A/B/C 顺序；本地校验器同时验证 `context_sha256`、canary、probe tokens、题目集合、视觉状态、模型/effort/context window 以及 `mastery_not_assessed=true`。原始响应保存在 `data/deepseek_http_probe_1.1.raw.json`，验收报告保存在 `data/deepseek_http_probe_1.1.json`。这是独立使用和内容理解的运行证据。

全章消费由 `scripts/deepseek/chapter_probe.py` 独立复跑，当前四节 `1.1 / 1.2+1.3 / 1.4 / micro专题1` 均为 `gate_passed=4`、`dispatched=4`、`consumption_passed=4`；对应回执保存在 `scripts/deepseek/out/chapter_probe_latest.json`。这证明四节无答案上下文均可被独立消费，但不签发学生掌握或奖励。
