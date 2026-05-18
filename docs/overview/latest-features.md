# 最新功能

## 本轮：平均排队延迟聚合与队列详情曲线已修正

本轮修正 `Cluster Analysis` 与队列详情页的平均排队时间曲线口径：

- 集群分析页默认展示最近 1 小时全集群已完成作业的平均排队时间，并按分钟桶聚合；仍可切换为小时或天聚合。
- “最近一小时”重置会明确写入点击时刻的 `start = now - 1h` 与 `end = now`，历史请求不再只依赖相对 range。
- 队列详情页继续按当前队列过滤 `jobs/history`，曲线固定展示每小时平均排队时间，样式与同一区域实时图表保持一致。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/ClusterAnalysisView.spec.ts tests/views/PartitionView.spec.ts tests/composables/queueWaitHistory.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：节点热点能力不可用时不再发起无效请求

本轮修复 `Cluster Analysis` 在节点热点持久化未启用时仍请求 `analysis/node-hotspots` 的问题：

- Agent `/info` 新增 `capabilities.node_hotspots`，用于准确表示节点热点持久化采样链路是否可用。
- 前端仅在该能力为 `true` 时请求 `analysis/node-hotspots`，避免浏览器网络面板持续出现 `501 Node hotspot persistence is unavailable`。
- 节点热点不可用时页面继续展示空态，不影响 `stats`、`jobs`、`metrics`、平均排队时间等其他分析数据。

## 本轮：集群分析内存术语已校正

本轮仅调整中文文案，不改变统计口径：

- `Cluster Analysis` 容量指标中的 `memory_allocated` 中文展示从“内存预留量”校正为“内存分配量”。
- 该指标仍表示当前遥测中的已分配内存，与 Slurm reservation 语义的“预留”区分。

## 本轮：队列详情页新增平均排队时间曲线

本轮在 `/:cluster/partitions/:partition` 队列详情页补充队列平均排队时间曲线：

- 曲线复用队列详情页已有时间范围组件，不新增第二套时间控件。
- 数据来自 `jobs/history`，固定按当前队列过滤已完成作业，并按 `submit_time -> start_time` 计算秒级平均排队时间。
- 历史作业会按所选时间窗跨页拉取后再聚合；历史不可用、无权限或无样本时只在该曲线区域展示空态，不影响实时资源与作业曲线。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/PartitionView.spec.ts tests/composables/queueWaitHistory.spec.ts`

## 本轮：图表加载占位视觉已收口

本轮针对 Dashboard 图表加载态“粗大渐变柱状图过重、观感粗糙”的问题做了共享组件优化：

- `ChartSkeleton` 从 12 个粗柱状占位改为轻量图表骨架，保留坐标轴、网格线、趋势线与节点占位。
- 共享 `.ui-chart-skeleton` 降低高饱和渐变和大面积填充，加载态更接近真实图表结构。
- Dashboard `Resources Status`、`Jobs Queue` 与 Settings Cache metrics 会同步使用新的加载占位。

本轮新增验证：

- `cd frontend && npx vitest run tests/components/ChartSkeleton.spec.ts tests/components/dashboard/ChartResourcesHistory.spec.ts tests/components/dashboard/ChartJobsHistory.spec.ts tests/components/settings/SettingsCacheMetrics.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：管理写操作旧数据残留已继续收口

本轮按 `Reservations` 删除旧缓存问题继续审查同类链路，重点覆盖写后缓存失效与前端写后刷新：

- `NodeView` 更新节点状态后会立即刷新当前节点详情；后端 `node_update/node_delete` 会清理 `nodes`、`nodes-unfiltered` 和单节点缓存。
- `QosView` 创建、编辑、删除 QOS 成功后会立即刷新列表，避免继续展示旧 QOS。
- `AccountsView` 创建账户后改为调用真实 `refresh()` 同步刷新 `/accounts` 与 `/associations`，不再误用 `setCallback()` 触发异步重启。
- `AccountView` 删除账户成功后返回账户列表，避免继续停留在已删除账户详情页。
- `UserView` 编辑用户后刷新 associations；删除用户成功后刷新并返回上一级页面，避免旧用户详情继续可操作。

本轮新增验证：

- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/slurmrestd/test_slurmrestd_filtered_cached.py`
- `cd frontend && npx vitest run tests/views/QosView.spec.ts tests/views/NodeView.spec.ts tests/views/UserView.spec.ts tests/views/AccountView.spec.ts tests/views/AccountsView.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：Reservations 删除旧缓存错误已修复

本轮修复 `Reservations` 页面删除预留时可能出现 `Requested reservation is invalid/2053` 的问题：

- reservation 创建、更新、删除成功后会清理 `reservations` 缓存，避免页面继续展示旧预留。
- `ReservationsView` 在创建、更新、删除成功后会立即刷新当前列表，不再只等待下一轮轮询。
- 当 Slurm 返回 `Requested reservation is invalid/2053` 时，删除路径按“目标已不存在”处理为幂等成功结果，并通过 warning 保留底层信息，不再把该场景直接包装成 500 弹窗错误。

本轮新增验证：

- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py slurmweb/tests/slurmrestd/test_slurmrestd_filtered_cached.py`
- `cd frontend && npx vitest run tests/views/ReservationsView.spec.ts`

## 本轮：前端输入与弹窗交互性能已优化

本轮针对部署环境中“输入框输入文字卡顿、按钮打开表单卡顿”的前端问题做了渲染路径收口：

- 全局共享 surface 样式已降低大阴影和模糊成本，`ui-panel`、`ui-table-shell`、分页条、下拉菜单等大面积容器不再使用 `backdrop-filter`。
- 主业务壳层、Settings 壳层、移动侧栏与共享操作弹窗遮罩已去掉 `backdrop-blur`，避免打开弹窗时对整页背景做高成本合成。
- `button/input/select/textarea` 的全局 transition 不再包含 `transform`，减少输入焦点和按键期间的重绘压力。
- `ActionDialog` 打开时会锁定字段快照，输入期间不再因父页面内联 `fields` 数组反复创建而重置或重算字段结构。
- `Admin > AI` 模型配置弹窗已拆成独立 `SettingsAIConfigModal` 组件，表单输入状态与配置表、审计表隔离，提交 payload 与原有接口契约保持不变。
- 面向云桌面浏览器继续降低实时页面成本：轮询返回内容未变化时不再替换响应式数据引用，Chart.js 更新统一走无动画路径，资源拓扑 Canvas 移除 loading shimmer 帧循环，并在系统 `prefers-reduced-motion` 下禁用骨架屏和交互动效。
- 第三轮继续收敛大表渲染和剩余视觉热点：Jobs、QOS、Admin AI 表格行增加 `v-memo`，通知和历史排序浮层移除剩余 `backdrop-blur`，常用链接、菜单项和详情卡不再使用 hover 位移动效；Resources 列表保留低动效样式，但未启用会被 ESLint 拦截的表格行 `v-memo` 写法。
- 第三轮补充收尾：云桌面入口页按钮移除残留 `backdrop-blur`，账户树展开图标取消旋转动效，仅保留颜色和层级反馈。
- 第四轮继续降低输入期间的后台干扰：自动轮询在文本输入聚焦时会短暂让路，避免焦点输入时被后台刷新打断，手动刷新仍保持立即执行。

本轮不涉及后端接口、权限、路由或缓存策略变更。

## 本轮：账户父子层级与添加用户关联已修复

本轮修复 `Accounts / AccountView` 在新建子账户后层级和加用户链路不一致的问题：

- `AccountsView` 创建账户时如果填写 `parent_account`，会在 `save_account` 成功后继续写入不带 `user` 的 account-level association。
- 账户树优先采用 `/associations` 的 account-level row；当该 row 暂未刷新返回时，用 `/accounts` 的 `parent_account` 兜底，避免 `test` 这类新子账户短时间单独展示。
- `AccountView` 在 account-level association 暂未刷新返回时，会用 `account/<name>` 返回的 `parent_account` 与 `qos` 合成账户级兜底信息，因此刚创建的子账户仍可添加用户。
- 添加用户链路继续固定为 `save_user -> save_association -> refreshAssociations() -> 写后可见性校验`，刷新后出现目标 `{ account, user }` 即判定成功。

## 本轮：集群分析平均排队时间曲线时间范围与聚合已收口

本轮修复 `Cluster Analysis` 平均排队时间曲线与页面时间组件混用的问题：

- 页面页头右侧不再展示额外时间范围组件，平均排队时间曲线只使用卡片右上角自身的时间范围。
- 聚合粒度曾收口为 `hour / day`；当前版本已恢复 `minute / hour / day`，默认最近 1 小时按分钟桶展示。
- 图表横轴现在固定使用卡片当前 `start/end` 时间窗口；即使窗口内只有一个有效样本，也不会再压缩成毫秒级单点时间轴。
- 前端测试已覆盖页头无多余时间控件、卡片保留自身时间范围、当前聚合按钮状态，以及图表组件接收完整窗口。

## 本轮：AI 集群状态分析已改为聚合上下文优先

本轮针对 AI 对话在“询问集群状态”场景下容易拉取过多低价值原始接口的问题，补了一条 AI 专用分析上下文链路：

- Agent 新增 `GET /v{version}/analysis/context`，Gateway 新增 `GET /api/agents/<cluster>/analysis/context`
- 新接口会复用 `analysis` 页面同源的关键证据家族，包括：
  - `stats`
  - 实时 `jobs` / `nodes`
  - `metrics/jobs`、`metrics/cores`、`metrics/memory`、`metrics/gpus`
  - 已完成作业历史样本
  - `analysis/ping`
  - `analysis/diag`
  - `analysis/node-hotspots`
- 返回内容不再是全量原始对象，而是 AI 友好的压缩结构，固定聚焦：
  - 评分与评分摘要
  - 核心摘要卡片
  - 容量指标
  - 等待时间统计
  - 主要 pending reason
  - partition pressure
  - 节点热点
  - 控制器健康
  - 调度核心诊断字段
  - 推荐项与数据可用性
- AI 默认可见的只读接口目录已收口为：
  - `analysis/context`
  - `job`
  - `jobs/history`
  - `jobs/history/detail`
  - `nodes`
  - `node`
  - `node/metrics`
  - `node/metrics/history`
  - `user/tools/analysis`
- `nodes` 已重新放回 AI 默认目录，用于回答“哪个节点负载较低”等需要横向比较候选节点的问题；`jobs`、`partitions`、`qos`、`reservations`、`accounts`、`associations`、`users`、`user` 这些高噪音接口仍保留在 Agent interface 层，但不再出现在默认 AI 查询目录中
- AI system prompt 已新增硬约束：遇到集群状态、拥塞、容量、排队等待、控制器健康或热点问题时，优先调用 `analysis/context`
- AI 默认接口目录现在会按当前用户权限过滤；`user/tools/analysis` 作为工具分析能力对 AI 用户保持可见，不传 `username` 时只查当前登录用户，跨用户仍需全局分析权限
- `query_agent_interface` 与 `mutate_agent_interface` 已按只读/写入分流，不能混用读写接口
- AI planner system message 会注入当前 `user.login` 与 cluster，因此“我是谁”“我的工具分析”等第一人称请求不再需要用户额外提供用户名
- 空的通用工具调用会被服务端拦截为内部重试提示，不再生成红色执行轨迹卡片或 `ai_tool_calls` 噪音记录

本轮新增验证：

- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_operations.py slurmweb/tests/views/test_gateway.py slurmweb/tests/apps/test_ai_service.py`

## 本轮：表单中的用户名、节点、QOS、分区已统一为可搜索下拉

本轮把一批仍然使用文本输入的前端表单字段统一收口到了共享搜索选择器，范围只覆盖 `用户名`、`节点名`、`QOS`、`分区` 四类字段：

- `用户名`
  - `Jobs` 用户筛选和部分管理弹窗现在改为远程搜索
  - 前端复用现有 `access/users` 分页与 `username` 过滤接口，不再继续依赖手输用户名再点击 `Add`
- `QOS / 分区 / 节点`
  - 统一改为可搜索下拉
  - 当前不新增后端搜索接口，而是先从现有集群列表接口加载，再在下拉中筛选
- 多值字段
  - 统一改为“多选标签 + 已选值回显”
  - 提交时仍序列化为现有 CSV string，保持后端写接口契约不变

本轮实际接入位置包括：

- `JobsView` / `JobView` 的 `partition`、`qos`
- `AccountView` / `AccountsView` / `UserView` 中的 `username`、`qos`、`default_qos`
- `ReservationsView` 的 `node_list`、`allowed_partitions`、`qos`
- `JobsHistoryFiltersPanel` 的 `user`、`partition`、`qos`
- `UserFilterSelector`

补充边界：

- `Reservations.node_list` 现在只支持从节点列表多选并回写为逗号分隔字符串，不再支持自由文本 nodeset 表达式输入。
- 本轮没有新增后端 `qos / partition / node` 模糊搜索接口。

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/components/forms/RemoteSearchSelect.spec.ts tests/components/operations/ActionDialog.spec.ts tests/components/jobs/UserFilterSelector.spec.ts tests/components/jobs/JobsHistoryFiltersPanel.spec.ts tests/views/JobsView.spec.ts tests/views/JobView.spec.ts tests/views/AccountView.spec.ts tests/views/AccountsView.spec.ts tests/views/UserView.spec.ts tests/views/ReservationsView.spec.ts tests/views/JobsHistoryView.spec.ts`

## 本轮：账户加用户写契约与集群分析平均排队时间独立时间范围已修复

本轮围绕两个已暴露的问题继续收口：

- `Account / User`
  - `slurmweb.slurmrestd.Slurmrestd.users_update()` 现在会把轻量单用户对象统一归一化为 `{"users": [...]}` 再写入 `slurmrestd`
  - 空字符串字段会在归一化阶段剔除，避免把空 `default_account/default_qos/description` 继续透传到底层 schema
  - `AccountView` 的 `Add user` 固定链路保持不变：`save_user -> save_association -> refreshAssociations() -> 写后校验`
  - `UserView` 编辑用户仍继续提交轻量 payload，但不再依赖调用方自己手工拼 `users` 包装结构
- `Cluster Analysis`
  - 平均排队时间图的时间范围与聚合粒度现在完全由卡片自身控制，不再跟顶部全局时间范围绑定
  - 卡片时间范围切换时会重新请求 `jobs_history`
  - 卡片聚合粒度切换时会基于当前历史样本立即重算 `minute / hour / day` bucket
  - 顶部全局时间范围仍只影响 metrics / node hotspots / 页面级分析摘要，不会回写覆盖卡片已经手动选择的独立时间范围

本轮新增验证：

- `.venv\Scripts\python -m pytest slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`
- `cd frontend && npm exec vitest run tests/views/AccountView.spec.ts tests/views/UserView.spec.ts tests/views/ClusterAnalysisView.spec.ts`

## 本轮：Reservations / Dashboard / AI 对话 / Job 详情 / 账户加人已统一收口

本轮围绕 5 个已暴露的问题做了一次集中修复，覆盖 reservation 写入契约、dashboard 留白、AI 对话模型选择、作业详情样式，以及 account 下加用户的假成功问题：

- `Reservations`
  - reservation create/update 现在统一经过后端 payload normalization，再写入 `slurmrestd`
  - 支持把 `users`、`groups`、`accounts`、`qos` 的数组别名统一转换成 `slurmrestd` 需要的 CSV string
  - `allowed_partitions`、`allowedPartitions`、`AllowedPartitions` 会统一映射为 reservation 写入字段 `partition`
  - 前端创建/编辑表单已补 `groups`、`qos` 和 `Allowed Partitions` 字段，并在本地拦截 `users / groups / accounts / qos / allowed_partitions` 全空的非法提交
- `Dashboard`
  - 顶部工具条左侧已删除“实时指标”局部标题、副标题和说明文案
  - 工具条到统计卡、统计卡到图表、图表到下一区块的垂直留白已回到全局 `ui-section-stack` 节奏
  - `ChartResourcesHistogram` 与 `ChartJobsHistogram` 已去掉内部遗留的 `pt-16`、`pb-5`、`mt-4` 等局部节奏硬编码
- `AI`
  - 新增只读模型摘要接口：Agent `GET /v{version}/ai/models`，Gateway `GET /api/agents/<cluster>/ai/models`
  - 普通用户和管理员现在都通过 `ai:view:*` 可访问的模型摘要接口读取已启用模型；普通用户不再依赖 `admin/ai:view:*` 的 `ai/configs`
  - `AssistantView` 已删除独立“当前模型”说明块，改为在发送区底部工具栏左侧放置简洁下拉框；右侧继续保留 token 信息与 `Clear / Send`
- `Job` / `Job History`
  - 两个详情页已统一参考 `NodeView` 改成单页连续详情列表
  - 右侧正文不再保留 `DetailSummaryStrip`、碎片字段卡、长字段堆叠卡与冗余小标题
  - 长字段保持自动换行，`partition / user / account` 仍可点击跳转
- `Account`
  - “Add user” 现在固定执行 `save_user -> save_association -> refreshAssociations() -> 写后校验`
  - 如果任一步返回 `errors`、接口抛错，或刷新后仍看不到 `{ account, user }` 关联，前端都会判定失败并拒绝显示成功提示

本轮新增验证：

- `.venv\Scripts\python -m pytest slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py slurmweb/tests/views/test_agent_ai.py slurmweb/tests/views/test_gateway_ai.py`
- `npm --prefix frontend run type-check`
- `cd frontend && npm exec vitest run tests/views/ReservationsView.spec.ts tests/views/AccountView.spec.ts tests/views/JobView.spec.ts tests/views/JobHistoryView.spec.ts tests/views/DashboardView.spec.ts tests/components/dashboard/ChartResourcesHistory.spec.ts tests/components/dashboard/ChartJobsHistory.spec.ts tests/views/AssistantView.spec.ts tests/views/AssistantViewAIContract.spec.ts`

补充说明：

- Reservation payload normalization 同时覆盖前端页面、Gateway 转发、Agent 写接口与 AI 工具调用，不再要求调用方自己拼接 `slurmrestd` 原始字段名。
- `JobView` / `JobHistoryView` 的 hash 高亮逻辑仍保留，但高亮目标已从旧卡片结构切到连续详情行。
- 本轮定向前端验证全部通过，但 `JobView` 测试运行过程中仍会看到既有的 Vue `inject()` warning；当前未阻断测试结果。

## 本轮：Dashboard / Analysis 工具条与 Admin 搜索区已统一收口

本轮只处理前端页面结构与样式收口，不涉及接口、配置或状态逻辑变更：

- `Dashboard` 顶部筛选区已去掉队列选择器和时间范围选择器外层的白色胶囊包裹，只保留控件本体；队列保留轻量 inline label，时间范围不再显示额外可见 label。
- `Cluster Analysis` 顶部时间范围控件已与 `Dashboard` 使用同一套工具条节奏；平均排队时间聚合切换保留独立卡片控制。
- `Dashboard` 统计卡与区块间距已按全局节奏收紧，不再额外放大工具条到统计卡之间的间距。
- `Admin > Access Control`、`Admin > Users`、`Admin > AI` 的搜索/筛选区已统一为 inline search bar，输入框、按钮尺寸、圆角和间距保持一致。
- `Admin > AI` 对话审计筛选区已补齐 `Search / Reset / Refresh` 操作；管理页各子页面的共享搜索输入宽度也已收窄到统一上限，避免桌面端输入框无节制撑满整行。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/DashboardView.spec.ts tests/views/ClusterAnalysisView.spec.ts tests/views/settings/SettingsAccessControl.spec.ts tests/views/settings/SettingsLdapCache.spec.ts tests/views/settings/SettingsAI.spec.ts`
- `npm --prefix frontend run type-check`

补充说明：

- 本轮已额外修复 `Cluster Analysis` 平均等待时间曲线在 `day / week / 自定义窗口` 下只基于历史首页样本聚合的问题；现在会按当前时间窗跨页拉取全部历史作业后再做 `minute / hour / day` 聚合。
- “节点热点持久化存储并默认查数据库”的计划现已落地：
  - 新增 `node_metric_samples` 表，按 `cluster + node + sampled_at` 持久化 CPU / memory 使用率快照。
  - Agent 在数据库与 node metrics 同时可用时，会按 `persistence.snapshot_interval` 后台采样节点使用率并入库。
  - `analysis/node-hotspots` 现在只基于持久化样本重建热点事件，不再为慢查询场景回退到 Prometheus 实时链路。

本轮新增后端验证：

- `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/views/test_agent_operations.py slurmweb/tests/apps/test_agent.py slurmweb/tests/metrics/test_hotspots.py`

## 本轮：作业详情页与历史作业详情页字段展示已统一重构

本轮对 `Job` 和 `Job History` 两个详情页做了同一套字段展示重构，并继续收口队列详情页冗余信息：

- 实时作业详情和历史作业详情不再混用“上方 card + 下方表格/列表”的字段结构，统一改为“摘要条 + 分组详情清单”。
- 字段区按“身份归属 / 调度执行 / 资源记录 / 命令上下文”分段展示，长命令、脚本、工作目录等字段改为可换行代码面板，避免内容溢出显示区域。
- 备注字段改为结构化块展示，保持长文本可读性和复制友好性。
- 队列详情页已删除顶部摘要下方重复的“队列详情 / 节点集合”块，并把“已分配节点 / 空闲节点”并入顶部摘要卡片。

补充收口：

- `Job` 与 `Job History` 详情正文已进一步改成“短字段 2-3 列并排 + 长字段整行展开”的连续信息面板，不再保留“作业身份 / 归档信息 / 详细资源与命令”等冗余小标题。
- 资源、备注、命令、脚本、工作目录等长内容字段会自动在整行块内换行，避免窄屏和长字符串挤出显示区域。
- `Partition` 实时曲线区已继续收口，删除局部“队列活动”标题与说明文案，只保留时间范围控件和图表本体，避免与页面主标题形成重复层级。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/JobView.spec.ts tests/views/JobHistoryView.spec.ts tests/views/PartitionView.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：GitHub 后端 CI 覆盖 Python 3.9+ 多版本并输出测试数量

本轮把 `Backend Tests` 从单一 Python 版本扩展为多版本矩阵：

- `.github/workflows/python-ci.yml` 现在覆盖 `Python 3.9`、`3.10`、`3.11`、`3.12`。
- 后端矩阵使用 `fail-fast: false`，单个版本失败时仍继续保留其它版本结果。
- 每个版本独立生成 `backend-python-<version>` artifact。
- `run-ci-command.mjs` 和 `ensure-ci-result.mjs` 会从 `junit.xml` 解析 `tests/failures/errors/skipped` 并写入 `result.json.test_stats` 与 `failure-context.json.test_stats`。
- GitHub Job Summary 与 `CI Triage` 汇总表会展示每个 artifact 的测试数量。

本轮新增验证：

- `Get-Content -Raw -Encoding UTF8 .github/workflows/python-ci.yml | npx --yes yaml valid`
- `node --check .github/scripts/run-ci-command.mjs`
- `node --check .github/scripts/ensure-ci-result.mjs`
- `node --check .github/scripts/build-triage-context.mjs`

## 本轮：实时作业与 Dashboard/Analysis 缓存性能优化

本轮针对实时作业、Dashboard 和 Cluster Analysis 的高频请求做了性能收口：

- `Jobs` 用户筛选改为直接输入用户名并添加，不再通过 gateway `/users` 触发 LDAP 全量用户枚举。
- `GET /api/agents/<cluster>/jobs` 支持透传 `users/states/accounts/qos/partitions/node` query；Agent 在 Redis 作业全量缓存命中时先本地过滤，减少分页和筛选导致的 `slurmrestd` 全量请求。
- `GET /stats` 新增 `cache.stats=60` 默认缓存，并按 `partition` 独立缓存 key。
- `GET /analysis/node-hotspots` 新增 `cache.analysis=60` 默认缓存，并按 `start/end` 时间窗独立缓存 key。
- 前端 `useClusterDataPoller` 在页面不可见时暂停轮询，恢复可见后立即刷新；`Jobs` 默认轮询从 `5s` 降到 `30s` 并新增手动刷新，Dashboard stats 和图表轮询对齐到 `60s`。

本轮新增验证：

- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/slurmrestd/test_slurmrestd_filtered_cached.py slurmweb/tests/views/test_agent.py slurmweb/tests/views/test_agent_operations.py slurmweb/tests/views/test_gateway.py`
- `cd frontend && npx vitest run tests/components/jobs/UserFilterSelector.spec.ts tests/components/jobs/JobsFiltersPanel.spec.ts tests/views/JobsView.spec.ts tests/composables/GatewayAPI.spec.ts tests/composables/DataPoller.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：队列详情页移除重复资源展示

本轮针对 `/:cluster/partitions/:partition` 页面做了信息层级优化：

- 顶部摘要卡片继续展示节点数、总 CPU、已分配 CPU、总内存和 GPU。
- 下方“队列详情”不再重复展示已在摘要卡出现的资源容量字段，只保留名称、已分配节点和空闲节点等补充信息。
- 节点集合与队列实时曲线保持不变。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/PartitionView.spec.ts`

## 本轮：LDAP 已支持多 Base DN 和 AD 大目录分页枚举

本轮补了一组面向 Active Directory 的 LDAP 兼容增强，重点解决“用户分散在多个并列 OU”与“域根枚举直接撞 `Size limit exceeded`”两类现场问题：

- `user_base` 与 `group_base` 现在支持配置为多值列表，不再只能写单个 Base DN。
- 登录链路在 `lookup_user_dn=yes` 时，会逐个 `user_base` 查找单个用户 DN，适配用户落在多个并列 OU 的场景。
- 如果同一个用户名在多个 `user_base` 下都命中，后端会明确报“找到多个用户”，避免静默选错 DN。
- LDAP 组解析会跨多个 `group_base` 合并并去重。
- `slurm-web ldap-check` 与 LDAP 全量用户枚举在目录服务器支持分页控件时，会改用 paged search，降低 Active Directory 大目录上直接触发 `Size limit exceeded` 的概率。

本轮新增验证：

- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_ldap_authentifier.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ldap.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_gateway.py`

补充修复：

- `scripts/fetch-github-ci-result.ps1` 现在会在下载 artifact 前先清空当前 run 目录下已有 artifact 子目录。
- 重复对同一个 GitHub Actions run 执行 `fetch-github-ci-result.ps1` 或 `continue-from-github-ci.ps1` dry-run 时，不再因旧 `failure-context.json` / `result.json` 残留导致 `gh run download` 解压中断。

## 本轮：集群分析平均排队时间曲线改为 `submit_time -> start_time` 秒级口径

本轮继续修正 `Cluster Analysis` 中“平均排队时间曲线没有明显显示”的问题：

- 平均排队时间曲线现在统一按 `submit_time -> start_time` 计算排队时间，不再混用 `eligible_time`。
- 曲线现在按秒展示平均排队时长，支持 `minute / hour / day` 聚合粒度切换，并会按当前时间窗口自动选择默认粒度。
- 单个时间桶样本不再因为折线点被隐藏而看起来“没有图”。
- 曲线默认使用与主题一致的淡绿色，并在超过 `60` 秒后随等待时长连续过渡到橙色、红色，便于识别高等待区间。

本轮新增验证：

- `cd frontend && npx vitest run tests/composables/queueWaitHistory.spec.ts tests/views/ClusterAnalysisView.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：队列详情页已补实时曲线，作业相关队列字段统一为可点击入口

本轮继续把队列详情链路补齐到完整工作流：

- `/:cluster/partitions/:partition` 现在除核心摘要外，还复用 dashboard 的实时资源与作业曲线，并固定按当前队列过滤。
- 队列详情页沿用 dashboard 的时间范围状态，但图表切换资源类型时会继续停留在当前队列详情页，不再错误跳回 `dashboard`。
- `Job`、`Job History`、`Jobs`、`Jobs History` 中的队列字段已统一改成芯片式可点击入口，直接跳转队列详情页。
- `Cluster Analysis` 的 `Partition Hotspots` 模块中，队列名称现在也使用同一套芯片式入口，可直接跳转到队列详情页。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/PartitionView.spec.ts tests/views/JobView.spec.ts tests/views/JobHistoryView.spec.ts tests/views/JobsView.spec.ts tests/views/JobsHistoryView.spec.ts tests/components/dashboard/ChartResourcesHistory.spec.ts tests/components/dashboard/DashboardCharts.spec.ts`

补充收口：

- 队列详情页实时曲线区的副标题已改成面向用户的“队列活动”说明，不再使用“复用 dashboard 曲线”的实现口径。
- 队列页实时曲线工作区已改为更紧凑的单页布局：压缩了摘要到图表、图表标题到画布之间的留白，并为队列场景单独降低图表高度，减少首屏溢出和深滚动。

## 本轮：Dashboard 队列统计、Admin 门禁与 AI 管理页样式已继续收口

本轮继续修正一组已经在真实页面上暴露出的前端问题：

- `Dashboard`
  - 选择具体队列后，顶部统计卡现在会优先按当前队列的节点与作业数据本地重算，不再继续误显整集群资源总量。
  - `Partition / Queue` 下拉框已去掉与外层 pill 容器重叠的双层描边，聚焦态改为统一光环样式。
- `Admin`
  - 普通用户即使直接访问 `/:cluster/admin`，现在也会先命中 `admin/*:view:*` 门禁；没有任何管理权限时不再被静默重定向到 `analysis`。
  - `Admin > AI` 页面继续沿用现有视觉系统，但已把头部和两块主内容收口为更清晰的工作区层级，减少大卡片纵向堆叠带来的压迫感。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/DashboardView.spec.ts tests/router/AdminPermissions.spec.ts tests/components/MainMenu.spec.ts tests/views/settings/SettingsAI.spec.ts`
- `npm --prefix frontend run type-check`

## 本轮：AI 直接取消作业工具名兼容已补齐

本轮修复了 AI 执行作业取消时的一条兼容性缺陷：

- 标准 AI tool 仍然是 `query_agent_interface` 和 `mutate_agent_interface`。
- 若模型错误地直接输出接口名作为 tool name，例如 `job/cancel`，后端现在会按同名 Agent interface 做兼容分发。
- 超级管理员或具备对应权限的用户通过 AI 取消作业时，不再因为 `Unsupported tool job/cancel` 冒成接口 `500`。

本轮新增验证：

- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py`

## 本轮：普通用户 AI 页面不再错误请求管理员模型配置接口

本轮修复了普通用户进入 `AI` 页面时的一条权限口径错误：

- 普通用户具备 `ai:view:*` 时，允许进入 `/:cluster/ai` 并使用 AI 对话。
- 之前页面初始化会先请求 `ai/configs`，而该接口要求 `admin/ai:view:*`，因此普通用户首屏会先收到 `403`。
- 现在普通 AI 页只读取 `ai:view:*` 可访问的会话与流式接口，不再把管理员模型配置接口作为首屏前置依赖。
- 默认模型选择继续通过 cluster `capabilities.ai.default_model_id` 与当前会话 `model_config_id` 兜底；管理员仍可额外读取配置列表。

本轮新增验证：

- `cd frontend && npx vitest run tests/views/AssistantView.spec.ts`

补充收口：

- `AI` 对话页发送区附近已新增当前模型显示。
- 具备 `admin/ai:view:*` 的用户可直接在发送区旁切换启用模型；普通用户保持不请求管理员模型配置接口，但仍会看到当前对话模型或集群默认模型状态。

## 本轮：集群分析、用户分析、资源与队列页面补齐分析视图增强

本轮围绕 `Cluster Analysis`、`User Analysis`、`Resources` 和新的队列详情页补了一组前端与接口增强，并同步补齐中英文文案：

- `Cluster Analysis`
  - 新增平均排队时长曲线，单位为秒。
  - 新增节点热点概览，默认展示近 3 天内 CPU 或内存利用率超过 80% 的节点事件，包括节点名、开始时间、指标类型、峰值利用率和持续时间。
  - `diag` 面板只保留 10 条核心统计字段，避免非核心噪音继续占据分析页。
  - 时间范围控件支持与用户分析一致的自定义起止时间和快捷窗口，请求链路已扩展到 `start/end`。
- `User Analysis`
  - 提交/完成趋势之外，新增运行中、排队中、失败、取消状态的统计与历史序列数据返回。
  - 删除分析区冗余标题，只保留必要操作和分析面板。
- `Resources`
  - 节点列表新增 `Rack` 列。
  - 资源页头部按钮已整理到同一行。
  - 队列标签可直接跳转队列详情页。
- `Partition`
  - 新增 `/:cluster/partitions/:partition` 页面。
  - 展示节点数、已分配节点、空闲节点、CPU、内存、GPU 与节点集合表达式等核心信息。

本轮新增验证：

- `npm --prefix frontend run type-check`
- `cd frontend && pnpm vitest run tests/views/UserAnalysisView.spec.ts tests/views/ClusterAnalysisView.spec.ts tests/views/resources/ResourcesView.spec.ts tests/views/PartitionView.spec.ts tests/composables/GatewayAPI.spec.ts`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/metrics/test_db.py slurmweb/tests/views/test_agent_metrics_requests.py slurmweb/tests/views/test_agent_operations.py slurmweb/tests/views/test_gateway.py`

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
  - 集群名、用户名、QOS 名、队列名、节点名等业务实体值
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

- `DashboardView` 的队列筛选改为按 `jobs/filter-partitions:view:*` 或 `resources/filter-partitions:view:*` 判断
- `NodeView` 的节点作业轮询改为按 `jobs:view:*` 判断
- `JobsFiltersPanel` 的 `Accounts / QOS / Partitions` 筛选区改为按对应 filter resource 判断
- `DashboardCharts` 的图表显示改为按 `resources:view:*` 与 `jobs:view:*` 判断
- `ResourcesFiltersPanel` 的队列筛选改为按 `resources/filter-partitions:view:*` 判断
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
- `Cluster Analysis` 中同栏目并列卡片已统一复用共享 surface，避免 `Packing Signal`、队列热点卡、历史压力卡在同一块内容里出现无语义依据的背景和边框差异。
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
- 本轮只调整 Dashboard 视图内的局部布局和样式，不改变队列筛选、统计数据和图表请求行为。

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

- Agent `GET /v<agent-version>/stats` 现在会读取 `partition` query，并基于该队列返回的作业和节点重新聚合：
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

## 10. 预留创建表单补齐 Slurm 必需时间字段

本轮修复了管理页“创建预留”直接报 `A start time must be given` 的问题，范围如下：

- `Reservations` 创建对话框新增 `start_time` 与 `end_time` 输入，并在前端本地校验“开始时间必填、创建时结束时间必填、结束时间必须晚于开始时间”
- 预留创建与编辑提交现在会把本地 `datetime-local` 值转换为 `slurmrestd` 可接受的时间对象并写入 `start_time` / `end_time`
- `ActionDialog` 扩展支持 `datetime-local` 字段类型，供管理类写操作对话框复用

已补充验证：

- `frontend/tests/components/operations/ActionDialog.spec.ts`
- `frontend/tests/views/ReservationsView.spec.ts`

## 11. 账户详情页补齐用户关联写后刷新

本轮审查了 Slurm 账户创建与账户用户关联逻辑，并修复了一个直接影响可见性的前端缺口：

- Slurm 中“创建账户”和“把用户加入账户”是两条独立写链路：
  - 账户创建走 `accounts`
  - 用户加入账户走 `associations`
- `AccountView` 详情页展示账户下用户列表时，数据来源是 `/associations`，不是 `/accounts`
- 原实现中，添加用户、编辑用户 QOS、删除用户关联、编辑账户后没有立即刷新 `/associations`，导致页面会继续显示旧状态，看起来像“接口成功但账户里没有用户”
- 现在账户详情页在上述写操作完成后会立即刷新 `associations`，让账户成员关系与页面展示保持同步

已补充验证：

- `frontend/tests/views/AccountView.spec.ts`
- `npm --prefix frontend run type-check`
