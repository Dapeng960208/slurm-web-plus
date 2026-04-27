# AI 功能需求说明

## 1. 范围

AI 功能当前覆盖：

- `Settings > AI`
  - 管理模型配置
  - 设置默认模型
  - 连接校验
- `/:cluster/ai`
  - 多轮对话
  - 模型选择
  - 个人会话历史
- 数据库存储：
  - 模型配置
  - 会话
  - 消息
  - 工具调用审计

## 2. 启用条件

AI 当前按数据库能力自动启用：

- `[database] enabled = yes`

说明：

- `ai.enabled` 已从 Agent 配置契约中删除。
- 数据库不可用时，AI 不会对外暴露能力。
- AI 能否启用只取决于数据库、模型配置存储和会话存储是否成功初始化。

## 3. 权限要求

当前页面与接口权限如下：

| 页面/接口 | 新规则 |
|---|---|
| `/:cluster/ai` | `ai:view:*` |
| `/:cluster/admin/ai` 查看 | `admin/ai:view:*` |
| `/:cluster/admin/ai` 新增/修改 | `admin/ai:edit:*` |
| `/:cluster/admin/ai` 删除 | `admin/ai:delete:*` |
| 拥有 `*:*:*` 的 super-admin | 自动满足以上全部权限 |

收口说明：

- `view-ai` 与 `manage-ai` 已不再作为可配置动作入口，也不会再出现在 `/permissions.actions` 或角色页兼容动作列表中。
- `admin-manage` 只是 `*:*:*` 的兼容别名，不是 AI 专属权限。

由于 `edit` 自动满足 `view`，只有编辑权限的用户仍可打开设置页。

## 4. 能力暴露

前端通过以下字段判断 AI 状态：

- Agent `/info.ai`
- Agent `/info.capabilities.ai`
- Gateway `/api/clusters[].ai`
- Gateway `/api/clusters[].capabilities.ai`

## 5. 运行约束

当前实现已经调整为：

- AI 工具层不再直接把 `slurmrestd` / store 暴露给模型，而是统一走 Agent 进程内的接口适配层
- 对模型暴露的是“接口能力目录”，每个接口只说明：
  - 能查询或写入什么
  - 需要哪些输入
  - 是否为写接口
- 模型可在同一轮问题处理中连续调用多个接口，例如：
  - 先查 `job`
  - 再查 `jobs/history`
  - 最后汇总回答
- 系统提示词不再把“某个问题必须调用某个接口”写死，而是要求模型基于信息缺口自行选择接口
- 模型不得编造集群数据；若现有接口信息不足，必须明确说明不确定性

当前首批对 AI 开放的查询接口包括：

- `stats`
- `jobs` / `job`
- `jobs/history` / `jobs/history/detail`
- `nodes` / `node`
- `node/metrics` / `node/metrics/history`
- `partitions`
- `qos`
- `reservations`
- `accounts` / `account`
- `associations`
- `users` / `user`
- `user/metrics/history`
- `user/activity/summary`

边界：

- 不向 AI 暴露 `/ai/*` 自身、`/permissions`、登录、静态资源、二进制绘图等递归或无意义接口
- 查询接口权限继续复用 Agent 现有规则与 owner-aware 逻辑
- 写接口也走 Agent 接口层的实时权限校验：
  - `admin` 默认的 `*:edit:*` 可通过 AI 执行对应 `edit` 类写接口
  - `delete`、`self` 等边界继续按当前用户实际规则与 owner-aware 逻辑判断
  - 普通用户若没有对应接口权限，AI 调用会收到拒绝响应，不能绕过接口层限制
- 密钥只返回掩码和配置状态
- 会话默认仅允许当前用户读取自己的记录

## 6. 相关实现

- 后端接口：`slurmweb/views/agent.py`
- AI 接口适配层：`slurmweb/ai/agent_interfaces.py`
- AI 工具编排：`slurmweb/ai/tools.py`
- 前端设置页：`frontend/src/views/settings/SettingsAI.vue`
- 前端对话页：`frontend/src/views/AssistantView.vue`

## 7. 执行轨迹

AI 执行轨迹当前按“工具 + 命中接口”双层记录：

- SSE `tool_start` / `tool_end` 事件都会带 `interface_key`
- `tool_end` 额外带 `status_code`
- 会话详情接口会返回历史 `tool_calls`
- `ai_tool_calls` 当前至少持久化：
  - `tool_name`
  - `permission`
  - `interface_key`
  - `status_code`
  - `input_payload`
  - `result_summary`
  - `status`
  - `error`
  - `duration_ms`

前端 `AssistantView` 默认只展示：

- 工具名
- 命中接口
- 状态码
- 耗时

参数、摘要和错误详情需要点击单条 trace 后展开查看。
