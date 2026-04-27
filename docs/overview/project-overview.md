# Slurm Web Plus 项目概览

## 1. 项目定位

Slurm Web Plus 是面向 Slurm HPC 集群的 Web 管理与分析平台。它在不替代 Slurm 原生能力的前提下，提供统一的监控、查询、分析、权限和设置入口。

当前仓库覆盖的核心能力包括：

- 集群实时概览与分析
- 作业、历史作业、节点、资源、账户、用户、QOS、预约查询与单对象管理
- 基于 PostgreSQL 的历史作业持久化、LDAP 用户缓存、访问控制和 AI 配置持久化
- 基于 Prometheus 的集群指标、节点指标和用户分析
- 基于角色的细粒度路由权限控制
- 集群级 `Admin` 页面统一管理 AI、Cache、LDAP Cache 与 Access Control，系统概览统一收口到 `analysis`
- 面向 `main` 分支协作的 GitHub 自动测试与结构化 CI 结果产物

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
- `/:cluster/admin`
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

- `resource` 采用“主路由 + 子资源”形式，例如 `admin/ai`、`user/profile`、`jobs/filter-qos`
- `operation` 当前支持 `view`、`edit`、`delete`
- `scope` 当前支持 `*` 和 `self`

已实现的规则特性：

- 精确资源匹配，例如 `jobs:view:*`
- 前缀资源匹配，例如 `admin/*:view:*`
- 全局通配，例如 `*:*:*`
- owner-aware 规则，例如 `jobs:view:self`、`user/profile:view:self`
- `edit` / `delete` 自动满足 `view`

当前与管理扩展直接相关的关键规则包括：

- `jobs:view|edit|delete:*|self`
- `resources:view|edit|delete:*`
- `reservations:view|edit|delete:*`
- `accounts:view|edit|delete:*`
- `users-admin:view|edit|delete:*`
- `qos:view|edit|delete:*`
- `analysis:view:*`
- `admin/ai:view|edit|delete:*`
- `admin/cache:view|edit:*`
- `admin/ldap-cache:view|edit:*`
- `admin/access-control:view|edit|delete:*`

## 4. 能力启用条件

系统当前按基础依赖自动推导能力，不再依赖独立业务开关：

| 基础条件 | 自动启用能力 |
|---|---|
| `[database] enabled = yes` | LDAP Cache、Jobs History、Access Control、AI |
| `[metrics] enabled = yes` | cluster metrics |
| `node_metrics.prometheus_host` 已配置 | node metrics |
| 数据库 + metrics | user metrics、user analytics |

说明：

- 已删除旧配置项 `persistence.enabled`、`persistence.access_control_enabled`、`user_metrics.enabled`、`node_metrics.enabled`、`ai.enabled`。
- 前端和 `/info` 看到的是推导后的能力状态。

## 5. 角色模型

数据库支持开启后，如果 `roles` 表为空，系统会自动预置三个角色：

- `user`
  - 默认包含非 `admin/*` 页面只读权限
  - 作业默认使用 `jobs:view:self`
  - 默认允许 `jobs:edit:self`
  - 默认允许 `jobs:delete:self`
  - 默认允许 `user/analysis:view:self`
- `admin`
  - 默认包含 `*:view:*`
  - 默认包含 `*:edit:*`
  - 默认不包含 `*:delete:*`
- `super-admin`
  - 直接使用 `*:*:*`

这些角色只会在首次空表时写入，后续允许通过页面继续编辑。

## 7. 发布命名说明

当前仓库的对外发布名已经切换为 `slurm-web-plus`，但为了降低升级风险，代码层仍保留一部分兼容命名：

- 对外品牌名、前端页面标题、包名入口以 `slurm-web-plus` 为主
- Python 包目录与导入名继续保持 `slurmweb`
- 现有 systemd service、默认配置目录、运行时目录仍大量保留 `slurm-web` 兼容前缀

因此，当前状态更准确地说是“发布名已切换，部署层兼容迁移未完全结束”，后续发布需要同时审阅 `conf/**`、`lib/**` 和运维脚本命名策略。

## 6. 旧权限兼容

新权限启用后，仍保留少量旧动作兼容映射：

- `cache-view` -> `admin/cache:view:*` + `admin/ldap-cache:view:*`
- `cache-reset` -> `admin/cache:edit:*`
- `admin-manage` -> `*:*:*`

收口说明：

- `view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage`、`view-ai`、`manage-ai` 已不再作为可配置动作入口。
- 普通用户默认的 `jobs:view|edit|delete:self` 与 `user/analysis:view:self` 来自数据库种子角色 `user`，不再来自 vendor policy 动作。
- 当新权限系统不可用时，普通用户也不再获得自有 Jobs 的旧动作兜底。

## 8. GitHub CI 交付基线

当前仓库的 GitHub 自动验证基线为：

- `pull_request` 到 `main`
- `push` 到 `main`

自动检查固定版本：

- 后端：`Python 3.12`
- 前端：`Node 18`

自动检查范围：

- 后端单元测试
- 前端单元测试
- 前端 `ESLint`
- 前端 `TypeScript type-check`
- 前端生产构建

后端自动 CI 的 `pytest` 入口固定为 `slurmweb/tests`，不把仓库内历史 `slurmweb4.2/tests` 兼容树纳入当前主线验证。

手工检查范围：

- rpm / deb OS 集成矩阵
- `CI Triage` 结构化结果聚合
