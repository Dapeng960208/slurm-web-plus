# 管理扩展需求说明

## 1. 背景与目标

本轮不新增独立“全量管理中心”，而是在现有业务页面上补单对象管理能力，并新增集群级 `/:cluster/admin` 页面统一承载后台管理能力。

目标包括：

- 在现有 `Jobs`、`Resources`、`Reservations`、`Accounts`、`User`、`QOS` 页面补创建、编辑、删除、取消等单对象能力
- 将 `AI`、`LDAP Cache`、`Cache`、`Access Control` 从 `/settings/*` 迁移到 `/:cluster/admin`
- 在 `analysis` 页面补 `Slurm diag` 与 `ping`
- 将 `analysis/ping`、`analysis/diag` 与 `admin/system/licenses` 从原始 JSON 文本收口为结构化字段展示
- 用 `resource:operation:scope` 做严格权限控制
- 为 `jobs` 资源落地后端 owner-aware `self` 校验
- 兼容 `slurmrestd` `0.39` 到 `0.44`

## 2. 功能范围

本次已实现：

- `JobsView` / `JobView`
  - 单作业提交
  - 单作业编辑
  - 单作业取消
- `ResourcesView` / `NodeView`
  - 单节点更新
  - 单节点删除
- `ReservationsView`
  - 创建
  - 更新
  - 删除
- `AccountsView` / `AccountView`
  - 账户创建
  - 账户更新
  - 账户删除
- `UserView`
  - SlurmDB 用户创建/更新
  - 用户删除
- `QosView`
  - QoS 创建
  - QoS 更新
  - QoS 删除
- `ClusterAnalysisView`
  - `Slurm ping`
  - `Slurm diag`
  - `hour/day/week` 时间范围切换
- `/:cluster/admin`
  - `System`
  - `AI`
  - `LDAP Cache`
  - `Cache`
  - `Access Control`

本次不做：

- 批量取消作业
- 批量节点操作
- 独立 JSON 专家模式

## 3. 路由与页面承载

新增或调整后的关键路由：

- `/:cluster/admin`
- `/:cluster/admin/ai`
- `/:cluster/admin/access-control`
- `/:cluster/admin/cache`
- `/:cluster/admin/ldap-cache`

旧路由迁移：

- `/settings/ai` -> `/:cluster/admin/ai`
- `/settings/access-control` -> `/:cluster/admin/access-control`
- `/settings/cache` -> `/:cluster/admin/cache`
- `/settings/ldap-cache` -> `/:cluster/admin/ldap-cache`

说明：

- `settings` 页面只保留 `General`、`Errors`、`Account`
- 主侧栏新增 `Admin`
- 主侧栏顺序调整为 `AI` 在上、`Admin` 在最下
- `Admin` 入口由任一 `admin/*:view:*` 控制显示
- `admin-manage` 现在只是 `*:*:*` 的兼容别名，因此只有 `super-admin` 语义的角色/用户会通过该别名显示 `Admin` 入口

## 4. 权限要求

业务资源：

- `jobs:view|edit|delete:*|self`
- `resources:view|edit|delete:*`
- `reservations:view|edit|delete:*`
- `accounts:view|edit|delete:*`
- `users-admin:view|edit|delete:*`
- `qos:view|edit|delete:*`
- `analysis:view:*`

后台资源：

- `admin/ai:view|edit|delete:*`
- `admin/ldap-cache:view|edit:*`
- `admin/cache:view|edit:*`
- `admin/access-control:view|edit|delete:*`
- `admin/system:view|edit|delete:*`

控制规则：

- 页面访问使用 `view`
- 创建、更新、状态修改使用 `edit`
- 删除、取消使用 `delete`
- `Admin` 页面至少要求一个 `admin/*:view:*`

## 5. `jobs self` 语义

`self` 首版只落地在 `jobs` 资源：

- `jobs:view:self`
  - 作业列表查询优先向 `slurmrestd` 注入 `user=<request.user.login>`
  - 后端再做一次 owner 过滤
- `jobs:edit:self`
  - 作业更新前先查询作业 owner，再校验当前登录用户
- `jobs:delete:self`
  - 作业取消前先查询作业 owner，再校验当前登录用户

安全边界：

- owner 判定只以后端查询到的作业实际 owner 为准
- 不接受前端传入用户名作为最终授权依据

## 6. 后端接口与兼容策略

后端新增或扩展：

- `analysis/ping`
- `analysis/diag`
- `admin/system/<query>`
- `jobs/submit`
- `job/<id>/update`
- `job/<id>/cancel`
- `node/<name>/update`
- `node/<name>/delete`
- `reservation`
- `reservation/<name>/update`
- `reservation/<name>/delete`
- `accounts`
- `account/<name>/delete`
- `users`
- `user/<name>/delete`
- `qos`
- `qos/<name>/delete`

`slurmrestd` 版本兼容：

- `0.41-0.44`
  - 当前主写路径已开放
- `0.39-0.40`
  - 维持读兼容
  - 未开放写操作返回 `501 unsupported_on_version` 风格降级结果

## 7. 默认角色与旧动作兼容

默认种子角色调整为：

- `user`
  - 不包含任何 `admin/*`
  - 对非 `Admin` 页面默认只具备只读能力
  - 默认包含 `jobs:view:self`
  - 默认包含 `jobs:edit:self`
  - 默认包含 `jobs:delete:self`
- `admin`
  - 默认包含 `*:view:*`
  - 默认包含 `*:edit:*`
  - 默认不包含 `*:delete:*`
- `super-admin`
  - `*:*:*`

旧动作兼容补充：

- `admin-manage` -> `*:*:*`

已移除的旧动作入口：

- `view-own-jobs`
- `edit-own-jobs`
- `cancel-own-jobs`
- `roles-view`
- `roles-manage`
- `view-ai`
- `manage-ai`

普通用户默认拥有 `jobs:*:self` 与 `user/analysis:view:self`，现在来自数据库种子角色 `user`，不再来自 vendor policy 动作；无数据库模式下也不再提供这组旧动作兜底。

## 8. 前端行为

前端统一采用：

- 列表页工具栏只放“创建”入口
- 行级与详情页放 `Edit` / `Delete` / `Cancel`
- 删除与取消统一二次确认
- 不展示任何批量操作 UI
- 共享表单统一显示字段 `Required` / `Optional`
- 编辑类按钮使用橙色语义，删除/取消使用红色警示语义
- 关键字段与操作按钮补 tooltip / hint，说明行为影响
- `Dashboard`、`Cluster Analysis`、`Node` 指标统一支持 `hour/day/week` 时间范围切换

`jobs:self` 的前端行为：

- 可根据当前登录用户与对象 owner 做隐藏/禁用
- 最终安全判定仍由后端执行

## 9. 降级与边界

- `admin/ldap-cache:edit:*` 已在权限模型中预留，但当前未提供实质写接口
- `accounts/users/qos/reservation` 当前前端使用轻量结构化表单，不覆盖全部官方 JSON 细节
- `admin/system` 当前仅先把 `licenses` 收口为结构化摘要；`shares` 与部分 `slurmdb` 面板仍保留原始 JSON 输出
- 全量后端回归仍需 Linux 环境补充

## 10. 相关实现与验证入口

- 前端：
  - `frontend/src/router/index.ts`
  - `frontend/src/views/AdminLayoutView.vue`
  - `frontend/src/views/AdminSystemView.vue`
  - `frontend/src/views/JobsView.vue`
  - `frontend/src/views/JobView.vue`
  - `frontend/src/views/resources/ResourcesView.vue`
  - `frontend/src/views/NodeView.vue`
- 后端：
  - `slurmweb/views/agent.py`
  - `slurmweb/views/gateway.py`
  - `slurmweb/apps/agent.py`
  - `slurmweb/apps/gateway.py`
  - `slurmweb/slurmrestd/__init__.py`
  - `slurmweb/permission_rules.py`
- 测试计划见 [`test-plan.md`](./test-plan.md)
