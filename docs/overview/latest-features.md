# 最新功能

## 本轮：GitHub Actions 已切到 `main` 分支自动测试，并补结构化结果 artifact

本轮把仓库 CI 从“以手工触发为主”收敛到“提交即自动验证”：

- `pull_request` 到 `main` 自动触发
- `push` 到 `main` 自动触发
- 仍保留 `workflow_dispatch`

当前自动 CI 固定版本为：

- 后端 `Python 3.12`
- 前端 `Node 18`

本轮自动运行的检查包括：

- 后端单元测试
- 前端单元测试
- 前端 `ESLint`
- 前端 `TypeScript type-check`
- 前端生产构建

其中后端 CI 已显式收敛到 `pytest slurmweb/tests`，避免把仓库内历史 `slurmweb4.2/tests` 兼容测试树误收进当前主线 CI。

随后又补了一次后端依赖声明修复：

- `cryptography` 已加入 `.[agent]` 与 `.[tests]`
- 避免 `slurmweb.ai.crypto` 在 GitHub `Backend Tests` 中导入失败
- AI 相关后端测试不再因为缺包在 collection 阶段整体中断

同时补了统一的 CI 结果产物契约，每个 job 都会尝试上传：

- `stdout.log`
- `result.json`
- `failure-context.json`

测试类 job 额外上传：

- `junit.xml`

为便于后续 AI 或脚本消费失败上下文，本轮新增手工 `CI Triage` workflow：

- 输入 `run_id`
- 可按 `backend` / `frontend` / `all` 聚合 artifact
- 输出 `triage-context.json`

明确边界：

- 当前仓库内置 AI 还不能直接读取 GitHub Actions
- 当前也不会自动修复失败测试或自动提 PR
- 本轮只把“结果可查询、可聚合”的基础设施铺平

发布后又补了一组前端 lint 修复：

- `JobsHistoryFiltersPanel` 与 `JobsHistoryFiltersBar` 不再直接修改 `filters` prop
- 改为通过 `update:filters` 事件回传新对象，由 `JobsHistoryView` 统一更新筛选状态
- 已补对应 Vitest 断言，覆盖“发事件而不是改 prop”的行为
- 同时清理了 `JobHistoryView`、`ClusterAnalysis`、`SettingsTabs` 与 `GatewayAPI` 中阻塞 `Frontend ESLint` 的未使用符号和空接口类型
- 继续清理了 `JobView`、`JobsView` 与 `SettingsAccessControl` 中剩余的未使用符号，补齐主线前端静态检查

## 本轮：旧动作配置收口、`admin-manage` 改为超级管理员别名并删除失效 agent 字段

本轮继续收紧权限与配置契约：

- `policy.yml` / `policy.ini` 已移除 7 个旧动作配置入口：
  - `view-own-jobs`
  - `edit-own-jobs`
  - `cancel-own-jobs`
  - `roles-view`
  - `roles-manage`
  - `view-ai`
  - `manage-ai`
- `GET /permissions.actions` 与 `GET /access/catalog.legacy_map` 不再暴露这 7 个动作
- 管理端角色页不再派生或展示这 7 个 compatibility actions
- `admin-manage` 现在只等价于 `*:*:*`
- 只有 `super-admin` 或其他实际拥有 `*:*:*` 的角色/用户才会回显 `admin-manage`
- `default_seed_roles().user` 继续保留：
  - `jobs:view:self`
  - `jobs:edit:self`
  - `jobs:delete:self`
  - `user/analysis:view:self`
- 上述默认自有 Jobs / 自有分析能力现在只来自数据库种子角色，不再来自 vendor policy 动作
- `default_seed_roles().admin` 继续是 `*:view:*` + `*:edit:*`
- `default_seed_roles().super-admin` 继续是 `*:*:*`
- Agent 配置中已物理删除：
  - `persistence.enabled`
  - `persistence.access_control_enabled`
  - `user_metrics.enabled`
  - `node_metrics.enabled`
  - `ai.enabled`
- AI 现在完全按数据库与模型配置可用性启用，不再读取显式 `ai.enabled`

## 本轮：默认权限模型按 `jobs:*:self` 与全局 `admin view/edit` 修正

本轮对权限基线做了审查修正，当前默认行为固定为：

- 普通 `user` 默认拥有非 `Admin` 页面只读权限
- 普通 `user` 默认拥有 `jobs:view:self`
- 普通 `user` 默认拥有 `jobs:edit:self`
- 普通 `user` 默认拥有 `jobs:delete:self`
- 默认 `admin` 角色拥有 `*:view:*` 与 `*:edit:*`
- 默认 `admin` 角色不拥有 `*:delete:*`

当前保留的旧动作兼容只剩：

- `cache-view` -> `admin/cache:view:*` + `admin/ldap-cache:view:*`
- `cache-reset` -> `admin/cache:edit:*`
- `admin-manage` -> `*:*:*`

这次修正不会改变资源级鉴权框架；最终判定仍然只依赖 `resource:operation:scope` 规则。

## 本轮：发布后审查补了共享操作对话框的安全回归修复

针对本轮新增的大量单对象写操作，发布后代码审查已补一个前端共享组件缺陷修复：

- `ActionDialog` 在复用到不同操作时会先清空旧表单字段
- 避免编辑/提交阶段的残留参数被错误带到删除、取消等空表单请求
- 已新增 `ActionDialog` 组件级回归测试覆盖该场景

## 本轮：基于现有页面增强的 Slurm 管理扩展

本轮继续采用“现有业务页面增强 + 集群级 `Admin` 页面 + `analysis` 页面补系统状态”的结构，没有再新增独立全量管理中心。

已落地的重点包括：

- `Jobs` / `Job`
  - 单作业提交、编辑、取消
- `Resources` / `Node`
  - 单节点更新、删除
- `Reservations`
  - 创建、更新、删除
- `Accounts` / `Account`
  - 创建、更新、删除
- `User`
  - SlurmDB 用户创建/更新、删除
- `QOS`
  - 创建、更新、删除
- `analysis`
  - 新增 `Slurm ping`
  - 新增 `Slurm diag`

明确未做：

- 批量取消作业
- 批量节点操作

## 本轮：后台管理入口统一迁移到 `/:cluster/admin`

以下原 `settings` 管理能力已迁移到集群级 `Admin`：

- `AI`
- `LDAP Cache`
- `Cache`
- `Access Control`

同时补充了 `Admin > System`，统一承载：

- `licenses`
- `shares`
- `reconfigure`
- `slurmdb diag`
- `slurmdb config`
- `instances`
- `tres`

旧路由会重定向到：

- `/settings/ai` -> `/:cluster/admin/ai`
- `/settings/access-control` -> `/:cluster/admin/access-control`
- `/settings/cache` -> `/:cluster/admin/cache`
- `/settings/ldap-cache` -> `/:cluster/admin/ldap-cache`

## 本轮：`jobs:self` 已落地到后端 owner-aware 校验

`jobs` 资源现在正式支持：

- `jobs:view:self`
- `jobs:edit:self`
- `jobs:delete:self`

当前语义：

- 列表查询优先注入 `user=<login>` 到 `slurmrestd`
- 详情、更新、取消都先查询作业 owner
- 如果用户只有 `self`，只能查看、编辑、取消自己的作业
- 前端只做辅助隐藏/禁用，不作为最终安全边界

默认普通用户的自有 Jobs / 自有分析能力现在来自数据库种子角色 `user`，不再依赖 vendor policy 里的旧动作配置。

行为边界：

- 数据库启用时，普通用户继续拥有 `jobs:view|edit|delete:self` 与 `user/analysis:view:self`
- 数据库未启用时，普通用户不再有自有 Jobs 的旧动作兜底

## 本轮：slurmrestd 写路径补齐并加入版本降级

`slurmweb.slurmrestd` 已扩展为通用请求层，支持：

- `GET`
- `POST`
- `DELETE`
- `DELETE` body

当前兼容策略：

- `0.41-0.44`
  - 开放主写路径
- `0.39-0.40`
  - 保持读兼容
  - 写操作返回 `501`

## 本轮验证结果

已通过：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/router/AdminRoutesContract.spec.ts tests/composables/GatewayAPIAdminContract.spec.ts tests/views/ClusterAnalysisView.spec.ts tests/components/MainMenu.spec.ts tests/stores/runtime.spec.ts`
- `cd frontend && npx vitest run tests/views/JobsView.spec.ts tests/views/ReservationsView.spec.ts tests/views/QosView.spec.ts tests/views/AccountView.spec.ts tests/views/AccountsView.spec.ts tests/views/UserView.spec.ts tests/views/resources/ResourcesView.spec.ts`
- `cd frontend && npx vitest run tests/composables/GatewayAPI.spec.ts tests/composables/GatewayAPIAdminContract.spec.ts tests/router/AdminRoutesContract.spec.ts tests/stores/runtime.spec.ts tests/components/MainMenu.spec.ts tests/components/settings/SettingsTabs.spec.ts tests/components/settings/SettingsTabsAIContract.spec.ts tests/views/settings/SettingsAI.spec.ts tests/views/settings/SettingsAccessControl.spec.ts tests/views/settings/SettingsCache.spec.ts tests/views/settings/SettingsLdapCache.spec.ts`
- `cd frontend && npx vitest run`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/test_access_control_policy.py slurmweb/tests/views/test_gateway.py slurmweb/tests/views/test_agent_operations.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/test_access_control_policy.py slurmweb/tests/views/test_agent_operations.py slurmweb/tests/views/test_gateway_operations.py slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent.py slurmweb/tests/views/test_gateway.py slurmweb/tests/views/test_gateway_clusters.py`

## 1. 路由权限系统切换为规则模型

当前权限模型已经从单一 `actions[]` 扩展为 `resource:operation:scope`：

- 支持主路由资源和子资源，例如 `admin/cache`
- 支持前缀资源，例如 `admin/*:view:*`
- 支持 `self` 场景，例如 `user/profile:view:self`
- 支持全局最高权限 `*:*:*`

当前兼容层只保留少量仍在使用的动作映射；`view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage`、`view-ai`、`manage-ai` 已不再作为正式配置入口或 API 回显动作。

## 2. Access Control 页面改为资源矩阵

`Settings > Access Control` 已从 action 复选框切换为目录驱动的权限矩阵：

- 页面通过 `GET /access/catalog` 获取全部资源目录
- 角色编辑以 `permissions[]` 为主
- 同时展示兼容 `actions[]`
- 支持首次空角色表自动预置 `user`、`admin`、`super-admin`

## 3. Agent 能力开关收敛

系统当前的业务能力按基础依赖自动推导：

- 数据库开启后，自动提供：
  - LDAP Cache
  - Jobs History
  - Access Control
  - AI
- Prometheus 开启后，自动提供：
  - metrics
  - node metrics
- 数据库和 Prometheus 同时开启后，自动提供：
  - user metrics
  - user analytics

旧 feature flag 中 `persistence.enabled`、`persistence.access_control_enabled`、`user_metrics.enabled`、`node_metrics.enabled`、`ai.enabled` 已从 Agent 配置定义中删除。

## 4. AI、Cache、用户空间全部接入新权限

以下页面和入口已经按新规则判定：

- `/:cluster/ai` 使用 `ai:view:*`
- `/:cluster/admin/ai` 使用 `admin/ai:view|edit|delete:*`
- `/:cluster/admin/cache` 使用 `admin/cache:view|edit:*`
- `/:cluster/admin/ldap-cache` 使用 `admin/ldap-cache:view|edit:*`
- `/:cluster/admin/access-control` 使用 `admin/access-control:view|edit|delete:*`
- 用户空间使用 `user/profile:view:*|self` 与 `user/analysis:view:*|self`

## 5. 本轮验证结果

已完成的定向验证包括：

- `npm --prefix frontend run type-check`
- `npx vitest run tests/stores/runtime.spec.ts tests/views/settings/SettingsAccessControl.spec.ts`
- `.venv\Scripts\python.exe -m pytest slurmweb/tests/views/test_agent_permissions.py -q`
- `.venv\Scripts\python.exe -m pytest slurmweb/tests/apps/test_agent.py -q`

## 6. 对外发布名切换到 `slurm-web-plus`

本轮开始把对外发布名统一切到 `slurm-web-plus`：

- Python 包名改为 `slurm-web-plus`
- 新增 `slurm-web-plus` CLI 入口，同时保留 `slurm-web` 兼容别名
- 前端标题、登录入口、匿名入口、品牌文案和日志输出同步切换为 `Slurm Web Plus`
- 前端开发说明中的 `VITE_BASE_PATH` 示例同步改为 `/slurm-web-plus/`

说明：

- 文档站、仓库链接、systemd/service 名和默认目录路径仍有一部分保留旧 `slurm-web` 前缀，尚未宣称“部署层全面改名完成”。

## 7. 发布前 review 与低风险修复

本轮已新增 `docs/review/` 作为发布审查出口，按前端、后端、测试拆分记录：

- `docs/review/frontend-review.md`
- `docs/review/backend-review.md`
- `docs/review/test-review.md`

同时已直接修复的明显问题包括：

- `gen-jwt-key` 在非 Unix 平台因 `pwd` / `geteuid` 缺失而导入失败
- `setfacl` 调用未校验返回码，ACL 设置失败可能被静默吞掉
- AI 显式启用但数据库不可用时缺少明确告警
- `user_activity_summary` / `user_metrics_history` 的权限 scope 解析在运行时错误引用用户名，导致接口可能直接抛异常
- 前端锁文件包名与 `package.json` 不一致

## 8. 本轮新增验证结果

新增通过：

- `npm --prefix frontend run build`
- `npx vitest run`
- `npx vitest run tests/views/LoginView.spec.ts tests/components/BrandLogo.spec.ts`
- `npx vitest run tests/composables/GatewayAPI.spec.ts tests/components/user/UserToolAnalysisChart.spec.ts`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_agent_ai.py -k database_support_missing`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/exec/test_main.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_load_ldap_password_from_file.py slurmweb/tests/apps/test_showconf.py slurmweb/tests/test_ui.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_metrics_requests.py -k user_activity_summary`
- `.venv\Scripts\python.exe -m compileall slurmweb/apps`

## 9. 测试基线已同步当前实现

本轮补齐了几组已经与当前实现脱节的测试：

- `slurmweb/tests/exec/test_main.py` 现在同时覆盖 `slurm-web-plus` 默认名与 `slurm-web` 兼容别名
- `slurmweb/tests/apps/test_genjwt.py` 已同步 `setfacl` 的 `check=True` 与现有日志行为
- `frontend/tests/composables/GatewayAPI.spec.ts` 已按权限规则归一化后的 `rules[]` / `permissions[]` 断言
- `frontend/tests/components/user/UserToolAnalysisChart.spec.ts` 已从旧 Chart.js canvas 断言切到当前 DOM 条形图实现
- `frontend/tests/views/JobHistoryView.spec.ts`、`JobView.spec.ts`、`UserAnalysisView.spec.ts` 与 `MainMenuAIContract.spec.ts` 已同步当前页面结构和权限模型
