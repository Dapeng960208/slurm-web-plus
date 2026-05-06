# 管理扩展测试计划

## 1. 目标

验证现有业务页面增强、`Admin` 路由迁移、`jobs:self` 后端校验、`analysis ping/diag`、以及 `slurmrestd 0.39-0.44` 兼容降级行为。

## 2. 后端测试

### 2.1 权限与 owner-aware

覆盖以下场景：

- `jobs:view:self` 只返回当前用户自己的作业
- `jobs:delete:self` 只能取消本人作业
- `jobs:edit:self` 只能更新本人作业
- `default_seed_roles()` 中 `user` 包含 `jobs:view:self`、`jobs:edit:self`、`jobs:delete:self`
- `default_seed_roles()` 中 `user` 不包含 `admin/*`
- `default_seed_roles()` 中 `admin` 只包含 `*:view:*` 与 `*:edit:*`
- `default_seed_roles()` 中 `admin` 不包含 `*:delete:*`
- `admin-manage` 等价于 `*:*:*`，仅作为 `super-admin` 兼容别名保留

对应重点：

- `slurmweb/tests/test_permission_rules.py`
- `slurmweb/tests/test_access_control_policy.py`
- `slurmweb/tests/views/test_agent_operations.py`

### 2.2 Gateway / Agent 路由

覆盖以下场景：

- `analysis/ping`
- `analysis/diag`
- 旧 `admin/system/*` 路由返回 404
- `job/<id>/update`
- `job/<id>/cancel`
- `node/<name>/update`
- `node/<name>/delete`
- `DELETE` body 经 Gateway 转发

对应重点：

- `slurmweb/tests/views/test_gateway_operations.py`
- `slurmweb/tests/views/test_gateway.py`

### 2.3 slurmrestd 写路径

覆盖以下场景：

- 通用 `request_json()` 透传 `method/payload/query`
- `DELETE` 带 body
- `supports_write_operations()` 对 `0.41-0.44` 返回 true
- `supports_write_operations()` 对 `0.39-0.40` 返回 false
- QOS 轻量 payload 会被包装为 `{ qos: [...] }`
- QOS 写入缺少常用限制时，后端默认补 `MaxSubmitJobsPerUser=100`、`MaxJobsPerUser=10`、`MaxWallDurationPerJob=1440`
- QOS 写入显式传入常用限制时，不被后端默认值覆盖
- account-user association 删除 payload 会转换为 `account/user/cluster` query 参数，避免 `DELETE /association` request body 被忽略后扩大删除范围

对应重点：

- `slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`

## 3. 前端测试

### 3.1 路由与导航

覆盖以下场景：

- `/:cluster/admin`
- `/:cluster/admin` 默认跳转 `analysis`
- `admin-ai`
- `admin-access-control`
- `admin-cache`
- `admin-ldap-cache`
- 旧 `settings/*` 管理路由重定向到 `admin/*`
- 主菜单 `Admin` 入口只在具备任一 `admin/*:view:*` 时显示
- 主菜单 `Admin` 入口在拥有 `admin-manage`（即 `*:*:*`）时也显示
- 角色页不再展示 `view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage`、`view-ai`、`manage-ai`

对应重点：

- `frontend/tests/router/AdminRoutesContract.spec.ts`
- `frontend/tests/components/MainMenu.spec.ts`
- `frontend/tests/stores/runtime.spec.ts`

### 3.2 页面行为

覆盖以下场景：

- `ClusterAnalysisView` 请求并展示 `Ping` / `Diag`
- `ClusterAnalysis` 内存容量详情以 GB 展示，评分和百分比继续使用 MB 原始值计算
- `JobsView` 在 `jobs:view|edit|delete:self` 下只对本人作业显示 `Edit/Cancel`
- `JobView` 在 `self` 下只对本人作业显示 `Edit/Cancel`
- `JobsView` / `JobView` 编辑作业时，填写 `Memory per CPU (MB)` 会提交 `memory_per_cpu: { set: true, infinite: false, number }`
- `UserFilterSelector` 支持手动输入用户名并点击 `Add username` 加入 `runtimeStore.jobs.filters.users`
- `UserFilterSelector` 不添加空用户名，也不会重复添加已存在用户名
- `JobsHistoryView` / `JobHistoryView` 的实时作业入口使用 Slurm `job_id` 跳转到 `job` 路由
- `JobsHistoryView` / `JobHistoryView` 不直接提供历史记录 Edit/Cancel 写操作
- `AccountView` 可增加 account-user association、编辑 association QOS/default QOS、删除 association，payload 复用现有 associations 写接口
- `AccountView` 删除 association 时只提交选中 `account` 与 `user`，不携带空 `qos/default` 字段
- `UserView` 编辑用户时提交 `default_qos` 和逗号分隔解析后的 `qos`
- `QosView` 创建 QOS 弹框预填 `MaxSubmitJobsPerUser=100`、`MaxJobsPerUser=10`、`MaxWallDurationPerJob=1-00:00:00`
- `QosView` 提交创建 QOS 时把 `MaxWallDurationPerJob` 转换为分钟；非法 walltime 不调用写接口并在弹框显示错误
- 触达页面的按钮样式按操作语义区分：创建/提交 primary，编辑 warning，删除/取消 danger，查看/返回/筛选 secondary
- 默认 `admin` 用户可见编辑入口，但删除入口仍继续受 `delete` 权限控制
- 页面无批量取消入口
- `ResourcesView` 不再渲染节点行尾 `Manage` / `Delete` 按钮，节点名称仍可跳转详情
- `NodeView` 的 Edit Node 中 `state` 渲染为下拉框，并按所选状态提交 `update_node`

对应重点：

- `frontend/tests/views/ClusterAnalysisView.spec.ts`
- `frontend/tests/views/JobsView.spec.ts`
- `frontend/tests/views/JobView.spec.ts`

### 3.3 Gateway API 契约

覆盖以下场景：

- `analysis/ping`
- `analysis/diag`
- 不再暴露 `admin/system/*`
- 新写接口路径与方法
- `RESTAPI.delete()` 支持 body
- 前端 `delete_association(cluster, payload)` 使用 `DELETE /agents/:cluster/associations` 并保留请求 body
- QOS 创建 payload 可携带 `max_submit_jobs_per_user`、`max_jobs_per_user`、`max_wall_duration_per_job`，后端仍作为默认值兜底
- `JobUpdatePayload.memory_per_cpu` 与 `ClusterAssociation.default.qos` 类型契约可被页面使用

对应重点：

- `frontend/tests/composables/GatewayAPI.spec.ts`
- `frontend/tests/composables/GatewayAPIAdminContract.spec.ts`

## 4. 验证入口

本轮至少执行：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests`

本轮定向验证可先执行：

- `cd frontend && npx vitest run tests/views/QosView.spec.ts tests/views/AccountView.spec.ts tests/composables/GatewayAPI.spec.ts`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`
- `cd frontend && npx vitest run tests/views/JobsView.spec.ts tests/views/JobView.spec.ts tests/views/JobsHistoryView.spec.ts tests/views/JobHistoryView.spec.ts tests/views/AccountView.spec.ts tests/views/UserView.spec.ts tests/composables/GatewayAPI.spec.ts tests/composables/ClusterAnalysis.spec.ts tests/components/operations/ActionDialog.spec.ts`
- `cd frontend && npx vitest run tests/views/resources/ResourcesView.spec.ts tests/views/NodeView.spec.ts tests/components/operations/ActionDialog.spec.ts tests/components/jobs/UserFilterSelector.spec.ts`
- `npm --prefix frontend run type-check`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py slurmweb/tests/views/test_agent_operations.py`

若存在失败，需要在 `docs/tracking/current-release.md` 记录失败项和结论。
