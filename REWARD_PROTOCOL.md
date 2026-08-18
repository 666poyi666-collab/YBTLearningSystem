# 第一章奖励协议

奖励是独立轴，不等于 `mastery_status`、`unlock_status` 或课程覆盖。

| 事件 | 奖励 | 必须证据 |
|---|---:|---|
| `full_pass` | 10 | 未污染、独立尝试、过程可解释、完整正确 |
| `near_transfer` | 15 | 独立的近变式题目 ID、未污染、独立完成并解释；不能作为原题同一次作答的布尔字段 |
| `delayed_recall` | 25 | `review_due` 到期后的冷重做，过程可解释；污染题只能走这条复测路径，污染标记不清除 |
| `section_complete` | 50 | 小节所有完成闸门满足，后续按实际证据发放 |

不奖励：只听课、猜中、只报答案、提示 H1+ 后的当次答对、看答案后复述、同一事件重复提交。污染题不能发 `full_pass`/`near_transfer`；到期冷重做通过可以发独立的 `delayed_recall`，但不得把污染题改写成未污染。`full_pass` 由 `record-attempt` 入账，`near_transfer` 必须另走 `record-near-variant --variant-item-id <独立题目ID>`，程序拒绝把原题和近变式合并为一次事件。

程序用 `idempotency_key` 去重；`review_due` 未到期不能复测，复测失败回到 `CF` 并安排最小补课。干净的 U4/U5 也必须挂隔天复测；污染题冷复测通过可到 U6 并发 `delayed_recall`，但污染标记永不清除，不能作为未污染 `full_pass`/`near_transfer`。`section_complete` 另需全部题目 U6/U7、无开放复习和非空完成证据。第一章测试固定验证：课程-only/猜中/提示后均为 0 奖励，独立完整+近迁移+冷复测共 50 分。
