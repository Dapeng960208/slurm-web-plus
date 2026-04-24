# Slurm Web Plus 近期增强能力（面向交付与维护）

本文聚焦最近一批已经落地的增强能力，目标是让开发、测试、交付和后续 AI 能快速理解“功能为什么加、怎么开、怎么用、依赖什么、文档应该改哪里”。

## 1. 功能概览

最近新增或显著增强的能力包括：

- 数据库持久化的 AI 集群助手
- 数据库驱动的访问控制自定义角色
- 用户分析与集群分析工作台
- 历史作业访问控制与 LDAP Cache 协同
- Cache 页面空态和可观测性改进

这些能力都不是孤立补丁，而是在已有 Gateway / Agent 架构上形成的一组“可选增强模块”。

## 2. AI 集群助手

### 2.1 目标

为单个集群提供受权限约束的多轮对话助手，让用户能够用自然语言查询：

- 集群状态
- 作业详情
- 节点资源
- 分区、QOS、账户、预约
- 节点和集群指标
- 历史作业数据

### 2.2 启用条件

需要同时满足：

- `[ai] enabled = yes`
- `[database] enabled = yes`
- 数据库已完成最新迁移
- 当前用户拥有 `view-ai` 或 `manage-ai` 权限

### 2.3 数据模型

AI 相关数据存储在数据库中，主要包括：

- `ai_model_configs`：模型配置
- `ai_conversations`：会话头信息
- `ai_messages`：会话消息
- `ai_tool_calls`：工具调用审计记录

关键约束：

- 每个集群可配置多个模型
- 每个集群只能有一个默认模型
- 密钥密文存储，返回前端时只暴露掩码

### 2.4 前端行为

入口与页面：

- 设置页：`/settings/ai`
- 会话页：`/:cluster/ai`
- 兼容重定向：`/:cluster/assistant -> /:cluster/ai`

用户可见能力：

- 模型配置增删改查
- 启用/禁用
- 设置默认模型
- 连接校验
- 多轮会话
- 会话历史恢复
- SSE 流式输出
- 工具调用执行轨迹展示

### 2.5 后端行为

Agent 暴露以下核心接口：

- `GET /v{version}/ai/configs`
- `POST /v{version}/ai/configs`
- `PATCH /v{version}/ai/configs/<id>`
- `DELETE /v{version}/ai/configs/<id>`
- `POST /v{version}/ai/configs/<id>/validate`
- `POST /v{version}/ai/chat/stream`
- `GET /v{version}/ai/conversations`
- `GET /v{version}/ai/conversations/<id>`

Gateway 在 `/api/agents/<cluster>/ai/...` 下做镜像代理。

### 2.6 安全边界

- AI 只能使用只读工具
- 工具执行受用户 RBAC 限制
- AI 不能透传原始 slurmrestd URL
- AI 不能透传原始 PromQL
- AI 不允许执行写操作、删除、提交、取消等变更行为

相关专项文档：

- [AI 需求说明](../features/ai/requirements.md)
- [AI 测试计划](../features/ai/test-plan.md)

## 3. 访问控制增强

### 3.1 目标

在原有文件策略 RBAC 的基础上，引入数据库持久化的“自定义角色 + 用户绑定”能力，满足更灵活的集群授权需求。

### 3.2 启用条件

- `[database] enabled = yes`
- `[persistence] access_control_enabled = yes`

### 3.3 权限合并模型

有效权限来源分三部分：

- `policy`：文件策略角色与动作
- `custom`：数据库自定义角色与动作
- `merged`：两者合并后的最终结果

前端在 `Settings > Account` 和 `Settings > Access Control` 中展示这些来源，便于排查“用户为什么有/没有某个权限”。

### 3.4 页面与交互

入口：

- 设置页标签：`Access Control`

页面能力：

- 自定义角色列表
- 角色创建、编辑、删除
- 基于缓存用户的搜索和分页
- 用户角色绑定编辑
- 只读模式与可编辑模式区分

### 3.5 后端行为

Agent 接口：

- `GET /v{version}/access/roles`
- `POST /v{version}/access/roles`
- `PATCH /v{version}/access/roles/<id>`
- `DELETE /v{version}/access/roles/<id>`
- `GET /v{version}/access/users`
- `GET /v{version}/access/users/<username>/roles`
- `PUT /v{version}/access/users/<username>/roles`

新权限动作：

- `roles-view`
- `roles-manage`

### 3.6 启动刷新机制

Agent 启动时，如果访问控制启用且数据库可用，会根据缓存用户刷新策略快照：

- 更新 `policy_roles`
- 更新 `policy_actions`
- 更新 `permission_synced_at`

这一步不会查询 LDAP，也不会阻塞其他核心功能启动。

相关专项文档：

- [访问控制需求说明](../features/access-control/requirements.md)
- [访问控制测试计划](../features/access-control/test-plan.md)

## 4. 用户分析与集群分析

### 4.1 用户分析

目标：

- 展示某个用户的提交趋势
- 统计工具链使用情况
- 给出日级执行汇总
- 从用户详情页直接跳转历史作业和分析页

入口：

- 用户详情：`/:cluster/users/:user`
- 用户分析：`/:cluster/users/:user/analysis`

启用条件：

- `user_metrics.enabled = yes`
- 数据库、Prometheus、作业历史均可用

数据来源：

- `job_snapshots`
- `user_tool_daily_stats`
- Prometheus 用户指标

相关专项文档：

- [用户分析后端说明](../features/user-analytics/backend.md)

### 4.2 集群分析工作台

目标：

- 把“集群现在忙不忙”和“为什么忙”聚合成一个分析视图
- 辅助判断是容量不足、排队阻塞、策略限制还是资源碎片化

入口：

- `/:cluster/analysis`

页面当前聚合：

- 容量利用率
- 队列阻塞原因
- 分区热点
- 历史压力
- 等待时间样本
- 推荐动作

它同时消费三类数据：

- 实时 `stats/jobs/nodes`
- Prometheus 历史指标
- 历史作业样本

这是当前仓库从“可视化看板”向“分析工作台”演进的关键页面。

## 5. 历史作业、LDAP Cache 与权限联动

### 5.1 历史作业

历史作业页已经不是简单的“数据库列表”，而是一个受 capability 和 permission 同时约束的能力：

- 集群必须启用 `persistence`
- 用户必须拥有 `view-history-jobs`

入口：

- `/:cluster/jobs/history`
- `/:cluster/jobs/history/:id`

### 5.2 LDAP Cache

登录成功后，Gateway 会把认证成功用户推送给支持数据库的 Agent，用于：

- 缓存用户基础信息
- 存储策略快照
- 支撑访问控制页面
- 支撑历史作业和分析页的用户展示

这让系统在历史查询路径上不必每次实时访问 LDAP。

## 6. Cache 页面改进

本轮对 `Settings > Cache` 做了明确的运维体验修正：

- 无流量时不再保留无意义空白区域
- metrics 开启但无样本时显示空态说明
- metrics 关闭时显示原因解释
- 统计区改为更稳定的信息布局

这类修改虽然不涉及后端模型，但直接改善了页面可读性和故障判断效率。

相关专项文档：

- [Cache 需求说明](../features/cache/requirements.md)
- [Cache 测试计划](../features/cache/test-plan.md)

## 7. 这些功能之间的关系

最近功能并不是并列孤岛，而是相互支撑：

- LDAP Cache 为访问控制和历史分析提供稳定用户维度
- 历史作业持久化为用户分析和集群分析提供样本
- 访问控制为 AI 和历史能力提供更细粒度边界
- AI 助手复用已有只读接口和权限模型，而不是自建旁路

因此后续新增能力时，优先复用现有的权限、持久化和 capability 体系，不要重复造新的入口或数据通路。

## 8. 后续文档维护要求

如果继续扩展以上任一能力，必须同步更新：

- [项目说明](./project-overview.md)
- [架构总览](./architecture-overview.md)
- 对应专项设计/测试文档
- `docs/tracking/` 中的当前发布跟踪记录
