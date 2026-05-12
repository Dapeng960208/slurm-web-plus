# 最新功能

## 本轮：AI 与 Admin 页面主体国际化已补齐

本轮继续补齐前端全站中英文切换，重点收口此前仍大量保留英文直出的 AI 和 Admin 页面主体：

- `AssistantView` 的历史区、工作区、提示词、对话轨迹、复制提示、token 提示、前端错误提示已接入中英文词典。
- `Settings > AI` / `Admin > AI` 的模型配置、审计表格、弹窗字段、前端校验提示、按钮和筛选文案已接入中英文词典。
- `Admin > AI Conversation Detail`、`Admin > Cache`、`Admin > Users`、`Admin > Access Control` 的页头、表头、空态、说明文案、只读提示和前端状态提示已补齐翻译。
- `SettingsTabs` / `AdminTabs` 已改为稳定 id 驱动选中态，不再把英文显示值和组件状态耦合在一起。
- `Cache` / `AI` 相关图表标签现在会随 locale 实时更新，不再只切换外围壳层。

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run`
- `npm --prefix frontend run build`

## 本轮：前端全站中英文切换已补齐到业务页面主体

本轮继续收口前端国际化，把之前只覆盖导航和公共壳层的状态扩展到核心业务页面主体：

- `vue-i18n`、locale store、`localStorage['locale']`、浏览器语言默认判定和 `document.documentElement.lang` 同步机制保持不变。
- 登录页、右上 `UserMenu`、`Settings > General` 三个语言入口继续保留，切换后即时生效，不刷新页面。
- 核心业务页面的页头、按钮、筛选、表格头、空态、弹窗、通知、前端状态提示和分析面板文案已补齐：
  - `Dashboard`
  - `Cluster Analysis`
  - `Jobs` / `Jobs History` / `Job`
  - `Resources` / `Node`
  - `Accounts` / `Account`
  - `User` / `User Analysis`
  - `QOS`
  - `Reservations`
- 公共时间范围控件、作业历史详情、节点实时指标、用户分析图表和工具分析表格现在会随 locale 实时更新，不再出现“侧栏已切换但页面主体仍是英文”的情况。
- 共享显示组件已统一按“翻译 key 或原始值”安全渲染，避免把后端原始值、实体名或状态码误送进 `t()` 触发 missing-key 告警。
- 当前仍不翻译：
  - 后端直接返回的原始错误消息
  - 集群名、用户名、QOS 名、分区名、节点名等业务实体值
  - 后端原始业务字段值

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run`
- `npm --prefix frontend run build`

## 本轮：已补本地 GitHub CI 拉取脚本

本轮已为本机协作补两条 PowerShell 脚本，方便直接读取 GitHub Actions 返回的测试结果并继续修复：

- `scripts/fetch-github-ci-result.ps1`
  - 可按 `run_id` 或 `workflow + branch` 拉取最新 run 概要
  - 可选下载 artifact
  - 可选导出 `gh run view --log-failed` 到本地
- `scripts/watch-github-ci.ps1`
  - 可按 workflow 轮询最新 run
  - run 完成后自动调用抓取脚本导出结果
- `scripts/continue-from-github-ci.ps1`
  - 基于已抓取的 artifact、`failure-context.json`、`result.json` 和 `failed.log` 生成 `codex-autofix-prompt.md`
  - 显式追加 `-RunCodex` 时，可直接调用本机 `codex exec` 继续修复
- `scripts/push-and-watch-github-ci.ps1`
  - 可按当前 `HEAD` 提交推送到 GitHub
  - 自动等待对应 commit 的 GitHub Actions run 完成
  - 完成后直接接到 `continue-from-github-ci.ps1`
- 发布后又补了一条脚本级修复：
  - `scripts/watch-github-ci.ps1` 在 workflow 完成后，改为用命名参数 hashtable 调 `fetch-github-ci-result.ps1`
  - 修复了 `-OutputRoot` 被误绑到 `-Conclusion`，导致 completed run 无法继续导出结果的问题

当前约束：

- 依赖本机已安装并登录 `gh`
- 默认只生成修复上下文，不会在未显式授权时自动改代码或提交

补充约束：

- 仓库级 AI 规则已新增要求：当任务涉及远端 GitHub Actions 结果查询、failed log/artifact 下载、CI 失败续修或推送后等待 workflow 完成时，必须优先复用这套 `github-ci-autofix` 仓库流程和 `scripts/*github-ci*.ps1`，不再临时发明 ad hoc 流程

## 本轮：共享 segmented 控件与筛选输入样式已统一

本轮继续收口前端明显不一致的局部控件，优先复用现有设计 token，不做页面结构重写：

- `ResourcesDiagramNavigation` 与 `ChartResourcesHistogram` 改为共享 `ui-segmented-control` / `ui-segmented-button`
- `AccountFilterSelector`、`QosFilterSelector`、`UserFilterSelector` 改为共享 `ui-combobox-*` 输入与下拉样式
- `ResourcesFiltersBar` 的 active filters 容器改为复用 `ui-panel-soft`
- `QosHelpModal` 改为复用共享 surface 和 `ui-button-secondary`
- `AccountTreeNode` 的卡片与统计 badge 改为复用 `ui-panel-soft` 与 `ui-chip`

## 本轮：Review 文档与访问控制专题已按当前实现重写

本轮对 `docs/review/*` 和访问控制专题文档做了事实校准，去掉旧的专项流水账口径，统一到当前代码实现：

- `docs/review/backend-review.md`、`frontend-review.md`、`test-review.md` 已改为当前仓库真实审查结论
- 新增 `docs/review/open-questions.md` 记录无法仅靠静态代码确认的事项
- `docs/features/access-control/requirements.md` 与 `test-plan.md` 已统一到当前 `resource:operation:scope`、`admin/*` 主路径和 `rules[]` 优先口径
- `docs/overview/project-overview.md` 与 `architecture-overview.md` 已明确 `/:cluster/admin/*` 是主管理入口，`/settings/*` 相关管理页仅保留兼容重定向

## 本轮：前端共享权限消费点已统一优先走 `resource:operation:scope`

本轮对几处仍依赖旧 `actions[]` 的共享权限判断做了收口，避免菜单、路由和页内局部控件继续出现不同步的授权口径：

- `DashboardView` 的分区筛选改为按 `jobs/filter-partitions:view:*` 或 `resources/filter-partitions:view:*` 判断
- `NodeView` 的节点作业轮询改为按 `jobs:view:*` 判断
- `JobsFiltersPanel` 的 `Accounts / QOS / Partitions` 筛选区改为按对应 filter resource 判断
- `DashboardCharts` 的图表显示改为按 `resources:view:*` 与 `jobs:view:*` 判断
- `ResourcesFiltersPanel` 的分区筛选改为按 `resources/filter-partitions:view:*` 判断
- `userWorkspace` 继续保留必要的 legacy fallback，但默认调用口径已与现有 route-rule 测试夹具对齐

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/views/DashboardView.spec.ts tests/views/NodeView.spec.ts tests/components/jobs/JobsFiltersPanel.spec.ts tests/components/dashboard/DashboardCharts.spec.ts tests/composables/userWorkspace.spec.ts`

## 本轮：GitHub `Backend Tests` 已改为 `Python 3.9`

本轮把提交到 GitHub 后自动触发的后端主线测试版本从 `Python 3.12` 调整为 `Python 3.9`：

- `.github/workflows/python-ci.yml` 的 `actions/setup-python` 已固定改为 `python-version: "3.9"`
- job 展示名已同步改为 `Python unit tests (Python 3.9)`
- 结构化结果 artifact 目录名已同步改为 `backend-python-3.9`
- 前端自动测试、前端静态检查、手工 `python-os-ci.yml` 和 `CI Triage` 的触发方式与职责不变

本轮新增验证：

- `Get-Content -Raw -Encoding UTF8 .github/workflows/python-ci.yml | npx --yes yaml valid`
- `rg -n "Python 3\\.12|backend-python-3\\.12|python-version: \\\"3\\.12\\\"" .github docs`

发布后补充修复：

- `slurmweb/tests/lib/gateway.py` 中的测试侧 `ldap` stub 已补成带 `ldap.filter` 子模块的 package 形态
- 避免 GitHub `Backend Tests` 在未安装 `python-ldap` 的 Linux runner 上，把 `ldap` 识别成普通模块后因 `import ldap.filter` 在 collection 阶段中断
- `slurmweb/version.py` 已补源码目录回退逻辑：若当前环境未安装 `slurm-web-plus` / `slurm-web` 包元数据，会回退读取仓库 `pyproject.toml` 中的版本号
- 避免本地或 CI 直接以源码 checkout 运行测试时，`get_version()` 因缺少已安装包元数据而让 gateway / agent / showconf 等测试在导入阶段失败
- `frontend/tests/components/MetricRangeSelector.spec.ts` 与 `frontend/tests/views/UserAnalysisView.spec.ts` 已改为只 fake `Date`
- 修复 `vue-i18n` 在 Vitest 全量 fake timers 接管 `performance` 后渲染时报 `invalid timestamp` 的前端单测失败

## 本轮：前端已接入浏览器优先的中英文切换

本轮在前端落地了第一阶段国际化能力，重点覆盖登录入口、共享导航、设置页和前端提示文案：

- 前端已接入 `vue-i18n`，支持 `zh-CN` 与 `en` 两种语言。
- 首次进入会优先读取 `localStorage['locale']`；若没有本地偏好，则按浏览器语言自动判定，`zh*` 默认中文，其余默认英文。
- 登录页新增语言切换入口，登录后可在右上 `UserMenu` 中切换语言，`Settings > General` 也提供语言偏好入口。
- 主导航、用户菜单、Settings 导航、Settings General / Errors、通知类型标签、分页文案、公共弹窗和前端生成的错误提示已接入翻译资源。
- 当前国际化只覆盖前端静态文案和前端生成消息，不翻译后端直接返回的原始错误内容与业务实体值。

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/stores/locale.spec.ts tests/views/LoginView.spec.ts tests/components/MainMenu.spec.ts tests/components/UserMenu.spec.ts tests/components/settings/SettingsTabs.spec.ts tests/views/settings/SettingsMain.spec.ts tests/components/NotificationsPanel.spec.ts tests/components/PaginationControls.spec.ts`

## 本轮：`Dashboard`、`Analysis` 与 `Admin` 内容页已补统一内部滚动

本轮继续收口固定应用壳下的内容页滚动问题，重点解决“表格能滚动，但非表格正文和配置内容无法继续下滚”的共性缺陷：

- `DashboardView` 已补共享 `ui-scroll-region`，页头保留在工作区顶部，筛选面板、统计卡片和图表区域改为在固定内容区内滚动。
- `ClusterAnalysisView` 已补同一套正文滚动容器，分析摘要、容量卡、建议区与控制器健康区不再被固定 shell 裁切。
- `AdminLayoutView` 现已在 `RouterView` 外层统一提供内部滚动区，`admin/ai`、`admin/access-control`、`admin/cache`、`admin/ldap-users` 以及管理员 AI 会话详情等子页面无需各自重复修补即可恢复内容滚动。
- 本轮修复继续保留表格页各自的局部滚动结构，不改变已存在的 `ui-table-scroll`、`ui-results-scroll` 和分页停靠方式。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/DashboardView.spec.ts tests/views/ClusterAnalysisView.spec.ts tests/views/AdminLayoutView.spec.ts tests/views/settings/SettingsAI.spec.ts tests/views/settings/SettingsAccessControl.spec.ts tests/views/settings/SettingsCache.spec.ts tests/views/settings/SettingsLdapCache.spec.ts tests/views/settings/SettingsAIConversationDetail.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：内容页滚动层级、按钮语义与 AI 工作区已统一收口

补充修正：

- `User`、`Account`、`Job`、`Job History`、`Node` 与 `User Analysis` 详情页现已补回正文内部滚动区。
- 详情页顶部返回按钮继续保留在工作区内，正文内容改为通过共享 `ui-scroll-region` 在固定可视区内滚动。
- 这次修复解决了“表格类页面仍可滚动，但非表格详情内容在固定 shell 中被裁切后无法继续下滚”的回归。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/UserView.spec.ts tests/views/JobView.spec.ts tests/views/NodeView.spec.ts tests/views/UserAnalysisView.spec.ts`

## 本轮：开发错误库已简化为时间、现象、解决办法三项

本轮对内部跟踪文档中的开发错误库做了结构收口，目标是降低维护成本并提高检索效率：

- `docs/tracking/error-log.md` 现已统一为精简格式，只保留 `时间`、`现象`、`解决办法` 三项。
- 旧条目中的场景、复现、根因、预防等冗余字段已从错误库中移除，不再要求逐条展开长篇复盘。
- `docs/standards/development-error-summary.md` 已同步更新为新的最小记录模板，避免正式规范与跟踪文档格式冲突。
- `docs/standards/ai-development-standard.md` 中对错误库的引用也已同步改为“时间 / 现象 / 解决办法”。

## 本轮：`admin/ai` 已统一为表格工作区和独立会话详情页

本轮继续收口管理员 AI 页面，重点解决模型配置仍是卡片堆叠、审计详情挤在同页右侧，以及搜索框样式与全局不一致的问题：

- `/:cluster/admin/ai` 顶部已收口为单个页头卡，不再保留额外统计卡和重复说明层。
- 模型配置列表已从紧凑卡片改为标准表格，统一展示模型名、provider、secret、默认状态、校验状态和操作按钮。
- 对话审计列表继续保留表格形态，但不再在同页右侧展示详情；详情入口改为独立跳转。
- 新增独立详情页 `/:cluster/admin/ai/conversations/:conversationId`，用于查看完整消息历史和工具调用明细。
- 审计搜索框已切回共享输入样式，避免 `admin/ai` 页面继续出现和全局不同的一套搜索框视觉。

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/views/settings/SettingsAI.spec.ts tests/views/settings/SettingsAIConversationDetail.spec.ts tests/router/AdminRoutesContract.spec.ts`

本轮继续收口登录后业务页面的工作区结构，重点解决内容过多时外层页面被持续撑高、同类按钮样式不一致，以及 AI 对话区随历史与消息增长不断下扩的问题：

- 共享布局和样式已统一补齐 `flex-1`、`min-h-0` 与内部滚动约束，业务内容页现在优先在表格区、列表区、消息区、侧栏或详情区内部滚动，而不是继续推高最外层容器。
- `ClusterMainLayout` 与 `SettingsLayout` 现已把 `ui-content-scroll` 固定为浏览器可视区内框；该区域高度会对齐 header 下方剩余视口，并保留与左侧桌面导航一致的底部留白，不再随着内容增长继续拉长整页。
- `Jobs`、`Jobs History`、`Resources`、`Dashboard`、`Analysis`、`Accounts`、`Account`、`User`、`Reservations`、`QOS`、`Admin` 等页面已接入统一内容工作区容器，页面滚动层级更稳定。
- `Jobs`、`Jobs History`、`Resources`、`QOS`、`Reservations`、`Accounts` 等单主结果区页面已改为“表格/树内容区单独滚动 + 分页条固定在工作区底部”的展示方式，更接近常见控制台工作区，不必先滚到整页最底部才能翻页。
- 表格共享滚动样式已去掉各视图里零散的负边距横向滚动写法，表格左右 gutter 与内边距恢复统一，列内容不再紧贴容器边缘。
- `Users` 页面已删除重复的页头卡片与集群标题，搜索和结果区统一合并为单个内容卡片，减少无效留白和重复说明。
- `Users` 作为多 cluster 特例，继续按 cluster 卡片独立滚动与分页；分页固定在各自卡片底部，不固定到浏览器底部，避免同页多分页器互相覆盖。
- `Cluster Analysis` 中同栏目并列卡片已统一复用共享 surface，避免 `Packing Signal`、分区热点卡、历史压力卡在同一块内容里出现无语义依据的背景和边框差异。
- `SettingsHeader` 与 `AdminHeader` 的固定套话已删除，页面标题继续按“唯一主标题 + 必要说明”收口，减少重复说明和冗余头部文本。
- `Add filters` 现已统一为共享次级按钮样式；`Jobs` 页面中的 `Submit job` 与 `Add filters` 已整理到同一操作区，同排、同高、同对齐。
- AI 对话页已改为固定高度工作区：左侧历史、中间消息区、右侧执行 trace 分别独立滚动，底部输入框固定在工作区底部；消息区内容增多时只在消息区内部滚动，不再把输入框向下挤走；历史列表仅显示会话标题与更新时间，不再显示消息摘要。
- 本轮补充修正后，AI 中间聊天列本身也锁定在 `ui-content-scroll` 可视区内，因此 composer 会停在浏览器可视区底部，而不是整页内容底部。

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/views/JobsView.spec.ts tests/views/JobsHistoryView.spec.ts tests/views/resources/ResourcesView.spec.ts tests/views/QosView.spec.ts tests/views/ReservationsView.spec.ts tests/views/AccountsView.spec.ts tests/views/AssistantView.spec.ts tests/views/settings/SettingsLdapCache.spec.ts tests/components/PaginationControls.spec.ts`

## 本轮：Dashboard 头部、筛选区与统计卡片样式已统一

本轮对 Dashboard 页面做了针对性的布局收口，解决头部信息分散、筛选区不对齐和卡片表面风格不一致的问题：

- `Open analysis` 已与头部 `Total Jobs` 摘要收敛到同一行，首屏操作和关键指标不再分散。
- `Partition / Queue` 与 `Time Range` 已收口到同一组横向工具栏，标签左对齐，控件间距和垂直对齐统一。
- 筛选区容器与顶部统计卡片已统一为同一套 surface 样式，避免不同区块背景、边框和层次语言不一致。
- 本轮只调整 Dashboard 视图内的局部布局和样式，不改变分区筛选、统计数据和图表请求行为。

本轮新增验证：

- `cd frontend && pnpm vitest run tests/views/DashboardView.spec.ts tests/components/dashboard/DashboardCharts.spec.ts tests/components/dashboard/ChartResourcesHistory.spec.ts tests/components/dashboard/ChartJobsHistory.spec.ts`

## 本轮：用户分析页头部、时间窗控件与分析区布局已压缩

本轮继续收口用户详情页中的分析区域，重点解决头部冗余、时间窗不明显和 `Submission Activity` 视觉空白过多的问题：

- `Analysis Window` 顶部说明已压缩为更短的工作区说明，不再重复展示全名和群组等低优先级身份信息。
- 时间范围选择器已提升为单独的高对比控制块，首屏更容易识别和操作。
- 时间范围控件外层额外卡片边框已移除，避免按钮区域出现三层嵌套描边。
- `Submission Activity` 与 `Usage Profile` 已收敛为更紧凑的双栏分析区，右侧 usage 指标改为网格布局，减少纵向拉伸和大片空白。
- `Usage Profile` 已移除低优先级的 `Busiest Tool` 卡片，右侧恢复稳定的 2x2 指标网格，与左侧图表区域底部对齐。
- `Completed Job Tool Analysis` 已去掉表格外层冗余 card，工具行下方重复的内存摘要也已移除，只保留表格主信息。
- 本轮只调整用户分析视图的布局和可读性，不改变时间窗查询、用户分析接口和数据口径。

本轮新增验证：

- `cd frontend && pnpm vitest run tests/views/UserAnalysisView.spec.ts tests/views/UserView.spec.ts`

## 本轮：Dashboard `stats` / `metrics` 已补 `partition` 接口契约与 Gateway 透传验证

本轮在不改动 collector、metrics DB 核心实现和 `slurmrestd` 核心实现的前提下，补齐了 Dashboard 相关接口对 `partition` query 的契约支持：

- Agent `GET /v<agent-version>/stats` 现在会读取 `partition` query，并基于该分区返回的作业和节点重新聚合：
  - `jobs.running`
  - `jobs.total`
  - `resources.nodes`
  - `resources.cores`
  - `resources.memory`
  - `resources.memory_allocated`
  - `resources.memory_available`
  - `resources.gpus`
- Agent `GET /v<agent-version>/metrics/<metric>` 现在会读取 `partition` query，并在底层 `metrics_db.request(...)` 签名支持时继续透传。
- 为兼容尚未升级到 `partition` 参数的旧 `metrics_db.request(metric, range)` 实现，Agent 会自动回退到旧调用方式，避免多 Agent 并行开发或不同合并顺序下直接抛出 `TypeError`。
- Gateway 现有统一 query string 透传逻辑已经满足需求，因此本轮没有新增业务分支，只补了 `/stats` 与 `/metrics/<metric>` 的透传回归测试。

本轮新增验证：

- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent.py slurmweb/tests/views/test_agent_metrics_requests.py slurmweb/tests/views/test_gateway.py`

## 本轮：补充 `slurm-web-agent` 缺少 `sqlalchemy` 时的系统包部署说明

本轮补充了一个现场排障结论，避免在 RHEL 系系统 Python 环境下重复踩坑：

- 当 `slurm-web-agent.service` 通过 `/usr/bin/slurm-web` 启动，并加载 `/usr/lib/python3.x/site-packages/slurmweb/...` 时，`pip install SQLAlchemy` 已显示成功，并不等于 systemd 服务就一定能导入该模块。
- 现场曾出现 `pip` 把 `SQLAlchemy` 安装到 `/usr/local/lib64/python3.9/site-packages`，但 agent 运行时仍报 `ModuleNotFoundError: No module named 'sqlalchemy'`。
- 针对这类通过系统 Python / RPM 部署的节点，文档现已明确优先使用 `dnf install -y python3-sqlalchemy`，把依赖安装到与 systemd 服务一致的系统包路径中。
- 部署指南已同步补充安装后执行 `systemctl reset-failed`、`systemctl restart` 与 `journalctl` 验证的最小排障步骤。
- 同时把这条经验上升为仓库约定：后续新引入包默认要求优先提供 `dnf install -y <package>` 方案，并同步更新正式文档，而不是只留下 `pip install`。

## 本轮：用户详情页已完成作业分析改为表格主视图并优化首屏行为

本轮继续收敛用户详情页 `Completed Job Tool Analysis` 的展示方式和首屏行为：

- 用户详情页默认先展示 `User Analysis / Submission and tool analytics`，再展示 `User Profile / Account associations and limits`。
- `Completed Job Tool Analysis` 已去掉重复标题层级和图表区，改为直接展示工具明细表。
- 明细表按工具展示已完成作业的：
  - 作业数量与占比
  - 平均内存
  - 最大内存
  - 中位数内存
  - 平均运行时间
  - 平均 CPU 使用
- 内存字段命名统一为 `Max Memory`，不再使用 `Peak Memory`。
- 明细表按作业数量优先排序，并补充体量条、排名编号和工具级资源摘要，便于快速比较不同工具的资源特征。
- 用户分析时间窗继续同步到 URL query；浏览器刷新时，如果 URL 已带时间窗参数，分析卡片会在首屏立即加载数据，不再出现空白。

## 本轮：`job_snapshots` 资源字段补齐从入库前迁移到日聚合前

本轮把 `job_snapshots` 资源字段补齐责任从快照采集阶段迁移到了用户工具日聚合前：

- 快照采集入库时不再为缺少 `used_memory_gb` 或 `used_cpu_cores_avg` 的终态作业同步调用 Slurm REST detail；原始 `job_snapshots` 先按采集结果落库。
- 后台当前日聚合、`slurmweb/scripts/rebuild-user-tool.py` 和 `slurmweb/scripts/repair-user-tool-daily-stats.py` 在真正统计前，会先扫描目标日期范围内 `COMPLETED` / `FAILED` 且资源字段缺失的终态作业，并用 Slurm REST detail 预补齐资源字段。
- `FAILED` 作业只参与这一步资源补齐，不参与 `user_tool_daily_stats` 的 `jobs_count` 和资源均值统计。
- `jobs/history/detail` 仍保留单条按需 enrich；读取历史详情时仍可通过 `_maybe_enrich_record()` 补齐并持久化该记录的资源字段。
- 独立脚本 `slurmweb/scripts/backfill-job-snapshot-usage.py` 继续保留作专项补数工具；其默认扫描范围已扩展到 `COMPLETED` / `FAILED` 缺资源终态作业。
- 历史修复顺序已简化为直接执行 `rebuild-user-tool.py` 或 `repair-user-tool-daily-stats.py`；这两个脚本会自带预补齐，不再要求调用者先手工执行 backfill。

## 本轮：`user_tool_daily_stats` 重构为单计数字段并扩展内存统计

本轮完成了 `user_tool_daily_stats` 聚合链路重构，并把内存统计扩展落到后端、脚本和前端：

- 日表去掉了冗余样本数字段 `memory_samples`、`cpu_samples`、`runtime_samples`，仅保留 `jobs_count` 作为完成作业计数。
- 日表内存字段改为 `avg_memory_gb`、`max_memory_gb`、`median_memory_gb`；旧 `avg_max_memory_gb` 在接口层继续兼容输出。
- 所有写入日表的浮点指标现在统一保留两位小数，包括内存、CPU 和运行时间。
- 当天后台聚合、按范围修复脚本和全表重建脚本现在复用同一条“按 `submit_time` 当天范围读取 `COMPLETED` 作业，再在 Python 中按用户+工具分组”的聚合逻辑，避免口径再次漂移。
- 用户分析前端已增加 Average Memory、Max Memory、Median Memory 展示，工具级面板和图表同步改为使用新字段。
- 全表重建后，跨多天 `tools/analysis` 仍只读 `user_tool_daily_stats`：`jobs_count` 表示提交时间落在当天、状态为 `COMPLETED` 且 `used_memory_gb` 非空的作业数，平均内存按日表 `jobs_count` 加权，峰值内存取窗口最大值，中位数内存按日中位数加权近似。
- 日聚合内存样本只以 `used_memory_gb` 为准；`used_memory_gb` 为空的作业会被跳过，不再用 `usage_stats` 或 TRES fallback 代替该字段。
- `rebuild-user-tool.py` 支持 `--date 20260504 --user lizenghui --dry-run` 定位单日单用户；默认只输出查询、日摘要、聚合行和总预览这几类核心日志。

## 本轮：`rebuild-user-tool.py` 默认只输出核心聚合日志

本轮收口了 `slurmweb/scripts/rebuild-user-tool.py` 的默认日志量，避免全量历史重建时控制台被逐作业明细刷满：

- 脚本现在会按 `activity_date + user_id + tool` 逐条打印将写入 `user_tool_daily_stats` 的日聚合明细。
- 脚本逐日重建时会在聚合前把每条源行的 `activity_date` 固定为当前重建日期，确保写库日期就是该 UTC 日期的年月日。
- 每条日志会带 `date`、`user_id`、`username`、`tool`、`jobs_count`、内存指标、`avg_cpu_cores` 和 `avg_runtime_seconds`。
- 每个 UTC 日期会先输出当天扫描到的 `source_jobs` 和当天将写入的聚合行数，再输出聚合行日志。
- 每日摘要现在同时输出 `counted`、`skipped_memory`、`missing_identity`、`cpu_missing`、`runtime_missing`，其中 `skipped_memory` 表示 `used_memory_gb` 为空而未计入 `jobs_count` 的源作业数。
- 在真正删除旧表数据并写入新数据前，脚本还会打印一次全表预览摘要，包含日期范围、扫描天数、源作业数、待删除旧行数和待写入新行数。
- 默认不再打印每条源作业的 `user_tool_daily_stats job:` 诊断日志，只保留查询、日摘要、聚合行和总预览这几类核心日志。

## 本轮：用户工具日聚合改为按提交时间统计 `COMPLETED` 且内存非空作业

本轮修正了 `user_tool_daily_stats` 的日聚合统计失真，并补齐排障信息：

- 日聚合现在先按 `submit_time` 的 UTC 当天范围读取 `job_state = COMPLETED` 的作业。
- 读取后的作业在 Python 中按 `activity_date + user_id + tool` 分类，不在 `user_tool_daily_stats` 链路中使用数据库聚合。
- `jobs_count` 只统计 `used_memory_gb` 非空的作业；当前字段域假设是该值只会大于 `0` 或为空。
- `avg_memory_gb`、`max_memory_gb`、`median_memory_gb` 基于同一批内存样本计算。
- `avg_cpu_cores` 以 `jobs_count` 为分母，缺失或非法 `used_cpu_cores_avg` 按 `0` 计入。
- `avg_runtime_seconds` 同样以 `jobs_count` 为分母，缺失运行时间按 `0` 计入。
- `tools/analysis` 的跨天汇总仍以日表为准；`avg_cpu_cores` 只会合并仍然带有效 CPU 样本的日行。
- 后台聚合线程每轮刷新会记录扫描作业数、计入作业数、跳过数和写入行数，方便排查聚合结果为空或 CPU 样本缺失。
- 历史修复脚本 `slurmweb/scripts/repair-user-tool-daily-stats.py` 已同步新口径，可按日期范围重建旧数据。

## 本轮：AI 协作规则补充测试强制要求与单问题澄清方式

本轮补充了仓库级 AI 协作规则：

- 任何开发都必须完成与改动对应的测试；如果无法执行，必须明确说明阻塞、未验证范围和风险。
- 进入方案讨论或规划阶段时，AI 必须持续澄清关键设计分支与依赖关系，直到形成共享理解。
- 方案澄清要求改为一次只问一个问题，并同时给出推荐答案，避免多分支问题混在一轮里。

## 本轮：多需求输入要求先归类再处理，并在对话完成前完成本地提交

本轮继续收紧仓库级 AI 协作规则：

- 当用户一次提出多个需求、问题或 bug 时，AI 必须先自行整理、分类，再按主题分别处理。
- 提交前必须先检查工作区，区分当前主题改动与其他未确认改动；未经确认，不得把其他改动混入提交。
- 对已经确认属于当前主题的改动，AI 必须按规范拆分提交，并至少完成一次本地提交保证可追溯。
- 若某轮结束时仍无法完成本地提交，必须把未提交范围与风险写入 `docs/tracking/`。

## 本轮：AI 写接口 payload 收紧到与前端表单一致

本轮专门收紧了 AI 写接口最容易绕过前端表单约束的两条管理写链路：

- `account/update` 现在要求 AI payload 显式提交 `organization`，缺失时直接返回 `400`，不再把后端按 `description/name` 自动补值当作 AI 主流程。
- `qos/update` 现在要求 AI payload 显式提交 `max_submit_jobs_per_user`、`max_jobs_per_user`、`max_wall_duration_per_job`，缺失任一字段时直接返回 `400`。
- `association/update` 继续保留自动补 `cluster`，因为这属于路由上下文注入，不是前端表单漏填的业务字段。
- AI 接口目录说明和定向后端测试已同步更新，确保 AI 写链路与前端主表单契约一致。

本轮新增验证：

- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py slurmweb/tests/views/test_agent_operations.py`

补充修正：

- `AccountsView` 不再只依赖 `associations` 构建账户树，现改为以 `accounts` 为主数据源、`associations` 作为补充用户和限制信息。
- 因此新创建但尚未返回 account-level association 的账户，现在也会在前端账户列表中显示。
- 创建 account 时，`description` 现已改为前端显式必填字段。
- 创建成功后，账户页会主动刷新 `accounts` 与 `associations` 两条数据链，而不是继续等待后台轮询。

## 本轮：AI 对话页布局稳定性修复

本轮修复普通 AI 对话页的两个前端布局问题：

- `AssistantView` 的消息区和输入框现在固定收口在左侧同一列，输入框不再脱离对话区跑到整行底部，左侧聊天工作区可完整撑满可用宽度。
- 消息滚动区域改为稳定高度容器，发送消息、流式回复和右侧 `Execution trace` 更新时，不再把对话框整体向下挤动。
- `AssistantView` 右侧 `Execution trace` 现在只展示最近 5 条 tool call，避免长对话时轨迹列表无限增长挤占侧栏空间。
- 空对话态的快捷问题按钮改为贴底布局，但仍保持在消息区内部，不再影响整体对话面板位置。
- 前端单测新增布局结构回归检查，确保 composer 与 message scroller 继续同属左侧聊天列。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/AssistantView.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：QOS、Accounts 与 account-user association 写路径修复

本轮修复 SlurmDB 写路径中的三个管理操作问题，并统一 QOS 创建默认限制：

- `slurmrestd` QOS 写入会把轻量 payload 统一包装为 `{ qos: [...] }`，避免创建 QOS 时触发 `Missing required field 'qos'`。
- `slurmrestd` Accounts 写入会把轻量 payload 统一包装为 `{ accounts: [...] }`，避免创建 account 时触发 `Missing required field 'accounts'`。
- `QosView` 创建/编辑弹框会显式预填并要求提交 `MaxSubmitJobsPerUser=100`、`MaxJobsPerUser=10`、`MaxWallDurationPerJob=6-00:00:00`，walltime 输入使用 `days-hh:mm:ss` 并在前端转换为分钟。
- 后端对 QOS 常用限制的默认补值仅保留为兼容旧调用方的兜底，不再作为前端主流程依赖。
- account-user association 删除不再依赖 `DELETE` request body 作为 SlurmDB 删除条件，后端会把单条 association payload 转换为 `account/user/cluster` query 参数，避免删除条件被忽略后命中过宽范围。
- `AccountView` 删除 association 时只提交目标 `account` 与 `user`，不再携带空的 `qos/default` 字段。

本轮新增验证：

- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`
- `cd frontend && npx vitest run tests/views/QosView.spec.ts tests/views/AccountView.spec.ts tests/views/AccountsView.spec.ts tests/composables/GatewayAPI.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：节点状态编辑与共享表单重置修复

本轮修复节点编辑和共享操作弹窗的两个前端交互问题：

- `NodeView` 的节点状态编辑下拉框已补 `MIXED` 当前态展示，避免 mixed 节点打开编辑弹窗时缺少对应状态。
- `NodeView`、Resources 和节点状态 badge 现在会把 `['IDLE', 'DRAIN']` 明确展示为 `DRAINED`，不再和管理员提交的 `DRAIN` 动作混淆。
- `MIXED` 在编辑表单中只作为当前状态占位显示，不作为可提交的状态动作；实际可编辑动作仍保持 `DRAIN`、`RESUME`、`UNDRAIN`、`DOWN`、`IDLE`、`FAIL`、`FUTURE`。
- 节点编辑表单对 `DRAINED` 也只作为禁用的当前状态占位显示；实际可提交动作仍使用 `DRAIN`，由 Slurm 自行过渡到 `DRAINING` 或 `DRAINED`。
- 节点编辑下拉框现在只保留可提交动作，`Current node state` 改为独立 hint 展示，避免 idle 节点被旧的禁用占位逻辑误判成 `DRAINED` 并卡住动作选择。
- 共享 `ActionDialog` 不再在弹窗保持打开期间因为后台轮询刷新 `initialValues` 而重置用户已输入的表单内容。
- `ActionDialog` 现在只会在弹窗重新打开，或同一弹窗实例切换到另一种操作时重新初始化表单，避免 Accounts、QOS、Jobs、Node 等页面编辑时输入被后台刷新覆盖。

本轮新增验证：

- `cd frontend && npx vitest run tests/composables/GatewayAPI.spec.ts tests/components/resources/NodeMainState.spec.ts tests/components/operations/ActionDialog.spec.ts tests/views/NodeView.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：Resource、Jobs Filter 与用户工具聚合修正

本轮继续在现有资源、作业筛选和用户分析链路上做收口：

- `ResourcesView` 节点列表不再显示行尾 `Manage` / `Delete` 按钮，节点名称仍可点击进入详情。
- `NodeView` 详情页继续保留 Edit / Delete，Edit Node 的 `state` 改为下拉框，选项为 `DRAIN`、`RESUME`、`UNDRAIN`、`DOWN`、`IDLE`、`FAIL`、`FUTURE`。
- `ActionDialog` 增加 `select` 字段类型，支持通用操作弹窗渲染下拉选项。
- Jobs 用户筛选保留 `/users` 查询建议，同时支持直接输入用户名并点击 `Add username` 加入筛选；空值不添加，重复用户名不重复添加，添加后清空输入。
- 用户工具当天日聚合按 `activity_date + user_id + tool` 分组，只纳入 `COMPLETED` 作业。
- 日聚合只统计 `used_memory_gb` 非空的完成作业；`jobs_count` 语义为“具备显式内存统计的完成作业数”，CPU 缺失按 `0` 计入平均值。
- 后台按 `[user_metrics].aggregation_interval` 周期刷新当天日表时，会先删除当天旧 `user_tool_daily_stats` 行，再写入新的有效统计，避免旧的 `jobs_count > 0 / avg_* = 0` 脏行残留。
- `user/<username>/tools/analysis` 继续只读取 `user_tool_daily_stats`，跨多天按 `sum(day.avg * day.jobs_count) / sum(day.jobs_count)` 合并内存和 CPU 均值；旧日表中的 `0`、`NULL` 或其他非法资源均值不再继续贡献 `completed_jobs`、工具列表或资源均值。
- 当时间窗内没有任何有效资源对作业时，接口返回空工具列表，`totals.completed_jobs = 0`，资源均值为 `null`。
- 新增维护脚本 `slurmweb/scripts/repair-user-tool-daily-stats.py`，支持 `--start`、`--end`、可选 `--user` 和 `--dry-run`，用于按新口径从 `job_snapshots` 重建 `user_tool_daily_stats`。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/resources/ResourcesView.spec.ts tests/views/NodeView.spec.ts tests/components/operations/ActionDialog.spec.ts tests/components/jobs/UserFilterSelector.spec.ts`
- `npm --prefix frontend run type-check`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_user_analytics_store.py`

## 本轮：作业、账户用户、QOS 与历史作业展示优化

本轮继续在现有 Vue 页面和 Gateway/Agent 写路径上做增强，没有新增独立管理中心：

- 按操作语义统一按钮颜色：
  - 创建/提交/主要确认使用 `ui-button-primary`
  - 编辑/保存修改使用 `ui-button-warning`
  - 删除/取消作业等破坏性操作使用 `ui-button-danger`
  - 查看/返回/筛选/普通导航/弹窗关闭使用 `ui-button-secondary`
- `JobsHistoryView` 与 `JobHistoryView` 增加 `Live job` 入口，使用 Slurm `job_id` 跳转到实时作业详情 `/:cluster/job/:job_id`
- 历史作业页只提供跳转实时作业详情，不在持久化历史记录上直接执行编辑或取消
- AI 单作业查询提示已明确：`jobs/history` 是持久化历史数据，字段与实时作业详情接近；已完成作业可保留 `used_memory_gb` 最大内存和 `used_cpu_cores_avg` 平均 CPU 使用核心数
- 查询单个作业时，如果实时 `job` 不足或作业已完成，AI 会被引导补查 `jobs/history` 或 `jobs/history/detail`
- `UserView` 编辑用户弹框支持提交 `default_qos` 和逗号分隔的 `qos`
- `AccountView` 的 `User Associations` 区域支持 `Add user`、行级 `Edit QOS` 和行级 `Delete`
- 前端 Gateway 新增 `delete_association(cluster, payload)`，复用现有 `DELETE /agents/:cluster/associations`
- `ClusterAssociation` 类型新增可选 `default.qos`
- `ClusterAnalysis` 内存容量详情改为 GB 展示，评分和百分比仍使用原始 MB 数值
- `JobsView` 与 `JobView` 的作业编辑弹框新增 `Memory per CPU (MB)`，填写正整数时向 Slurm REST 提交 `memory_per_cpu` 对象，空值不发送

本轮新增验证：

- `cd frontend && npx vitest run tests/views/JobsView.spec.ts tests/views/JobView.spec.ts tests/views/JobsHistoryView.spec.ts tests/views/JobHistoryView.spec.ts tests/views/AccountView.spec.ts tests/views/UserView.spec.ts tests/composables/GatewayAPI.spec.ts tests/composables/ClusterAnalysis.spec.ts tests/components/operations/ActionDialog.spec.ts`
- `npm --prefix frontend run type-check`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py slurmweb/tests/views/test_agent_operations.py`

## 本轮：AI 审计、会话逻辑删除、复制操作与指标时间窗弹框

本轮围绕节点指标、用户分析和 AI 对话做交互与审计收口：

- 节点详情页 `Real Metrics` 支持点击按钮打开时间范围弹框
- 节点指标自定义窗口支持 `start` / `end`，精确到时分，并同步到 URL query
- 用户工具分析页改为与节点详情一致的时间范围按钮和弹框
- 时间范围弹框新增 `1 day`、`3 days`、`7 days`、`15 days`、`1 month` 快捷窗口
- 用户数据分析页移除了重复的用户名信息卡，LDAP 姓名、组和更新时间压缩到时间范围栏中
- 集群页与 Settings 页主内容区改为独立滚动区域，底部保留固定 `2rem` 浏览器边缘留白
- 用户分析的 `Submission Activity`、`Usage Profile` 与 `Completed Job Tool Analysis` 继续共享同一时间窗
- 用户详情分析页已将原 `Tool Analysis` 与 `Top Tools` 合并为一个 `Completed Job Tool Analysis` 栏目，集中展示已完成作业的工具维度数据分析
- `user/<username>/tools/analysis` 只按时间窗覆盖的 UTC 日期读取 `user_tool_daily_stats` 并汇总返回工具分类统计；查询多天时，当前实现按 `jobs_count` 加权合并多天日表的内存与 CPU 均值，请求路径不实时扫描 `job_snapshots` 或 SlurmDB
- 后台用户工具日聚合按 `[user_metrics].aggregation_interval` 周期更新当天 UTC 自然日统计，并与 `slurmweb/scripts/repair-user-tool-daily-stats.py` 维护脚本复用同一套聚合函数，保持工具归类、空值过滤和插入口径一致
- `user_tool_daily_stats` 当前使用 `jobs_count + avg/max/median memory + avg_cpu_cores + avg_runtime_seconds` 保存日聚合；内存与 CPU 跨日返回按每日 `jobs_count` 加权
- 用户分析资源统计明确按已完成作业计算：
  - 平均内存：当前日聚合只使用 `used_memory_gb` 非空的样本，无有效样本时不写入日表行
  - 平均运行时间：`end_time - start_time`，返回小时与兼容秒字段
  - 平均 CPU 核数：以 `jobs_count` 为分母，缺失或非法 `used_cpu_cores_avg` 按 `0` 计入
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

- 后端 `Python 3.9`
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

- `policy.yml` / `policy.ini` 已移除 6 个旧动作配置入口：
  - `view-own-jobs`
  - `edit-own-jobs`
  - `cancel-own-jobs`
  - `roles-view`
  - `roles-manage`
  - `manage-ai`
- `view-ai` 保留为 `ai:view:*` 兼容别名
- `GET /permissions.actions` 与 `GET /access/catalog.legacy_map` 不再暴露这 6 个无效旧动作
- 管理端角色页不再派生或展示这 6 个无效 compatibility actions；`view-ai` 继续按 `ai:view:*` 兼容
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

- `cache-view` -> `admin/cache:view:*` + `admin/ldap-users:view:*`
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
- `Users`
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
- `/settings/ldap-cache` 与 `/settings/ldap-users` -> `/:cluster/admin/ldap-users`

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

当前兼容层只保留少量仍在使用的动作映射；`view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage`、`manage-ai` 已不再作为正式配置入口或 API 回显动作，`view-ai` 继续兼容映射到 `ai:view:*`。

## 本轮：删除 6 个无效旧动作兼容并保留 `view-ai`

- 后端 `roles.actions` 归一化现在只保留 `view-ai` 与 `admin-manage` 的权限补齐
- `view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage`、`manage-ai` 会在角色归一化时直接丢弃，不再迁移到 `roles.permissions`
- 前端运行时补回 `view-ai -> ai:view:*` fallback，确保旧 `actions[]` 集群仍能正确显示 `AI` 页面入口
- `admin/ldap-users:edit:*` 已正式定义为 LDAP 用户缓存维护动作，不表示修改 LDAP 源数据

## 2. Access Control 页面改为资源矩阵

`Settings > Access Control` 已从 action 复选框切换为目录驱动的权限矩阵：

- 页面通过 `GET /access/catalog` 获取全部资源目录
- 角色编辑以 `permissions[]` 为主
- 同时展示兼容 `actions[]`
- 支持首次空角色表自动预置 `user`、`admin`、`super-admin`

## 3. Agent 能力开关收敛

系统当前的业务能力按基础依赖自动推导：

- 数据库开启后，自动提供：
  - Users
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
- 默认 `user` 角色现已包含 `ai:view:*`，普通用户可见并可使用 `AI`
- 没有任一 `admin/*` 或 `*:*:*` 权限的普通用户不会看到 `Admin` 入口，也不能进入 `/:cluster/admin/*`
- `/:cluster/admin/cache` 使用 `admin/cache:view|edit:*`
- `/:cluster/admin/ldap-users` 使用 `admin/ldap-users:view|edit:*`

## 本轮：LDAP cache 管理页已统一改名为 `Users`

本轮把 LDAP 用户缓存的正式前端命名、路由与权限资源统一到 `Users` 口径，同时保留低风险兼容：

- 正式管理页改为 `/:cluster/admin/ldap-users`
- 兼容 settings 入口改为 `/settings/ldap-users`
- 旧 `/settings/ldap-cache` 与 `/:cluster/admin/ldap-cache` 继续保留为重定向兼容入口
- 正式权限资源改为 `admin/ldap-users:view|edit:*`
- 后端与前端权限归一化继续兼容历史 `admin/ldap-cache:*` 角色规则，不会让旧角色立刻失效

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/router/AdminRoutesContract.spec.ts tests/composables/GatewayAPIAdminContract.spec.ts tests/composables/GatewayAPI.spec.ts tests/stores/runtime.spec.ts tests/components/MainMenu.spec.ts tests/components/settings/SettingsTabs.spec.ts tests/components/settings/SettingsTabsAIContract.spec.ts tests/views/settings/SettingsLdapCache.spec.ts`
- `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py slurmweb/tests/views/test_agent.py`
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
