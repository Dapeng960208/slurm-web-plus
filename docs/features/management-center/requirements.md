# 管理扩展需求说明

## 1. 背景与目标

本轮不新增独立“全量管理中心”，而是在现有业务页面上补单对象管理能力，并新增集群级 `/:cluster/admin` 页面统一承载后台管理能力。

目标包括：

- 在现有 `Jobs`、`Resources`、`Reservations`、`Accounts`、`User`、`QOS` 页面补创建、编辑、删除、取消等单对象能力
- 将 `AI`、`Users`、`Cache`、`Access Control` 从 `/settings/*` 迁移到 `/:cluster/admin`
- 在 `analysis` 页面补 `Slurm diag` 与 `ping`
- 将 `analysis/ping`、`analysis/diag` 从原始 JSON 文本收口为结构化字段展示
- 用 `resource:operation:scope` 做严格权限控制
- 为 `jobs` 资源落地后端 owner-aware `self` 校验
- 兼容 `slurmrestd` `0.39` 到 `0.44`

## 2. 功能范围

本次已实现：

- `JobsView` / `JobView`
  - 单作业提交
  - 单作业编辑
  - 单作业取消
  - 编辑时可填写 `Memory per CPU (MB)`，正整数会提交为 Slurm REST `memory_per_cpu` 对象；空值不发送
  - `partition`、`qos` 字段已统一改为可搜索下拉
- `JobsHistoryView` / `JobHistoryView`
  - 支持从历史作业跳转实时作业详情
  - 使用历史记录中的 Slurm `job_id` 跳转到 `/:cluster/job/:job_id`
  - 历史页不直接提供编辑或取消，避免对持久化历史记录误发写操作
- `ResourcesView` / `NodeView`
  - `ResourcesView` 列表页只保留节点名称详情跳转，不在行尾显示 `Manage` / `Delete`
  - `NodeView` 详情页保留单节点更新和删除入口
  - `NodeView` 编辑节点时，`state` 使用下拉框选择：`DRAIN`、`RESUME`、`UNDRAIN`、`DOWN`、`IDLE`、`FAIL`、`FUTURE`
- `ReservationsView`
  - 创建
  - 更新
  - 删除
  - 前端表单已补 `groups`、`qos`、`Allowed Partitions`
  - `node_list`、`allowed_partitions`、`qos` 已统一改为可搜索下拉
  - `node_list` 现在仅支持从当前集群节点列表多选并回写为逗号分隔字符串，不再保留自由文本 nodeset 表达式输入
  - 创建/编辑前固定校验 `users / groups / accounts / qos / allowed_partitions` 至少一项非空；若全空则在弹窗内直接报错，不发请求
  - reservation create/update payload 会统一走后端 normalization，再映射到 `slurmrestd` reservation 写入契约
- `AccountsView` / `AccountView`
  - 账户创建
  - 账户更新
  - 账户删除
  - account-user association 增加用户、编辑 QOS/default QOS、删除用户关联
  - 账户和 association 相关的 `username`、`qos`、`default_qos` 已统一改为可搜索下拉
  - `Add user` 现在先确保用户实体存在，再补 association，并在刷新后校验关联真实可见才显示成功
  - `users.update` 写接口现在接受轻量单用户对象，并由后端统一归一化为 `{"users": [...]}` 后再写入 `slurmrestd`
- `UserView`
  - SlurmDB 用户创建/更新
  - 用户删除
  - 编辑用户默认 QOS 与分配 QOS
  - `default_qos` 与分配 `qos` 已统一改为可搜索下拉
- `QosView`
  - QoS 创建
  - QoS 更新
  - QoS 删除
- `ClusterAnalysisView`
  - `Slurm ping`
  - `Slurm diag`
  - `hour/day/week` 时间范围切换
  - 平均排队时间图使用卡片自身时间范围与 `hour/day` 独立聚合粒度，不再跟页面页头右侧全局时间组件绑定
  - 平均排队时间图横轴按卡片当前 `start/end` 窗口展开，单点样本不会再压缩成毫秒级时间轴
  - 内存容量详情按 GB 展示，评分与百分比仍使用原始 MB 数值
- `DashboardView`
  - 删除顶部工具条左侧“实时指标”局部标题、副标题和说明文案
  - 工具条、统计卡、图表区的垂直节奏统一回到页面级共享 spacing
- `JobView` / `JobHistoryView`
  - 左侧继续保留 `JobProgress` / timeline
  - 右侧详情统一参考 `NodeView` 改成单页连续详情列表
  - 不再保留 `DetailSummaryStrip`、碎片字段卡、长字段卡片堆叠与冗余小标题
  - `partition / user / account` 仍保持可点击入口；长字段保持自动换行
- `/:cluster/admin`
  - `AI`
  - `Users`
  - `Cache`
  - `Access Control`

本次不做：

- 批量取消作业
- 批量节点操作
- 独立 JSON 专家模式

## 3. 路由与页面承载

新增或调整后的关键路由：

- `/:cluster/admin`
- `/:cluster/admin/ai`
- `/:cluster/admin/access-control`
- `/:cluster/admin/cache`
- `/:cluster/admin/ldap-users`

旧路由迁移：

- `/settings/ai` -> `/:cluster/admin/ai`
- `/settings/access-control` -> `/:cluster/admin/access-control`
- `/settings/cache` -> `/:cluster/admin/cache`
- `/settings/ldap-users` -> `/:cluster/admin/ldap-users`

说明：

- `settings` 页面只保留 `General`、`Errors`、`Account`
- 主侧栏新增 `Admin`
- 主侧栏顺序调整为 `AI` 在上、`Admin` 在最下
- `/:cluster/admin` 直接访问时会跳转到 `/:cluster/analysis`
- `Admin` 入口由任一 `admin/*:view:*` 控制显示
- `admin-manage` 现在只是 `*:*:*` 的兼容别名，因此只有 `super-admin` 语义的角色/用户会通过该别名显示 `Admin` 入口

## 4. 权限要求

业务资源：

- `jobs:view|edit|delete:*|self`
- `resources:view|edit|delete:*`
- `reservations:view|edit|delete:*`
- `accounts:view|edit|delete:*`
- `users-admin:view|edit|delete:*`
- `qos:view|edit|delete:*`
- `analysis:view:*`

后台资源：

- `admin/ai:view|edit|delete:*`
- `admin/ldap-users:view|edit:*`
- `admin/cache:view|edit:*`
- `admin/access-control:view|edit|delete:*`

控制规则：

- 页面访问使用 `view`
- 创建、更新、状态修改使用 `edit`
- 删除、取消使用 `delete`
- `Admin` 页面至少要求一个 `admin/*:view:*`

## 5. `jobs self` 语义

`self` 首版只落地在 `jobs` 资源：

- `jobs:view:self`
  - 作业列表查询优先向 `slurmrestd` 注入 `user=<request.user.login>`
  - 后端再做一次 owner 过滤
- `jobs:edit:self`
  - 作业更新前先查询作业 owner，再校验当前登录用户
- `jobs:delete:self`
  - 作业取消前先查询作业 owner，再校验当前登录用户

安全边界：

- owner 判定只以后端查询到的作业实际 owner 为准
- 不接受前端传入用户名作为最终授权依据

## 6. 后端接口与兼容策略

后端新增或扩展：

- `analysis/ping`
- `analysis/diag`
- `jobs/submit`
- `job/<id>/update`
- `job/<id>/cancel`
- `node/<name>/update`
- `node/<name>/delete`
- `reservation`
- `reservation/<name>/update`
- `reservation/<name>/delete`
- `accounts`
- `associations`
- `DELETE associations`
- `account/<name>/delete`
- `users`
- `user/<name>/delete`
- `qos`
- `qos/<name>/delete`

`slurmrestd` 版本兼容：

- `0.41-0.44`
  - 当前主写路径已开放
- `0.39-0.40`
  - 维持读兼容
  - 未开放写操作返回 `501 unsupported_on_version` 风格降级结果

## 7. 默认角色与旧动作兼容

默认种子角色调整为：

- `user`
  - 不包含任何 `admin/*`
  - 对非 `Admin` 页面默认只具备只读能力
  - 默认包含 `jobs:view:self`
  - 默认包含 `jobs:edit:self`
  - 默认包含 `jobs:delete:self`
- `admin`
  - 默认包含 `*:view:*`
  - 默认包含 `*:edit:*`
  - 默认不包含 `*:delete:*`
- `super-admin`
  - `*:*:*`

旧动作兼容补充：

- `admin-manage` -> `*:*:*`

已移除的旧动作入口：

- `view-own-jobs`
- `edit-own-jobs`
- `cancel-own-jobs`
- `roles-view`
- `roles-manage`
- `manage-ai`

仍保留的旧动作兼容：

- `view-ai` -> `ai:view:*`
- `admin-manage` -> `*:*:*`

普通用户默认拥有 `jobs:*:self` 与 `user/analysis:view:self`，现在来自数据库种子角色 `user`，不再来自 vendor policy 动作；无数据库模式下也不再提供这组旧动作兜底。

## 8. 前端行为

前端统一采用：

- 列表页工具栏只放“创建”入口
- 行级与详情页放 `Edit` / `Delete` / `Cancel`
- 删除与取消统一二次确认
- 不展示任何批量操作 UI
- 共享表单统一显示字段 `Required` / `Optional`
- 编辑类按钮使用橙色语义，删除/取消使用红色警示语义
- 关键字段与操作按钮补 tooltip / hint，说明行为影响
- 共享写操作表单中的 `用户名 / 节点名 / QOS / 分区` 优先使用同一套搜索选择器，而不是继续保留分散的文本输入
- `用户名` 搜索复用现有 `access_users` 分页/用户名过滤接口做真正远程搜索
- `QOS / 分区 / 节点` 搜索复用现有 `qos / partitions / nodes` 列表接口，先从远端加载，再在下拉框内筛选
- 多值字段统一以“多选标签 + CSV 序列化回现有 payload”提交，不改后端写接口契约
- `Dashboard`、`Cluster Analysis`、`Node` 指标统一支持 `hour/day/week` 时间范围切换
- 按操作语义统一按钮颜色：
  - 创建/提交/主要确认：`ui-button-primary`
  - 编辑/保存修改：`ui-button-warning`
  - 删除/取消作业/破坏性操作：`ui-button-danger`
  - 查看/返回/筛选/普通导航/弹窗关闭：`ui-button-secondary`
- 不把所有按钮统一改为同一颜色；页面按钮按实际操作语义选择样式
- Jobs 用户筛选保留 `/users` 查询建议，同时支持直接输入用户名并通过 `Add username` 加入筛选；空值不添加，重复用户名不重复添加，添加后清空输入。
- `Jobs`、`Jobs History`、`Resources`、`QOS`、`Reservations`、`Accounts` 已统一采用共享结果工作区结构：
  - 筛选区或页头说明停留在结果滚动区之外
  - 表格或账户树主体独立滚动
  - 分页条固定在页面工作区底部，而不是跟随表格高度落到整页底部
- 登录后共享主布局中的 `ui-content-scroll` 必须等于 header 下方剩余浏览器可视区高度，并与左侧桌面导航保持同级底部留白；页面内容只能在该可视区内部滚动，不得再把主壳体向下撑长。
- 共享表格滚动样式已统一恢复左右 gutter 与内容内边距，不再依赖各视图手写负边距；长列或窄屏下继续通过表格内部横向滚动处理。

`jobs:self` 的前端行为：

- 可根据当前登录用户与对象 owner 做隐藏/禁用
- 最终安全判定仍由后端执行

## 9. 降级与边界

- `admin/ldap-users:edit:*` 当前表示 LDAP 用户缓存维护动作，例如刷新、重建或失效缓存；不表示修改 LDAP 源数据
- `accounts/users/qos/reservation` 当前前端使用轻量结构化表单，不覆盖全部官方 JSON 细节
- reservation 轻量表单当前额外接受 `groups`、`qos`、`allowed_partitions` 三类访问控制字段别名；最终仍由后端归一化为 `slurmrestd` 实际写入字段
- 全量后端回归仍需 Linux 环境补充

## 10. 相关实现与验证入口

- 前端：
  - `frontend/src/router/index.ts`
  - `frontend/src/views/AdminLayoutView.vue`
  - `frontend/src/views/JobsView.vue`
  - `frontend/src/views/JobView.vue`
  - `frontend/src/views/resources/ResourcesView.vue`
  - `frontend/src/views/NodeView.vue`
- 后端：
  - `slurmweb/views/agent.py`
  - `slurmweb/views/gateway.py`
  - `slurmweb/apps/agent.py`
  - `slurmweb/apps/gateway.py`
  - `slurmweb/slurmrestd/__init__.py`
  - `slurmweb/permission_rules.py`
- 测试计划见 [`test-plan.md`](./test-plan.md)
