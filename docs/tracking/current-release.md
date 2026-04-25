# 当前发布跟踪：代码审查、发布命名切换与补文档

## 1. 当前主题

本轮发布聚焦三条主线：

- 基于现有代码完成前端、后端、测试审查并补齐 `docs/review/`
- 对外发布名切换到 `slurm-web-plus`
- 修复可直接落地的明显低风险问题，同时把风险和待确认项写入文档

## 2. 已完成项

- 新增 `docs/review/README.md`
- 新增前端审查文档 `docs/review/frontend-review.md`
- 新增后端审查文档 `docs/review/backend-review.md`
- 新增测试审查文档 `docs/review/test-review.md`
- Python 包名切换到 `slurm-web-plus`
- 新增 `slurm-web-plus` CLI 入口，同时保留 `slurm-web` 兼容别名
- 前端标题、品牌文案、登录页、匿名页、日志文案切换为 `Slurm Web Plus`
- 前端锁文件根包名与 `package.json` 对齐
- `gen-jwt-key` 增加非 Unix 平台兼容兜底，避免导入阶段直接失败
- `gen-jwt-key` 的 `setfacl` 调用改为校验返回码
- AI 显式启用但数据库不可用时，Agent 现在会记录明确告警
- AI 需求文档增加“数据库不可用时的告警与降级”说明
- 前端 `GatewayAPI` / `UserToolAnalysisChart` 测试基线已同步当前实现
- 后端 CLI 改名兼容与 `gen-jwt-key` 修复对应测试基线已补齐
- `AGENTS.md` 已增加“Windows PowerShell 读取中文文档必须显式 UTF-8”的约束
- `AGENTS.md` 与 `docs/**/*.md` 已统一补齐 UTF-8 BOM，降低 WinPS 5 裸 `Get-Content` 读取中文文档时的乱码概率
- 前端全量 Vitest 已恢复绿色，历史明细/用户分析/MainMenu 契约测试基线已同步当前 UI
- 修复 `user_activity_summary` / `user_metrics_history` 装饰器权限 scope 解析错误，避免请求用户名作用域在运行时触发异常

## 3. 进行中项

- 确认部署层是否继续保留旧 `slurm-web` 服务名、目录名和路径前缀
- 确认 Linux 发布环境下的最终回归与打包验证范围

## 4. 风险与阻塞

- 后端部署层命名迁移尚未完成：
  - `conf/**`
  - `lib/**`
  - 旧 systemd / uWSGI / sysusers / 兼容脚本
- 全量后端测试仍需要 Linux 环境完成最终验证
- `pytest -q slurmweb/tests` 在当前 Windows 环境仍存在大量既有失败，不能作为发版前全量回归结论

## 5. 已同步文档

- `docs/README.md`
- `docs/review/README.md`
- `docs/review/frontend-review.md`
- `docs/review/backend-review.md`
- `docs/review/test-review.md`
- `docs/overview/project-overview.md`
- `docs/overview/latest-features.md`
- `docs/features/ai/requirements.md`
- `docs/tracking/current-release.md`
- `docs/tracking/error-log.md`

## 6. 验证状态

已通过：

- `npm --prefix frontend run type-check`
- `npx vitest run tests/views/LoginView.spec.ts tests/components/BrandLogo.spec.ts`
- `npx vitest run tests/composables/GatewayAPI.spec.ts tests/components/user/UserToolAnalysisChart.spec.ts`
- `npm --prefix frontend run build`
- `npx vitest run`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_agent_ai.py -k database_support_missing`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/exec/test_main.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_load_ldap_password_from_file.py slurmweb/tests/apps/test_showconf.py slurmweb/tests/test_ui.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_metrics_requests.py -k user_activity_summary`
- `.venv\Scripts\python.exe -m compileall slurmweb/apps`
