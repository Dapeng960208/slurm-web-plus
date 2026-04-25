# 访问控制需求说明

## 1. 背景与目标

现有基于 `actions[]` 的权限控制粒度不够，无法表达“只允许查看某个主路由”“允许编辑但仅限自己”“允许整个 settings 子树查看”这类规则。

本次改造目标：

- 建立新的权限模型 `resource:operation:scope`
- 保留旧权限名兼容层，避免已有角色立即失效
- 在启用数据库支持后提供自定义角色与用户绑定
- 页面上可配置所有主路由及子资源权限

## 2. 功能范围

本次已实现：

- 新权限规则解析、匹配、排序与 owner-aware `self`
- 旧权限到新规则的内置映射
- `GET /access/catalog`
- 角色表新增 `permissions`
- 自定义角色新旧字段双读双写
- Access Control 页面改为资源矩阵
- 首次空角色表自动预置 `user`、`admin`、`super-admin`

本次不做：

- deny 规则
- 用户直授权限
- 详情页单独拆新的资源命名体系

## 3. 启用条件

访问控制的运行条件已经收敛为：

- `[database] enabled = yes`

说明：

- 数据库开启后，访问控制支持会自动装配。
- 历史独立开关仅保留兼容占位定义，不再推荐继续使用。
- 当数据库不可用或访问控制 store 初始化失败时，系统退回文件策略与旧 `actions[]` 行为。

## 4. 权限模型

权限规则格式：

```text
resource:operation:scope
```

当前支持：

- `resource`
  - 精确资源，例如 `jobs`
  - 子资源，例如 `settings/cache`
  - 前缀资源，例如 `settings/*`
  - 全局通配 `*`
- `operation`
  - `view`
  - `edit`
  - `delete`
- `scope`
  - `*`
  - `self`

规则语义：

- `edit` / `delete` 自动满足 `view`
- `*:*:*` 表示最高权限
- `self` 仅在 owner-aware 资源上生效

当前资源目录包含：

- 主路由：
  - `dashboard`
  - `analysis`
  - `ai`
  - `jobs`
  - `jobs-history`
  - `resources`
  - `qos`
  - `reservations`
  - `accounts`
- settings：
  - `settings/general`
  - `settings/errors`
  - `settings/account`
  - `settings/ai`
  - `settings/access-control`
  - `settings/cache`
  - `settings/ldap-cache`
- 用户空间：
  - `user/profile`
  - `user/analysis`
- 共享过滤资源：
  - `jobs/filter-accounts`
  - `jobs/filter-partitions`
  - `jobs/filter-qos`
  - `resources/filter-partitions`

## 5. 旧权限兼容映射

系统内置至少包含以下映射：

| 旧权限 | 新规则 |
|---|---|
| `view-stats` | `dashboard:view:*` + `analysis:view:*` |
| `view-jobs` | `jobs:view:*` + `user/analysis:view:self` |
| `view-history-jobs` | `jobs-history:view:*` |
| `view-nodes` | `resources:view:*` |
| `view-qos` | `qos:view:*` + `jobs/filter-qos:view:*` |
| `view-reservations` | `reservations:view:*` |
| `associations-view` | `accounts:view:*` + `user/profile:view:*` |
| `view-accounts` | `jobs/filter-accounts:view:*` |
| `view-partitions` | `jobs/filter-partitions:view:*` + `resources/filter-partitions:view:*` |
| `cache-view` | `settings/cache:view:*` |
| `cache-reset` | `settings/cache:edit:*` |
| `roles-view` | `settings/access-control:view:*` |
| `roles-manage` | `settings/access-control:edit:*` + `settings/access-control:delete:*` |
| `view-ai` | `ai:view:*` |
| `manage-ai` | `settings/ai:edit:*` |

扩展方式：

- 可通过 `policy.permission_map` 覆盖或补充映射

## 6. 数据模型与接口

数据库变化：

- `roles.permissions JSONB`

接口变化：

- `GET /permissions`
  - 返回 `roles`
  - 返回 `actions`
  - 返回 `rules`
  - 返回 `sources.policy/custom/merged`
- `GET /access/catalog`
  - 返回资源目录、操作、scope、旧权限映射
- `GET /access/roles`
  - 返回 `actions` 与 `permissions`
- `POST/PATCH /access/roles`
  - 支持同时写入 `actions` 与 `permissions`

## 7. 前端行为

前端当前的关键行为：

- `runtime.hasRoutePermission(...)` 作为新规则判定入口
- 主菜单、路由守卫、Settings Tabs、AI/Cache/LDAP Cache/用户空间统一读取规则
- `Settings > Access Control` 使用目录驱动矩阵编辑 `permissions`
- 角色展示同时显示 `permissions` 与兼容 `actions`

## 8. 预置角色

数据库支持开启且 `roles` 表为空时，自动写入：

- `user`
  - 全量可查看权限
- `admin`
  - 全量资源的 `view/edit/delete`
- `super-admin`
  - `*:*:*`

这些角色只在首次空表时自动写入一次。

## 9. 降级与边界

- 当访问控制不可用时：
  - 继续按旧 `actions[]` 鉴权
  - 不强制依赖新规则
- 当前版本只做 allow，不做 deny
- `self` 只在 owner-aware 资源中使用
- 页面详情默认继承主页面资源，不额外拆权限

## 10. 相关验证入口

- 后端测试见 [`test-plan.md`](./test-plan.md)
- 运行时目录见 `slurmweb/permission_rules.py`
- 前端矩阵页面见 `frontend/src/views/settings/SettingsAccessControl.vue`
