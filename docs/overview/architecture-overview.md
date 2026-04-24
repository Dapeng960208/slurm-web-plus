# Slurm Web Plus 架构总览（交付级）

本文是内部维护型架构主文档，内容基于当前仓库实现事实编写，避免概念性空话。

实现事实来源（必读代码边界）：

- `slurmweb/apps/gateway.py`
- `slurmweb/apps/agent.py`
- `frontend/src/router/index.ts`

本轮不重构也不替代 Antora/手册体系（`docs/modules/`、`docs/man/`、`docs/antora.yml`、`docs/update-materials`）。

## 1. 系统分层拓扑

```text
Browser (Vue SPA)
  -> Gateway (单入口 + JWT + 集群发现 + 代理)
     -> Agent (单集群边界 + 能力装配)
        -> slurmrestd (实时 Slurm 数据源)
        -> Prometheus (历史指标 / 节点指标数据源)
        -> PostgreSQL (持久化：用户缓存 / 历史作业 / 访问控制 / AI)
        -> LDAP (认证与用户基础信息来源)
        -> Cache Service (可选：缓存与命中统计)
```

边界约束（实现事实）：

- 浏览器只访问 Gateway，不直连 Agent。
- Gateway 不直接连接 PostgreSQL，不承载 Slurm 业务计算。
- Agent 是单集群边界，负责装配该集群的底层依赖与可选能力。
- “实时数据路径”和“历史数据路径”不是同一个数据源，接口也不同。

## 2. 前端架构

前端是 `Vue 3 + TypeScript + Vue Router + Pinia` 的 SPA，关键职责集中在三件事：

1. 路由与集群上下文（cluster-scoped routing）
2. 能力门控（capability gating）+ 权限门控（permission gating）
3. 统一 API 访问与轮询（GatewayAPI + DataPoller）

### 2.1 路由拓扑与 Settings / Cluster-scoped 页面

路由定义：`frontend/src/router/index.ts`。

结构特征（实现事实）：

- 全局入口：
  - `/login`、`/anonymous`、`/signout`
  - `/clusters`（集群选择页）
  - `/settings`（设置中心，非 cluster-scoped，但内部会选择一个“settings cluster”作为上下文）
- cluster-scoped 路由统一挂在 `/:cluster` 下：
  - `/:cluster/dashboard`
  - `/:cluster/analysis`
  - `/:cluster/ai`（兼容 `/:cluster/assistant -> /:cluster/ai`）
  - `/:cluster/jobs`、`/:cluster/jobs/history`、`/:cluster/jobs/history/:id`
  - `/:cluster/resources`、`/:cluster/node/:nodeName`
  - `/:cluster/qos`、`/:cluster/reservations`、`/:cluster/accounts`
  - `/:cluster/users/:user`、`/:cluster/users/:user/analysis`

### 2.2 基于 capability/permission 的菜单与路由守卫

前端门控由两类输入共同决定：

- capability：某集群“是否支持某能力”
- permission：当前用户“是否被授权使用某能力”

实现事实示例：

- Jobs History 路由守卫（`frontend/src/router/index.ts`）：
  - 必须 `cluster.persistence = true`
  - 且必须拥有 `view-history-jobs`
  - 否则重定向回 `/:cluster/jobs`
- Settings AI（`/settings/ai`）：
  - 必须集群支持 AI（`hasClusterAIAssistant`）
  - 且必须拥有 `manage-ai`
  - 否则重定向回 settings 主页
- Settings Access Control（`/settings/access-control`）：
  - 必须集群支持访问控制（`hasClusterAccessControl`）
  - 否则回到 account settings

菜单门控（实现事实）：

- `frontend/src/components/MainMenu.vue` 基于 `permission` + `feature` 双条件渲染导航项。
- AI 菜单由 `hasClusterAIAssistant(cluster)` 决定是否启用。
- Jobs History 菜单由 `cluster.persistence` 决定是否启用，同时仍受 `view-history-jobs` 权限约束。

### 2.3 `GatewayAPI.ts` 与 `DataPoller.ts` 职责

统一 API 客户端：`frontend/src/composables/GatewayAPI.ts`

- 定义 Gateway 侧 typed API（`/api/...`）。
- 对 `/api/clusters` 返回的集群对象进行归一化：
  - `access_control` 兼容旧字段与 `capabilities.access_control`
  - `ai` 归一化为固定字段集合（enabled/configurable/streaming/...）
  - `permissions` 归一化为 `policy/custom/merged` 三来源

轮询器：`frontend/src/composables/DataPoller.ts`

- 定期轮询某个 cluster-scoped 接口（callback 为 `GatewayAPI` 的方法名）。
- 支持请求取消（`gateway.abort()`），在切换集群/切换接口/卸载组件时中止在途请求。
- 统一处理认证失败、权限错误、服务端错误的 UI 降级路径。

## 3. Gateway 架构

Gateway 入口：`slurmweb/apps/gateway.py`，视图层：`slurmweb/views/gateway.py`。

### 3.1 认证、JWT 与匿名模式

实现事实：

- 认证开关由 gateway 配置控制：
  - 开启：`POST /api/login` 通过 LDAP 认证，签发 JWT
  - 关闭：`GET /api/anonymous` 签发匿名 JWT
- JWT 由 `RFLTokenizedWebApp` 管理，前端通过 `Authorization: Bearer <token>` 访问后续接口。

### 3.2 集群发现、`/api/clusters` 能力聚合

发现机制（实现事实）：

- Gateway 从配置 `agents.url` 列表轮询 Agent 的 `/info`。
- 对 Agent 版本做最小版本检查（避免不兼容 API）。
- 发现结果缓存 300 秒，可强制刷新。

`GET /api/clusters` 聚合机制（实现事实）：

1. 对每个已发现 Agent 先请求该用户在该集群的 `/permissions`（带 token）。
2. 若 `ui.hide_denied = true` 且该集群 `permissions.actions` 为空，则隐藏该集群。
3. 返回给前端的 cluster 对象包含：
   - `permissions`
   - 若干顶层布尔能力字段（如 `persistence`、`access_control`、`node_metrics`、`user_metrics` 等）
   - `ai` 与 `capabilities`（用于细粒度能力描述）

### 3.3 Agent proxy、SSE 透传

实现事实：

- Gateway 将大多数集群接口以“透明代理”方式暴露在 `/api/agents/<cluster>/...` 下。
- 普通 JSON 接口走 aiohttp 异步代理。
- SSE（AI chat stream）走 `requests` 的 streaming proxy，透传事件流，并设置：
  - `Cache-Control: no-cache`
  - `X-Accel-Buffering: no`

### 3.4 登录后用户缓存同步到 Agent

实现事实（见 `slurmweb/views/gateway.py::async_cache_user_on_agents`）：

- 登录成功后，Gateway 会把认证用户的 `username/fullname/groups` 推送到“已发现且数据库可用”的 Agent：
  - `POST <agent>/v{version}/users/cache`
- 目的：
  - 缓存用户基础信息到 Agent 本地数据库
  - 写入/刷新策略快照（policy_roles/policy_actions）
  - 支撑访问控制管理页与 LDAP Cache 页的用户维度数据

## 4. Agent 架构

Agent 入口：`slurmweb/apps/agent.py`，视图层：`slurmweb/views/agent.py`。

### 4.1 应用装配入口与可选能力开关

Agent 在启动时按配置装配以下模块，并在依赖缺失时降级：

- slurmrestd 客户端（实时数据）
- cache service（可选）
- metrics collector（可选：导出 `/metrics`）
- Prometheus 查询（可选：历史指标/节点指标/用户指标）
- PostgreSQL stores（可选：用户缓存/历史作业/访问控制/AI）
- AI 服务（可选）
- 访问控制 store（可选）
- 用户分析/用户指标聚合（可选）
- 节点实时/历史指标（可选）

### 4.2 `slurmrestd`、Prometheus、PostgreSQL stores 初始化边界

实现事实（`slurmweb/apps/agent.py`）：

- `users_store`（数据库基础能力）：
  - 仅当 `[database] enabled = yes` 且连接校验通过才启用
- `jobs_store`（历史作业持久化）：
  - 仅当 `[persistence] enabled = yes` 且数据库可用才启用
  - 负责后台快照写入并提供 `/jobs/history` 查询
- `access_control_store`（访问控制）：
  - 仅当 `[persistence] access_control_enabled = yes` 且数据库可用才启用
  - 将自定义角色动作合并进权限解析
- `user_analytics_store` / `user_metrics_store`（用户分析）：
  - 仅当 `[user_metrics] enabled = yes` 且数据库 + metrics + jobs_store 均可用才启用
- `node_metrics_db`（节点指标）：
  - 仅当 `[node_metrics] enabled = yes` 才启用（Prometheus host/job 由配置提供）
- `ai_service`（AI）：
  - 仅当 `[ai] enabled = yes` 且数据库可用才启用
  - AI 密钥加密使用 `jwt.key` 派生（不通过前端配置）

### 4.3 能力暴露（`/info`）

实现事实（`slurmweb/views/agent.py::info`）：

- `/info` 返回顶层能力布尔值：`database`、`persistence`、`access_control`、`node_metrics`、`user_metrics`
- 同时返回：
  - 顶层 `ai`（对象）
  - `capabilities`（对象，包含更细粒度字段，例如 `user_metrics`、`user_analytics` 的结构化描述）

## 5. 数据流（固定四条链路）

### 5.1 实时 Slurm 查询链路

```text
Frontend
  -> Gateway /api/agents/<cluster>/jobs|job|nodes|node|...
  -> Agent /v{version}/jobs|job|nodes|node|...
  -> slurmrestd
```

典型接口（经 Gateway）：

- `GET /api/agents/<cluster>/jobs`
- `GET /api/agents/<cluster>/job/<id>`
- `GET /api/agents/<cluster>/nodes`
- `GET /api/agents/<cluster>/node/<name>`

### 5.2 历史指标链路（Prometheus）

```text
Frontend
  -> Gateway /api/agents/<cluster>/metrics/<metric>
  -> Agent /v{version}/metrics/<metric>
  -> Prometheus HTTP API
```

节点指标（实时/历史）：

```text
Frontend
  -> Gateway /api/agents/<cluster>/node/<name>/metrics(/history)
  -> Agent
  -> Prometheus HTTP API
```

### 5.3 历史作业与用户分析链路（PostgreSQL）

后台写入（实现事实）：

```text
Agent JobsStore background thread
  -> slurmrestd jobs snapshot
  -> PostgreSQL job_snapshots (partitioned)
  -> PostgreSQL user_tool_daily_stats (user analytics rollup)
```

前端查询（经 Gateway）：

- 历史作业：
  - `GET /api/agents/<cluster>/jobs/history`
  - `GET /api/agents/<cluster>/jobs/history/<id>`
- 用户分析：
  - `GET /api/agents/<cluster>/user/<username>/activity/summary`
  - `GET /api/agents/<cluster>/user/<username>/metrics/history?range=hour|day|week`

### 5.4 AI 对话与工具执行链路

```text
Frontend (SSE)
  -> Gateway /api/agents/<cluster>/ai/chat/stream
  -> Agent /v{version}/ai/chat/stream
  -> AIService (provider client + tool registry)
     -> read-only tool calls (jobs/nodes/metrics/history/...)
  -> PostgreSQL (configs / conversations / messages / tool_calls)
```

边界（实现事实）：

- AI 工具仅允许内部白名单只读工具（见 `slurmweb/ai/tools.py`）。
- 工具执行同样受用户 RBAC 约束，不能绕过 `rbac_action(...)`。

## 6. 能力门控模型（Agent 暴露 -> Gateway 聚合 -> 前端消费）

### 6.1 Agent 暴露

Agent `/info` 返回两层信息：

- 顶层布尔字段（便于旧前端/快速门控）
- `capabilities`（用于细粒度能力描述）

例（实现事实，字段名以实际返回为准）：

- `database`、`persistence`、`access_control`、`node_metrics`、`user_metrics`
- `ai`（对象）
- `capabilities.job_history`、`capabilities.ldap_cache`、`capabilities.access_control`、`capabilities.node_metrics`
- `capabilities.ai`、`capabilities.user_metrics`、`capabilities.user_analytics`

### 6.2 Gateway 聚合

Gateway `/api/clusters` 会把：

- 当前用户在该集群的 `permissions`
- 该集群能力字段（含顶层字段与 `capabilities`）

合并成“前端用于渲染与路由守卫”的 cluster 描述对象。

### 6.3 前端消费

实现事实（`frontend/src/composables/GatewayAPI.ts` + `frontend/src/router/index.ts`）：

- 前端对 cluster 对象做归一化（兼容顶层字段与 `capabilities.*`）。
- 菜单门控 + 路由守卫均使用 capability + permission 双门控。
- 后端 RBAC 仍是最终裁决，前端门控仅用于用户体验与预防性导航。

## 7. 关键依赖与部署关系（含降级行为）

### 7.1 PostgreSQL

依赖 PostgreSQL 的能力（实现事实）：

- 用户缓存与 LDAP Cache（`users_store`）
- 历史作业持久化（`jobs_store`）
- 访问控制自定义角色（`access_control_store`）
- AI 配置/会话/审计（`ai_*_store`）
- 用户分析聚合（`user_analytics_store` / `user_metrics_store`）

降级行为（实现事实）：

- 若 `[database] enabled = yes` 但连接失败：Agent 会记录 warning 并禁用数据库相关能力，实时 slurm 查询仍可用。

### 7.2 Prometheus

依赖 Prometheus 的能力（实现事实）：

- 历史指标查询（`/metrics/<metric>` API 的数据源）
- 节点实时/历史指标（`node_metrics_db`）
- 用户指标聚合（`user_metrics` 启用条件之一）

降级行为（实现事实）：

- metrics 关闭时，相关 API 返回 `501` 并给出原因；前端应显示不可用说明而不是空白。

### 7.3 LDAP

依赖 LDAP 的能力（实现事实）：

- Gateway `POST /api/login`（认证开启时）
- `GET /api/users`（认证开启时才可用）

降级行为（实现事实）：

- 认证关闭时，前端应走匿名模式；用户列表接口返回 `501`。

### 7.4 Cache Service

依赖 cache service 的能力（实现事实）：

- cache 命中统计与 reset（`/cache/stats` / `/cache/reset`）

降级行为（实现事实）：

- cache 关闭时，接口返回 `501`；前端应提示“缓存服务禁用/不可用”。

## 8. 新旧文档边界

- 本文与 `docs/` 下的 Markdown 文档是内部维护入口（面向开发、交付、测试与 AI 协作）。
- Antora/手册体系（`docs/modules/`、`docs/man/`、`docs/utils/`）属于对外/站点资料，本轮不重构；如需改动需在 `docs/tracking/` 明确记录并同步入口。
