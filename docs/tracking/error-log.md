# 开发错误库（避免重复踩坑）

本文件用于记录开发过程中遇到的可复现错误、根因与解决方案，目标是让后续开发者与 AI 能快速检索并避免重复踩同一个坑。

写入规则见：`docs/standards/development-error-summary.md`。

## 记录格式（示例）

### 2026-04-24：示例标题（用一句话概括）

- 场景：
- 现象：
- 复现：
- 根因：
- 解决：
- 预防：

## 条目

### 2026-04-28：用户分析自定义时间窗下 `Submission Activity` 可能不显示历史任务

- 场景：在用户工具分析页面选择自定义起止时间后查看 `Submission Activity`。
- 现象：时间窗内预期有任务，但提交/完成趋势没有展示有效任务数据。
- 复现：历史作业快照中 `submit_time` 缺失，或 `job_state` 保存为 `completed` 等小写状态时，选择包含这些作业的自定义窗口。
- 根因：提交趋势只按 `submit_time` 过滤，旧快照缺少该字段时无法命中；完成趋势和工具分析用 `js.job_state LIKE %COMPLETED%` 做大小写敏感匹配，小写终态不会被统计。
- 解决：`submission_timeline` 改为 `COALESCE(submit_time, start_time, last_seen)` 作为提交时间兜底；终态过滤改为 `UPPER(job_state) LIKE %STATE%`；补 `test_user_analytics_store.py` 回归。
- 预防：后续历史快照统计不要假设关键时间字段必定完整，也不要对外部状态字符串做大小写敏感匹配。

### 2026-04-28：AI `association/update` 成功返回但账户页和集群端未显示新增用户

- 场景：让 AI 给 account `ip-user` 添加用户 `guojianpeng`。
- 现象：AI 调用 `association/update` 返回成功，但账户页面查询 `ip-user` 没有该用户，在集群管理端检查也未添加成功或仍显示旧状态。
- 复现：通过 AI 发起 association update，payload 中只带 account/user 等字段但缺少 association `cluster`，随后立即查询 account 或 associations。
- 根因：SlurmDB association 写入需要集群上下文；AI 生成的写入 payload 可能缺少 `cluster`。同时写入后 `accounts` / `associations` 缓存未失效时，页面可能继续读取旧缓存。
- 解决：`slurmweb/slurmrestd/__init__.py` 在 association 写入 payload 缺少 `cluster` 时按当前集群补齐；account/user/association/qos 写入和删除后统一失效相关缓存。
- 预防：后续新增 AI 写接口时，必须对照底层 SlurmDB 契约补齐隐式上下文，并为写后缓存失效补单元测试。

### 2026-04-28：新增 AI 会话审计字段后，旧前端 GatewayAPI 测试仍按旧响应结构断言

- 场景：执行前端定向 Vitest，覆盖 `frontend/tests/composables/GatewayAPI.spec.ts`。
- 现象：AI conversation summary 断言失败，测试期望结构缺少 `username`、`deleted_at`、`deleted_by`。
- 复现：在新增管理员审计和逻辑删除字段后运行 `cd frontend && npx vitest run tests/composables/GatewayAPI.spec.ts`。
- 根因：Gateway API 类型和运行时解析已经返回审计字段，但测试夹具仍停留在逻辑删除前的最小结构。
- 解决：同步更新 `GatewayAPI.spec.ts` 的响应夹具和期望字段。
- 预防：会话、审计、权限等 API 响应字段扩展时，必须同步检查 GatewayAPI 类型、夹具和页面测试，不要只改后端返回。

### 2026-04-28：节点 metrics 自定义 `start/end` 非法输入返回非 JSON 400，测试无法稳定断言

- 场景：为 `node/metrics/history` 增加自定义 `start` / `end` 后补 Agent 视图测试。
- 现象：非法 `start/end` 用例返回 400，但响应体不是稳定 JSON，测试按 `response.json["description"]` 断言失败。
- 复现：访问 `GET /v<version>/node/<node>/metrics/history?start=bad&end=...` 并在测试中直接读取 JSON body。
- 根因：新增分支最初沿用了非 JSON 错误路径；而该接口其他错误测试期望 JSON 结构，导致同一视图错误响应契约不一致。
- 解决：`node_metrics_history` 对非法自定义窗口返回明确 JSON 错误响应，并保持 400 状态码。
- 预防：为已有 JSON 契约的 Agent 视图新增错误分支时，要保持同接口错误响应格式一致，并补非法参数回归测试。

### 2026-04-27：用户分析图表升级为双曲线后，旧 Vitest 仍按单数据集断言

- 场景：执行 `cd frontend && npx vitest run` 做前端全量回归。
- 现象：`frontend/tests/components/user/UserSubmissionHistoryChart.spec.ts` 失败，报 `expected ... datasets to have a length of 1 but got 2`。
- 复现：在当前分支运行前端全量 Vitest；`UserSubmissionHistoryChart.vue` 已同时渲染 `Submissions` 和 `Completions` 两条曲线，但旧测试仍只断言一条数据集。
- 根因：用户分析页已经把提交/完成双指标统一到同一张趋势图，测试基线没有跟着组件契约同步更新。
- 解决：把该单测改为同时断言两条数据集的标签和点位，并在清空场景补齐 `completions` 输入夹具。
- 预防：后续图表从单指标扩展到多指标时，必须同步检查 dataset 数量、顺序和图例标签断言，不能只沿用旧的“首条曲线存在”测试。

### 2026-04-27：Flask 400 响应测试不能假设 `response.json` 一定存在

- 场景：为 `user/tools/analysis` 的缺失时间窗和非法时间窗补 Agent 视图回归测试。
- 现象：执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_metrics_requests.py` 时，两个 `400` 用例 `response.status_code` 正确，但 `response.json` 为 `None`，直接按 JSON 结构断言会失败。
- 复现：访问 `GET /v<version>/user/<username>/tools/analysis` 或传入 `start >= end`，然后在测试里直接读取 `response.json["description"]`。
- 根因：当前错误响应链路在部分 `abort(400, ...)` 场景下不会稳定返回 JSON；测试把“HTTP 状态正确”和“响应一定有 JSON body”错误地绑定在一起。
- 解决：测试改为优先断言 `status_code`，再按 `response.json is not None` 分支分别校验 JSON 或 `response.text`。
- 预防：后续在本仓库补 Flask 视图错误路径测试时，不要默认所有 `4xx` 都会产出 JSON；先核对当前 app 的错误处理链路，再决定断言方式。

### 2026-04-27：当前 Windows PowerShell 不支持把 Bash 风格 `&&` 当作命令分隔符

- 场景：在仓库根目录想串行执行 `git add ... && git commit ...` 完成本地跟踪提交。
- 现象：PowerShell 直接报 `The token '&&' is not a valid statement separator in this version.`，命令未执行。
- 复现：在当前终端执行任意包含 `&&` 的 PowerShell 命令串。
- 根因：当前环境不是支持该语法的现代 shell，上下文是 Windows PowerShell 旧版本，不能把 Bash 风格 `&&` 当成默认命令分隔方式。
- 解决：改为分两条命令执行，或在 PowerShell 中使用分号/显式流程控制。
- 预防：后续在本仓库的 Windows PowerShell 环境下执行串行命令时，不要默认使用 `&&`；优先拆成独立命令，避免提交或验证步骤被 shell 语法直接拦截。

### 2026-04-27：AI 服务写接口测试在 dummy slurmrestd 缺少 `api_version` 时会因结果归一化直接报 `AttributeError`

- 场景：把 AI 写接口权限从 `super-admin` 总闸改为复用接口层实时权限校验后，补 `slurmweb/tests/apps/test_ai_service.py` 的写权限回归。
- 现象：执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py` 时，`test_write_interface_requires_matching_user_permission` 在成功调用 `job/cancel` 后抛 `AttributeError: 'DummySlurmrestd' object has no attribute 'api_version'`。
- 复现：使用当前测试文件中的 `DummySlurmrestd` 执行任一成功的 AI 写接口测试。
- 根因：`slurmweb/ai/agent_interfaces.py` 的 `_normalize_operation_result()` 会读取 `self.app.slurmrestd.api_version`；旧 dummy 只覆盖了读接口，没有补齐写接口归一化所需的版本字段。
- 解决：给 `DummySlurmrestd` 补 `cluster_name`、`slurm_version`、`api_version`，并顺手把 `job()` 调整成可区分 owner 的夹具，覆盖 `self` / `*` 写权限场景。
- 预防：后续为 AI 或 Agent 写接口补单测时，测试夹具不能只模拟业务 payload，还要补齐版本探测、owner 判定等写路径公共依赖字段。

### 2026-04-27：`npm --prefix frontend run test:unit -- --run ...` 不会切到单次执行，导致命令在开发中超时

- 场景：为验证 AI 页面和 `GatewayAPI` 改动，尝试运行指定前端单测文件。
- 现象：执行 `npm --prefix frontend run test:unit -- --run tests/views/AssistantView.spec.ts ...` 后命令超时，没有像预期那样直接退出。
- 复现：在仓库根目录执行上述命令；`frontend/package.json` 中 `test:unit` 实际映射为裸 `vitest`。
- 根因：`npm run test:unit -- --run ...` 只是把参数附加到 `vitest`，而不是显式切换到 `vitest run` 子命令；在当前脚本定义下容易落到交互/监听模式，导致自动化调用超时。
- 解决：改用 `cd frontend && npx vitest run <files...>` 直接执行单次测试。
- 预防：后续在本仓库跑定向前端单测时，优先使用显式的 `npx vitest run`，不要假设 `npm run test:unit -- --run` 一定会进入单次执行模式。

### 2026-04-27：AI trace 状态枚举从 `done` 收紧为 `ok|error|running` 后，`AssistantView` 遗留旧字面量导致 `vue-tsc` 失败

- 场景：扩展 AI 执行轨迹类型，新增 `status_code`、`interface_key` 并把前端 trace 状态细化为成功/失败/进行中。
- 现象：执行 `npm --prefix frontend run type-check` 时，`src/views/AssistantView.vue` 报 `TS2345: Argument of type '"done"' is not assignable to parameter of type '"ok" | "error" | "running"'`。
- 复现：在当前分支执行 `npm --prefix frontend run type-check`。
- 根因：`ToolRun` 类型已改为 `ok|error|running`，但 `onToolEnd` 回调里仍沿用旧的 `'done'` 字面量。
- 解决：把 `onToolEnd` 改为根据 `status_code` 映射到 `ok` 或 `error`，与新的 trace 类型保持一致。
- 预防：后续收紧前端字面量联合类型时，要同步搜索所有事件回调和测试夹具，不要只改类型定义。

### 2026-04-27：`admin/system/slurmdb/instances` 在无实例时会因缺少 `instances` key 直接 500

- 场景：访问 `Admin > System` 页面，前端请求 `GET /v6.0.0/admin/system/slurmdb/instances`。
- 现象：Agent 日志先记录 `slurmdb_instances_get() found nothing` warning，随后在 `slurmweb.slurmrestd.instances()` 里抛 `KeyError: 'instances'`，接口返回 500。
- 复现：当 SlurmDB `instances` 查询返回仅包含 `warnings` / `errors`、但没有 `instances` 字段时访问上述接口。
- 根因：`slurmweb/slurmrestd/__init__.py` 里的 `instances()` 直接调用 `_request(..., "instances")`，默认把 `instances` 当成必有 key；但“查到 0 条实例”的 slurmdb 返回是 warning-only 响应，不带空数组字段。
- 解决：`instances()` 改为先取完整响应；若存在 `instances` 则正常返回，若 warning 描述包含 `found nothing` 则兼容返回空列表 `[]`，并补 `slurmweb/tests/slurmrestd/test_slurmrestd.py` 与 `slurmweb/tests/views/test_agent_operations.py` 回归测试。
- 预防：后续对接 SlurmDB 只读列表端点时，不要假设“空结果一定返回空数组 key”；对 warning-only / empty-result 响应要先核对真实协议，再决定是否做窄范围兼容。

### 2026-04-25：共享操作对话框复用时会把上一次表单字段带入后续删除/取消请求

- 场景：Slurm 管理扩展上线后，多个业务页复用 `frontend/src/components/operations/ActionDialog.vue` 承载提交、编辑、删除、取消等单对象操作。
- 现象：先打开带字段的编辑/提交对话框，再切到 `fields=[]` 的删除/取消对话框时，组件仍可能提交上一次残留的 payload。
- 复现：渲染 `ActionDialog`，先以 `fields=[{ key: 'comment', ... }]` 提交一次，再在同一个组件实例上切换到空字段配置并再次提交；第二次 `submit` 事件会带出旧 `comment`。
- 根因：`resetForm()` 只覆盖当前 `props.fields` 对应的键，没有清理响应式 `form` 中上一次操作留下的旧键值。
- 解决：`resetForm()` 先删除 `form` 上已有键，再按当前字段重新填充默认值，并补 `frontend/tests/components/operations/ActionDialog.spec.ts` 做回归。
- 预防：后续复用型表单/弹窗组件在“编辑 -> 删除”“创建 -> 取消”这类跨场景切换时，必须补状态清理测试，不能只验证单次打开场景。

### 2026-04-25：全量后端测试时 Prometheus collector 注册表残留，导致 `/metrics` 用例串扰

- 场景：执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests` 做后端全量回归。
- 现象：`slurmweb/tests/views/test_agent_metrics_collector.py` 在单独运行时通过，但放进全量测试会批量失败，并在 Windows 上掉进 `socket.AF_UNIX` 不可用的真实 Unix socket 请求栈。
- 复现：先运行会创建 `metrics_collector` 的 Agent 测试，再运行 `/metrics` 相关视图测试；Prometheus 全局注册表会同时采集旧 collector。
- 根因：`TestAgentBase.setup_client()` 创建带 `/metrics` 的 app 后，没有统一注册测试清理逻辑；部分测试虽然手动 `unregister()`，但并不能覆盖所有调用路径。
- 解决：`slurmweb/tests/lib/agent.py` 已在测试基类里对 `metrics_collector.unregister()` 做统一 cleanup，并兼容重复清理。
- 预防：后续凡是往全局注册表、事件循环、线程、后台任务注册对象的测试基类，都必须在基类层统一 cleanup，不要依赖单个测试自己记得回收。

### 2026-04-25：Slurm 管理扩展后，Agent 装饰器未保留函数名导致 Flask 路由 endpoint 冲突

- 场景：补 `jobs self`、analysis/admin 扩展相关后端测试，运行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_jobs_self_permissions.py`。
- 现象：`setup_client()` 初始化 Agent 时直接报 `AssertionError: View function mapping is overwriting an existing endpoint function: wrapper`。
- 复现：在仓库根目录执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_jobs_self_permissions.py`。
- 根因：`slurmweb/views/agent.py` 中 `handle_slurmrestd_errors` 返回的包装函数统一命名为 `wrapper`，没有用 `functools.wraps` 保留原视图函数名；新增 POST/DELETE 管理路由后，Flask endpoint 名冲突被放大并阻塞应用启动。
- 解决：`slurmweb/views/agent.py` 的 `handle_slurmrestd_errors` 已补 `@wraps`，相关定向回归已恢复。
- 预防：后续新增 Flask 视图装饰器时必须保留原函数元数据，新增路由后至少跑一轮最小化 app 初始化测试。

### 2026-04-25：`default_seed_roles()` 仍给 `user` 注入 `admin/*` 资源，导致默认角色越权

- 场景：补权限模型测试，运行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py`。
- 现象：`test_default_seed_roles_grant_jobs_self_to_user_and_admin_pages_to_admin` 失败，`user` 角色实际包含 `admin/system:view:*`、`admin/cache:view:*`、`admin/access-control:view:*` 等管理权限。
- 复现：在仓库根目录执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py`。
- 根因：默认种子角色还沿用旧的宽泛能力集合，新增的 `admin/xx` 资源没有从普通用户默认权限中剥离。
- 解决：`default_seed_roles()` 已收紧，`user` 不再包含 `admin/*`，并补了对应权限目录测试。
- 预防：凡是权限模型升级到资源级 `view/edit/delete` 时，都要同步检查 seed role、vendor policy、前端路由守卫三处是否一致。

### 2026-04-25：前端测试夹具只写 `actions[]` 时，新规则页面会被误判为无权限

- 场景：迁移前端页面到 `hasRoutePermission(...)` 后，运行 Settings、AI、用户空间相关单测。
- 现象：页面直接进入“无权限”分支，测试里原本可见的按钮、表格和链接全部消失。
- 复现：在测试里直接给 `runtimeStore.availableClusters` 塞只有 `permissions.actions`、没有 `permissions.rules` 的对象，然后渲染新权限页面。
- 根因：这些测试夹具绕过了 `normalizeClusterPermissions(...)`，而新页面优先按规则判权。
- 解决：在 `runtime.hasRoutePermission(...)` 中增加从旧 `actions[]` 到规则的兼容回退，并逐步为新测试数据补充 `rules[]`。
- 预防：后续前端测试若直接构造 cluster 权限对象，优先写入 `rules[]`，或先经过统一的权限归一化逻辑。

### 2026-04-25：Windows 下执行全量 `pytest -q` 会在收集阶段因平台依赖和旧测试树失败

- 场景：提交前尝试在当前开发机上执行仓库全量后端测试。
- 现象：`pytest -q` 在收集阶段直接失败，典型错误包括 `ModuleNotFoundError: No module named 'pwd'`、`ModuleNotFoundError: No module named 'racksdb'`，以及 `slurmweb4.2` 测试树依赖 `SlurmwebConfSeed` 导入失败。
- 复现：在当前 Windows 环境执行 `.venv\Scripts\python.exe -m pytest -q`。
- 根因：仓库里同时包含 Unix 依赖模块、可选依赖未安装的测试，以及 `slurmweb4.2` 兼容测试树；这些条件在当前 Windows 环境下并不满足。
- 解决：本次改动仅对受影响模块执行定向 pytest，未继续扩大到当前环境无法收集的全量测试树。
- 预防：后续若需要跑全量后端测试，应先按平台拆分测试入口，或在 CI / 文档中明确哪些测试需在 Linux 且装齐可选依赖后执行。

### 2026-04-24：ripgrep 的 look-around 默认不可用导致搜索表达式报错

- 场景：在仓库内用 `rg` 搜索旧文档路径引用时，想用 look-ahead/behind 过滤结果。
- 现象：`rg: regex parse error: look-around ... is not supported`
- 复现：执行包含 `(?=...)` 或 `(?!...)` 的 `rg` 正则（未加参数）。
- 根因：ripgrep 默认正则引擎不支持 look-around，需要启用 PCRE2。
- 解决：对需要 look-around 的搜索加 `--pcre2`，或改写为不依赖 look-around 的多次搜索。
- 预防：在需要复杂正则时优先用 `rg --pcre2`，并把关键搜索命令写入跟踪或指南中。

### 2026-04-24：文档中的 Gateway 端点漏了 `/api` 前缀导致验证命令误用

- 场景：按文档用 curl 获取 token / 查询 clusters。
- 现象：访问 `http://localhost:5012/login`、`http://localhost:5012/clusters` 得到 404 或非预期结果。
- 复现：直接照搬旧文档命令访问不带 `/api` 的路径。
- 根因：Gateway 路由以 `/api/...` 为前缀（例如 `POST /api/login`、`GET /api/clusters`），旧文档残留了不一致路径。
- 解决：统一修正文档命令为 `/api/login`、`/api/anonymous`、`/api/clusters`，集群接口走 `/api/agents/<cluster>/...`。
- 预防：写验证命令时优先对照 `slurmweb/apps/gateway.py` 的路由表，避免凭印象写路径。

### 2026-04-24：网络原因导致无法 push 到 GitHub（已本地 commit）

- 场景：提交完成后执行 `git push origin main`。
- 现象：`Failed to connect to github.com port 443 ... Could not connect to server`。
- 复现：在网络不可达/被防火墙阻断的环境执行 push。
- 根因：网络不可用或访问 GitHub 被阻断（非仓库内容问题）。
- 解决：按规范先完成本地 `git commit`，待网络恢复后再 push。
- 预防：提交前不以 push 成功为前提；若 push 失败，必须在 `docs/tracking/` 留下“已本地提交、待 push”的记录。

### 2026-04-25：PowerShell 环境中不存在 `python` 命令导致临时脚本无法执行

- 场景：为排查文档读取乱码，尝试用内联 Python 脚本按字节解码 Markdown 文件。
- 现象：执行 `@' ... '@ | python -` 时返回 `python : The term 'python' is not recognized as the name of a cmdlet...`。
- 复现：在当前仓库终端直接执行 `python` 或把脚本管道给 `python -`。
- 根因：当前 PowerShell 环境未安装 `python`，或 `python` 未加入 `PATH`。
- 解决：改用纯 PowerShell 方式读取字节并通过 `[System.Text.Encoding]::UTF8.GetString(...)` 解码文件内容。
- 预防：在依赖解释器前先确认命令是否存在；本仓库的简单文件读取、编码排查优先使用 PowerShell 原生命令，避免把 `python` 作为默认前置条件。

### 2026-04-25：CLI 改名后 `test_main.py` 仍按旧默认程序名断言

- 场景：把对外默认 CLI 名称切到 `slurm-web-plus` 后，执行主入口定向测试。
- 现象：`.venv\Scripts\python.exe -m pytest -q slurmweb/tests/exec/test_main.py` 失败 4 条，主要断言仍是 `slurm-web` 帮助输出和版本输出。
- 复现：在当前仓库根目录执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/exec/test_main.py`。
- 根因：运行时代码已默认展示 `slurm-web-plus`，测试基线没有同步兼容命名策略。
- 解决：在 `docs/review/test-review.md` 记录该缺口，后续需要同步更新 `slurmweb/tests/exec/test_main.py`。
- 预防：凡是更改 CLI 对外名称、帮助信息或别名策略时，必须同步检查 `slurmweb/tests/exec/**` 中的字符串断言。

### 2026-04-25：`gen-jwt-key` 修复后 `test_genjwt.py` 仍按旧行为断言

- 场景：为避免 `setfacl` 失败被静默吞掉，以及兼容非 Unix 平台，对 `slurmweb/apps/genjwt.py` 做修复后执行定向测试。
- 现象：`.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py` 失败 3 条，分别涉及 `subprocess.run(..., check=True)` 与新增/已有告警输出不一致。
- 复现：在当前仓库根目录执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py`。
- 根因：测试仍按旧的 `subprocess.run(...)` 调用签名和旧日志集合断言，未跟随后端修复。
- 解决：先在 `docs/review/test-review.md` 记录为测试基线缺口，后续需同步更新 `slurmweb/tests/apps/test_genjwt.py`。
- 预防：后端修复若改变日志集合、外部命令参数或容错分支，必须同步审查对应测试文件，避免把有效修复变成 CI 假失败。

### 2026-04-25：在仓库根目录直接跑前端 Vitest 会因 `@/` 别名解析失败

- 场景：为复查前端剩余失败用例，在仓库根目录直接执行前端测试命令。
- 现象：`tests/composables/GatewayAPI.spec.ts`、`tests/components/user/UserToolAnalysisChart.spec.ts` 报 `Failed to load url @/...`，显示找不到 `@/composables/GatewayAPI`、`@/components/...`。
- 复现：在仓库根目录执行 `npm --prefix frontend exec vitest run tests/composables/GatewayAPI.spec.ts tests/components/user/UserToolAnalysisChart.spec.ts`。
- 根因：Vitest 运行目录不在 `frontend/`，导致前端工程的 Vite 别名配置没有按预期生效。
- 解决：切到 `frontend/` 目录执行 `npx vitest run ...`，按前端项目自身上下文加载配置。
- 预防：凡是使用 `@/` 路径别名的前端测试，优先在 `frontend/` 目录执行，避免把“命令上下文错误”误判成代码缺陷。

### 2026-04-25：Windows PowerShell 读取 UTF-8 无 BOM 中文文档时会出现乱码

- 场景：在当前 Windows 终端直接执行 `Get-Content docs/README.md` 查看中文文档。
- 现象：输出内容出现 `鍐呴儴鏂囨。` 一类乱码，即使先把控制台输出编码切到 UTF-8 也不能恢复正常。
- 复现：在 Windows PowerShell 5 中执行 `Get-Content docs/README.md`，目标文件为 UTF-8 无 BOM。
- 根因：`Get-Content` 默认按本地 ANSI/系统代码页解释无 BOM 文件；问题出在“读取时解码错误”，不在“输出时编码错误”。
- 解决：
  - 在 `AGENTS.md` 写死中文文档读取规则，要求优先使用 `Get-Content -Encoding UTF8 <path>`。
  - 将 `AGENTS.md` 与 `docs/**/*.md` 统一补齐 UTF-8 BOM，兼容 WinPS 5 的默认编码探测。
- 预防：后续 AI 在 Windows PowerShell 中读取中文文档时，不要把裸 `Get-Content <path>` 当成默认做法；若怀疑编码问题，优先按 UTF-8 显式读取。

### 2026-04-25：完整前端 Vitest 仍会被旧页面断言和旧权限契约测试拖红

- 场景：执行 `npx vitest run` 做前端全量回归。
- 现象：`JobHistoryView.spec.ts`、`JobView.spec.ts`、`UserAnalysisView.spec.ts`、`MainMenuAIContract.spec.ts` 失败，表现为旧 DOM 选择器、旧 `permission` 字段断言、旧权限夹具与当前实现不一致。
- 复现：在 `frontend/` 目录执行 `npx vitest run`。
- 根因：页面已切换到 `DetailSummaryStrip` 和新规则权限模型，部分测试仍按旧 overview grid、旧 `view-ai` 菜单配置和旧用户分析授权方式断言。
- 解决：同步更新上述测试到当前 UI 结构和权限模型。
- 预防：前端若重构详情页布局或菜单权限结构，必须同轮同步更新契约测试和页面单测。

### 2026-04-25：用户分析接口权限 scope 在装饰器中错误引用路由用户名

- 场景：扩大后端验证到 `slurmweb/tests/views/test_agent_metrics_requests.py -k user_activity_summary`。
- 现象：访问 `GET /v<version>/user/<username>/activity/summary` 时，权限装饰器在解析 `self` / `*` scope 阶段抛出 `NameError`，后续在修正为传参后又暴露出 lambda 不接收 `username` 关键字参数。
- 复现：执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_metrics_requests.py -k user_activity_summary`。
- 根因：`permission_required(...)` 的 scope callable 需要在运行时根据路由参数解析，但原实现既没有把路由参数传入 callable，lambda 本身也没声明 `username` 参数。
- 解决：
  - `_resolved_scope(...)` 改为向 callable 透传 `*args, **kwargs`
  - `user_metrics_history` / `user_activity_summary` 的 scope lambda 显式接收 `username`
- 预防：凡是按请求参数动态判定 `self` / `*` 的权限装饰器，都要补对应回归测试，避免闭包或参数绑定错误在运行时才暴露。

### 2026-04-25：当前 PowerShell 环境缺少 `ConvertFrom-Yaml`，不能把它当成 workflow 校验默认工具

- 场景：为验证新增 GitHub Actions workflow，尝试在当前 Windows PowerShell 环境执行 `Get-Content -Raw -Encoding UTF8 <workflow> | ConvertFrom-Yaml`。
- 现象：终端返回 `ConvertFrom-Yaml : The term 'ConvertFrom-Yaml' is not recognized as the name of a cmdlet...`。
- 复现：在当前仓库终端执行 `Get-Content -Raw -Encoding UTF8 .github/workflows/python-ci.yml | ConvertFrom-Yaml`。
- 根因：当前 PowerShell 环境未提供 `ConvertFrom-Yaml` cmdlet，不能假定它像 `ConvertFrom-Json` 一样默认可用。
- 解决：改用 `Get-Content -Raw -Encoding UTF8 <workflow> | npx --yes yaml valid` 做 YAML 语法校验，同时保留人工检查。
- 预防：后续在 Windows 环境校验 YAML 时，不要默认依赖 `ConvertFrom-Yaml`；先确认 cmdlet 是否存在，或直接使用独立 YAML CLI。

### 2026-04-25：GitHub Actions job 名包含 `:` 但未加引号时，workflow YAML 会直接解析失败

- 场景：新增手工 `python-os-ci.yml` 后，用 YAML CLI 校验 workflow 语法。
- 现象：`Get-Content -Raw -Encoding UTF8 .github/workflows/python-os-ci.yml | npx --yes yaml valid` 返回 `YAMLParseError: Nested mappings are not allowed in compact mappings`，错误定位到 job `name:` 行。
- 复现：在 job 名写入 `name: OS integration tests (rpm: ${{ matrix.envs.artifact }})` 这类未加引号的值后执行 YAML 校验。
- 根因：YAML 把未加引号的 `:` 解释为映射分隔符，导致 job 名字符串被错误拆解。
- 解决：把含 `:` 的 job 名改为带双引号的标量，例如 `name: "OS integration tests (rpm: ...)"`。
- 预防：后续在 workflow 里凡是名称、说明、命令片段包含 `:`、`{}`、`${{ ... }}` 等复杂字符时，优先显式加引号，并在提交前跑一轮 YAML 语法校验。

### 2026-04-27：后端 CI 使用裸 `pytest` 时会把历史 `slurmweb4.2/tests` 一起收集，导致主线 workflow 直接失败

- 场景：GitHub `Backend Tests` workflow 执行 `pytest --junitxml=...` 作为主命令。
- 现象：`backend-unit-tests` 在 CI 中以 `exit code 2` 失败；当前仓库根目录同时存在 `slurmweb/tests` 和历史 `slurmweb4.2/tests` 两套测试树。
- 复现：在仓库根目录执行裸 `pytest`，让 pytest 按默认递归收集全仓 `test*.py`。
- 根因：主线 CI 没有显式限制测试入口，pytest 会把历史兼容树 `slurmweb4.2/tests` 也一起收集；该树包含旧依赖和旧导入路径，不应进入当前主线 CI。
- 解决：把 `python-ci.yml` 和 `python-os-ci.yml` 中的测试命令统一收敛到 `pytest slurmweb/tests` / `pytest-3 slurmweb/tests`。
- 预防：后续仓库内如果长期保留兼容代码树或归档测试树，CI 必须显式指定测试根目录，不能依赖裸 `pytest` 默认收集规则。

### 2026-04-27：Vue 组件直接写 `props.filters` 会被 ESLint `vue/no-mutating-props` 拦下

- 场景：GitHub `Frontend ESLint` 检查扫描 `JobsHistoryFiltersPanel.vue` 和 `JobsHistoryFiltersBar.vue`。
- 现象：`Unexpected mutation of "filters" prop` 连续报在 `v-model="props.filters.*"`、`props.filters.state = ...` 和筛选 chip 删除逻辑上。
- 复现：在 `frontend/` 目录执行 `npx eslint src/components/jobs/JobsHistoryFiltersPanel.vue src/components/jobs/JobsHistoryFiltersBar.vue src/views/JobsHistoryView.vue`。
- 根因：两个组件把父级传入的 `filters` 当成可变本地状态直接修改，违反 Vue 单向数据流和仓库 ESLint 规则。
- 解决：改为通过 `update:filters` 事件向父级回传新对象，由 `JobsHistoryView` 统一更新 store 中的 `filters`。
- 预防：后续凡是对象型筛选器、表单状态从父级传入时，都不要直接在子组件里写 prop；优先使用 `v-model:<prop>` 或显式 `update:*` 事件。

### 2026-04-27：移除 Jobs/AI/Access-Control 旧动作后，未同步的视图测试会先被 403 权限门控拦截

- 场景：收紧 `view-own-jobs` / `edit-own-jobs` / `cancel-own-jobs` / `roles-view` / `roles-manage` / `view-ai` / `manage-ai` 后，执行权限与视图相关回归测试。
- 现象：`slurmweb/tests/views/test_agent.py` 中原本验证 `slurmrestd` 错误透传的 `/jobs` 用例提前返回 403；AI 与 access-control 视图测试里 patch `allowed_user_action` 也不再生效。
- 复现：在仓库根目录执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent.py slurmweb/tests/views/test_agent_ai.py slurmweb/tests/views/test_agent_permissions.py`。
- 根因：默认无数据库模式下，普通用户不再有自有 Jobs 的旧动作兜底；同时新装饰器统一基于 `allowed_user_permission(...)` 和 `rules[]` 判定，而旧测试仍按 `allowed_user_action` 或旧动作夹具构造授权。
- 解决：
  - 为需要穿透到业务逻辑的视图测试显式注入 `jobs:view:*`、`admin/access-control:*`、`admin/ai:*`、`ai:view:*` 等规则
  - 把 `user_permissions()` 的 mock 统一补成 `(roles, actions, permissions)` 三元组
  - 新增 `test_access_control_store.py` 覆盖废弃动作迁移
- 预防：后续只要调整默认动作、compatibility map 或权限装饰器实现，必须同轮检查“测试是验证权限门控本身，还是验证被门控后的业务逻辑”，避免断言点被更早的 403 掩盖。

### 2026-04-27：后端 CI 安装 `.[agent]` / `.[tests]` 后仍缺 `cryptography`，AI 相关测试在 collection 阶段中断

- 场景：GitHub `Backend Tests` workflow 在 `Python 3.12` 环境执行 `pip install . '.[agent]' '.[gateway]' '.[tests]' && pytest slurmweb/tests`。
- 现象：pytest 收集 `slurmweb/tests/apps/test_ai_service.py`、`slurmweb/tests/views/test_agent_ai.py` 等用例时抛 `ModuleNotFoundError: No module named 'cryptography'`，最终以 `21 errors during collection` 和 `exit code 2` 失败。
- 复现：在一个干净虚拟环境中执行 `pip install -e ".[agent,tests,gateway]"` 后运行 `pytest slurmweb/tests`，会在导入 `slurmweb.ai.crypto` 或直接导入 `cryptography.fernet` 的测试时失败。
- 根因：`slurmweb.ai.crypto` 依赖 `cryptography`，但 `pyproject.toml` 没有把它声明到 `agent` 或 `tests` extras；CI 虽然安装了这些 extras，实际仍拿不到该依赖。
- 解决：把 `cryptography` 同步加入 `.[agent]` 与 `.[tests]`，使后端 AI 运行链路和对应测试在自动 CI 中都能获得完整依赖。
- 预防：后续新增 Python 可选模块时，要同时检查“运行时导入链”和“测试直接导入链”是否都覆盖到 extras；不要只看本地已有环境是否碰巧装过依赖。

### 2026-04-27：Windows 本地验证 `.[agent]` 时会被 `RacksDB[web]` 的 `PyGObject` 编译链拦下

- 场景：在当前 Windows 开发环境为复查 CI 依赖，执行 `.venv\Scripts\python.exe -m pip install -e ".[agent,tests,gateway]"`。
- 现象：`cryptography` 已被识别为 `slurm-web-plus` 依赖，但安装继续解析 `RacksDB[web]` 时，`PyGObject` 元数据构建因本机缺少 `cl/gcc/clang` 等编译器失败。
- 复现：在无 Visual Studio Build Tools 或等价 C 编译链的 Windows PowerShell 环境执行上述命令。
- 根因：`.[agent]` 依赖里的 `RacksDB[web]` 会继续拉起 `PyGObject`，其 Windows 安装需要本地 C/GTK 编译环境；当前机器没有对应工具链。
- 解决：本轮不把该本地失败当成 CI 结论，改用定向 AI pytest 验证 `cryptography` 导入链；完整 agent extra 仍以 Ubuntu GitHub runner 为准。
- 预防：后续在 Windows 上验证 Linux-oriented Python extras 时，要先区分“依赖声明是否正确”和“本机是否具备原生编译环境”，避免把平台编译问题误记为 workflow 回归。

### 2026-04-27：`Frontend ESLint` 会被未使用符号和空接口类型直接拦下

- 场景：GitHub `Frontend Static Analysis` 在 `Node 18` 环境执行 `npm run lint`。
- 现象：`JobHistoryView.vue`、`JobView.vue`、`JobsView.vue`、`SettingsAccessControl.vue`、`ClusterAnalysis.ts`、`SettingsTabs.vue` 与 `GatewayAPI.ts` 因未使用导入/变量，以及 `interface extends X {}` 空接口类型，被 `@typescript-eslint/no-unused-vars` 和 `@typescript-eslint/no-empty-object-type` 拦下。
- 复现：在 `frontend/` 目录执行 `npx eslint src/views/JobHistoryView.vue src/views/JobView.vue src/views/JobsView.vue src/views/settings/SettingsAccessControl.vue src/composables/GatewayAPI.ts src/composables/ClusterAnalysis.ts src/components/settings/SettingsTabs.vue`。
- 根因：页面和类型层重构后残留了未被模板或运行时代码使用的符号，且若干仅做别名用途的接口仍保留 `interface extends` 空壳写法。
- 解决：删除未使用符号，并把仅做类型别名的空接口改成 `type`。
- 预防：后续前端重构后，提交前至少对改动链路相关文件跑一轮定向 ESLint；若只是做类型别名，不要再保留 `interface extends Foo {}` 这种空接口写法。

补充：

- 当前仓库已把前端源码里的这两条规则降级为 warning，GitHub `Frontend ESLint` 仍会显示告警，但不再因这两类历史清理项单独失败。

### 2026-04-27：本地已提交前端 ESLint 修复，但 push 到 GitHub 时再次被网络阻断

- 场景：完成 `fix(frontend): clear remaining eslint blockers` 本地 commit 后执行 `git push origin main`。
- 现象：连续两次 push 分别报 `Recv failure: Connection was reset` 和 `Failed to connect to github.com port 443`，导致 commit `024bde9` 仍停留在本地。
- 复现：在当前网络不可达或访问 GitHub 不稳定的环境执行 `git push origin main`。
- 根因：外部网络连通性问题，不是本次 ESLint 修复内容导致的仓库错误。
- 解决：保留本地 commit，并在 `docs/tracking/current-release.md` 记录待 push 状态；待网络恢复后重试 push。
- 预防：当远端 workflow 依赖最新修复时，push 前后都要预留网络失败回退路径；若 push 失败，必须先把本地 commit hash 和记账状态写入跟踪文档。

补充：

- 后续新增的 `fix(frontend): remove remaining eslint dead code` 本地提交 `f90d428` 也因同一网络问题尚未 push。

### 2026-04-28：`vue-router-mock` 未提供 admin 路径上下文时，`SettingsAI` 审计测试不会触发管理员接口

- 场景：为 `SettingsAI` 增加管理员 Conversation Audit 搜索和“点击后加载详情”测试时，测试 helper 使用 `router.push({ name: 'admin-ai', params: { cluster: 'foo' } })`。
- 现象：`ai_admin_conversations` 断言失败，实际调用次数为 0；组件没有进入 admin 路由分支。
- 复现：在 `frontend/` 目录执行 `npx vitest run tests/views/settings/SettingsAI.spec.ts tests/views/AssistantView.spec.ts`。
- 根因：当前测试使用的是 `vue-router-mock`，未加载真实路由表；按命名路由 push 不能稳定给 `useRoute()` 提供真实 admin path/name 上下文，导致 `isAdminRoute` 判定不成立。
- 解决：
  - 测试 helper 改为 `router.push('/foo/admin/ai')`，直接提供 admin path。
  - `SettingsAI` 的 admin 路由判定补充 path 兜底：route name 以 `admin-` 开头，或 route path 包含 `/admin/`。
- 预防：后续测试依赖路由分支但未使用真实 router 时，应优先设置组件实际依赖的 `path` / `params`；若组件逻辑只依赖 `route.name`，要确认 mock router 是否真的注入了该 name。

### 2026-04-28：用户分析 7 天窗口因 day bucket 时区不一致导致 `metrics/history` 序列全 0

- 场景：用户工具分析页点击时间范围弹框中的 `7 days`，前端调用 `user/<username>/metrics/history?start=<iso>&end=<iso>`。
- 现象：时间窗内实际有提交或完成作业，但接口返回的 `submissions` / `completions` 序列值全部为 0，页面显示无活动数据。
- 复现：对超过 48 小时的自定义窗口触发 `day` bucket，数据库 session timezone 与前端 UTC ISO 窗口不一致时，`date_trunc('day', timestamptz)` 返回的 bucket 与 Python UTC 游标不完全一致。
- 根因：SQL 侧以数据库 session timezone 对 `TIMESTAMPTZ` 做 `date_trunc`，Python 侧以 UTC 对齐 bucket；`values` 又直接用 `datetime` 对象做 key，导致实际有数据的 bucket 无法命中。
- 解决：
  - SQL bucket 改为 `date_trunc(..., <timestamp> AT TIME ZONE 'UTC')`。
  - Python 侧把 DB bucket 和游标都转换为 UTC epoch milliseconds 后匹配。
  - 新增 7 天窗口单测，覆盖 naive UTC bucket 仍能命中非 0 数据。
- 预防：后续涉及 `TIMESTAMPTZ` 聚合 bucket 时，必须明确接口标准时区；跨 SQL 与 Python 匹配时优先使用 epoch 或显式 timezone，不要直接混用 naive/aware `datetime` 对象作为 key。

### 2026-04-28：用户工具分析资源均值在顶层字段为空时返回空值

- 场景：用户工具分析页或 AI 工具调用查询 `user/<username>/tools/analysis?start=<iso>&end=<iso>`，时间窗内有已完成作业。
- 现象：`avg_max_memory_gb` 与 `avg_cpu_cores` 返回 `null`，但作业快照的 `usage_stats` 中已有定时采集程序计算出的内存和 CPU 数据。
- 复现：构造 `job_snapshots.used_memory_gb IS NULL`、`job_snapshots.used_cpu_cores_avg IS NULL`，但 `usage_stats.memory.value_gb` 与 `usage_stats.cpu.estimated_cores_avg` 有值的历史作业，再查询用户工具分析接口。
- 根因：用户分析实时聚合和当前日定时聚合只读取顶层 `used_memory_gb` / `used_cpu_cores_avg`，没有沿用采集程序写入 `usage_stats` 的资源统计结果；旧数据或部分采集链路补写不完整时，均值样本数为 0。
- 解决：
  - 用户分析聚合新增统一数值解析 helper。
  - 内存优先使用 `used_memory_gb`，为空时回退 `usage_stats.memory.value_gb`。
  - CPU 优先使用 `used_cpu_cores_avg`，兼容 `used_cpu_core_avg`，为空时回退 `usage_stats.cpu.estimated_cores_avg`。
  - 当前日定时写入 `user_tool_daily_stats` 使用同一口径。
- 预防：后续新增由采集程序派生出的统计字段时，聚合层必须同时检查“规范化顶层列”和“原始/派生 `usage_stats`”两条数据路径，并用单测覆盖顶层列为空的历史数据。
