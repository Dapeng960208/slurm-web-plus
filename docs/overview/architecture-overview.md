# Slurm Web Plus 架构概览

## 1. 分层结构

系统保持 Browser -> Gateway -> Agent 的三层结构：

```text
Browser (Vue SPA)
  -> Gateway
     -> Agent
        -> slurmrestd
        -> Prometheus
        -> PostgreSQL
        -> LDAP
        -> Cache Service
```

职责边界保持不变：

- 浏览器只访问 Gateway
- Gateway 负责认证、集群发现、聚合权限与代理转发
- Agent 负责单集群能力装配、权限判定和后端存储集成

## 2. 权限链路

当前权限链路已经收敛为“规则优先、动作兼容”：

1. 文件策略 `policy.ini` 继续提供原始 `actions[]`
2. `AccessControlPolicyManager` 通过内置映射把旧动作转换为 `rules[]`
3. 数据库自定义角色从 `roles.permissions` 读取新规则，同时兼容 `roles.actions`
4. policy + custom 合并后统一产出：
   - `roles`
   - `actions`
   - `rules`
   - `sources.policy/custom/merged`
5. 前端运行时使用 `hasRoutePermission(...)` 按 `resource:operation:scope` 判定访问

对应核心实现：

- `slurmweb/permission_rules.py`
- `slurmweb/access_control.py`
- `slurmweb/persistence/access_control_store.py`
- `frontend/src/stores/runtime.ts`

与本轮管理扩展直接相关的资源已经迁移为：

- `admin/ai`
- `admin/cache`
- `admin/ldap-cache`
- `admin/access-control`

补充说明：

- `policy.yml` / `policy.ini` 已移除 `view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage`、`view-ai`、`manage-ai` 这 7 个旧动作入口。
- `admin-manage` 现在只对应 `*:*:*`，仅作为 `super-admin` 兼容别名保留。
- `jobs` 资源同时支持 `*` 与 `self` scope，最终 owner 判定只在 Agent 后端执行。

当前默认角色语义为：

- `user`：非 `Admin` 页面默认 `view`，同时拥有 `jobs:view|edit|delete:self`
- `admin`：默认拥有 `*:view:*` 与 `*:edit:*`
- `admin` 不默认拥有 `*:delete:*`
- `super-admin`：默认拥有 `*:*:*`

## 3. 能力推导链路

Agent 当前不再以独立业务开关驱动能力，而是根据基础依赖推导：

- 数据库可用：
  - 初始化 `UsersStore`
  - 自动启用 Jobs History store
  - 自动启用 Access Control store
  - 自动启用 AI service
- Prometheus 可用：
  - 提供 cluster metrics
  - 当 `node_metrics.prometheus_host` 存在时提供 node metrics
- 数据库 + Prometheus 同时可用：
  - 提供 user metrics / user analytics

这些推导结果会同步暴露到：

- Agent `/info`
- Gateway `/api/clusters`
- 前端 `ClusterDescription.capabilities`

## 4. AI 接口编排链路

本轮 AI 助手不再把工具层直接绑定到底层数据源，而是改为先收敛到 Agent 进程内的接口适配层：

```text
AI model
  -> AIService planner loop
     -> AIToolRegistry
        -> AIAgentInterfaceRegistry
           -> Agent 查询/写接口语义
              -> slurmrestd / PostgreSQL / Prometheus
```

当前约束：

- 模型看到的是“接口能力目录”，而不是底层实现细节
- 单个问题可连续调用多个接口后再回答，例如 `job` + `jobs/history`
- 对用户工具资源推荐类问题，优先使用 `user/tools/analysis` 聚合证据，再视情况补查 `jobs/history`
- 查询接口继续复用 Agent 已有资源规则和 owner-aware 逻辑
- AI 写接口不再额外走 `super-admin` 总闸，而是复用 Agent 接口层现有权限校验
- 当接口层拒绝访问时，工具执行会把权限错误与状态码回传给模型和执行轨迹
- 若模型错误回显内部 `tool_request` / `interface_key` / `arguments` envelope，AIService 不会把它透传为最终消息，而是继续要求模型输出合法 `final`

执行轨迹链路同步变为：

- SSE `tool_start` / `tool_end`
- `tool_end` 记录 `interface_key` 与 `status_code`
- `ai_conversations/<id>` 会返回历史 `tool_calls`
- `ai_tool_calls` 持久化接口名、状态码、输入、摘要、错误和耗时

## 5. 集群管理写路径

本轮在不改变三层架构的前提下，补齐了从前端到 `slurmrestd` 的单对象管理链路：

```text
Vue 页面
  -> Gateway `/api/agents/<cluster>/...`
     -> Agent `/v<version>/...`
        -> slurmrestd `/slurm/...` 或 `/slurmdb/...`
```

关键点：

- Gateway 现在支持把 `DELETE` body 继续代理给 Agent
- Agent 为 `jobs self` 先查 owner，再按 `self` 校验
- `slurmweb.slurmrestd` 扩展为通用 `GET/POST/DELETE` 请求层
- `analysis/ping`、`analysis/diag` 走集群级系统接口

典型写路径包括：

- `job/<id>/update`
- `job/<id>/cancel`
- `node/<name>/update`
- `node/<name>/delete`
- `reservation`
- `reservation/<name>/update`
- `reservation/<name>/delete`
- `accounts`
- `users`
- `qos`

## 6. slurmrestd 版本兼容

当前版本兼容策略为：

- `0.41-0.44`
  - 开放本轮主写路径
- `0.39-0.40`
  - 保持读兼容
  - 写操作返回 `501` 降级结果

## 7. 数据模型

访问控制相关表当前包括：

- `users`
  - 缓存 LDAP 用户信息与 policy 快照
- `roles`
  - `actions JSONB`
  - `permissions JSONB`
- `user_roles`
  - 用户与自定义角色绑定

新增迁移：

- `slurmweb/alembic/versions/20260425_0007_access_control_permissions.py`
- `slurmweb/alembic/versions/20260427_0008_ai_tool_interface_audit.py`

说明：

- 当前仍兼容读取 `roles.actions`，但启动时会把已废弃的 7 个旧动作迁入 `roles.permissions` 后移除。
- 历史 `roles.actions` 中如果存在 `admin-manage`，启动时会统一补齐 `*:*:*` 到 `roles.permissions`。
- `permissions` 为空时，后端仍会根据剩余兼容动作自动推导规则。
- `ai_tool_calls` 当前新增：
  - `interface_key`
  - `status_code`

## 8. 前端权限消费点

前端已经把以下关键位置切到新规则：

- `runtime.hasRoutePermission(...)`
- 主菜单 `MainMenu.vue`
- 路由守卫 `router/index.ts`
- Settings tabs
- `AdminLayoutView.vue`
- `SettingsAccessControl.vue` 权限矩阵
- `SettingsAI.vue`
- `SettingsCache.vue`
- `SettingsLdapCache.vue`
- `AssistantView.vue`
- `UserView.vue`
- `JobsView.vue` / `JobView.vue`
- `ResourcesView.vue` / `NodeView.vue`
- `ReservationsView.vue`
- `AccountsView.vue` / `AccountView.vue`
- `QosView.vue`
- `ClusterAnalysisView.vue`

旧 `hasClusterPermission(...)` 仍保留，用于兼容尚未迁移的 action 级消费点和旧测试数据。

## 9. GitHub 自动 CI 与 triage 链路

本轮新增一条独立于运行时架构之外的仓库交付链路：

```text
GitHub push / pull_request(main)
  -> GitHub Actions workflows
     -> 单版本后端/前端检查
     -> 统一 artifact 目录
        -> stdout.log
        -> result.json
        -> failure-context.json
        -> junit.xml (tests only)
  -> 手工 CI Triage workflow
     -> 按 run_id 下载 artifact
     -> 生成 triage-context.json
```

当前职责分工：

- `python-ci.yml`
  - 自动后端单元测试
  - 固定 `Python 3.12`
  - 仅收集 `slurmweb/tests`
- `frontend-ci.yml`
  - 自动前端单元测试
  - 固定 `Node 18`
- `frontend-static.yml`
  - 自动 `lint`、`type-check`、`build`
  - 固定 `Node 18`
- `python-os-ci.yml`
  - 手工 rpm/deb OS 集成矩阵
  - 同样仅收集 `slurmweb/tests`
- `ci-triage.yml`
  - 手工聚合结构化 CI artifact

仓库内置 AI 当前不在这条链路内：

- 不直接读取 GitHub Actions run
- 不自动修改代码
- 不自动创建 PR

因此本轮 CI 设计目标不是“自动修复”，而是先把失败上下文标准化为后续 agent 可消费的数据接口。
