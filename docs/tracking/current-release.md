# 当前发布跟踪：基于现有页面增强的 Slurm 管理扩展

## 1. 当前主题

本轮发布聚焦以下目标：

- 在现有业务页面补单对象管理能力，不做独立全量管理中心
- 将 `AI`、`LDAP Cache`、`Cache`、`Access Control` 迁移到 `/:cluster/admin`
- 在 `analysis` 页面补 `Slurm ping` 与 `diag`
- 以 `jobs:view|edit|delete:*|self` 落地 owner-aware 权限校验
- 补齐 `slurmrestd 0.39-0.44` 的读写兼容策略与测试基线
- 收敛 GitHub CI 到 `main` 分支自动测试，并为后续 AI / 脚本补结构化结果产物

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
- `policy.yml` / `policy.ini` 已移除 7 个旧动作配置入口：
  - `view-own-jobs`
  - `edit-own-jobs`
  - `cancel-own-jobs`
  - `roles-view`
  - `roles-manage`
  - `view-ai`
  - `manage-ai`
- 默认角色已进一步修正为：
  - `user`：非 `Admin` 页面默认只读 + `jobs:view|edit|delete:self` + `user/analysis:view:self`
  - `admin`：`*:view:*` + `*:edit:*`
  - `admin`：默认不含 `*:delete:*`
- `admin-manage` 已改为 `*:*:*` 兼容别名，仅对应 `super-admin`
- AccessControlStore 启动时会把历史 `roles.actions` 中的废弃动作迁入 `roles.permissions`
- `agent.yml` 已删除：
  - `persistence.enabled`
  - `persistence.access_control_enabled`
  - `user_metrics.enabled`
  - `node_metrics.enabled`
  - `ai.enabled`
- 新增/更新了与本任务相关的前后端测试基线
- GitHub Actions 已补自动触发：
  - `pull_request` 到 `main`
  - `push` 到 `main`
- 自动 CI 当前固定版本为：
  - 后端 `Python 3.12`
  - 前端 `Node 18`
- 自动 CI 当前覆盖：
  - 后端单元测试
  - 前端单元测试
  - 前端 `ESLint`
  - 前端 `TypeScript type-check`
  - 前端生产构建
- 后端自动/手工 CI 的 `pytest` 入口已统一收敛到 `slurmweb/tests`
- 后端 `.[agent]` / `.[tests]` extras 已补 `cryptography`，修复 AI 测试在 GitHub Actions 的导入失败
- 后端 rpm/deb OS 集成矩阵已拆到手工 `python-os-ci.yml`
- 新增统一 CI 结果产物：
  - `stdout.log`
  - `result.json`
  - `failure-context.json`
  - `junit.xml`（测试类 job）
- 新增手工 `CI Triage` workflow，可按 `run_id` 聚合 `backend` / `frontend` / `all` artifact
- `JobsHistoryFiltersPanel` / `JobsHistoryFiltersBar` 已改为 `update:filters` 事件链，修复 `vue/no-mutating-props` 导致的前端 CI 失败
- `JobHistoryView`、`ClusterAnalysis`、`SettingsTabs` 与 `GatewayAPI` 已清理剩余 ESLint 阻塞项，修复未使用符号和空接口类型告警
- `JobView`、`JobsView` 与 `SettingsAccessControl` 已清理新增 ESLint 阻塞项，修复未使用符号告警

## 3. 进行中项

- 对齐 `accounts/users/qos/reservation` 的轻量前端表单字段与官方 JSON 结构边界
- 继续评估是否需要为 `admin/system` 补更多官方只读面板
- 视 Linux/CI 环境情况补全更大范围后端回归
- 评估后续是否需要把 `CI Triage` 结果继续接给外部 AI agent 做只读诊断
- 评估是否需要为结构化 CI 结果补 GitHub issue / PR comment 自动摘要
- `fix(frontend): clear remaining eslint blockers` 已完成本地提交 `024bde9`，当前因网络不可达待 push 到 `origin/main`

## 4. 风险与阻塞

- 当前前端对 `accounts/users/qos/reservation` 使用的是高频结构化字段，不覆盖全部官方 JSON 细节
- `admin/ldap-cache:edit:*` 已在权限模型中预留，但当前没有对应实质写接口
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests` 在当前 Windows 环境下仍不适合作为本轮唯一验收结论
- Windows 本地执行 `pip install -e ".[agent,tests,gateway]"` 会继续卡在 `RacksDB[web] -> PyGObject` 编译；后端依赖修复已通过定向 AI pytest 验证，但完整 agent extra 仍更适合以 Ubuntu CI 为准
- 部分前端测试夹具仍以旧 `actions[]` 为主，若继续扩大回归范围，需继续向 `rules[]` 夹具收敛
- 无数据库部署下，普通用户不再有自有 Jobs 的旧动作兜底；该差异需要部署文档显式说明
- 当前仓库内置 AI 仍不能直接读取 GitHub Actions run；本轮只打通“结构化结果可查询”，未实现自动修复

## 5. 已同步文档

- `docs/README.md`
- `docs/overview/project-overview.md`
- `docs/overview/architecture-overview.md`
- `docs/overview/latest-features.md`
- `docs/features/access-control/requirements.md`
- `docs/features/access-control/test-plan.md`
- `docs/features/ai/requirements.md`
- `docs/features/ai/test-plan.md`
- `docs/features/cache/requirements.md`
- `docs/features/ci/requirements.md`
- `docs/features/ci/verification.md`
- `docs/features/management-center/requirements.md`
- `docs/features/management-center/test-plan.md`
- `docs/guides/database-migrations.md`
- `docs/guides/deployment-guide.md`
- `docs/guides/verification-checklist.md`
- `docs/features/user-analytics/backend.md`
- `docs/tracking/current-release.md`
- `docs/tracking/error-log.md`

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
- `node --check .github/scripts/run-ci-command.mjs`
- `node --check .github/scripts/ensure-ci-result.mjs`
- `node --check .github/scripts/build-triage-context.mjs`
- `Get-Content -Raw -Encoding UTF8 .github/workflows/python-ci.yml | npx --yes yaml valid`
- `Get-Content -Raw -Encoding UTF8 .github/workflows/python-os-ci.yml | npx --yes yaml valid`
- `Get-Content -Raw -Encoding UTF8 .github/workflows/frontend-ci.yml | npx --yes yaml valid`
- `Get-Content -Raw -Encoding UTF8 .github/workflows/frontend-static.yml | npx --yes yaml valid`
- `Get-Content -Raw -Encoding UTF8 .github/workflows/ci-triage.yml | npx --yes yaml valid`
- `cd frontend && npx vitest run tests/components/jobs/JobsHistoryFiltersPanel.spec.ts tests/components/jobs/JobsHistoryFiltersBar.spec.ts`
- `cd frontend && npx eslint src/components/jobs/JobsHistoryFiltersPanel.vue src/components/jobs/JobsHistoryFiltersBar.vue src/views/JobsHistoryView.vue tests/components/jobs/JobsHistoryFiltersPanel.spec.ts tests/components/jobs/JobsHistoryFiltersBar.spec.ts`
- `cd frontend && npx eslint src/views/JobHistoryView.vue src/composables/GatewayAPI.ts src/composables/ClusterAnalysis.ts src/components/settings/SettingsTabs.vue`
- `cd frontend && npx eslint src/views/JobHistoryView.vue src/views/JobView.vue src/views/JobsView.vue src/views/settings/SettingsAccessControl.vue src/composables/GatewayAPI.ts src/composables/ClusterAnalysis.ts src/components/settings/SettingsTabs.vue`
- `npm --prefix frontend run type-check`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/test_access_control_policy.py slurmweb/tests/test_access_control_store.py slurmweb/tests/apps/test_agent.py slurmweb/tests/apps/test_agent_ai.py slurmweb/tests/views/test_agent_permissions.py slurmweb/tests/views/test_agent_ai.py slurmweb/tests/views/test_agent.py slurmweb/tests/views/test_gateway.py`
- `cd frontend && npx vitest run tests/stores/runtime.spec.ts tests/components/MainMenu.spec.ts tests/views/JobsView.spec.ts tests/views/JobView.spec.ts tests/views/AssistantView.spec.ts tests/views/settings/SettingsAI.spec.ts tests/views/settings/SettingsAccessControl.spec.ts tests/composables/GatewayAPIAdminContract.spec.ts tests/composables/GatewayAPI.spec.ts tests/router/AdminPermissions.spec.ts tests/views/ForbiddenView.spec.ts`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py slurmweb/tests/apps/test_agent_ai.py slurmweb/tests/views/test_agent_ai.py`
