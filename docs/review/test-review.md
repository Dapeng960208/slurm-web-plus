# 测试审查报告

## 1. 审查范围

本次测试审查覆盖：

- `frontend/tests/**`
- `slurmweb/tests/**`
- `tests/**`
- 与测试执行直接相关的构建/入口验证命令

目标是识别：

- 当前已通过的定向验证
- 因改名或后端修复而失效的测试基线
- 发布前必须补齐的测试空白

## 2. 已确认通过的验证

### 2.1 前端

已通过：

- `npm --prefix frontend run type-check`
- `npm --prefix frontend run build`
- `npx vitest run`
- `npx vitest run tests/components/BrandLogo.spec.ts`
- `npx vitest run tests/views/LoginView.spec.ts tests/components/BrandLogo.spec.ts`
- `npx vitest run tests/composables/GatewayAPI.spec.ts tests/components/user/UserToolAnalysisChart.spec.ts`

结论：

- 本次品牌名调整没有破坏当前已覆盖的登录页和品牌组件测试。
- `GatewayAPI` 权限归一化和 `UserToolAnalysisChart` 新版 DOM 呈现的测试基线已同步到当前实现。
- 前端完整单测当前为 `78 passed / 508 passed`，构建产物也能正常生成。

### 2.2 后端

已通过：

- `.\\.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/apps/test_agent_ai.py -k database_support_missing`
- `.\\.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/exec/test_main.py`
- `.\\.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py`
- `.\\.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/apps/test_load_ldap_password_from_file.py slurmweb/tests/apps/test_showconf.py slurmweb/tests/test_ui.py`
- `.\\.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/views/test_agent_metrics_requests.py -k user_activity_summary`
- `.\\.venv\\Scripts\\python.exe -m compileall slurmweb/apps`

结论：

- “AI 显式启用但数据库不可用时记录明确告警” 的补丁已被定向验证覆盖。
- CLI 改名兼容和 `gen-jwt-key` 新行为对应的后端测试基线已补齐。
- `user_activity_summary` / `user_metrics_history` 的权限 scope 解析 bug 已补测通过。
- `slurmweb/apps` 目录编译通过。

## 3. 已直接修复的测试基线缺口

### 3.1 `test_main.py` 已同步新旧 CLI 命名兼容策略

- 变更：`slurmweb/tests/exec/test_main.py` 已同时覆盖默认名 `slurm-web-plus` 与旧兼容名 `slurm-web`。
- 当前结果：`.\\.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/exec/test_main.py` -> `10 passed`
- 说明：这类断言以后凡是改 CLI help/version 文案，都要同步检查。

### 3.2 `test_genjwt.py` 已同步 `setfacl` 与日志新行为

- 变更：`slurmweb/tests/apps/test_genjwt.py` 已同步 `check=True`、现有告警与平台兼容分支。
- 当前结果：`.\\.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py` -> `6 passed`
- 说明：后端修复若改变日志集合或外部命令参数，测试应同轮更新，避免制造 CI 假失败。

## 4. 发布风险

### 4.1 Windows 不能代表后端最终发布验证环境

- 全量 `pytest -q` 仍受 `pwd`、`racksdb`、`slurmweb4.2` 兼容树等平台与依赖问题影响。
- 即使把入口收敛到 `pytest -q slurmweb/tests`，当前 Windows 环境下仍存在一批路径、权限、平台语义差异导致的既有失败，不能作为“后端全量已绿”的依据。
- 当前 Windows 本地验证只能做定向检查，不能替代 Linux 完整回归。

### 4.2 还缺少“新旧命名兼容策略”的测试说明

当前代码已经进入“对外名改为 `slurm-web-plus`，内部兼容保留 `slurm-web`”阶段，但测试尚未明确覆盖：

- systemd/service 名称与部署路径是否继续保留旧名
- 发布后文档中的命令示例
- 旧路径/旧服务名是否继续兼容

说明：

- 默认 CLI 输出与旧别名启动帮助信息已经在 `slurmweb/tests/exec/test_main.py` 覆盖。
- 仍未形成自动化验证的是部署层兼容策略，而不是当前 Python 入口本身。

## 5. 发布前建议执行清单

- 在 Linux 环境执行至少一轮后端定向回归：
  - `slurmweb/tests/exec/test_main.py`
  - `slurmweb/tests/apps/test_genjwt.py`
  - `slurmweb/tests/apps/test_agent_ai.py`
- 视发布范围补充部署兼容性验证：
  - systemd unit 名称
  - `/etc/slurm-web` 与 `/etc/slurm-web-plus` 路径策略
  - 旧服务名、旧命令名是否继续并存
- 若继续扩展前端用户空间分析页面，保持 `UserToolAnalysisChart` 的 DOM 结构测试与 `GatewayAPI` 权限归一化测试同步更新

## 6. 本次涉及文件

- `docs/review/test-review.md`
- `frontend/tests/composables/GatewayAPI.spec.ts`
- `frontend/tests/components/user/UserToolAnalysisChart.spec.ts`
- `frontend/tests/components/MainMenuAIContract.spec.ts`
- `frontend/tests/views/JobHistoryView.spec.ts`
- `frontend/tests/views/JobView.spec.ts`
- `frontend/tests/views/UserAnalysisView.spec.ts`
- `slurmweb/tests/exec/test_main.py`
- `slurmweb/tests/apps/test_genjwt.py`
- `slurmweb/tests/apps/test_load_ldap_password_from_file.py`
- `slurmweb/tests/apps/test_showconf.py`
- `slurmweb/tests/test_ui.py`
- `slurmweb/tests/views/test_agent_metrics_requests.py`

本次审查已直接补齐一批失效测试基线；当前剩余风险主要集中在 Linux 发布验证和部署层命名兼容策略。
