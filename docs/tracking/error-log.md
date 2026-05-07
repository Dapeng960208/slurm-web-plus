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

### 2026-05-06：创建 account 时向 SlurmDB 发送裸对象会触发 `Missing required field 'accounts'`

- 场景：从管理页面或 AI 调用 `accounts/update` 创建 Slurm 账户。
- 现象：`slurmrestd` 返回 `Missing required field 'accounts' in dictionary (#/accounts/) [Unable to resolve path/9200]`，创建账户失败。
- 复现：向 `POST /slurmdb/v0.0.44/accounts/` 发送轻量 payload，例如 `{ "name": "science", "description": "Science" }`。
- 根因：官方 Slurm REST 文档定义该接口的 request body 为 `v0.0.44_openapi_accounts_resp`，顶层必须带 `accounts` 数组；本地适配层之前把前端轻量对象直接透传给 `slurmrestd`。
- 解决：`slurmweb/slurmrestd/__init__.py` 新增 `accounts` payload 规范化，把轻量对象自动包装为 `{ "accounts": [payload] }`；并补 `slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py` 与 `frontend/tests/views/AccountsView.spec.ts` 回归。
- 预防：后续新增或封装 SlurmDB 写接口时，先按官方 OpenAPI 核对 request body 顶层 schema，不能假设单对象接口接受裸 payload；前端轻量表单与后端 Slurm schema 之间必须始终保留适配层。

### 2026-05-06：创建 account 时缺少 `organization` 被 `slurmrestd` 拒绝

- 场景：从 Accounts 页面或 AI 调用 `accounts/update` 创建 account，前端继续发送轻量 payload `{ name, description, parent_account, qos }`。
- 现象：`slurmrestd` 返回 `Missing required field 'organization' in dictionary (#/accounts[0]/organization/) [Unable to resolve path/9200]`，创建失败。
- 复现：向 `POST /slurmdb/v0.0.44/accounts/` 发送 `{ "accounts": [{ "name": "science", "description": "Science" }] }`。
- 根因：虽然上一轮已经把轻量 payload 包装成了官方要求的 `accounts` 数组，但没有继续按官方 OpenAPI / accounting 接口要求补齐 account 对象的必填字段 `organization`。
- 解决：
  - `slurmweb/slurmrestd/__init__.py` 的 accounts payload 规范化新增 `_normalize_single_account()`。
  - 前端 `AccountsView` / `AccountView` 已补 `organization` 必填字段，并在创建/编辑请求中显式提交该值。
  - 后端仅在缺少 `organization` 时按 `description -> name -> "unknown"` 顺序补默认值，作为兼容旧调用方的兜底。
  - 补 `slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`、`slurmweb/tests/views/test_agent_operations.py`、`frontend/tests/views/AccountsView.spec.ts` 与 `frontend/tests/views/AccountView.spec.ts` 回归。
- 预防：后续封装 SlurmDB 写接口时，除了检查 request body 顶层 schema，还必须把 required 字段同步到前端表单和前端 payload 校验；后端默认补值只能作为兼容兜底，不能替代前端契约。

### 2026-05-06：创建 account 成功后前端列表仍不显示新账户

- 场景：在 `AccountsView` 创建 account，后端返回成功，但列表里看不到刚创建的账户。
- 现象：前端提示创建成功，但账户树没有出现新条目，容易误判为创建失败。
- 复现：
  - 通过 `Create Account` 创建一个新的 account。
  - 底层 `accounts` 已存在新对象，但 `associations` 还没有对应 account-level association 行时，账户页仍为空或不显示新账户。
- 根因：`AccountsView` 之前只用 `associations` 构建账户树；而新建 account 是否立刻出现在 `associations` 里并不稳定，导致页面数据源与实际账户主数据脱节。
- 解决：
  - `AccountsView` 改为以 `accounts` 为主数据源构建账户树，再用 `associations` 补用户、QOS 和限制信息。
  - 创建成功后主动刷新 `accounts` 与 `associations` 两条 poller 链路。
  - 同时把 `description` 调整为创建 account 的前端显式必填字段。
  - 补 `frontend/tests/views/AccountsView.spec.ts` 回归，覆盖“无 association 也能显示新账户”。
- 预防：后续账户列表、树和导航类页面，主对象列表必须优先绑定对象主数据源，不能只依赖 association、metrics 或其他附属视图来判断对象是否存在。

### 2026-05-06：QOS 常用限制值仍主要依赖后端默认补全，前后端契约不一致

- 场景：`QosView` 创建或编辑 QOS 时，前端弹框虽然预填了 `MaxSubmitJobsPerUser`、`MaxJobsPerUser`、`MaxWallDurationPerJob`，但字段本身不是必填；如果被清空，最终仍主要依赖后端默认补值。
- 现象：用户在前端看不到“这些值不能为空”的约束，但后端又会把空值改写成默认值，导致表单行为与实际写入契约不一致。
- 复现：
  - 打开 `Create QOS` 或 `Edit QOS` 弹框。
  - 清空常用限制字段后提交；前端不会因必填失败阻止提交，后端仍可能按默认值补齐。
- 根因：前端只做了“预填默认值”，没有把这组默认值提升为显式表单契约；后端默认补值被错误地承担了主流程责任。
- 解决：
  - `QosView` 的创建/编辑弹框把 `MaxSubmitJobsPerUser`、`MaxJobsPerUser`、`MaxWallDurationPerJob` 全部设为必填。
  - 编辑弹框若后端当前值未设置，则回退到前端默认值，避免出现空表单。
  - 保留后端默认补值仅作为兼容旧调用方和历史 payload 的兜底。
  - 补 `frontend/tests/views/QosView.spec.ts` 回归，断言这三项字段为 `required: true`，且编辑时缺失值会回退到前端默认值。
- 预防：凡是后端存在“默认补值”的高频写表单字段，前端如果要支持该能力，就必须同时显式展示、预填并校验；不能只做 UI 提示而把实际约束留给后端。

### 2026-05-06：AI 写接口 payload 直接透传时会绕过前端表单必填约束

- 场景：AI 或脚本直接调用 `account/update`、`qos/update` 这类管理写接口。
- 现象：即使前端已经把 `organization`、`max_submit_jobs_per_user`、`max_jobs_per_user`、`max_wall_duration_per_job` 设为显式必填，AI 路径仍可省略这些字段并依赖后端默认补值成功写入。
- 复现：
  - 调用 `mutate_agent_interface(account/update)`，payload 只传 `{ name, description }`。
  - 调用 `mutate_agent_interface(qos/update)`，payload 只传 `{ name, description }` 或缺失三项常用限制字段中的任意一项。
- 根因：`slurmweb/ai/agent_interfaces.py` 之前只做 `payload must be an object` 这类通用校验，随后就把对象原样透传给 `slurmrestd`；而 `slurmrestd` 适配层为了兼容旧调用方又会补默认字段，导致 AI 主写链路和前端主表单契约分叉。
- 解决：
  - `slurmweb/ai/agent_interfaces.py` 新增 AI 层 payload 校验。
  - `account/update` 的每个 account entry 现在要求显式提交 `name` 和 `organization`。
  - `qos/update` 的每个 qos entry 现在要求显式提交 `name`、`max_submit_jobs_per_user`、`max_jobs_per_user`、`max_wall_duration_per_job`。
  - 缺失这些字段时，AI 接口层直接返回 `400`，并写入 `ai_tool_calls` 错误审计。
  - 补 `slurmweb/tests/apps/test_ai_service.py` 回归，覆盖通过与拒绝路径。
- 预防：后续审 AI 写接口时，不能只看权限是否复用 Agent；还要逐条对照前端表单契约，凡是前端已经定义为显式必填的业务字段，AI 主写链路也必须在接口层显式校验，不能继续依赖后端隐藏默认值。

### 2026-05-06：`QosView` 弹窗错误提示测试不能从页面总文本断言

- 场景：为 `QosView` 创建 QOS 的 `MaxWallDurationPerJob` 非法输入补 Vitest 回归。
- 现象：`npx vitest run tests/views/QosView.spec.ts tests/views/AccountView.spec.ts tests/composables/GatewayAPI.spec.ts` 中 `rejects invalid qos wall duration before submitting` 失败，页面总文本没有包含预期错误文案。
- 复现：挂载 `QosView`，打开 `Create QOS` 弹框，通过 `ActionDialog` 组件触发 submit，并直接对 `wrapper.text()` 断言错误信息。
- 根因：测试操作的是 `ActionDialog` 组件事件，错误状态通过 `error` prop 传回弹窗；在当前 Headless UI/Dialog 测试结构下，弹窗文本不稳定出现在 `wrapper.text()` 中。
- 解决：断言改为定位标题为 `Create QOS` 的 `ActionDialog` 组件，并检查其 `error` prop 是否为 `MaxWallDurationPerJob must use days-hh:mm:ss or hh:mm:ss.`。
- 预防：后续测试共享弹窗错误状态时，优先断言组件 prop 或 emit 行为，不用页面总文本承载弹窗内部状态。

### 2026-05-06：当前 Windows PowerShell 的 `Format-Hex` 不支持 `-Count`

- 场景：排查 `docs/overview/latest-features.md` 补丁上下文不匹配，尝试查看文件开头字节。
- 现象：执行 `Format-Hex -Path docs/overview/latest-features.md -Count 32` 报 `A parameter cannot be found that matches parameter name 'Count'.`
- 复现：在当前 PowerShell 环境执行带 `-Count` 参数的 `Format-Hex`。
- 根因：当前 PowerShell 版本中的 `Format-Hex` cmdlet 没有 `-Count` 参数，不能按较新示例使用该参数。
- 解决：改用 `Get-Content -Encoding UTF8` 检查文件开头，并用更窄的 `apply_patch` 上下文插入文档内容。
- 预防：后续在 Windows PowerShell 使用 cmdlet 参数前先考虑版本差异；若只是检查 Markdown 内容，优先用 `Get-Content -Encoding UTF8`。

### 2026-05-06：Headless UI Teleport 残留 DOM 导致前端弹窗表单测试提交错对象

- 场景：为 `JobsView`、`JobView`、`AccountView` 补作业内存和 association QOS 写操作前端单测。
- 现象：`update_job` 没有被调用，或第二次 association 保存把上一轮 Add User 弹窗的输入当成当前 Edit QOS 表单字段。
- 复现：在 `frontend/` 下执行 `npx vitest run tests/views/JobsView.spec.ts tests/views/JobView.spec.ts tests/views/AccountView.spec.ts tests/views/UserView.spec.ts`，测试通过 `document.body.querySelector('form')` 或全局 `input` 下标提交弹窗。
- 根因：Headless UI Dialog/Transition 与 `attachTo: document.body` 会把弹窗内容渲染到 body；关闭后的过渡 DOM 或前一个测试残留 DOM 可能仍被全局选择器命中，导致测试操作的不是当前业务弹窗。
- 解决：相关测试改为清理 `document.body.innerHTML`，并直接定位页面内的 `ActionDialog` 组件后触发其 `submit` 事件，验证页面提交 payload，而不是依赖弹窗内部 DOM 排序。
- 预防：后续测试复用 `ActionDialog`、Headless UI Dialog 或 Teleport 弹窗时，不要用全局表单/输入下标作为核心断言路径；优先按组件实例、标题或明确 test id 定位当前弹窗。

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

### 2026-05-06：用户工具分析在 Slurm step 级内存缺失时 `avg_max_memory_gb` 仍为空

- 场景：用户工具分析页或 AI 工具调用查询 `user/<username>/tools/analysis?start=<iso>&end=<iso>`，时间窗内作业存在 `tres_allocated` / `tres_requested` 内存 TRES，但 SlurmDB step 的 `consumed.max.mem` 为空。
- 现象：接口返回的 `avg_max_memory_gb` 仍为 `null`，前端 `tools/analysis` 的内存均值为空。
- 复现：构造 `job_snapshots.used_memory_gb IS NULL`、`usage_stats.memory.value_gb IS NULL`，但 `tres_allocated` 或 `tres_requested` 中存在 `{type: "mem", count: <MiB>}` 的终态作业，再查询用户工具分析接口。
- 根因：前一轮只补了 `used_memory_gb` 与 `usage_stats.memory.value_gb` 两条实际用量路径；部分 SlurmDB 返回的 step `consumed.max.mem` 为空，但 job 级 `tres.allocated/requested` 仍有内存配置，聚合 SQL 又没有把这些 TRES 字段取出，导致日表重建时内存样本数仍为 0。
- 解决：
  - `user_analytics_store` 的聚合查询补取 `tres_req_str`、`tres_per_job`、`tres_per_node`、`tres_requested`、`tres_allocated`。
  - 内存解析在实际用量缺失后，从 `tres_allocated`、`tres_requested` 的 `mem` TRES（MiB）兜底，再从 TRES 字符串中的 `mem=<MiB>` 兜底。
  - `slurmweb/scripts/rebuild-user-tool.py` 使用同一口径，避免维护脚本重建 `user_tool_daily_stats` 后再次写入空值。
  - 新增聚合和当前日刷新回归测试，覆盖 TRES list 与 TRES string 两类兜底。
- 预防：后续排查资源均值为空时，需要同时检查 step 实际用量和 job 级 TRES 配置；维护脚本必须与在线聚合保持字段选择和解析口径一致。

### 2026-05-06：`tools/analysis` 请求链路误触发日表重建

- 场景：排查 `avg_max_memory_gb` 为空时，直接在 `user_tool_analysis()` 请求路径调用 `_refresh_user_tool_daily_stats()`，先从 `job_snapshots` 聚合写入 `user_tool_daily_stats`，再读日表返回。
- 现象：`tools/analysis` 虽然最终读的是 `user_tool_daily_stats`，但每次接口请求都会同步扫描历史作业快照并重写时间窗内日聚合数据，不符合“前端接口只查 `UserToolDailyStat`”的设计要求。
- 复现：调用 `GET /user/<username>/tools/analysis?start=<iso>&end=<iso>`，可观察到请求链路执行 `_refresh_user_tool_daily_stats()`，并对 `user_tool_daily_stats` 做删除和插入。
- 根因：将数据修复职责放进了在线查询路径；没有把“日聚合表生成/修复”和“接口读取日聚合表”两个职责分开。
- 解决：
  - `user_tool_analysis()` 移除 `_refresh_user_tool_daily_stats()` 调用，只执行 `_user_tool_daily_summary()`。
  - 保留后台当前日聚合和 `slurmweb/scripts/rebuild-user-tool.py` 的资源解析修复，负责生成或修复 `user_tool_daily_stats`。
  - 单测改为断言 `user_tool_analysis()` 只读取日聚合摘要。
- 预防：后续调整 `tools/analysis` 返回字段时，接口层只能读 `user_tool_daily_stats`；如需补历史数据，应通过后台聚合任务、迁移或维护脚本完成。

### 2026-05-07：`source_jobs` 很大但 `jobs_count` 只剩少数显式内存行

- 场景：执行 `slurmweb/scripts/rebuild-user-tool.py` 全表重建，某天日志显示 `source_jobs=1983`，但 `user_tool_daily_stats row` 里 `jobs_count=4`。
- 现象：当天有上千条提交时间落在该日且状态为 `COMPLETED` 的作业，但日表只写入极少数作业，导致用户工具统计严重偏低。
- 复现：构造多条完成作业，其中 `used_memory_gb` 为空，但 `usage_stats.memory.value_gb`、`tres_allocated` 或 `tres_req_str` 可解析出正内存；原日聚合只统计显式 `used_memory_gb > 0` 的行。
- 根因：`aggregate_user_tool_daily_rows()` 没有复用已有 `_memory_gb(row)` 完整内存解析链，只直接读取 `row["used_memory_gb"]`，导致已在 `usage_stats` 或 TRES 中存在内存证据的作业被计入 `rows_skipped_memory`。
- 解决：
  - 日聚合改为通过 `_memory_gb(row)` 解析内存，优先使用 `used_memory_gb`，再回退到 `usage_stats.memory.value_gb`、`tres_allocated` / `tres_requested`、`tres_req_str` / `tres_per_job` / `tres_per_node`。
  - `rebuild-user-tool.py` 每日摘要增加 `counted`、`skipped_memory`、`missing_identity`、`cpu_missing`、`runtime_missing`，便于直接确认源作业未计入原因。
  - 更新后台当前日聚合和共享日聚合测试，覆盖 `usage_stats` 与 TRES fallback 内存也会进入 `jobs_count`。
- 预防：后续凡是按内存判断作业是否进入用户工具日表，都必须调用统一 `_memory_gb(row)`，不能直接读取单一物理列。

### 2026-05-07：`rebuild-user-tool.py` 仍可能沿用源行 `activity_date`

- 场景：全表重建 `user_tool_daily_stats` 时，脚本逐日读取历史作业并调用共享聚合函数生成日表 payload。
- 现象：如果 `JobsStore` 返回的源行携带了非当前重建日期的 `activity_date`，脚本会把该日期继续交给聚合函数，导致明细日志和写库 payload 的 `activity_date` 不一定等于当前循环日期。
- 复现：在 `rebuild-user-tool.py` 单测中 mock `completed_job_rows_for_activity_date(date(2026, 4, 24))` 返回 `activity_date=date(2026, 4, 23)` 的源行，原脚本会按源行日期聚合。
- 根因：脚本依赖下游 `JobsStore` 正确填充 `activity_date`，自身没有在“当前正在重建哪一天”的边界上做标准化。
- 解决：
  - `slurmweb/scripts/rebuild-user-tool.py` 新增 `completed_rows_for_rebuild_day()`，读取每日作业后复制源行并强制设置 `activity_date` 为当前重建日期。
  - 明细日志字段名同步为 `jobs_count`，与 `user_tool_daily_stats` 和聚合 payload 保持一致。
  - `TestRebuildUserToolScript` 增加回归断言：即使源行日期错误，dry-run 日志和 payload 仍使用当前重建日期。
- 预防：维护脚本在进入共享聚合函数前必须固定统计日期；后续若新增 rebuild/repair 脚本，也应把 `activity_date` 视为脚本边界输入而不是源行事实。

### 2026-05-06：后台日聚合与 `slurmweb/scripts/rebuild-user-tool.py` 聚合口径漂移

- 场景：要求 `user_analytics_store` 的后台聚合与 `slurmweb/scripts/rebuild-user-tool.py` 的数据聚合和插入逻辑保持一致，并由 `tools/analysis` 只读 `UserToolDailyStat` 后多日合并返回。
- 现象：后台当前日聚合与重建脚本存在重复实现，后台按数据库本地 `CURRENT_DATE` 取当天，重建脚本按 UTC 日期取数；`regr_*` 工具归并只在重建脚本中存在。
- 复现：分别执行后台当前日聚合和维护脚本重建同一天数据，在数据库 timezone 非 UTC 或工具名为 `regr_foo` / `regr-bar` 时，可能写出不同的 `activity_date` 或 `tool`。
- 根因：聚合、工具归类和时间口径分散在两个文件中维护，缺少共享函数和回归测试。
- 解决：
  - `user_analytics_store` 新增共享 `aggregate_user_tool_daily_rows()`，负责日聚合、资源空值过滤、样本数统计与工具归类。
  - 后台 `_aggregate_daily_rows()` 与 `slurmweb/scripts/rebuild-user-tool.py` 均复用该共享函数。
  - 后台当前日查询改为 UTC 自然日，并过滤 `user_id IS NULL` 与 `COALESCE(end_time, last_seen) IS NULL` 的行。
  - `tools/analysis` 保持只读 `user_tool_daily_stats`，多日查询由 `_aggregate_daily_stat_rows()` 按 `memory_samples` / `cpu_samples` / `runtime_samples` 加权合并。
- 预防：后续修改日聚合字段、工具归类或资源解析时，只改共享聚合函数，并补后台路径与维护脚本一致性的测试。

### 2026-05-06：`tools/analysis` 可返回 `jobs_count > 0` 但资源均值为 `0`

- 场景：用户分析页或 AI 工具调用查询 `user/<username>/tools/analysis?start=<iso>&end=<iso>`，时间窗内 `user_tool_daily_stats` 已存在旧日聚合行，且部分行只有 `jobs_count`，没有有效的 `avg_max_memory_gb` / `avg_cpu_cores`。
- 现象：接口会返回 `completed_jobs` 或 `tool_breakdown[].jobs` 大于 `0`，但同一条统计的 `avg_max_memory_gb`、`avg_cpu_cores` 显示为 `0`，与“只把有效资源统计当作推荐证据”的预期不一致。
- 复现：
  - 先写入或保留一条 `user_tool_daily_stats` 行，其中 `jobs_count > 0`，但 `avg_max_memory_gb` / `avg_cpu_cores` 为 `0`、`NULL` 或其他非法值。
  - 调用 `GET /user/<username>/tools/analysis?start=<iso>&end=<iso>`，可观察到接口继续把该行计入 `completed_jobs` 或工具级 `jobs`。
  - 对当天数据按 `[user_metrics].aggregation_interval` 周期刷新时，如果新 payload 为空，原实现只做 upsert、不做 delete，当天旧脏行会继续残留。
- 根因：
  - 日聚合写入阶段此前把无有效资源对的作业也累加进 `jobs_count`，并把资源均值写成 `0`。
  - 跨天读取 `_aggregate_daily_stat_rows()` 又会继续把这些 `0`/`NULL` 资源日行计入 `completed_jobs`。
  - 当前日后台刷新只做 upsert，没有在重算当天前删除旧日行，导致按间隔刷新后脏行仍可能保留。
- 解决：
  - `aggregate_user_tool_daily_rows()` 只纳入 `used_memory_gb > 0` 且 `used_cpu_cores_avg > 0` 的作业；不再为无效资源对写入 `jobs_count` 或 `avg_* = 0` 行。
  - `_aggregate_daily_stat_rows()` 读取日表时直接跳过 `jobs_count <= 0` 或资源均值不是有效正数的旧行，不再让这些旧行贡献接口的 `completed_jobs`、工具列表或资源均值。
  - 当前日后台刷新改为“先删当天旧行，再写当天新 payload”，确保按聚合间隔刷新时不会残留旧脏统计。
  - 补充聚合、当前日刷新和 repair/rebuild 脚本回归测试，覆盖“无有效资源对时不写行”和“旧 0 行不再被接口读出”。
- 预防：后续只要 `jobs_count` 的定义依赖某组资源字段，就必须在“日写入”和“跨日读取”两层保持同一过滤口径；后台按周期重算某天统计时必须替换整天数据，而不是只做 upsert。

### 2026-05-07：用户工具日聚合把缺 CPU 样本的完成作业整条丢弃

- 场景：排查 `tools/analysis` 全空时，发现某些完成作业已经有 `used_memory_gb > 0`，但没有 `used_cpu_cores_avg`，导致整条作业没有进入 `user_tool_daily_stats`。
- 现象：
  - 用户明明有完成作业和有效内存数据，但 `tools/analysis` 仍可能返回空列表或 `completed_jobs = 0`。
  - 后台聚合线程缺少每轮核心计数日志，无法快速判断是“完全没作业”还是“作业被过滤掉”。
- 复现：
  - 写入一条终态 `job_snapshots`，其中 `used_memory_gb > 0`，`used_cpu_cores_avg` 为 `NULL` 或 `0`。
  - 执行后台当天聚合或 `repair-user-tool-daily-stats.py`，原实现不会为该作业生成日表统计。
- 根因：
  - `aggregate_user_tool_daily_rows()` 把 `used_memory_gb` 和 `used_cpu_cores_avg` 同时视为写表硬门槛。
  - 聚合线程没有输出每轮扫描数、跳过数和写入数，排障只能靠手工 SQL 对比。
- 解决：
  - 日聚合写表改为只强制 `used_memory_gb > 0`；`used_cpu_cores_avg` 缺失时仍保留该作业的 `jobs_count`、内存均值和运行时样本。
  - `avg_cpu_cores` 与 `cpu_samples` 仅统计有有效 CPU 样本的子集；跨天 `tools/analysis` 只对这类日行合并 CPU 均值。
  - `refresh_current_day_summary()` 增加每轮聚合汇总日志，记录扫描作业数、缺内存跳过数、缺 CPU 样本数和最终写入行数。
  - `repair-user-tool-daily-stats.py` 与 `slurmweb/scripts/rebuild-user-tool.py` 同步新口径，用于重建历史 `user_tool_daily_stats`。
- 预防：后续只要调整 `jobs_count`、`avg_cpu_cores` 或样本数字段语义，必须同时更新在线聚合、跨天汇总、维护脚本和诊断日志，并补对应回归测试。

### 2026-05-06：前端单测入口误用 `npm test` 与 `npm run test:unit -- --run ...`

- 场景：验证用户分析页面合并 `Tool Analysis` 与 `Top Tools` 栏目时，先执行 `npm test -- --run ...`，随后执行 `npm run test:unit -- --run ...`。
- 现象：
  - `npm test -- --run ...` 报 `Missing script: "test"`。
  - `npm run test:unit -- --run ...` 在当前环境超时，没有输出有效失败详情。
- 复现：
  - 在 `frontend/` 下执行 `npm test -- --run tests/views/UserAnalysisView.spec.ts`。
  - 在 `frontend/` 下执行 `npm run test:unit -- --run tests/views/UserAnalysisView.spec.ts tests/views/UserView.spec.ts tests/components/user/UserToolAnalysisChart.spec.ts`。
- 根因：前端 `package.json` 没有 `test` 脚本，实际单测脚本为 `test:unit`；在当前环境中直接用 `npx vitest run ...` 跑目标 spec 更稳定。
- 解决：改用 `npx vitest run tests/views/UserAnalysisView.spec.ts tests/views/UserView.spec.ts tests/components/user/UserToolAnalysisChart.spec.ts`，目标测试通过。
- 预防：后续前端定向单测优先使用 `npx vitest run <spec...>`；需要通过 npm 脚本时先检查 `frontend/package.json` 的 scripts。

### 2026-05-06：AI 对话页输入框脱离左侧聊天列，流式对话时面板整体下移

- 场景：在普通 AI 对话页持续发送消息，或等待 assistant 流式回复并同时查看右侧 `Execution trace`。
- 现象：
  - 左侧聊天区没有完整撑满工作区宽度，输入框显示在左右两列下方而不是左侧对话列内。
  - 对话过程中消息区会被整体向下挤动，视觉上像整个聊天框下沉。
- 复现：打开 `/:cluster/ai`，在有右侧 trace 栏的情况下发送消息，观察消息区和输入框布局；当消息数增长或 trace 更新时，左侧面板位置发生跳动。
- 根因：`AssistantView` 把消息滚动区放在左右两列 grid 内，但把 composer `form` 放在 grid 外，导致输入框跨越整行；消息区又使用内容驱动的 `min/max-height` 与空态 `justify-between`，在流式更新和右侧栏高度变化时容易触发重新布局。
- 解决：
  - 把消息滚动区和 composer 一起收进左侧单独的 `flex flex-col` 容器。
  - 给消息滚动区稳定高度和 `min-w-0`，避免左右列互相挤压时触发宽度和高度漂移。
  - 空态快捷按钮改为 `mt-auto` 贴底，保持仍在消息区内部，但不再依赖 `justify-between` 撑满整块容器。
  - 补 `AssistantView.spec.ts` 结构回归测试，断言 message scroller 和 composer 同属左侧聊天列。
- 预防：后续做双列聊天页布局时，输入组件必须跟消息滚动容器处于同一列容器内；对流式内容区域优先使用稳定高度或 `flex-1/min-h-0` 结构，避免把输入区挂在外层 grid 之后。
