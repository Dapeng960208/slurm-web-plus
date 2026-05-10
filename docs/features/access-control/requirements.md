# 访问控制需求说明

## 1. 目标

当前权限系统的正式模型是 `resource:operation:scope`。目标是让后端授权、前端路由守卫、主菜单和页内局部控件围绕同一套资源规则工作，同时保留必要的旧 `actions[]` 兼容能力，避免历史角色和旧测试数据立即失效。

## 2. 当前实现范围

已实现：

- 规则解析、标准化、匹配与 `self` scope
- 旧动作到新规则的内置映射
- 文件策略与数据库角色的统一合并
- `GET /permissions` 与 `GET /access/catalog`
- `roles.permissions` 主字段
- 角色矩阵页面按资源目录编辑 `permissions`
- 空角色表自动种子 `user`、`admin`、`super-admin`

明确不做：

- deny 规则
- 用户直授权限
- 为详情页单独拆一套新资源命名

## 3. 启用条件

- `[database] enabled = yes`

说明：

- 数据库可用时，访问控制 store 会自动启用。
- 当数据库不可用或访问控制 store 初始化失败时，系统仍可退回文件策略与兼容 `actions[]`。

## 4. 规则模型

规则格式：

```text
resource:operation:scope
```

当前语义：

- `resource`
  - 精确资源，例如 `jobs`
  - 子资源，例如 `admin/cache`
  - 前缀资源，例如 `admin/*`
  - 全局通配 `*`
- `operation`
  - `view`
  - `edit`
  - `delete`
- `scope`
  - `*`
  - `self`

补充规则：

- `edit` / `delete` 自动满足 `view`
- `*:*:*` 表示最高权限
- `self` 只在 owner-aware 资源上生效

## 5. 当前资源目录

主路由资源：

- `dashboard`
- `analysis`
- `ai`
- `jobs`
- `jobs-history`
- `resources`
- `qos`
- `reservations`
- `accounts`
- `users-admin`

Settings 资源：

- `settings/general`
- `settings/errors`
- `settings/account`

Admin 资源：

- `admin/ai`
- `admin/access-control`
- `admin/cache`
- `admin/ldap-cache`

用户空间资源：

- `user/profile`
- `user/analysis`

共享筛选资源：

- `jobs/filter-accounts`
- `jobs/filter-partitions`
- `jobs/filter-qos`
- `resources/filter-partitions`

说明：

- 当前前端主工作路径已经是 `/:cluster/admin/*`。
- `/settings/ai`、`/settings/access-control`、`/settings/cache`、`/settings/ldap-cache` 只是兼容重定向入口，不再是主资源名。

## 6. 兼容映射

系统当前保留的主要旧动作映射包括：

| 旧动作 | 规则 |
|---|---|
| `view-stats` | `dashboard:view:*` + `analysis:view:*` |
| `view-jobs` | `jobs:view:*` |
| `view-history-jobs` | `jobs-history:view:*` |
| `view-nodes` | `resources:view:*` |
| `view-qos` | `qos:view:*` + `jobs/filter-qos:view:*` |
| `view-reservations` | `reservations:view:*` |
| `associations-view` | `accounts:view:*` + `user/profile:view:*` |
| `view-accounts` | `jobs/filter-accounts:view:*` |
| `view-partitions` | `jobs/filter-partitions:view:*` + `resources/filter-partitions:view:*` |
| `view-ai` | `ai:view:*` |
| `cache-view` | `admin/cache:view:*` + `admin/ldap-cache:view:*` |
| `cache-reset` | `admin/cache:edit:*` |
| `admin-manage` | `*:*:*` |

说明：

- `view-ai` 当前继续作为 `ai:view:*` 的兼容别名。
- `admin-manage` 当前只作为 `*:*:*` 的兼容别名。
- `view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage` 已彻底失效，不再作为正式配置入口，也不再参与兼容推导。
- `manage-ai` 已不再作为正式配置入口。

## 7. 数据模型与接口

数据库主字段：

- `roles.permissions JSONB`

兼容字段：

- `roles.actions JSONB`

关键接口返回：

- `GET /permissions`
  - `roles`
  - `actions`
  - `rules`
  - `sources.policy/custom/merged`
- `GET /permissions.actions`
  - 不再返回 `view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage`、`manage-ai`
  - 仍可能返回保留兼容项 `view-ai` 与 `admin-manage`
- `GET /access/catalog`
  - 资源目录
  - 操作列表
  - scope 列表
  - `legacy_map`
- `GET /access/roles`
  - 返回 `actions` 与 `permissions`
- `POST/PATCH /access/roles`
  - 支持提交 `actions` 与 `permissions`

## 8. 预置角色

数据库启用且角色表为空时，自动写入：

- `user`
  - 非 `admin/*` 页面默认只读
  - `jobs:view:self`
  - `jobs:edit:self`
  - `jobs:delete:self`
  - `user/profile:view:self`
  - `user/analysis:view:self`
- `admin`
  - `*:view:*`
  - `*:edit:*`
  - 不默认包含 `*:delete:*`
- `super-admin`
  - `*:*:*`

## 9. 前端消费要求

- 主判定入口应优先使用 `runtime.hasRoutePermission(...)`
- 需要同时接受 `*` 与 `self` 时使用 `hasRoutePermissionAnyScope(...)`
- 旧 `hasPermission()` / `hasClusterPermission()` 仅保留给兼容 fallback，不应成为新增页面的默认方案

## 10. 边界

- 当前版本只做 allow，不做 deny
- 页面详情默认继承主页面资源
- `self` 只在 owner-aware 资源中使用
- 前端隐藏/禁用只作为辅助，最终安全边界仍以后端 owner-aware 鉴权为准
