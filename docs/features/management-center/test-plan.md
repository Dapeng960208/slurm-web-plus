# 管理扩展测试计划

## 1. 目标

验证现有业务页面增强、`Admin` 路由迁移、`jobs:self` 后端校验、`analysis ping/diag`、以及 `slurmrestd 0.39-0.44` 兼容降级行为。

## 2. 后端测试

### 2.1 权限与 owner-aware

覆盖以下场景：

- `jobs:view:self` 只返回当前用户自己的作业
- `jobs:delete:self` 只能取消本人作业
- `jobs:edit:self` 只能更新本人作业
- 管理员持有 `jobs:*:*` 时可操作所有作业
- `default_seed_roles()` 中 `user` 不包含 `admin/*`

对应重点：

- `slurmweb/tests/test_permission_rules.py`
- `slurmweb/tests/test_access_control_policy.py`
- `slurmweb/tests/views/test_agent_operations.py`

### 2.2 Gateway / Agent 路由

覆盖以下场景：

- `analysis/ping`
- `analysis/diag`
- `admin/system/licenses`
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

对应重点：

- `slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`

## 3. 前端测试

### 3.1 路由与导航

覆盖以下场景：

- `/:cluster/admin`
- `admin-system`
- `admin-ai`
- `admin-access-control`
- `admin-cache`
- `admin-ldap-cache`
- 旧 `settings/*` 管理路由重定向到 `admin/*`
- 主菜单 `Admin` 入口只在具备任一 `admin/*:view:*` 时显示

对应重点：

- `frontend/tests/router/AdminRoutesContract.spec.ts`
- `frontend/tests/components/MainMenu.spec.ts`
- `frontend/tests/stores/runtime.spec.ts`

### 3.2 页面行为

覆盖以下场景：

- `ClusterAnalysisView` 请求并展示 `Ping` / `Diag`
- `JobsView` 在 `jobs:view|edit|delete:self` 下只对本人作业显示 `Edit/Cancel`
- `JobView` 在 `self` 下只对本人作业显示 `Edit/Cancel`
- 页面无批量取消入口
- `ResourcesView` 无批量节点操作入口

对应重点：

- `frontend/tests/views/ClusterAnalysisView.spec.ts`
- `frontend/tests/views/JobsView.spec.ts`
- `frontend/tests/views/JobView.spec.ts`

### 3.3 Gateway API 契约

覆盖以下场景：

- `analysis/ping`
- `analysis/diag`
- `admin/system/*`
- 新写接口路径与方法
- `RESTAPI.delete()` 支持 body

对应重点：

- `frontend/tests/composables/GatewayAPI.spec.ts`
- `frontend/tests/composables/GatewayAPIAdminContract.spec.ts`

## 4. 已执行的定向验证

已通过：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/router/AdminRoutesContract.spec.ts tests/composables/GatewayAPIAdminContract.spec.ts tests/views/ClusterAnalysisView.spec.ts tests/components/MainMenu.spec.ts tests/stores/runtime.spec.ts`
- `cd frontend && npx vitest run tests/views/JobsView.spec.ts tests/views/ReservationsView.spec.ts tests/views/QosView.spec.ts tests/views/AccountView.spec.ts tests/views/AccountsView.spec.ts tests/views/UserView.spec.ts tests/views/resources/ResourcesView.spec.ts`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/test_access_control_policy.py slurmweb/tests/views/test_agent_operations.py slurmweb/tests/views/test_gateway_operations.py slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`

## 5. 待补充验证

当前未在本轮完成：

- `npx vitest run` 全量前端回归
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests` 全量后端回归

说明：

- 当前 Windows 环境下全量后端测试仍受既有平台依赖与旧测试基线影响，不能作为本轮唯一验收结论。
