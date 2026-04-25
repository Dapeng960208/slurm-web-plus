# 当前发布跟踪：基于现有页面增强的 Slurm 管理扩展

## 1. 当前主题

本轮发布聚焦以下目标：

- 在现有业务页面补单对象管理能力，不做独立全量管理中心
- 将 `AI`、`LDAP Cache`、`Cache`、`Access Control` 迁移到 `/:cluster/admin`
- 在 `analysis` 页面补 `Slurm ping` 与 `diag`
- 以 `jobs:view|edit|delete:*|self` 落地 owner-aware 权限校验
- 补齐 `slurmrestd 0.39-0.44` 的读写兼容策略与测试基线

## 2. 已完成项

- 发布后代码审查已补共享写操作对话框回归修复：
  - `ActionDialog` 复用时会先清空旧表单键，避免编辑/提交残留字段泄漏到后续删除/取消请求体
  - 已补对应前端组件回归测试
- 新增集群级 `/:cluster/admin` 路由与 `Admin` 菜单入口
- 旧 `/settings/ai|access-control|cache|ldap-cache` 已重定向到 `admin/*`
- `Admin` 页面已统一承载：
  - `System`
  - `AI`
  - `LDAP Cache`
  - `Cache`
  - `Access Control`
- `ClusterAnalysisView` 已补 `Slurm ping` 与 `diag`
- `JobsView` / `JobView` 已补单作业提交、编辑、取消
- `ResourcesView` / `NodeView` 已补单节点更新、删除
- `ReservationsView` 已补创建、更新、删除
- `AccountsView` / `AccountView` 已补创建、更新、删除
- `UserView` 已补 SlurmDB 用户更新、删除
- `QosView` 已补创建、更新、删除
- `slurmweb.slurmrestd` 已扩展为通用 `GET/POST/DELETE` 请求层
- Gateway -> Agent -> `slurmrestd` 已支持 `DELETE` body
- `jobs self` 后端校验已落地：
  - 列表优先注入 `user=<login>`
  - 详情、更新、取消先查 owner 再校验
- 权限资源已切换到：
  - `admin/system`
  - `admin/ai`
  - `admin/cache`
  - `admin/ldap-cache`
  - `admin/access-control`
- `default_seed_roles()` 已收紧，普通 `user` 不再默认带 `admin/*`
- vendor policy 已切到：
  - `view-own-jobs`
  - `edit-own-jobs`
  - `cancel-own-jobs`
- 默认角色已进一步修正为：
  - `user`：非 `Admin` 页面默认只读 + `jobs:view|edit|delete:self`
  - `admin`：`*:view:*` + `*:edit:*`
  - `admin`：默认不含 `*:delete:*`
- 新增旧动作兼容：
  - `admin-manage`
  - `edit-own-jobs`
- 新增/更新了与本任务相关的前后端测试基线

## 3. 进行中项

- 对齐 `accounts/users/qos/reservation` 的轻量前端表单字段与官方 JSON 结构边界
- 继续评估是否需要为 `admin/system` 补更多官方只读面板
- 视 Linux/CI 环境情况补全更大范围后端回归

## 4. 风险与阻塞

- 当前前端对 `accounts/users/qos/reservation` 使用的是高频结构化字段，不覆盖全部官方 JSON 细节
- `admin/ldap-cache:edit:*` 已在权限模型中预留，但当前没有对应实质写接口
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests` 在当前 Windows 环境下仍不适合作为本轮唯一验收结论
- 部分前端测试夹具仍以旧 `actions[]` 为主，若继续扩大回归范围，需继续向 `rules[]` 夹具收敛
- `admin-manage` 只覆盖 `/:cluster/admin` 下资源，不会自动授予独立 AI 工作台 `ai:view:*`

## 5. 已同步文档

- `docs/README.md`
- `docs/overview/project-overview.md`
- `docs/overview/architecture-overview.md`
- `docs/overview/latest-features.md`
- `docs/features/access-control/requirements.md`
- `docs/features/access-control/test-plan.md`
- `docs/features/ai/requirements.md`
- `docs/features/cache/requirements.md`
- `docs/features/management-center/requirements.md`
- `docs/features/management-center/test-plan.md`
- `docs/guides/deployment-guide.md`
- `docs/tracking/current-release.md`

## 6. 验证状态

已通过：

- `cd frontend && npx vitest run tests/components/operations/ActionDialog.spec.ts`
- `npm --prefix frontend run type-check`
- `npm --prefix frontend run build`
- `cd frontend && npx vitest run`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests`
- `cd frontend && npx vitest run tests/router/AdminRoutesContract.spec.ts tests/composables/GatewayAPIAdminContract.spec.ts tests/views/ClusterAnalysisView.spec.ts tests/components/MainMenu.spec.ts tests/stores/runtime.spec.ts`
- `cd frontend && npx vitest run tests/views/JobsView.spec.ts tests/views/ReservationsView.spec.ts tests/views/QosView.spec.ts tests/views/AccountView.spec.ts tests/views/AccountsView.spec.ts tests/views/UserView.spec.ts tests/views/resources/ResourcesView.spec.ts`
- `cd frontend && npx vitest run tests/composables/GatewayAPI.spec.ts tests/composables/GatewayAPIAdminContract.spec.ts tests/router/AdminRoutesContract.spec.ts tests/stores/runtime.spec.ts tests/components/MainMenu.spec.ts tests/components/settings/SettingsTabs.spec.ts tests/components/settings/SettingsTabsAIContract.spec.ts tests/views/settings/SettingsAI.spec.ts tests/views/settings/SettingsAccessControl.spec.ts tests/views/settings/SettingsCache.spec.ts tests/views/settings/SettingsLdapCache.spec.ts`
- `cd frontend && npx vitest run`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/test_access_control_policy.py slurmweb/tests/views/test_gateway.py slurmweb/tests/views/test_agent_operations.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/test_access_control_policy.py slurmweb/tests/views/test_agent_operations.py slurmweb/tests/views/test_gateway_operations.py slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent.py slurmweb/tests/views/test_gateway.py slurmweb/tests/views/test_gateway_clusters.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/test_access_control_policy.py slurmweb/tests/views/test_agent_permissions.py slurmweb/tests/apps/test_agent.py`
