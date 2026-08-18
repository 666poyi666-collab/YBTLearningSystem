# 浏览器采集协议

版本：1.2

`scripts/browser_collect.py` 是数学项目浏览历史的可复现、只读采集器。它只把 Edge/Chrome 的 `History` 数据库复制到临时目录，再以 SQLite `mode=ro` 查询；原始浏览器数据库不写入。

采集器禁止读取 cookies、localStorage、密码、浏览器 profile、账号凭据；禁止输入账号、发送消息、上传文件或改变网页状态。浏览器可见 DOM 如果由已登录会话另行读取，必须以 `dom_evidence` 独立记录，不能伪装成历史证据。

证据字段至少包括 `collector_version`、`history_verified_at`、每个历史副本的 SHA-256、`8.5` 与 `8.5课程` 的独立状态和采集事件。只允许数学项目中的这两个精确对话进入学习上下文；其他相似名称均为范围外数据。

网页正文由已登录 Edge 会话另行只读采集并存为摘要：`8.5课程` 提供听课核验、逐动作学习和掌握判定规则；`8.5` 当前为空对话。不得把空对话补写成历史内容。

运行：

```powershell
python scripts/browser_collect.py
```

输出：`data/browser_evidence.json` 与追加式 `data/browser_collection_events.jsonl`。
