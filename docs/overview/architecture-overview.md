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

- `admin/system`
- `admin/ai`
- `admin/cache`
- `admin/ldap-cache`
- `admin/access-control`

`jobs` 资源同时支持 `*` 与 `self` scope，最终 owner 判定只在 Agent 后端执行。

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

## 4. 集群管理写路径

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
- `analysis/ping`、`analysis/diag` 与 `admin/system/*` 走集群级系统接口

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

## 5. slurmrestd 版本兼容

当前版本兼容策略为：

- `0.41-0.44`
  - 开放本轮主写路径
- `0.39-0.40`
  - 保持读兼容
  - 写操作返回 `501` 降级结果

## 6. 数据模型

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

说明：

- 当前采用新旧字段双读双写过渡。
- `permissions` 为空时，后端会根据旧 `actions` 自动推导规则。

## 7. 前端权限消费点

前端已经把以下关键位置切到新规则：

- `runtime.hasRoutePermission(...)`
- 主菜单 `MainMenu.vue`
- 路由守卫 `router/index.ts`
- Settings tabs
- `AdminLayoutView.vue` / `AdminSystemView.vue`
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
