# 访问控制（自定义角色）需求说明

本文描述“数据库驱动的自定义角色”能力，它叠加在既有 `policy.ini`（文件策略）RBAC 之上，并保持原行为在功能关闭时不受影响。

## 1. 范围与目标

- `users` 表仍然是缓存 LDAP 用户的锚点表。
- `roles` 存储自定义角色定义。
- `user_roles` 存储用户与角色的绑定关系。
- 前端 `Settings > Access Control` 页面只管理“当前集群”，不做跨集群聚合。
- 有效权限模型（实现事实）：
  - 文件策略动作（policy）
  - 数据库自定义角色动作（custom）
  - 最终有效权限（merged）为两者并集（UNION）

## 2. 数据模型（数据库）

迁移脚本：`slurmweb/alembic/versions/20260424_0005_access_control_roles.py`。

### 2.1 `users`

新增：

- `policy_roles JSONB NOT NULL DEFAULT []`
- `policy_actions JSONB NOT NULL DEFAULT []`
- `permission_synced_at TIMESTAMPTZ NULL`

### 2.2 `roles`

新增表字段：

- `id`
- `name`（唯一）
- `description`
- `actions JSONB`
- `created_at`
- `updated_at`

### 2.3 `user_roles`

新增表字段：

- `user_id`
- `role_id`
- `created_at`
- 主键 `(user_id, role_id)`
- 外键 `ON DELETE CASCADE`

## 3. 配置与策略

配置开关（实现事实）：

- `[persistence] access_control_enabled = yes|no`（默认 `no`）

策略动作（实现事实）：

- `roles-view`
- `roles-manage`

约束：

- 功能关闭时保持既有 vendor/site `policy.ini` 行为不变。
- 功能开启后，需要运维显式在策略中给对应用户/角色授权上述动作，否则前端页面应进入只读/不可用状态。

## 4. 后端行为要求（对齐实现）

### 4.1 权限解析

- 文件策略是基础来源（policy）。
- 当访问控制启用且数据库可用时：
  - 从 `user_roles -> roles.actions` 加载 custom 动作
  - 将 policy 与 custom 做集合并集（UNION）
  - 对 roles/actions 去重并排序后返回

### 4.2 `/permissions`

返回字段（实现事实）：

- `roles`
- `actions`
- `sources.policy.roles`
- `sources.policy.actions`
- `sources.custom.roles`
- `sources.custom.actions`
- `sources.merged.*`（或由顶层 `roles/actions` 表示 merged）

### 4.3 `/users/cache`（用户缓存写入）

当缓存认证用户时：

- 刷新 LDAP 用户基础信息（username/fullname/groups）
- 刷新 `policy_roles` / `policy_actions`
- 刷新 `permission_synced_at`

### 4.4 Agent 启动时的策略快照刷新

当 `[persistence] access_control_enabled = yes` 且数据库可用时：

- Agent 启动会对 `users` 中已有缓存用户刷新策略快照
- 刷新仅使用缓存的 `username` / `fullname` / `groups`
- 刷新会更新：
  - `policy_roles`
  - `policy_actions`
  - `permission_synced_at`
- 刷新不会：
  - 新建用户
  - 查询 LDAP
  - 修改 `user_roles`
- 单用户刷新失败只记录日志，不阻塞 Agent 启动

## 5. 接口契约

### 5.1 Agent 接口

- `GET /v{version}/access/roles`
- `POST /v{version}/access/roles`
- `PATCH /v{version}/access/roles/<id>`
- `DELETE /v{version}/access/roles/<id>`
- `GET /v{version}/access/users`
- `GET /v{version}/access/users/<username>/roles`
- `PUT /v{version}/access/users/<username>/roles`

授权（实现事实）：

- 读接口要求 `roles-view`
- 写接口要求 `roles-manage`
- 功能关闭时返回 `501`

### 5.2 Gateway 代理接口

- `GET /api/agents/<cluster>/permissions`
- `GET/POST /api/agents/<cluster>/access/roles`
- `PATCH/DELETE /api/agents/<cluster>/access/roles/<id>`
- `GET /api/agents/<cluster>/access/users`
- `GET/PUT /api/agents/<cluster>/access/users/<username>/roles`

### 5.3 能力暴露

必须在以下位置暴露 `access_control`（实现事实）：

- Agent `/info`
- Gateway `/api/clusters`
- 前端集群对象能力字段（用于 settings tab 门控）

## 6. 前端行为要求

- 仅当集群支持访问控制（capability）时显示 `Access Control` tab。
- 权限分级：
  - 无 `roles-view`：提示无权限，不加载数据
  - 有 `roles-view` 且无 `roles-manage`：只读模式
  - 有 `roles-manage`：允许编辑角色与绑定
- `SettingsAccount` 必须展示 `policy/custom/merged` 三个来源视图，便于排查“为什么有/没有某权限”。

测试计划见：[`docs/features/access-control/test-plan.md`](./test-plan.md)。
