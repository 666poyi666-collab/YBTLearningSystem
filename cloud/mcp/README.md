# Math Learning Cloud MCP

这是一本通数学学习系统主仓库内的 Cloudflare 远程 MCP，不是独立项目。

## 能力

- 读取教材/题目索引、课程映射、网课方法和时间片。
- 读取真实用户当前任务与学习状态。
- 幂等记录课程学习、作答、疑问、提示使用、题目通过、循环完成和进度快照。
- D1 保存查询索引和学习事件；R2 保存版本化题包、题图和课程转写。

## 安全边界

- `math:read` 与 `math:write` 分离。
- `math_mark_item_passed` 必须有冻结证据哈希、baseVersion 和用户确认。
- 内部模拟进度不得进入真实用户状态。
- 第二章缺少时间轴的课程返回 `null` 时间，不做推测。
- `OAUTH_RS_CLIENT_SECRET` 只通过 Cloudflare secret 配置。

## 当前状态

代码、D1 schema、私有 R2、共享 OAuth audience/scopes 和独立资源服务器凭据均已建立。远端迁移、生产部署和未授权访问验收已通过；`/healthz`、`/readyz` 与 protected-resource 元数据均为 200，无令牌 `/mcp` 为 401。

教材、题包、题图与课程转写尚未导入 D1/R2，因此当前是“服务和认证就绪、学习内容待导入”，不能把空内容库描述为完整生产数据。
