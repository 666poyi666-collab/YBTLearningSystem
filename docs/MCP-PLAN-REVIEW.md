# 绘画 ID 对话方案核对

来源任务：`01a014e8-a429-7583-9dcc-7e7b5befe270`

## 可以保留的判断

- 必须使用 Cloudflare 远程 MCP，不能依赖电脑常开。
- D1 保存可查询索引和学习事件，R2 保存版本化题包、题图与课程转写。
- 学习进度采用事件记录、幂等键和版本控制，不只覆盖一个百分比。
- 题目、课程、教师方法、时间片和真实用户进度应在一次学习上下文查询中闭合。
- 第一章有句段时间轴；第二章没有原音视频时不能从全文伪造时间轴。

## 必须修改的部分

1. 不创建独立 `math-cloud-mcp` 仓库；代码必须位于数学主仓库 `cloud/mcp`。
2. 不采用旧 `McpAgent`。使用 Cloudflare `createMcpHandler` + `@modelcontextprotocol/server` 2.0，目标协议为 MCP 2026-07-28，并保留旧 stateless 客户端兼容。
3. `initialize` 不再是新版唯一验收；必须验证 `server/discover`、无 session ID、tools/list 和实际工具调用。
4. 旧方案对 ChatGPT Plus 的限制判断已经不符合当前账户实际状态：当前 Plus 账户已经连接多个自定义 OAuth MCP。数学可以在 OAuth/部署完成后直接作为 ChatGPT 插件连接，不必先另造一个使用 OpenAI API 的聊天壳。
5. Cloudflare Pages 不是 MCP 的必要条件。现有学习网页可在主产品需要时部署 Pages，但 MCP Worker、D1、R2 和 OAuth 应独立验收。
6. 共享 `poyi-oauth-as` 当前没有 `math:read` / `math:write`，需要恢复源码、登记资源、创建独立 resource-server secret 后才能部署生产。
7. Cloudflare 免费层 D1 已达到 10/10，后续再增加数据库前必须升级或清理经确认无依赖的重复资源。

## 可直接发给原任务的建议

> 方案方向保留，但请停止创建独立 MCP 仓库。数学 MCP 已改为主仓库 `cloud/mcp`，使用 MCP 2026-07-28 无状态架构；Cloudflare Worker、D1、R2 已创建。下一步先恢复并版本化共享 OAuth AS，增加 `math:read/write`，再执行 D1 迁移、资料导入、正式部署和 ChatGPT 连接。第二章没有原音视频时继续返回“无可靠时间轴”，不能估算伪造。ChatGPT Plus 当前账户已经能连接自定义 OAuth MCP，因此不再把 Business/Enterprise 当成上线前提。
