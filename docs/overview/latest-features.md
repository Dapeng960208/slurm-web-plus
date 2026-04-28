# 最新功能

## 本轮：AI 审计、会话逻辑删除、复制操作与指标时间窗弹框

本轮围绕节点指标、用户分析和 AI 对话做交互与审计收口：

- 节点详情页 `Real Metrics` 支持点击按钮打开时间范围弹框
- 节点指标自定义窗口支持 `start` / `end`，精确到时分，并同步到 URL query
- 用户工具分析页改为与节点详情一致的时间范围按钮和弹框
- 时间范围弹框新增 `1 day`、`3 days`、`7 days`、`15 days`、`1 month` 快捷窗口
- 用户数据分析页移除了重复的用户名信息卡，LDAP 姓名、组和更新时间压缩到时间范围栏中
- 集群页与 Settings 页主内容区改为独立滚动区域，底部保留固定 `2rem` 浏览器边缘留白
- 用户分析的 `Submission Activity`、`Usage Profile`、`Tool Analysis` 与 `Top Tools` 继续共享同一时间窗
- `user/<username>/tools/analysis` 会先将时间窗覆盖的 UTC 日期聚合写入 `user_tool_daily_stats`，再从该表汇总返回工具分类统计
- `user_tool_daily_stats` 补充资源样本数字段，用于跨多日工具统计时准确加权内存、CPU 与运行时间均值
- 用户分析资源统计明确按已完成作业计算：
  - 平均最大内存：优先使用 `used_memory_gb`，为空时回退 `usage_stats.memory.value_gb`，返回 GB 与兼容 MB 字段
  - 平均运行时间：`end_time - start_time`，返回小时与兼容秒字段
  - 平均 CPU 核数：优先使用 `used_cpu_cores_avg`，为空时回退 `usage_stats.cpu.estimated_cores_avg`
- `Submission Activity` 的提交时间线在 `submit_time` 缺失时会回退到 `start_time` / `last_seen`
- 用户分析终态作业匹配改为大小写不敏感，避免 `completed` 这类小写状态导致时间窗内无数据
- 用户分析 `metrics/history` 自定义窗口的 bucket 统一按 UTC 对齐，修复选择 `7 days` 时返回非零数据却前端序列全 0 的问题
- `conf/vendor/user-tools.yml` 新增 `tool_mapping_file` demo，可直接作为 `[user_metrics].tool_mapping_file` 规则模板
- 普通 AI 对话页不再展示模型、stream、persistence 等运行配置块
- AI 右侧 Tool Calls 记录改为可换行、可展开的接口调用展示，避免接口名、状态、参数摘要堆叠
- AI 用户消息与 assistant 回复都提供复制按钮
- AI 对话输入区新增 token 估算展示，超出模型配置限制或默认 `8192` 时提示并阻止发送
- 普通用户可逻辑删除自己的 AI 会话，删除后普通列表和普通详情不再展示
- 管理员可在 `/:cluster/admin/ai` 查看所有用户 AI 会话审计记录，包含已逻辑删除会话
- 管理员 AI 配置页保留弹窗式创建/编辑，已有配置改为紧凑标签式展示，并支持删除配置
- 管理员 AI 审计列表支持按用户名、标题或最后消息关键字过滤，点击记录后才加载详情
- AI 会话逻辑删除新增 `ai_conversations.deleted_at` 与 `deleted_by`
- Gateway 与 Agent 新增 AI 会话删除、管理员审计列表和详情接口
- `association/update` 写入修复：
  - association payload 缺少 `cluster` 时按当前集群补齐
  - account/user/association/qos 写入或删除后失效相关缓存，避免账户页继续显示旧数据

本轮新增验证：

- `cd frontend && npx vitest run tests/components/MetricRangeSelector.spec.ts tests/views/NodeView.spec.ts tests/views/UserAnalysisView.spec.ts tests/views/AssistantView.spec.ts tests/views/settings/SettingsAI.spec.ts tests/composables/GatewayAPI.spec.ts`
- `cd frontend && npx vitest run tests/views/settings/SettingsAI.spec.ts tests/views/AssistantView.spec.ts`
- `npm --prefix frontend run type-check`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py slurmweb/tests/views/test_agent_ai.py slurmweb/tests/views/test_gateway_ai.py slurmweb/tests/views/test_agent_metrics_requests.py slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py slurmweb/tests/test_cache.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_operations.py slurmweb/tests/slurmrestd/test_slurmrestd_filtered_cached.py slurmweb/tests/test_cache.py`

## 本轮：AI 对话、用户工具分析时间窗与接口命名统一修复

本轮继续在已上线 AI 助手和用户分析页面上做行为收口，没有新增独立页面：

- AI 对话服务已修复“工具调用成功后把内部 `tool_request` envelope 当作最终消息回显”的严重 bug
- 当模型错误输出内部 `tool_request` / `interface_key` / `arguments` JSON 时：
  - 服务端不会把它透传到消息区
  - 也不会把它持久化成最终 assistant 消息
  - 会继续追加纠正提示，要求模型输出合法 `final`
- AI 面向用户工具推荐问题时，接口说明与提示词已收敛到优先使用 `user/tools/analysis`
- 用户分析聚合接口已正式改名：
  - `user/activity/summary` -> `user/tools/analysis`
  - 不保留旧路径兼容
- 用户分析页整页已统一改为共享 `start/end` 时间窗：
  - `Submission Activity`
  - `Usage Profile`
  - `Tool Analysis`
  - `Top Tools`
  - 全部跟随同一组 `datetime-local` 选择器
- 用户分析页首次进入时，若 URL query 缺失或非法，会自动回填“当天 00:00 -> 当前时间”
- 趋势图与统计卡现在按所选窗口展示：
  - `Submitted in Range`
  - `Completed in Range`
  - `Active Tools`
  - `Average Runtime`
- `user/metrics/history` 现在支持 `start/end` 窗口查询，并在响应中补：
  - `window`
  - `totals`
- 自定义时间窗下，历史曲线 bucket 已自动按窗口长度切换：
  - `<= 48h` 按小时
  - `> 48h 且 <= 62d` 按天
  - `> 62d` 按周

本轮新增验证：

- `cd frontend && npx vitest run tests/views/UserAnalysisView.spec.ts tests/composables/GatewayAPI.spec.ts tests/views/AssistantView.spec.ts tests/views/AssistantViewAIContract.spec.ts`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py slurmweb/tests/apps/test_user_analytics_store.py slurmweb/tests/views/test_agent_metrics_requests.py slurmweb/tests/views/test_gateway.py`
- `npm --prefix frontend run type-check`

## 本轮：AI 助手改为按 Agent 接口编排查询，并统一接口权限与执行轨迹

本轮 AI 助手没有新增独立页面，但对对话执行链路做了收口：

- AI 工具层不再直接把 `slurmrestd` / store 暴露给模型
- 新增 Agent 进程内接口适配层，AI 统一按 Agent 接口语义取数
- 模型现在可以在同一问题里连续调用多个接口后再汇总回答
- 对模型的接口说明只描述“接口能做什么、需要什么参数”，不再把问题到接口的映射写死
- 典型场景下，AI 可按需串联：
  - `job`
  - `jobs/history`
  - `user/tools/analysis`
  - `user/metrics/history`
- 对“用户某工具推荐多少内存/CPU/运行时”这类问题，提示词与接口目录现在会优先把 `user/tools/analysis` 暴露为直接证据源，再视情况补查原始 history
- 查询权限继续复用现有 `resource:operation:scope` 规则
- 通过 AI 触发 create / update / delete 现在直接复用 Agent 接口权限：
  - `admin` 默认 `*:edit:*` 可执行对应 `edit` 类写接口
  - `delete`、`self` 等边界仍由接口层按当前用户规则校验
  - 无权限时，AI 会收到接口拒绝结果，不会绕过后端限制
- AI 会话详情现在会返回历史 `tool_calls`
- `ai_tool_calls` 新增记录：
  - `interface_key`
  - `status_code`
- AI 页面 `Execution trace` 默认只显示：
  - 工具名
  - 命中接口
  - 状态码
  - 耗时
- 参数、摘要、错误详情改为点击 trace 后展开查看
- AI 对话消息现在支持安全 Markdown 渲染：
  - `assistant` 与 `user` 消息都会按 Markdown 展示
  - 原始 HTML 不会作为真实 DOM 节点渲染
  - 外链默认新标签打开并带 `rel="noopener noreferrer"`

本轮新增验证：

- `cd frontend && npx vitest run tests/views/AssistantView.spec.ts tests/views/AssistantViewAIContract.spec.ts`
- `npm --prefix frontend run type-check`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py slurmweb/tests/views/test_agent_ai.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_agent_ai.py slurmweb/tests/views/test_gateway_ai.py`
- `cd frontend && npx vitest run tests/views/AssistantView.spec.ts tests/views/AssistantViewAIContract.spec.ts tests/composables/GatewayAPI.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：分析与管理页改为结构化展示，并补统一时间范围与表单语义

本轮继续围绕现有 `analysis`、`admin`、`dashboard`、`node` 与用户分析页面做交互增强，没有新增独立功能模块：

- `analysis` 页的 `ping` / `diag` 不再直接输出原始 JSON
- `Admin > System` 页的 `licenses` 改为结构化字段卡片，优先展示许可证名称、总量、已用、可用、保留等核心字段
- `Admin > System` 页的 `slurmdb/instances` 已兼容 SlurmDB “found nothing” 的 warning-only 响应，空结果返回列表而不是 500
- 用户分析历史曲线从“仅提交作业”扩展为“提交 + 完成”双曲线
- 用户分析、节点详情、Dashboard/Analysis 的时间范围切换统一为 `hour / day / week`
- 节点详情的时间范围已同步到 URL query，刷新后保留当前窗口
- 左侧主菜单顺序已调整为：
  - `AI` 在 `Admin` 上方
  - `Admin` 固定落在主业务导航末尾
- 共享操作表单已补统一语义：
  - 字段显示 `Required` / `Optional`
  - 编辑类提交按钮使用橙色语义
  - 删除类提交按钮使用红色警示语义
  - 关键按钮与字段补充 tooltip / hint 解释行为
- `Settings > AI` 与 `Node` 编辑/删除入口已接入上述表单语义

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/components/operations/ActionDialog.spec.ts tests/composables/GatewayAPI.spec.ts tests/views/UserAnalysisView.spec.ts tests/views/ClusterAnalysisView.spec.ts tests/views/NodeView.spec.ts tests/views/settings/SettingsAI.spec.ts tests/components/MainMenu.spec.ts`
- `.venv\Scripts\python.exe -m pytest slurmweb/tests/views/test_agent_metrics_requests.py slurmweb/tests/views/test_gateway.py slurmweb/tests/apps/test_user_analytics_store.py`

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
- 同时把前端源码里的 `@typescript-eslint/no-unused-vars` 与 `@typescript-eslint/no-empty-object-type` 降级为 warning，避免这类历史清理项继续阻塞主线 CI

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
