# 管理扩展测试计划

## 1. 目标

验证现有业务页面增强、`Admin` 路由迁移、`jobs:self` 后端校验、`analysis ping/diag`、以及 `slurmrestd 0.39-0.44` 兼容降级行为。

## 2. 后端测试

### 2.1 权限与 owner-aware

覆盖以下场景：

- `jobs:view:self` 只返回当前用户自己的作业
- `jobs:delete:self` 只能取消本人作业
- `jobs:edit:self` 只能更新本人作业
- `default_seed_roles()` 中 `user` 包含 `jobs:view:self`、`jobs:edit:self`、`jobs:delete:self`
- `default_seed_roles()` 中 `user` 不包含 `admin/*`
- `default_seed_roles()` 中 `admin` 只包含 `*:view:*` 与 `*:edit:*`
- `default_seed_roles()` 中 `admin` 不包含 `*:delete:*`
- `admin-manage` 等价于 `*:*:*`，仅作为 `super-admin` 兼容别名保留

对应重点：

- `slurmweb/tests/test_permission_rules.py`
- `slurmweb/tests/test_access_control_policy.py`
- `slurmweb/tests/views/test_agent_operations.py`

### 2.2 Gateway / Agent 路由

覆盖以下场景：

- `analysis/ping`
- `analysis/diag`
- 旧 `admin/system/*` 路由返回 404
- `job/<id>/update`
- `job/<id>/cancel`
- `node/<name>/update`
- `node/<name>/delete`
- `DELETE` body 经 Gateway 转发

对应重点：

- `slurmweb/tests/views/test_gateway_operations.py`
- `slurmweb/tests/views/test_gateway.py`

### 2.3 slurmrestd 写路径

覆盖以下场景：

- 通用 `request_json()` 透传 `method/payload/query`
- `DELETE` 带 body
- `supports_write_operations()` 对 `0.41-0.44` 返回 true
- `supports_write_operations()` 对 `0.39-0.40` 返回 false
- user 轻量 payload 会被包装为 `{ users: [...] }`
- user 写入中的空字符串字段会在后端归一化时剔除，避免直接透传到 `slurmrestd`
- account-level association 写入 payload 不带 `user` 时，后端仍会按当前集群注入 `cluster`
- reservation create/update payload normalization 统一覆盖创建与更新路径
- `allowed_partitions` / `allowedPartitions` / `AllowedPartitions` 会映射到 reservation 写入字段 `partition`
- reservation 的 `users/groups/accounts/qos` 数组别名会转换为 `slurmrestd` 所需 CSV string
- reservation create/update/delete 会清理 `reservations` 缓存
- reservation delete 遇到 Slurm `Requested reservation is invalid/2053` 时按幂等删除结果返回，不继续包装为 500
- node update/delete 会清理 `nodes`、`nodes-unfiltered` 与单节点缓存
- QOS 轻量 payload 会被包装为 `{ qos: [...] }`
- QOS 写入缺少常用限制时，后端默认补 `MaxSubmitJobsPerUser=100`、`MaxJobsPerUser=10`、`MaxWallDurationPerJob=1440`
- QOS 写入显式传入常用限制时，不被后端默认值覆盖
- account-user association 删除 payload 会转换为 `account/user/cluster` query 参数，避免 `DELETE /association` request body 被忽略后扩大删除范围

对应重点：

- `slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`

## 3. 前端测试

### 3.1 路由与导航

覆盖以下场景：

- `/:cluster/admin`
- `/:cluster/admin` 默认跳转 `analysis`
- `admin-ai`
- `admin-access-control`
- `admin-cache`
- `admin-ldap-users`
- 旧 `settings/*` 管理路由重定向到 `admin/*`
- 主菜单 `Admin` 入口只在具备任一 `admin/*:view:*` 时显示
- 主菜单 `Admin` 入口在拥有 `admin-manage`（即 `*:*:*`）时也显示
- 角色页不再展示 `view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage`、`manage-ai`
- 旧 `view-ai` 仍可作为兼容动作存在，但应继续映射到 `ai:view:*`

对应重点：

- `frontend/tests/router/AdminRoutesContract.spec.ts`
- `frontend/tests/components/MainMenu.spec.ts`
- `frontend/tests/stores/runtime.spec.ts`

### 3.2 页面行为

覆盖以下场景：

- `ClusterAnalysisView` 请求并展示 `Ping` / `Diag`
- `ClusterAnalysis` 内存容量详情以 GB 展示，评分和百分比继续使用 MB 原始值计算
- `JobsView` 在 `jobs:view|edit|delete:self` 下只对本人作业显示 `Edit/Cancel`
- `JobView` 在 `self` 下只对本人作业显示 `Edit/Cancel`
- `JobsView` / `JobView` 编辑作业时，填写 `Memory per CPU (MB)` 会提交 `memory_per_cpu: { set: true, infinite: false, number }`
- `UserFilterSelector` 改为远程搜索多选用户名，复用 `access_users`，不再通过手工输入 + `Add username` 按钮添加
- `JobsHistoryFiltersPanel` 的 `user / partition / qos` 使用搜索下拉并通过 `update:filters` 回传
- `JobsHistoryView` / `JobHistoryView` 的实时作业入口使用 Slurm `job_id` 跳转到 `job` 路由
- `JobsHistoryView` / `JobHistoryView` 不直接提供历史记录 Edit/Cancel 写操作
- `AccountView` 可增加 account-user association、编辑 association QOS/default QOS、删除 association，payload 复用现有 associations 写接口
- `AccountView` 的 `Add user` 必须先调用 `save_user`，再调用 `save_association`
- `AccountView` 在 `refreshAssociations()` 后若仍看不到目标 `{ account, user }`，必须提示失败且不能显示成功 toast
- `AccountView` 删除 association 时只提交选中 `account` 与 `user`，不携带空 `qos/default` 字段
- `AccountsView` 创建带 `parent_account` 的账户时，必须先调用 `save_account`，再调用 `save_association` 写入不带 `user` 的 account-level association
- `AccountsView` 当 `/accounts` 已返回 `{ name, parent_account }` 但 `/associations` 暂无该账户的 account-level row 时，账户树仍应把子账户展示在父账户下
- `AccountView` 当 `account/<name>` 已返回 `parent_account` 但 `/associations` 暂无当前账户的 account-level row 时，仍应识别该账户存在并展示父账户链路
- `AccountView` 给子账户添加用户时，刷新后只要 `/associations` 出现目标 `{ account, user }` 即判定成功并关闭弹框
- `AccountsView` 创建账户成功后调用真实 `refresh()` 刷新 `/accounts` 与 `/associations`
- `AccountView` 删除账户成功后返回 `Accounts` 列表
- `UserView` 编辑用户时提交 `default_qos` 和逗号分隔解析后的 `qos`
- `UserView` 编辑用户成功后刷新 associations；删除用户成功后刷新并返回上一级页面
- `ActionDialog` 支持共享搜索单选/多选字段，初始值可回填，并在提交时保持 CSV 序列化
- `RemoteSearchSelect` 支持：
  - 用户远程搜索
  - QOS/分区/节点远端列表加载后搜索
  - 多选标签回显和移除
- `ClusterAnalysisView` 的平均排队时间卡片切换自身时间范围时，会重新请求 `jobs_history`
- `ClusterAnalysisView` 的平均排队时间卡片切换自身时间范围时，不会重拉 metrics 与 node hotspots
- `ClusterAnalysisView` 顶部全局时间范围变化时，不会覆盖卡片已手动选择的独立时间范围
- `ClusterAnalysisView` 页头右侧不再展示额外时间范围组件；平均排队时间卡片保留自身时间范围按钮
- `ClusterAnalysisView` 的平均排队时间卡片展示 `minute/hour/day` 聚合粒度；最近一小时默认按分钟聚合，小时按小时平均排队时间聚合，天按天平均排队时间聚合
- `ClusterAnalysisView` 的平均排队时间图横轴按卡片当前时间范围展开，单点样本不会再显示为毫秒级 X 轴
- `QosView` 创建 QOS 弹框预填 `MaxSubmitJobsPerUser=100`、`MaxJobsPerUser=10`、`MaxWallDurationPerJob=1-00:00:00`
- `QosView` 提交创建 QOS 时把 `MaxWallDurationPerJob` 转换为分钟；非法 walltime 不调用写接口并在弹框显示错误
- `QosView` 创建、编辑、删除 QOS 成功后主动刷新列表
- `ReservationsView` 创建/编辑表单会提交 `groups`、`qos`、`allowed_partitions`
- `ReservationsView` 在 `users / groups / accounts / qos / allowed_partitions` 全空时，只显示本地校验错误且不调用写接口
- `ReservationsView` 创建、编辑、删除成功后会主动刷新列表，避免继续展示旧 reservation
- 触达页面的按钮样式按操作语义区分：创建/提交 primary，编辑 warning，删除/取消 danger，查看/返回/筛选 secondary
- 默认 `admin` 用户可见编辑入口，但删除入口仍继续受 `delete` 权限控制
- 页面无批量取消入口
- `DashboardView` 不再渲染“实时指标”局部文案块；图表组件不再输出旧的顶部 `pt-16/pb-5/mt-4`
- `JobsView`、`JobsHistoryView`、`ResourcesView`、`QosView`、`ReservationsView` 结果区存在独立 `.ui-table-scroll`，分页节点位于 `.ui-results-dock .ui-results-pagination`，而不再留在 `.ui-table-shell` 内部
- `AccountsView` 账户树列表存在独立 `.ui-tree-scroll`，分页固定在工作区底部
- `ClusterMainLayout` 的 `main.ui-content-scroll` 具备显式 `flex-1` 与 `min-h-0`，作为浏览器可视区内框，而不是随子内容增长的普通文档流容器
- `UserView`、`AccountView`、`JobView`、`JobHistoryView`、`NodeView`、`UserAnalysisView` 详情页正文存在独立 `.ui-scroll-region`，返回按钮保留在工作区顶部，非表格详情内容可以在固定 shell 内继续下滚
- `JobView` / `JobHistoryView` 右侧详情区应为连续列表，不再存在 `detail-summary-strip` 或卡片网格
- `DashboardView` 与 `ClusterAnalysisView` 页面正文存在独立 `.ui-scroll-region`，页头保留在工作区顶部，非表格内容区可以在固定 shell 内继续下滚
- `AdminLayoutView` 会在 `RouterView` 外层提供 `.ui-scroll-region`，保证 `admin/ai`、`admin/access-control`、`admin/cache`、`admin/ldap-users` 与管理员详情子页面在固定 shell 中仍可滚动
- `ResourcesView` 不再渲染节点行尾 `Manage` / `Delete` 按钮，节点名称仍可跳转详情
- `NodeView` 的 Edit Node 中 `state` 渲染为下拉框，并按所选状态提交 `update_node`
- `NodeView` 更新节点成功后主动刷新当前节点详情

对应重点：

- `frontend/tests/views/ClusterAnalysisView.spec.ts`
- `frontend/tests/views/JobsView.spec.ts`
- `frontend/tests/views/JobView.spec.ts`
- `frontend/tests/views/JobsHistoryView.spec.ts`
- `frontend/tests/views/JobHistoryView.spec.ts`
- `frontend/tests/views/resources/ResourcesView.spec.ts`
- `frontend/tests/views/QosView.spec.ts`
- `frontend/tests/views/ReservationsView.spec.ts`
- `frontend/tests/views/AccountsView.spec.ts`
- `frontend/tests/views/AccountView.spec.ts`
- `frontend/tests/components/PaginationControls.spec.ts`

### 3.3 Gateway API 契约

覆盖以下场景：

- `analysis/ping`
- `analysis/diag`
- 不再暴露 `admin/system/*`
- 新写接口路径与方法
- `RESTAPI.delete()` 支持 body
- 前端 `delete_association(cluster, payload)` 使用 `DELETE /agents/:cluster/associations` 并保留请求 body
- QOS 创建 payload 可携带 `max_submit_jobs_per_user`、`max_jobs_per_user`、`max_wall_duration_per_job`，后端仍作为默认值兜底
- `JobUpdatePayload.memory_per_cpu` 与 `ClusterAssociation.default.qos` 类型契约可被页面使用

对应重点：

- `frontend/tests/composables/GatewayAPI.spec.ts`
- `frontend/tests/composables/GatewayAPIAdminContract.spec.ts`

## 4. 验证入口

本轮至少执行：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests`

本轮定向验证可先执行：

- `cd frontend && npx vitest run tests/views/QosView.spec.ts tests/views/AccountView.spec.ts tests/composables/GatewayAPI.spec.ts`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`
- `.venv\Scripts\python -m pytest slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py slurmweb/tests/views/test_agent_ai.py slurmweb/tests/views/test_gateway_ai.py`
- `cd frontend && npx vitest run tests/views/JobsView.spec.ts tests/views/JobView.spec.ts tests/views/JobsHistoryView.spec.ts tests/views/JobHistoryView.spec.ts tests/views/AccountView.spec.ts tests/views/UserView.spec.ts tests/composables/GatewayAPI.spec.ts tests/composables/ClusterAnalysis.spec.ts tests/components/operations/ActionDialog.spec.ts`
- `cd frontend && npm exec vitest run tests/views/ReservationsView.spec.ts tests/views/AccountView.spec.ts tests/views/JobView.spec.ts tests/views/JobHistoryView.spec.ts tests/views/DashboardView.spec.ts tests/components/dashboard/ChartResourcesHistory.spec.ts tests/components/dashboard/ChartJobsHistory.spec.ts tests/views/AssistantView.spec.ts tests/views/AssistantViewAIContract.spec.ts`
- `cd frontend && npx vitest run tests/views/resources/ResourcesView.spec.ts tests/views/NodeView.spec.ts tests/components/operations/ActionDialog.spec.ts tests/components/jobs/UserFilterSelector.spec.ts`
- `cd frontend && npx vitest run tests/components/forms/RemoteSearchSelect.spec.ts tests/components/operations/ActionDialog.spec.ts tests/components/jobs/UserFilterSelector.spec.ts tests/components/jobs/JobsHistoryFiltersPanel.spec.ts tests/views/JobsView.spec.ts tests/views/JobView.spec.ts tests/views/AccountView.spec.ts tests/views/AccountsView.spec.ts tests/views/UserView.spec.ts tests/views/ReservationsView.spec.ts tests/views/JobsHistoryView.spec.ts`
- `cd frontend && npx vitest run tests/views/UserView.spec.ts tests/views/JobView.spec.ts tests/views/NodeView.spec.ts tests/views/UserAnalysisView.spec.ts`
- `cd frontend && npx vitest run tests/views/DashboardView.spec.ts tests/views/ClusterAnalysisView.spec.ts tests/views/AdminLayoutView.spec.ts tests/views/settings/SettingsAI.spec.ts tests/views/settings/SettingsAccessControl.spec.ts tests/views/settings/SettingsCache.spec.ts tests/views/settings/SettingsLdapCache.spec.ts tests/views/settings/SettingsAIConversationDetail.spec.ts`
- `npm --prefix frontend run type-check`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py slurmweb/tests/views/test_agent_operations.py`

若存在失败，需要在 `docs/tracking/current-release.md` 记录失败项和结论。
