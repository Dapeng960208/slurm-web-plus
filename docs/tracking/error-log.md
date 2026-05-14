# 开发错误库（简化版）
本文件仅保留可复现错误的时间、现象和解决办法，便于快速检索。
写入规则见：`docs/standards/development-error-summary.md`。

## 记录格式

### YYYY-MM-DD：一句话概括
- 时间：YYYY-MM-DD
- 现象：
- 解决办法：

## 条目

### 2026-05-14：AD 域根做 LDAP 用户枚举时触发 `Size limit exceeded`
- 时间：2026-05-14
- 现象：`slurm-web ldap-check --debug --debug-flags rfl` 在服务账号 bind 成功后，继续对 `DC=...` 域根执行用户枚举时抛 `ldap.SIZELIMIT_EXCEEDED`；而现场目录结构同时把用户分散在多个并列 OU 下，单一 `user_base` 又不足以覆盖全部登录入口
- 解决办法：本地 LDAP 适配层已补多 `user_base` / `group_base` 支持，登录时逐个 base 查单用户；`ldap-check` / `users()` 在支持分页控件时改用 paged search，降低 Active Directory 大目录直接撞 size limit 的概率；运维侧仍建议优先把 base 收窄到真实 OU，而不是继续使用域根

### 2026-05-14：GitHub CI dry-run 重复下载同一 run artifact 时会因旧文件残留中断
- 时间：2026-05-14
- 现象：执行 `powershell -ExecutionPolicy Bypass -File scripts/continue-from-github-ci.ps1 -RunId 25776927006` 时，内部二次调用 `fetch-github-ci-result.ps1` 下载同一成功 run 的 artifact，`gh run download` 报 `error extracting "failure-context.json": ... The file exists`
- 解决办法：`scripts/fetch-github-ci-result.ps1` 在 `-DownloadArtifacts` 分支先清空当前 run 目录下所有已有 artifact 子目录，再执行 `gh run download`，避免仅按最新 artifact 名单局部删除时遗漏旧残留文件

### 2026-05-12：Dashboard 分区切换后统计卡仍可能显示整集群资源，且队列下拉框与外层描边重叠
- 时间：2026-05-12
- 现象：在 `/:cluster/dashboard` 选择具体分区后，下方统计卡仍可能继续显示整集群的节点、CPU、内存和作业总量；同时分区下拉框的内层描边与外层 pill 容器边缘叠在一起，视觉上像“双层挤压”
- 解决办法：Dashboard 视图在选中分区且具备 `jobs/resources` 可见性时，优先按当前分区的节点和作业数据在前端重算统计卡，避免继续误显全局资源；同时收紧下拉框内边距、去掉额外外框并改为聚焦光环，消除与外层 toolbar 容器的描边重叠

### 2026-05-12：普通用户可直接访问 `/:cluster/admin` 顶层入口
- 时间：2026-05-12
- 现象：虽然普通用户没有任何 `admin/*` 权限时不会通过 `admin-cache` 等子路由守卫，但直接访问 `/:cluster/admin` 会先命中默认重定向到 `analysis`，导致前端没有先返回 `forbidden`，形成后台入口越权跳转
- 解决办法：把 `admin` 默认子路由改为带权限判断的 `redirect`；只有具备任一 `admin/*:view:*` 或 `*:*:*` 时才允许执行默认跳转，否则直接返回 `forbidden` 并携带 `admin/*:view:*` 缺权信息

### 2026-05-12：用户分析历史新增状态曲线后，旧后端测试只准备两次查询结果
- 时间：2026-05-12
- 现象：在执行扩展后的本地回归 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_user_analytics_store.py ...` 时，`test_user_metrics_history_seven_day_window_matches_naive_utc_buckets` 因 `user_metrics_history()` 现在会额外查询 `running/pending/failed/cancelled` 四条状态时间线，而旧测试只给 `cursor.fetchall.side_effect` 提供“提交/完成”两次返回，最终在第三次读取时抛 `StopIteration`
- 解决办法：把该测试夹具补齐为 6 次 `fetchall()` 返回，并同时断言新增状态总量为 `0`，避免后续再次把“能力扩展后的正常附加查询”误报成回归

### 2026-05-12：Frontend Tests 仍按旧用户分析文案和双曲线假设断言
- 时间：2026-05-12
- 现象：GitHub Actions `Frontend Tests` run `25736916169` 中，`tests/views/UserView.spec.ts` 仍断言 analytics section 包含旧文案 `Submission and tool analytics`，而当前页面通过 stub 只呈现 `Completed Job Tool Analysis`；`tests/components/user/UserSubmissionHistoryChart.spec.ts` 仍假设图表只有 `submissions/completions` 两条数据集，但当前实现已扩展为 `submissions/completions/running/pending/failed/cancelled` 六条曲线，导致远端单测失败
- 解决办法：把 `UserView` 测试改为断言 `#analysis` 区块存在且 analytics stub 已渲染；把 `UserSubmissionHistoryChart` 测试更新为断言 6 条数据集及新增状态曲线的空数组默认值，避免已实现的多状态分析继续被旧测试误判为失败

### 2026-05-12：AI 直接输出 `job/cancel` 作为 tool name 时会被后端误判为不支持工具
- 时间：2026-05-12
- 现象：超级管理员在 AI 对话中执行取消作业时，模型直接输出 `job/cancel` 作为 tool name，`slurmweb.ai.tools.AIToolRegistry` 只接受 `query_agent_interface` / `mutate_agent_interface`，最终返回 `Unsupported tool job/cancel` 并在前端表现为接口 `500`
- 解决办法：AI 工具层增加“直接接口名”兼容分发；当 tool name 命中已注册 Agent interface 时，按接口读写属性自动映射到 `dynamic-query` 或 `dynamic-mutate`，并继续复用原有权限与 owner-aware 校验

### 2026-05-12：普通用户 AI 页面首屏错误请求 `ai/configs` 会直接冒出 403
- 时间：2026-05-12
- 现象：普通用户虽然具备 `ai:view:*` 且允许进入 `/:cluster/ai`，但 `AssistantView` 初始化时仍先请求 `ai/configs`；该接口要求 `admin/ai:view:*`，导致页面首屏直接显示 `Request failed with status code 403`
- 解决办法：普通 AI 页不再把管理员模型配置接口作为初始化前置依赖；仅当用户具备 `admin/ai:view:*` 时才读取 `ai/configs`，普通用户改为依赖 `capabilities.ai.default_model_id` 和会话自身 `model_config_id` 兜底

### 2026-04-24：示例标题（用一句话概括）
- 时间：2026-04-24
- 现象：
- 解决办法：

### 2026-05-12：集群分析页自定义时间窗只改路由但不会立即刷新分析数据
- 时间：2026-05-12
- 现象：`ClusterAnalysisView.vue` 已把 `start/end` 写入 query，但刷新逻辑只监听 `selectedRange`，导致手动应用自定义时间窗后 metrics、历史作业和热点数据不会立刻重拉
- 解决办法：把分析页数据刷新 watch key 扩展到 `cluster + selectedRange + customStart + customEnd`，确保自定义窗口变化后立即触发统一刷新

### 2026-05-12：节点热点接口缺少时间窗时仍继续访问 slurmrestd 节点列表
- 时间：2026-05-12
- 现象：`/analysis/node-hotspots` 在缺少 `start/end` 时，本应直接返回 `400`，但因为未先拦截空窗口，测试环境继续进入 `slurmrestd.nodes()`，在 Windows 下触发 `socket.AF_UNIX` 相关异常栈
- 解决办法：在 `analysis_node_hotspots()` 中显式要求 `start` 和 `end` 同时存在，缺失时先抛 `ValueError("start and end must both be provided")` 并返回 `400`

### 2026-05-08：Dashboard 视图测试直接用 `wrapper.text()` 断言 `RouterLink` 文本会误报失败
- 时间：2026-05-08
- 现象：页面真实实现仍存在跳转按钮，但 `tests/views/DashboardView.spec.ts` 使用 `wrapper.text()` 或直接查 `RouterLinkStub` 时断言失败；同组 dashboard 测试其余用例全部通过，失败集中在头部 actions 区域文案检查
- 解决办法：改为断言 `[data-testid="dashboard-header-tools"] .ui-button-primary` 的存在性，直接覆盖头部操作区真实 DOM

### 2026-05-10：前端接入 `vue-i18n` 后，旧测试基线会因缺少插件和硬编码文案断言失败
- 时间：2026-05-10
- 现象：执行 `cd frontend && npx vitest run` 时，部分组件测试因新组件调用 `useI18n()` 但挂载时未注入 `i18n` 插件而报 `Need to install with app.use function`；另有少量测试仍直接断言旧英文菜单字段或固定中文文案，导致国际化改造后全量回归失败
- 解决办法：为相关组件测试统一注入 `i18n` 插件；对语言敏感测试显式设置 locale；把旧硬编码菜单/页面文案断言改为翻译 key 或当前 locale 下的目标文案

### 2026-05-12：远端 CI 在前端国际化提交后暴露出 lint 回归和后端旧测试夹具不匹配
- 时间：2026-05-12
- 现象：GitHub Actions 中 `Frontend Static Analysis` 的 `Frontend ESLint` 失败，`ClusterAnalysisView.vue` 和 `UserView.vue` 用 `locale.value` 作为无副作用表达式建立响应依赖，被 `@typescript-eslint/no-unused-expressions` 拦截；同一提交的 `Backend Tests` 中，`slurmweb/tests/views/test_agent_metrics_collector.py` 仍按旧行为只 mock `nodes/jobs`，但当前 `SlurmWebMetricsCollector` 已无条件追加分区级指标请求，导致 `/metrics` 视图测试在 CI 中耗尽 mocked slurmrestd 响应并抛 `RuntimeError: generator raised StopIteration`
- 解决办法：前端把 `ClusterAnalysisView` 的 locale 依赖改为显式传参给 `analyzeCluster()`，移除 `UserView` 中多余的 `locale` 访问，并清理 `SettingsLdapCache.vue` 的未使用导入；后端保持 collector 当前分区指标实现不变，只把 `test_agent_metrics_collector.py` 调整为显式 mock `self.app.slurmrestd.partitions = []`，让该视图层测试继续只验证 `/metrics` 端点基础行为，分区级指标细节仍由 `slurmweb/tests/metrics/test_collector.py` 覆盖

### 2026-05-12：`watch-github-ci.ps1` 用字符串数组转发参数时会把 `-OutputRoot` 误绑到 `-Conclusion`
- 时间：2026-05-12
- 现象：执行 `scripts/watch-github-ci.ps1` 轮询到 workflow 完成后，二次调用 `fetch-github-ci-result.ps1` 会报 `Cannot validate argument on parameter 'Conclusion'. The argument ".ci-results/github" does not belong to the set ...`，导致本地 `github-ci-autofix` 流程在抓取最终结果前中断
- 解决办法：把 `watch-github-ci.ps1` 的二次调用从字符串数组 splat 改为命名参数 hashtable splat，确保 `RunId`、`OutputRoot`、`DownloadArtifacts`、`ShowFailedLog` 按参数名稳定绑定

### 2026-05-12：CI 修复提交本地完成但推送 GitHub 时遇到 443 连接失败
- 时间：2026-05-12
- 现象：执行 `powershell -ExecutionPolicy Bypass -File scripts/push-and-watch-github-ci.ps1 -Workflow "Frontend Tests"` 时，`git push origin main` 失败，报错 `Failed to connect to github.com port 443 after 21095 ms: Could not connect to server`；最新本地提交 `1f2c7c9` 未触发新的远端 GitHub Actions
- 解决办法：先完成本地提交并保留验证记录，待网络恢复后重新执行 `git push origin main` 或仓库脚本 `scripts/push-and-watch-github-ci.ps1`

### 2026-05-10：GitHub `Backend Tests` 在无 `python-ldap` 环境下会因 `import ldap.filter` 在 collection 阶段中断
- 时间：2026-05-10
- 现象：GitHub Actions Linux runner 上执行 `pytest slurmweb/tests` 时，`slurmweb/tests/lib/gateway.py` 里的旧 `ldap` stub 只伪造了顶层 `ldap` 模块；`rfl.authentication.ldap` 继续执行 `import ldap.filter` 后报 `ModuleNotFoundError: No module named 'ldap.filter'; 'ldap' is not a package`，导致 gateway / ldap 相关测试在 collection 阶段中断
- 解决办法：把测试侧 `ldap` stub 改成 package 形态，补 `__path__`、`sys.modules["ldap.filter"]` 和最小 `filter_format()`；继续允许 gateway / ldap 测试在无 `python-ldap` 的 CI 环境下导入模块图

### 2026-05-10：源码目录直接跑后端测试时，`get_version()` 会因缺少包元数据让 gateway / agent 测试导入失败
- 时间：2026-05-10
- 现象：在未执行 `pip install -e .` 的本地或 CI 环境中，`slurmweb.apps.agent` 和 `slurmweb.tests.lib.gateway.fake_slurmweb_agent()` 会在导入或构造阶段调用 `get_version()`；若环境里没有 `slurm-web-plus` / `slurm-web` 的已安装包元数据，就会抛 `PackageNotFoundError: Neither slurm-web-plus nor slurm-web is installed`
- 解决办法：`slurmweb/version.py` 保留“优先读已安装包元数据”的逻辑，但在源码 checkout 中回退读取仓库 `pyproject.toml` 的 `project.version`；补 `slurmweb/tests/test_version.py` 覆盖回退成功和回退缺失两条分支

### 2026-05-10：Vitest 全量 fake timers 会让 `vue-i18n` 在渲染时触发 `invalid timestamp`
- 时间：2026-05-10
- 现象：`MetricRangeSelector.spec.ts` 和 `UserAnalysisView.spec.ts` 在 `vi.useFakeTimers()` 后挂载带 `useI18n()` 的组件时，`vue-i18n` 开发态会经过 `window.performance.mark/measure`，最终报 `TypeError: -670107.545519 is not a valid timestamp`
- 解决办法：对这类只需要冻结“当前时间”的测试，改为 `vi.useFakeTimers({ toFake: ['Date'] })`，只伪造 `Date`，不接管 `performance` 和其它浏览器计时器

### 2026-05-09：固定应用壳下非表格内容页缺少内部滚动容器会导致正文无法下滚
- 时间：2026-05-09
- 现象：`Dashboard`、`Analysis` 以及 `/:cluster/admin/*` 子页面在使用固定高度 `ui-shell` / `ui-content-workspace` 时，若正文直接堆叠在工作区下方而没有内部 `ui-scroll-region`，页面会出现“表格区域能滚动，但详情或配置内容无法继续向下滚动”的共性问题
- 解决办法：为非表格内容页统一补充 `ui-scroll-region min-h-0 flex-1 pr-1` 作为正文滚动容器；对管理页改在 `AdminLayoutView` 父布局统一包裹 `RouterView`，避免在各管理子页面重复修补

### 2026-05-07：本地提交流程被 `.git/index.lock` 短暂阻断
- 时间：2026-05-07
- 现象：Git 返回 `fatal: Unable to create '.../.git/index.lock': File exists.`，导致暂存失败
- 解决办法：先检查活跃 Git 进程和 `.git/index.lock` 是否仍存在；确认锁文件已经消失后，重新执行 `git add`

### 2026-05-07：根目录执行 `pytest -q` 会被 `slurmweb4.2` 参考测试树和可选依赖阻断
- 时间：2026-05-07
- 现象：pytest 在收集阶段直接失败，未进入当前主线 `slurmweb/tests/**` 的执行阶段；典型错误包括 `ImportError: cannot import name 'SlurmwebConfSeed' from 'slurmweb.apps'` 和 `ModuleNotFoundError: No module named 'racksdb'`；报错来源集中在 `slurmweb4.2/tests/**`
- 解决办法：本轮验收改为执行当前主线测试入口 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests`；同时保留根级 `pytest -q` 失败记录，避免误判为本轮业务改动导致的主线回归

### 2026-05-07：把资源补齐共享到聚合前链路后，脚本测试仍按“原始浮点值”和“不会初始化 Slurm REST”断言
- 时间：2026-05-07
- 现象：`rebuild-user-tool.py` 相关测试仍断言脚本“不会初始化 `slurmrestd`”；`backfill-job-snapshot-usage.py` 相关测试仍断言写回值和日志使用 detail 原始浮点值，而不是 `job_snapshots` 实际入库时的两位小数
- 解决办法：更新 `rebuild-user-tool.py` / `repair-user-tool-daily-stats.py` 测试，补 `make_slurmrestd` 与 `JobsStore.backfill_usage_fields()` mock，并断言先执行预补齐；更新 `backfill-job-snapshot-usage.py` 测试，改为断言写回值和日志使用两位小数

### 2026-05-07：`pip install SQLAlchemy` 显示已安装，但 `slurm-web-agent` 仍报 `No module named 'sqlalchemy'`
- 时间：2026-05-07
- 现象：`pip` 输出 `Requirement already satisfied: SQLAlchemy in /usr/local/lib64/python3.9/site-packages`；但 `journalctl -u slurm-web-agent` 仍持续报 `ModuleNotFoundError: No module named 'sqlalchemy'`；启动栈显示服务入口是 `/usr/bin/slurm-web`，代码加载路径是 `/usr/lib/python3.9/site-packages/slurmweb/...`
- 解决办法：对这类系统 Python / RPM 部署节点，改用系统包安装：`dnf install -y python3-sqlalchemy`；安装后执行 `systemctl reset-failed slurm-web-agent && systemctl restart slurm-web-agent`

### 2026-05-07：`backfill-job-snapshot-usage.py` 全量输出 `detail_error`
- 时间：2026-05-07
- 现象：日志显示 `job_snapshot_usage updated: scanned=278126 updated=0 skipped=278126`，逐条记录均为 `decision=skipped reason=detail_error`，无法判断是认证、连接、版本还是调用错误
- 解决办法：新增 `fetch_job_detail()`，当 client 有 `job()` 时使用公开方法，否则用 `_acctjob()` 加可选 `_ctldjob(ignore_notfound=True)` 兼容基础 `Slurmrestd`；`job_snapshot_usage row:` 日志新增 `error_type` 与截断后的 `error`，避免系统性失败时丢失异常上下文；补单测覆盖基础 `Slurmrestd` 无 `job()` 方法和 `detail_error` 异常信息输出

### 2026-05-07：`job/history/detail` 补齐资源但日表重建仍看到 `used_memory_gb = NULL`
- 时间：2026-05-07
- 现象：示例作业 `job_id=996542` 的详情接口返回 `used_memory_gb=2.3984947204589844`、`used_cpu_cores_avg=0.8976156767441861`，但 rebuild 日志仍显示 `used_memory_gb=null`、`used_cpu_cores_avg=null`
- 解决办法：`JobsStore._prepare_rows()` 在 `COMPLETED` 作业持久化前对缺失 `used_memory_gb` 或 `used_cpu_cores_avg` 的行同步查询 Slurm REST detail，并只把这两个字段写入待持久化 row；新增 `slurmweb/scripts/backfill-job-snapshot-usage.py`，用于补齐历史 `job_snapshots.used_memory_gb` 与 `used_cpu_cores_avg`；`rebuild-user-tool.py` 删除统计查询时 enrich 逻辑，继续只读取 `job_snapshots` 当前字段；历史修复顺序为先 backfill，再 rebuild

### 2026-05-07：PowerShell 中使用 `&&` 串联 Git 验证命令失败
- 时间：2026-05-07
- 现象：执行 `git show --stat --oneline --no-patch HEAD && git show --stat --format=short HEAD` 时，PowerShell 报错 `The token '&&' is not a valid statement separator in this version`
- 解决办法：改为分别执行 Git 命令，或使用 PowerShell 原生命令分隔方式

### 2026-05-07：按 `used_memory_gb` 单字段口径同步 rebuild 时旧测试仍断言 fallback
- 时间：2026-05-07
- 现象：`.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_user_analytics_store.py` 初次失败，旧断言仍要求 `_aggregate_rows()` 和日表聚合使用 `usage_stats` / TRES fallback，且旧测试仍把 `0`、负数和字符串当作日表输入
- 解决办法：更新用户分析聚合测试，明确 `used_memory_gb is None` 时跳过，即使 `usage_stats` / TRES 有内存也不写入 `user_tool_daily_stats`；更新 `rebuild-user-tool.py` 脚本测试，覆盖 dry-run 下 fallback 内存存在但 `used_memory_gb` 为空时只输出 `skipped_memory=1`，不输出日表行；修正 CPU missing 断言，保持 `avg_cpu_cores` 仍以 `jobs_count` 为分母，缺失或非法 CPU 按 `0` 计入

### 2026-05-06：创建 account 时向 SlurmDB 发送裸对象会触发 `Missing required field 'accounts'`
- 时间：2026-05-06
- 现象：`slurmrestd` 返回 `Missing required field 'accounts' in dictionary (#/accounts/) [Unable to resolve path/9200]`，创建账户失败
- 解决办法：`slurmweb/slurmrestd/__init__.py` 新增 `accounts` payload 规范化，把轻量对象自动包装为 `{ "accounts": [payload] }`；并补 `slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py` 与 `frontend/tests/views/AccountsView.spec.ts` 回归

### 2026-05-06：创建 account 时缺少 `organization` 被 `slurmrestd` 拒绝
- 时间：2026-05-06
- 现象：`slurmrestd` 返回 `Missing required field 'organization' in dictionary (#/accounts[0]/organization/) [Unable to resolve path/9200]`，创建失败
- 解决办法：`slurmweb/slurmrestd/__init__.py` 的 accounts payload 规范化新增 `_normalize_single_account()`；前端 `AccountsView` / `AccountView` 已补 `organization` 必填字段，并在创建/编辑请求中显式提交该值；后端仅在缺少 `organization` 时按 `description -> name -> "unknown"` 顺序补默认值，作为兼容旧调用方的兜底；补 `slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`、`slurmweb/tests/views/test_agent_operations.py`、`frontend/tests/views/AccountsView.spec.ts` 与 `frontend/tests/views/AccountView.spec.ts` 回归

### 2026-05-06：创建 account 成功后前端列表仍不显示新账户
- 时间：2026-05-06
- 现象：前端提示创建成功，但账户树没有出现新条目，容易误判为创建失败
- 解决办法：`AccountsView` 改为以 `accounts` 为主数据源构建账户树，再用 `associations` 补用户、QOS 和限制信息；创建成功后主动刷新 `accounts` 与 `associations` 两条 poller 链路；同时把 `description` 调整为创建 account 的前端显式必填字段；补 `frontend/tests/views/AccountsView.spec.ts` 回归，覆盖“无 association 也能显示新账户”

### 2026-05-06：QOS 常用限制值仍主要依赖后端默认补全，前后端契约不一致
- 时间：2026-05-06
- 现象：用户在前端看不到“这些值不能为空”的约束，但后端又会把空值改写成默认值，导致表单行为与实际写入契约不一致
- 解决办法：`QosView` 的创建/编辑弹框把 `MaxSubmitJobsPerUser`、`MaxJobsPerUser`、`MaxWallDurationPerJob` 全部设为必填；编辑弹框若后端当前值未设置，则回退到前端默认值，避免出现空表单；保留后端默认补值仅作为兼容旧调用方和历史 payload 的兜底；补 `frontend/tests/views/QosView.spec.ts` 回归，断言这三项字段为 `required: true`，且编辑时缺失值会回退到前端默认值

### 2026-05-06：AI 写接口 payload 直接透传时会绕过前端表单必填约束
- 时间：2026-05-06
- 现象：即使前端已经把 `organization`、`max_submit_jobs_per_user`、`max_jobs_per_user`、`max_wall_duration_per_job` 设为显式必填，AI 路径仍可省略这些字段并依赖后端默认补值成功写入
- 解决办法：`slurmweb/ai/agent_interfaces.py` 新增 AI 层 payload 校验；`account/update` 的每个 account entry 现在要求显式提交 `name` 和 `organization`；`qos/update` 的每个 qos entry 现在要求显式提交 `name`、`max_submit_jobs_per_user`、`max_jobs_per_user`、`max_wall_duration_per_job`；缺失这些字段时，AI 接口层直接返回 `400`，并写入 `ai_tool_calls` 错误审计；补 `slurmweb/tests/apps/test_ai_service.py` 回归，覆盖通过与拒绝路径

### 2026-05-06：`QosView` 弹窗错误提示测试不能从页面总文本断言
- 时间：2026-05-06
- 现象：`npx vitest run tests/views/QosView.spec.ts tests/views/AccountView.spec.ts tests/composables/GatewayAPI.spec.ts` 中 `rejects invalid qos wall duration before submitting` 失败，页面总文本没有包含预期错误文案
- 解决办法：断言改为定位标题为 `Create QOS` 的 `ActionDialog` 组件，并检查其 `error` prop 是否为 `MaxWallDurationPerJob must use days-hh:mm:ss or hh:mm:ss.`

### 2026-05-06：当前 Windows PowerShell 的 `Format-Hex` 不支持 `-Count`
- 时间：2026-05-06
- 现象：执行 `Format-Hex -Path docs/overview/latest-features.md -Count 32` 报 `A parameter cannot be found that matches parameter name 'Count'.`
- 解决办法：改用 `Get-Content -Encoding UTF8` 检查文件开头，并用更窄的 `apply_patch` 上下文插入文档内容

### 2026-05-06：Headless UI Teleport 残留 DOM 导致前端弹窗表单测试提交错对象
- 时间：2026-05-06
- 现象：`update_job` 没有被调用，或第二次 association 保存把上一轮 Add User 弹窗的输入当成当前 Edit QOS 表单字段
- 解决办法：相关测试改为清理 `document.body.innerHTML`，并直接定位页面内的 `ActionDialog` 组件后触发其 `submit` 事件，验证页面提交 payload，而不是依赖弹窗内部 DOM 排序

### 2026-04-28：用户分析自定义时间窗下 `Submission Activity` 可能不显示历史任务
- 时间：2026-04-28
- 现象：时间窗内预期有任务，但提交/完成趋势没有展示有效任务数据
- 解决办法：`submission_timeline` 改为 `COALESCE(submit_time, start_time, last_seen)` 作为提交时间兜底；终态过滤改为 `UPPER(job_state) LIKE %STATE%`；补 `test_user_analytics_store.py` 回归

### 2026-04-28：AI `association/update` 成功返回但账户页和集群端未显示新增用户
- 时间：2026-04-28
- 现象：AI 调用 `association/update` 返回成功，但账户页面查询 `ip-user` 没有该用户，在集群管理端检查也未添加成功或仍显示旧状态
- 解决办法：`slurmweb/slurmrestd/__init__.py` 在 association 写入 payload 缺少 `cluster` 时按当前集群补齐；account/user/association/qos 写入和删除后统一失效相关缓存

### 2026-04-28：新增 AI 会话审计字段后，旧前端 GatewayAPI 测试仍按旧响应结构断言
- 时间：2026-04-28
- 现象：AI conversation summary 断言失败，测试期望结构缺少 `username`、`deleted_at`、`deleted_by`
- 解决办法：同步更新 `GatewayAPI.spec.ts` 的响应夹具和期望字段

### 2026-04-28：节点 metrics 自定义 `start/end` 非法输入返回非 JSON 400，测试无法稳定断言
- 时间：2026-04-28
- 现象：非法 `start/end` 用例返回 400，但响应体不是稳定 JSON，测试按 `response.json["description"]` 断言失败
- 解决办法：`node_metrics_history` 对非法自定义窗口返回明确 JSON 错误响应，并保持 400 状态码

### 2026-04-27：用户分析图表升级为双曲线后，旧 Vitest 仍按单数据集断言
- 时间：2026-04-27
- 现象：`frontend/tests/components/user/UserSubmissionHistoryChart.spec.ts` 失败，报 `expected ... datasets to have a length of 1 but got 2`
- 解决办法：把该单测改为同时断言两条数据集的标签和点位，并在清空场景补齐 `completions` 输入夹具

### 2026-04-27：Flask 400 响应测试不能假设 `response.json` 一定存在
- 时间：2026-04-27
- 现象：执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_metrics_requests.py` 时，两个 `400` 用例 `response.status_code` 正确，但 `response.json` 为 `None`，直接按 JSON 结构断言会失败
- 解决办法：测试改为优先断言 `status_code`，再按 `response.json is not None` 分支分别校验 JSON 或 `response.text`

### 2026-04-27：当前 Windows PowerShell 不支持把 Bash 风格 `&&` 当作命令分隔符
- 时间：2026-04-27
- 现象：PowerShell 直接报 `The token '&&' is not a valid statement separator in this version.`，命令未执行
- 解决办法：改为分两条命令执行，或在 PowerShell 中使用分号/显式流程控制

### 2026-04-27：AI 服务写接口测试在 dummy slurmrestd 缺少 `api_version` 时会因结果归一化直接报 `AttributeError`
- 时间：2026-04-27
- 现象：执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py` 时，`test_write_interface_requires_matching_user_permission` 在成功调用 `job/cancel` 后抛 `AttributeError: 'DummySlurmrestd' object has no attribute 'api_version'`
- 解决办法：给 `DummySlurmrestd` 补 `cluster_name`、`slurm_version`、`api_version`，并顺手把 `job()` 调整成可区分 owner 的夹具，覆盖 `self` / `*` 写权限场景

### 2026-04-27：`npm --prefix frontend run test:unit -- --run ...` 不会切到单次执行，导致命令在开发中超时
- 时间：2026-04-27
- 现象：执行 `npm --prefix frontend run test:unit -- --run tests/views/AssistantView.spec.ts ...` 后命令超时，没有像预期那样直接退出
- 解决办法：改用 `cd frontend && npx vitest run <files...>` 直接执行单次测试

### 2026-04-27：AI trace 状态枚举从 `done` 收紧为 `ok|error|running` 后，`AssistantView` 遗留旧字面量导致 `vue-tsc` 失败
- 时间：2026-04-27
- 现象：执行 `npm --prefix frontend run type-check` 时，`src/views/AssistantView.vue` 报 `TS2345: Argument of type '\"done\"' is not assignable to parameter of type '\"ok\" | \"error\" | \"running\"'`
- 解决办法：把 `onToolEnd` 改为根据 `status_code` 映射到 `ok` 或 `error`，与新的 trace 类型保持一致

### 2026-04-27：`admin/system/slurmdb/instances` 在无实例时会因缺少 `instances` key 直接 500
- 时间：2026-04-27
- 现象：Agent 日志先记录 `slurmdb_instances_get() found nothing` warning，随后在 `slurmweb.slurmrestd.instances()` 里抛 `KeyError: 'instances'`，接口返回 500
- 解决办法：`instances()` 改为先取完整响应；若存在 `instances` 则正常返回，若 warning 描述包含 `found nothing` 则兼容返回空列表 `[]`，并补 `slurmweb/tests/slurmrestd/test_slurmrestd.py` 与 `slurmweb/tests/views/test_agent_operations.py` 回归测试

### 2026-04-25：共享操作对话框复用时会把上一次表单字段带入后续删除/取消请求
- 时间：2026-04-25
- 现象：先打开带字段的编辑/提交对话框，再切到 `fields=[]` 的删除/取消对话框时，组件仍可能提交上一次残留的 payload
- 解决办法：`resetForm()` 先删除 `form` 上已有键，再按当前字段重新填充默认值，并补 `frontend/tests/components/operations/ActionDialog.spec.ts` 做回归

### 2026-04-25：全量后端测试时 Prometheus collector 注册表残留，导致 `/metrics` 用例串扰
- 时间：2026-04-25
- 现象：`slurmweb/tests/views/test_agent_metrics_collector.py` 在单独运行时通过，但放进全量测试会批量失败，并在 Windows 上掉进 `socket.AF_UNIX` 不可用的真实 Unix socket 请求栈
- 解决办法：`slurmweb/tests/lib/agent.py` 已在测试基类里对 `metrics_collector.unregister()` 做统一 cleanup，并兼容重复清理

### 2026-04-25：Slurm 管理扩展后，Agent 装饰器未保留函数名导致 Flask 路由 endpoint 冲突
- 时间：2026-04-25
- 现象：`setup_client()` 初始化 Agent 时直接报 `AssertionError: View function mapping is overwriting an existing endpoint function: wrapper`
- 解决办法：`slurmweb/views/agent.py` 的 `handle_slurmrestd_errors` 已补 `@wraps`，相关定向回归已恢复

### 2026-04-25：`default_seed_roles()` 仍给 `user` 注入 `admin/*` 资源，导致默认角色越权
- 时间：2026-04-25
- 现象：`test_default_seed_roles_grant_jobs_self_to_user_and_admin_pages_to_admin` 失败，`user` 角色实际包含 `admin/system:view:*`、`admin/cache:view:*`、`admin/access-control:view:*` 等管理权限
- 解决办法：`default_seed_roles()` 已收紧，`user` 不再包含 `admin/*`，并补了对应权限目录测试

### 2026-04-25：前端测试夹具只写 `actions[]` 时，新规则页面会被误判为无权限
- 时间：2026-04-25
- 现象：页面直接进入“无权限”分支，测试里原本可见的按钮、表格和链接全部消失
- 解决办法：在 `runtime.hasRoutePermission(...)` 中增加从旧 `actions[]` 到规则的兼容回退，并逐步为新测试数据补充 `rules[]`

### 2026-04-25：Windows 下执行全量 `pytest -q` 会在收集阶段因平台依赖和旧测试树失败
- 时间：2026-04-25
- 现象：`pytest -q` 在收集阶段直接失败，典型错误包括 `ModuleNotFoundError: No module named 'pwd'`、`ModuleNotFoundError: No module named 'racksdb'`，以及 `slurmweb4.2` 测试树依赖 `SlurmwebConfSeed` 导入失败
- 解决办法：本次改动仅对受影响模块执行定向 pytest，未继续扩大到当前环境无法收集的全量测试树

### 2026-04-24：ripgrep 的 look-around 默认不可用导致搜索表达式报错
- 时间：2026-04-24
- 现象：`rg: regex parse error: look-around ... is not supported`
- 解决办法：对需要 look-around 的搜索加 `--pcre2`，或改写为不依赖 look-around 的多次搜索

### 2026-04-24：文档中的 Gateway 端点漏了 `/api` 前缀导致验证命令误用
- 时间：2026-04-24
- 现象：访问 `http://localhost:5012/login`、`http://localhost:5012/clusters` 得到 404 或非预期结果
- 解决办法：统一修正文档命令为 `/api/login`、`/api/anonymous`、`/api/clusters`，集群接口走 `/api/agents/<cluster>/...`

### 2026-04-24：网络原因导致无法 push 到 GitHub（已本地 commit）
- 时间：2026-04-24
- 现象：`Failed to connect to github.com port 443 ... Could not connect to server`
- 解决办法：按规范先完成本地 `git commit`，待网络恢复后再 push

### 2026-04-25：PowerShell 环境中不存在 `python` 命令导致临时脚本无法执行
- 时间：2026-04-25
- 现象：执行 `@' ... '@ | python -` 时返回 `python : The term 'python' is not recognized as the name of a cmdlet...`
- 解决办法：改用纯 PowerShell 方式读取字节并通过 `[System.Text.Encoding]::UTF8.GetString(...)` 解码文件内容

### 2026-04-25：CLI 改名后 `test_main.py` 仍按旧默认程序名断言
- 时间：2026-04-25
- 现象：`.venv\Scripts\python.exe -m pytest -q slurmweb/tests/exec/test_main.py` 失败 4 条，主要断言仍是 `slurm-web` 帮助输出和版本输出
- 解决办法：在 `docs/review/test-review.md` 记录该缺口，后续需要同步更新 `slurmweb/tests/exec/test_main.py`

### 2026-04-25：`gen-jwt-key` 修复后 `test_genjwt.py` 仍按旧行为断言
- 时间：2026-04-25
- 现象：`.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py` 失败 3 条，分别涉及 `subprocess.run(..., check=True)` 与新增/已有告警输出不一致
- 解决办法：先在 `docs/review/test-review.md` 记录为测试基线缺口，后续需同步更新 `slurmweb/tests/apps/test_genjwt.py`

### 2026-04-25：在仓库根目录直接跑前端 Vitest 会因 `@/` 别名解析失败
- 时间：2026-04-25
- 现象：从仓库根目录执行 `npx vitest run frontend/tests/...` 时，Vite 无法解析 `@/stores/runtime` 之类的别名
- 解决办法：切到 `frontend/` 目录执行 `npx vitest run ...`，或使用 `npm --prefix frontend ...`

### 2026-04-25：Windows PowerShell 读取 UTF-8 无 BOM 中文文档时会出现乱码
- 时间：2026-04-25
- 现象：直接读取中文 Markdown 时出现乱码，影响文档核对
- 解决办法：先设置控制台与 `$OutputEncoding` 为 UTF-8，或使用 `[System.IO.File]::ReadAllText(..., [System.Text.UTF8Encoding]::new($false))`

### 2026-04-25：完整前端 Vitest 仍会被旧页面断言和旧权限契约测试拖红
- 时间：2026-04-25
- 现象：执行 `npx vitest run` 时，多处测试仍按旧详情页结构、旧菜单顺序和旧权限契约断言，导致全量回归失败
- 解决办法：同步更新受影响视图和权限测试基线，使其匹配当前实现

### 2026-04-25：用户分析接口权限 scope 在装饰器中错误引用路由用户名
- 时间：2026-04-25
- 现象：`user_activity_summary` / `user_metrics_history` 等接口在运行时可能因 scope lambda 参数不匹配直接抛异常
- 解决办法：修正权限装饰器对路由参数的传递，并补相应回归测试

### 2026-04-25：当前 PowerShell 环境缺少 `ConvertFrom-Yaml`，不能把它当成 workflow 校验默认工具
- 时间：2026-04-25
- 现象：执行 `Get-Content -Raw -Encoding UTF8 <workflow> | ConvertFrom-Yaml` 时报缺少 cmdlet
- 解决办法：改用独立 YAML CLI 校验 workflow，或先确认环境中存在该 cmdlet

### 2026-04-25：GitHub Actions job 名包含 `:` 但未加引号时，workflow YAML 会直接解析失败
- 时间：2026-04-25
- 现象：workflow 名称中含 `:`、`${{ ... }}` 等复杂字符且未加引号时，YAML 解析失败
- 解决办法：为这类 job 名显式加引号，并在提交前运行 YAML 语法校验

### 2026-04-27：后端 CI 使用裸 `pytest` 时会把历史 `slurmweb4.2/tests` 一起收集，导致主线 workflow 直接失败
- 时间：2026-04-27
- 现象：GitHub `Backend Tests` workflow 在 collection 阶段被历史兼容测试树和旧依赖拖垮
- 解决办法：把 CI 测试入口显式收敛到 `pytest slurmweb/tests`

### 2026-04-27：Vue 组件直接写 `props.filters` 会被 ESLint `vue/no-mutating-props` 拦下
- 时间：2026-04-27
- 现象：`Frontend ESLint` 在 `JobsHistoryFiltersPanel.vue` 和 `JobsHistoryFiltersBar.vue` 上报直接修改 props 的错误
- 解决办法：改为通过 `update:filters` 事件把新对象回传给父组件，由父组件统一更新筛选状态

### 2026-04-27：移除 Jobs/AI/Access-Control 旧动作后，未同步的视图测试会先被 403 权限门控拦截
- 时间：2026-04-27
- 现象：一批原本测试业务逻辑的后端/前端用例先被新的权限门控拦下，断言点提前失效
- 解决办法：更新测试夹具和断言方式，使其匹配新的 `rules[]` 权限模型和默认授权语义

### 2026-04-27：后端 CI 安装 `.[agent]` / `.[tests]` 后仍缺 `cryptography`，AI 相关测试在 collection 阶段中断
- 时间：2026-04-27
- 现象：AI 相关测试导入 `slurmweb.ai.crypto` 或 `cryptography.fernet` 时失败
- 解决办法：把 `cryptography` 加入 `agent` / `tests` 相关 extras，保证 CI 安装后可直接导入

### 2026-04-27：Windows 本地验证 `.[agent]` 时会被 `RacksDB[web]` 的 `PyGObject` 编译链拦下
- 时间：2026-04-27
- 现象：在 Windows 环境执行 `pip install -e ".[agent,tests,gateway]"` 时，`PyGObject` 编译链阻断安装
- 解决办法：将其识别为平台编译环境限制，不把它误记为当前主线功能回归；主线验证改以可执行的定向测试和 Linux/CI 为准

### 2026-04-27：`Frontend ESLint` 会被未使用符号和空接口类型直接拦下
- 时间：2026-04-27
- 现象：页面和类型层重构后残留未使用符号与空接口，导致前端静态检查失败
- 解决办法：清理未使用符号，并将空接口改为类型别名或直接删除

### 2026-04-27：本地已提交前端 ESLint 修复，但 push 到 GitHub 时再次被网络阻断
- 时间：2026-04-27
- 现象：`git push origin main` 因外部网络连通性问题失败
- 解决办法：按规范先保留本地提交并在跟踪文档中记录 commit hash 和待 push 状态

### 2026-04-28：`vue-router-mock` 未提供 admin 路径上下文时，`SettingsAI` 审计测试不会触发管理员接口
- 时间：2026-04-28
- 现象：使用命名路由 push 的测试没有命中管理员分支，导致审计接口不触发
- 解决办法：测试 helper 改为 `router.push('/foo/admin/ai')` 直接提供 admin path；组件判定补 path 兜底

### 2026-04-28：用户分析 7 天窗口因 day bucket 时区不一致导致 `metrics/history` 序列全 0
- 时间：2026-04-28
- 现象：时间窗内实际有提交或完成作业，但接口返回的 `submissions` / `completions` 序列值全部为 0
- 解决办法：SQL bucket 改为按 UTC 截断；Python 侧统一转为 UTC epoch milliseconds 对齐，并补 7 天窗口回归测试

### 2026-04-28：用户工具分析资源均值在顶层字段为空时返回空值
- 时间：2026-04-28
- 现象：`avg_max_memory_gb` 与 `avg_cpu_cores` 返回 `null`，但作业快照 `usage_stats` 中已有可用资源数据
- 解决办法：聚合层新增统一数值解析 helper；内存和 CPU 在顶层字段缺失时回退到 `usage_stats` 对应字段，并同步当前日聚合口径

### 2026-05-06：用户工具分析在 Slurm step 级内存缺失时 `avg_max_memory_gb` 仍为空
- 时间：2026-05-06
- 现象：`used_memory_gb` 和 `usage_stats.memory.value_gb` 都为空时，接口仍无法从 TRES 数据给出内存均值
- 解决办法：聚合查询补取 TRES 字段，并在内存解析中增加 `tres_allocated`、`tres_requested` 和 TRES 字符串兜底；`rebuild-user-tool.py` 同步复用该口径

### 2026-05-06：`tools/analysis` 请求链路误触发日表重建
- 时间：2026-05-06
- 现象：每次调用 `user/<username>/tools/analysis` 都会同步扫描历史作业并重写时间窗内的 `user_tool_daily_stats`
- 解决办法：`user_tool_analysis()` 移除 `_refresh_user_tool_daily_stats()` 调用，接口只读 `user_tool_daily_stats`，补数改由后台任务和维护脚本完成

### 2026-05-07：误把 `usage_stats` / TRES fallback 纳入 `jobs_count`
- 时间：2026-05-07
- 现象：`used_memory_gb` 为空但 fallback 有值的作业被错误计入 `jobs_count`
- 解决办法：`aggregate_user_tool_daily_rows()` 改回只读取 `row["used_memory_gb"]`；为空或非法时直接跳过，并补高精度字符串场景测试

### 2026-05-07：`source_jobs` 很大但 `jobs_count` 只剩少数显式内存行
- 时间：2026-05-07
- 现象：某天 `source_jobs=1983`，但日表最终只写入极少数 `jobs_count`
- 解决办法：日聚合改为通过统一 `_memory_gb(row)` 解析链判断内存，并在 `rebuild-user-tool.py` 每日摘要增加 `counted`、`skipped_memory` 等关键计数

### 2026-05-07：`rebuild-user-tool.py` 仍可能沿用源行 `activity_date`
- 时间：2026-05-07
- 现象：当源行带错 `activity_date` 时，重建脚本可能把错误日期继续写入日表 payload
- 解决办法：新增 `completed_rows_for_rebuild_day()`，在进入共享聚合函数前强制把 `activity_date` 固定为当前重建日期

### 2026-05-06：后台日聚合与 `slurmweb/scripts/rebuild-user-tool.py` 聚合口径漂移
- 时间：2026-05-06
- 现象：后台当前日聚合与维护脚本在日期口径、工具归类和资源过滤上存在重复实现与偏差
- 解决办法：抽出共享 `aggregate_user_tool_daily_rows()`，让后台聚合与维护脚本复用同一条逻辑，并保持 `tools/analysis` 只读日表

### 2026-05-06：`tools/analysis` 可返回 `jobs_count > 0` 但资源均值为 `0`
- 时间：2026-05-06
- 现象：接口会返回 `completed_jobs > 0`，但同一条统计的资源均值为 `0` 或无效值
- 解决办法：日聚合写入阶段不再写入无有效资源对的统计；跨日读取阶段也跳过旧脏行；当前日刷新改为先删当天旧行再写新行

### 2026-05-07：用户工具日聚合把缺 CPU 样本的完成作业整条丢弃
- 时间：2026-05-07
- 现象：有有效内存但缺 `used_cpu_cores_avg` 的完成作业未进入 `user_tool_daily_stats`
- 解决办法：日聚合写表改为只强制 `used_memory_gb > 0`；CPU 缺失时仍保留作业计数与内存指标，`avg_cpu_cores` 只对有效 CPU 子集统计；同步后台日志和维护脚本口径

### 2026-05-06：前端单测入口误用 `npm test` 与 `npm run test:unit -- --run ...`
- 时间：2026-05-06
- 现象：`npm test -- --run ...` 报缺少脚本，`npm run test:unit -- --run ...` 在当前环境下超时
- 解决办法：改用 `npx vitest run <spec...>` 执行定向前端单测

### 2026-05-06：AI 对话页输入框脱离左侧聊天列，流式对话时面板整体下移
- 时间：2026-05-06
- 现象：左侧聊天区没有完整撑满工作区宽度，输入框脱离左侧列；流式回复和 trace 更新时，对话面板会整体下移
- 解决办法：把消息滚动区和 composer 一起收进左侧 `flex flex-col` 容器，给消息区稳定高度和 `min-w-0`，并补 `AssistantView.spec.ts` 结构回归测试
