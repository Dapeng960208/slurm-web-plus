# Slurm Web Plus 项目概览

## 1. 项目定位

Slurm Web Plus 是面向 Slurm HPC 集群的 Web 管理与分析平台。它在不替代 Slurm 原生能力的前提下，提供统一的监控、查询、分析、权限和设置入口。

当前仓库覆盖的核心能力包括：

- 集群实时概览与分析
- 作业、历史作业、节点、资源、账户、用户、QOS、预约查询
- 基于 PostgreSQL 的历史作业持久化、LDAP 用户缓存、访问控制和 AI 配置持久化
- 基于 Prometheus 的集群指标、节点指标和用户分析
- 基于角色的细粒度路由权限控制

## 2. 当前主要入口

全局入口：

- `/clusters`
- `/settings`
- `/login`
- `/anonymous`
- `/signout`
- `/forbidden`

集群范围入口：

- `/:cluster/dashboard`
- `/:cluster/analysis`
- `/:cluster/ai`
- `/:cluster/jobs`
- `/:cluster/jobs/history`
- `/:cluster/resources`
- `/:cluster/qos`
- `/:cluster/reservations`
- `/:cluster/accounts`
- `/:cluster/users/:user`
- `/:cluster/me`

## 3. 权限模型

当前有效权限模型为 `resource:operation:scope`：

- `resource` 采用“主路由 + 子资源”形式，例如 `settings/cache`、`user/profile`、`jobs/filter-qos`
- `operation` 当前支持 `view`、`edit`、`delete`
- `scope` 当前支持 `*` 和 `self`

已实现的规则特性：

- 精确资源匹配，例如 `jobs:view:*`
- 前缀资源匹配，例如 `settings/*:view:*`
- 全局通配，例如 `*:*:*`
- owner-aware 规则，例如 `user/profile:view:self`
- `edit` / `delete` 自动满足 `view`

## 4. 能力启用条件

系统当前按基础依赖自动推导能力，不再依赖独立业务开关：

| 基础条件 | 自动启用能力 |
|---|---|
| `[database] enabled = yes` | LDAP Cache、Jobs History、Access Control、AI |
| `[metrics] enabled = yes` | cluster metrics |
| `node_metrics.prometheus_host` 已配置 | node metrics |
| 数据库 + metrics | user metrics、user analytics |

说明：

- 旧配置项 `persistence.enabled`、`persistence.access_control_enabled`、`user_metrics.enabled`、`node_metrics.enabled`、`ai.enabled` 仍保留兼容定义，但不应继续作为新配置语义使用。
- 前端和 `/info` 看到的是推导后的能力状态。

## 5. 角色模型

数据库支持开启后，如果 `roles` 表为空，系统会自动预置三个角色：

- `user`
  - 默认只包含可查看权限
- `admin`
  - 包含全量资源的 `view/edit/delete` 组合
- `super-admin`
  - 直接使用 `*:*:*`

这些角色只会在首次空表时写入，后续允许通过页面继续编辑。

## 6. 旧权限兼容

新权限启用后，旧权限名仍通过内置映射自动转换，例如：

- `cache-view` -> `settings/cache:view:*`
- `cache-reset` -> `settings/cache:edit:*`
- `roles-view` -> `settings/access-control:view:*`
- `roles-manage` -> `settings/access-control:edit:*` + `settings/access-control:delete:*`
- `view-ai` -> `ai:view:*`
- `manage-ai` -> `settings/ai:edit:*`

当新权限系统不可用时，系统继续按旧 `actions[]` 逻辑鉴权，不改变原有行为。
