# 最新功能

## 1. 路由权限系统切换为规则模型

当前权限模型已经从单一 `actions[]` 扩展为 `resource:operation:scope`：

- 支持主路由资源和子资源，例如 `settings/cache`
- 支持前缀资源，例如 `settings/*:view:*`
- 支持 `self` 场景，例如 `user/profile:view:self`
- 支持全局最高权限 `*:*:*`

同时保留旧权限名兼容层，`view-ai`、`roles-manage`、`cache-reset` 等历史动作会自动映射到新规则。

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
- `Settings > AI` 使用 `settings/ai:view|edit|delete:*`
- `Settings > Cache` 使用 `settings/cache:view|edit:*`
- `Settings > LDAP Cache` 使用 `settings/ldap-cache:view:*`
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
