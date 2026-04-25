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

## 本轮：默认权限模型按 `jobs:*:self` 与全局 `admin view/edit` 修正

本轮对权限基线做了审查修正，当前默认行为固定为：

- 普通 `user` 默认拥有非 `Admin` 页面只读权限
- 普通 `user` 默认拥有 `jobs:view:self`
- 普通 `user` 默认拥有 `jobs:edit:self`
- 普通 `user` 默认拥有 `jobs:delete:self`
- 默认 `admin` 角色拥有 `*:view:*` 与 `*:edit:*`
- 默认 `admin` 角色不拥有 `*:delete:*`

同时新增两个旧动作兼容映射：

- `edit-own-jobs` -> `jobs:edit:self`
- `admin-manage` -> `/:cluster/admin` 下全部 `admin/*` 管理规则

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

为兼容旧动作，新增：

- `view-own-jobs`
- `edit-own-jobs`
- `cancel-own-jobs`

vendor policy 中普通 `user` 已从全量 `view-jobs` 切到 `view-own-jobs` / `edit-own-jobs` / `cancel-own-jobs`，且不再默认带 cache/admin 管理动作。

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

同时保留旧权限名兼容层，`view-ai`、`roles-manage`、`admin-manage`、`edit-own-jobs`、`cache-reset` 等历史动作会自动映射到新规则。

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

旧 feature flag 仅保留兼容占位定义，不再作为实际产品语义来源。

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
