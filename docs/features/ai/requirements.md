# AI 功能需求说明（集群侧，受能力与权限门控）

本文描述 Slurm Web Plus 的集群侧 AI 助手能力（Agent 侧装配，Gateway 代理，前端按能力门控显示）。

## 1. 范围

本能力新增/增强点：

- `Settings > AI`：按集群管理模型配置
- `/:cluster/ai`：多轮对话、模型选择、历史会话
- 数据库持久化：模型配置、会话、消息、工具调用审计
- Gateway/Agent `/ai/*` 接口（SSE 透传）
- RBAC 动作：`view-ai`、`manage-ai`
- 只读 AI 工具：复用现有作业/节点/指标/历史接口，并受 RBAC 约束

不在本期范围（未实现，不应写成已完成）：

- 跨集群聚合对话
- 会话删除/导出
- 管理员读取其他用户会话
- 任意 raw API / 任意 raw PromQL 执行

## 2. 核心规则（必须满足）

- 模型配置由前端创建/编辑，通过接口写入数据库。
- 配置粒度按集群隔离，不存在全局继承。
- 同一集群可配置多个模型；同一集群最多一个默认模型。
- 只有“当前集群 + enabled=true”的配置可在对话中被选择。
- Provider 密钥加密存储在数据库中；返回前端时只提供掩码与“是否已配置”状态。
- AI 只能调用内部白名单只读工具；工具执行必须尊重用户 RBAC，并写入审计记录。
- 是否启用 AI 由 Agent 配置决定（`[ai] enabled = yes|no`），而不是前端开关。
- AI 运行时限制（轮数、历史消息数、chunk 大小）为 Agent 侧配置，默认值存在但不暴露为前端可配置项。

## 3. 权限（RBAC）

新增动作（实现事实）：

- `view-ai`：展示 AI 菜单、进入对话页、读取模型列表、读取自己的会话
- `manage-ai`：创建/编辑/删除模型配置、设置默认模型、启用/禁用、校验连接

说明：

- UI 隐藏不等于权限；后端 RBAC 始终是最终裁决。

## 4. 支持的 Provider（实现事实）

当前支持列表（对应 `slurmweb/ai/providers.py`）：

- `openai`
- `azure-openai`
- `anthropic`
- `google`
- `openai-compatible`
- `qwen`
- `deepseek`
- `kimi`
- `ollama`

映射规则（实现事实）：

- `qwen` / `deepseek` / `kimi` 与 `openai-compatible` 走同一 OpenAI-compatible 客户端路径。
- `ollama` 使用独立客户端路径。
- 后端会对不同 provider 的必填字段做校验（例如 `azure-openai` 需要 `base_url` + `deployment`）。

## 5. 数据模型（数据库）

迁移脚本：`slurmweb/alembic/versions/20260424_0006_ai_assistant.py`。

主要表：

- `ai_model_configs`：模型配置（包含密钥密文、默认模型约束、校验时间与错误）
- `ai_conversations`：会话头（cluster、username、title、model_config_id）
- `ai_messages`：会话消息
- `ai_tool_calls`：工具调用审计记录

约束（实现事实）：

- `ai_model_configs`：唯一 `cluster + name`
- 同一集群 `is_default = true` 只能存在一条（通过部分唯一索引实现）

## 6. 接口契约（对齐实现）

### 6.1 Agent 接口（集群内）

- `GET /v{version}/ai/configs`
- `POST /v{version}/ai/configs`
- `PATCH /v{version}/ai/configs/<id>`
- `DELETE /v{version}/ai/configs/<id>`
- `POST /v{version}/ai/configs/<id>/validate`
- `POST /v{version}/ai/chat/stream`（SSE）
- `GET /v{version}/ai/conversations`
- `GET /v{version}/ai/conversations/<id>`

### 6.2 Gateway 代理接口（浏览器只访问 Gateway）

Gateway 镜像代理在：

- `/api/agents/<cluster>/ai/...`

### 6.3 能力暴露

Agent `/info` 与 Gateway `/api/clusters` 必须让前端能判断 AI 是否可用：

- 顶层字段 `ai`
- `capabilities.ai`

AI capability 必备字段（实现事实，来自 `AIService.capabilities()`）：

- `enabled`
- `configurable`
- `streaming`
- `persistence`
- `available_models_count`
- `default_model_id`
- `providers`
- `tool_mode`

## 7. Agent 运行时默认值（实现事实）

- `ai.enabled`：能力开关
- 密钥加密：由 `jwt.key` 派生，不通过前端配置
- 运行时限制（有默认值，允许通过 Agent 配置覆盖）：
  - `max_rounds = 4`
  - `max_history_messages = 24`
  - `stream_chunk_size = 32`

## 8. 请求与 SSE 事件

对话请求示例：

```json
{
  "message": "Which node has the most free resources?",
  "conversation_id": 12,
  "model_config_id": 3
}
```

SSE 事件类型（实现事实）：

- `conversation`
- `content`
- `tool_start`
- `tool_end`
- `complete`
- `error`
- `done`

前端行为要求：

- 从 `content` 增量渲染 assistant 输出
- 通过 `tool_start`/`tool_end` 显示工具轨迹
- 收到 `done` 后刷新会话详情
- 当用户选择了模型时，必须发送明确的 `model_config_id`

## 9. 只读工具边界（必须遵守）

允许的工具白名单（实现事实，见 `slurmweb/ai/tools.py`）覆盖：

- 集群统计（stats）
- 作业列表/详情（jobs/job）
- 节点列表/详情（nodes/node）
- 节点实时/历史指标（node metrics）
- 分区、QOS、预约、账户、关联关系
- 历史作业（当持久化启用时）

禁止项：

- 透传原始 slurmrestd URL
- 透传原始 PromQL
- 写操作（submit/cancel/patch/delete 等任何变更）

## 10. 验收标准（最小集）

- 单集群端到端可用：模型配置 CRUD、默认模型约束、连接校验、会话持久化
- SSE 能从 Agent 经 Gateway 正常透传到浏览器，并包含工具轨迹事件
- 密钥密文存储且响应只返回掩码
- AI 不能绕过底层 RBAC（jobs/nodes/metrics/history 等）

测试计划见：[`docs/features/ai/test-plan.md`](./test-plan.md)。
