# 访问控制测试计划

## 1. 目标

验证当前 `resource:operation:scope` 权限模型、旧动作兼容映射、数据库角色兼容逻辑，以及前端菜单/路由/局部控件的权限消费口径是否一致。

## 2. 后端测试

### 2.1 规则匹配

至少覆盖：

- 精确资源匹配
- `admin/*` 前缀资源匹配
- `*:view:*`、`*:edit:*`、`*:*:*`
- `self`
- `edit` / `delete` 满足 `view`
- 旧动作映射到新规则
- `cache-reset -> admin/cache:edit:*`
- `admin-manage -> *:*:*`

对应重点：

- `slurmweb/permission_rules.py`
- `slurmweb/tests/test_permission_rules.py`
- `slurmweb/tests/test_access_control_policy.py`

### 2.2 策略合并与数据库兼容

至少覆盖：

- 文件策略动作转规则
- 数据库 `roles.permissions` 读取
- 仅有 `roles.actions` 时的规则推导
- 历史无效旧动作的清理，以及 `view-ai` / `admin-manage` 的保留兼容
- `admin-manage` 的超级管理员兼容行为
- 空角色表自动种子 `user`、`admin`、`super-admin`

对应重点：

- `slurmweb/access_control.py`
- `slurmweb/persistence/access_control_store.py`
- `slurmweb/tests/test_access_control_store.py`

### 2.3 网关 / Agent 权限链路

至少覆盖：

- `allowed_user_permission()` 主判定链路
- `jobs:self`、`user/profile:self`、`user/analysis:self`
- 普通用户与管理员分支
- Gateway / Agent 权限接口返回

对应重点：

- `slurmweb/tests/views/test_agent_permissions.py`
- `slurmweb/tests/views/test_gateway_permissions.py`
- 如涉及 AI 权限映射，再补 `slurmweb/tests/apps/test_ai_service.py`

## 3. 前端测试

### 3.1 运行时权限

至少覆盖：

- `hasRoutePermission(...)`
- `hasRoutePermissionAnyScope(...)`
- `rules[]` 优先口径
- 旧 `actions[]` fallback
- `self` 场景

对应重点：

- `frontend/tests/stores/runtime.spec.ts`
- `frontend/tests/router/AdminPermissions.spec.ts`
- `frontend/tests/composables/userWorkspace.spec.ts`

### 3.2 导航与页面

至少覆盖：

- 主菜单显示
- 路由守卫跳转 `/forbidden`
- `Admin` 入口与 `AI` 入口权限对齐
- `SettingsAccessControl` 的只读 / 可编辑 / 可删除状态

对应重点：

- `frontend/tests/components/MainMenu.spec.ts`
- `frontend/tests/views/settings/SettingsAccessControl.spec.ts`

### 3.3 本轮共享权限消费点

至少覆盖：

- `DashboardView`
- `NodeView`
- `JobsFiltersPanel`
- `DashboardCharts`
- `ResourcesFiltersPanel`
- `userWorkspace`

说明：

- 这几处应优先以 `rules[]` 夹具断言，不再把旧 action 作为唯一测试前提。

## 4. 本轮建议执行顺序

1. `npm --prefix frontend run type-check`
2. `cd frontend && npx vitest run tests/views/DashboardView.spec.ts tests/views/NodeView.spec.ts tests/components/jobs/JobsFiltersPanel.spec.ts tests/components/dashboard/DashboardCharts.spec.ts tests/composables/userWorkspace.spec.ts`
3. `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/test_access_control_policy.py slurmweb/tests/test_access_control_store.py slurmweb/tests/views/test_agent_permissions.py slurmweb/tests/views/test_gateway_permissions.py`
4. 如涉及 AI 权限映射，再执行 `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py`

## 5. 未验证范围记录要求

如果本轮无法完成：

- 全量 `vitest`
- 全量 `pytest -q`
- Linux 发布环境回归

则必须在 review / tracking 文档中明确写出：

- 未执行项
- 阻塞原因
- 未验证范围
- 风险
