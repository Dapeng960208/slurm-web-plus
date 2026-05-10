# 测试审查报告

## 1. 审查范围

本次测试审查聚焦以下主题：

- 权限规则与共享权限消费点的关键测试是否覆盖
- 本地源码目录运行测试时是否还会被环境问题提前阻断
- 前端样式/权限本轮修复点是否有定向测试
- 当前未验证范围是否被明确记录

重点核对文件：

- `frontend/tests/stores/runtime.spec.ts`
- `frontend/tests/router/AdminPermissions.spec.ts`
- `frontend/tests/components/MainMenu.spec.ts`
- `frontend/tests/views/settings/SettingsAccessControl.spec.ts`
- `frontend/tests/views/DashboardView.spec.ts`
- `frontend/tests/views/NodeView.spec.ts`
- `frontend/tests/components/jobs/JobsFiltersPanel.spec.ts`
- `frontend/tests/components/dashboard/DashboardCharts.spec.ts`
- `frontend/tests/composables/userWorkspace.spec.ts`
- `slurmweb/tests/test_permission_rules.py`
- `slurmweb/tests/test_access_control_policy.py`
- `slurmweb/tests/test_access_control_store.py`
- `slurmweb/tests/views/test_agent_permissions.py`
- `slurmweb/tests/views/test_gateway_permissions.py`
- `slurmweb/tests/test_version.py`

## 2. 已确认通过的关键验证

### 2.1 前端

已通过：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/views/DashboardView.spec.ts tests/views/NodeView.spec.ts tests/components/jobs/JobsFiltersPanel.spec.ts tests/components/dashboard/DashboardCharts.spec.ts tests/composables/userWorkspace.spec.ts`

结论：

- 本轮共享权限消费点的修复都有对应定向 Vitest 覆盖。
- 新增断言已经开始优先使用 `rules[]`，而不是继续把旧 `actions[]` 作为唯一测试基线。

### 2.2 后端

已通过：

- `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/test_version.py`
- `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/test_access_control_policy.py slurmweb/tests/test_access_control_store.py slurmweb/tests/views/test_agent_permissions.py slurmweb/tests/views/test_gateway_permissions.py`

结论：

- 权限规则解析、策略合并、数据库兼容逻辑和网关/Agent 权限主链路已有定向回归。
- 源码 checkout 直接跑后端测试时，`get_version()` 的包元数据缺失问题已有专门回归测试。

## 3. 已确认并已修复的测试基线问题

### 3.1 源码目录运行后端测试会因缺少包元数据提前失败

已修复：

- `slurmweb/version.py` 在找不到已安装包元数据时，回退读取仓库 `pyproject.toml` 的 `project.version`
- `slurmweb/tests/test_version.py` 覆盖“回退成功”和“回退仍缺失”两条路径

影响：

- 本地或 CI 直接在源码目录运行 `pytest slurmweb/tests` 时，不会因为 `PackageNotFoundError` 在导入阶段提前中断

### 3.2 无 `python-ldap` 环境下 gateway / ldap 测试会在 collection 阶段失败

已修复：

- `slurmweb/tests/lib/gateway.py` 的测试侧 `ldap` stub 已补 `ldap.filter` 子模块

影响：

- GitHub Linux runner 在未安装 `python-ldap` 的情况下，仍可完成 gateway / ldap 相关测试收集

### 3.3 前端部分时间窗测试会因全量 fake timers 干扰 `vue-i18n`

已修复：

- `frontend/tests/components/MetricRangeSelector.spec.ts`
- `frontend/tests/views/UserAnalysisView.spec.ts`

处理方式：

- 改为 `vi.useFakeTimers({ toFake: ['Date'] })`
- 只冻结当前时间，不接管 `performance`

## 4. 当前缺口与风险

### 4.1 仍有部分前端测试夹具以旧 `actions[]` 为主

- 本轮触达的共享权限消费点已经补了 `rules[]` 覆盖。
- 仓库中仍有部分未改到的旧夹具，后续扩大权限回归时需要继续迁移。

### 4.2 当前没有把全量测试作为本轮唯一验收标准

- Windows 本地环境不适合把 `pytest -q` 作为最终结论。
- 全量前端 `vitest` 虽可继续执行，但当前更有价值的是围绕改动点做定向验证，避免把历史噪音误记为本轮失败。

## 5. 未验证范围

- 本轮未重新全量执行 `cd frontend && npx vitest run`
- 本轮未重新执行全量 `pytest -q`
- 本轮未在 Linux 发布环境重跑完整后端回归

## 6. 建议

- 新增权限相关页面时，测试夹具优先提供 `rules[]`，`actions[]` 只作为兼容补充。
- 对会受运行时环境影响的测试问题，优先先做“源码态可收集、可运行”的稳定性修复，再讨论扩大回归范围。
- 若后续继续调整 `Admin` / `Settings` 权限资源名，必须同步补 `MainMenu`、路由守卫和页面局部控件的定向测试。
