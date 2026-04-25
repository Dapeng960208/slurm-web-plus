# AI 测试计划（端到端）

目标：验证集群侧 AI 助手在 Agent、Gateway、前端、权限与持久化层面端到端可用，并且严格遵守只读工具边界与 RBAC。

## 1. 后端覆盖点

执行：

```powershell
.venv\Scripts\python.exe -m pytest
```

重点覆盖：

- Agent `/info` 暴露 `ai` 与 `capabilities.ai`
- Agent 配置项对 AI 行为的影响边界：
  - `ai.enabled`
  - `ai.max_rounds`
  - `ai.max_history_messages`
  - `ai.stream_chunk_size`
- 模型配置 CRUD、默认模型切换、provider 校验、连接校验
- 密钥掩码返回与 keep/replace/clear 的更新路径
- `view-ai` / `manage-ai` 授权边界
- SSE 事件契约与透传一致性
- 会话/消息/工具调用审计的数据库持久化
- 只读工具的权限映射与拒绝逻辑（不允许执行未授权或不在白名单的工具）
- 同一 `jwt.key` 下派生出的 AI secret 加密密钥跨重启保持稳定

## 2. 前端覆盖点

执行：

```powershell
npm --prefix frontend run test:unit
```

重点覆盖：

- `GatewayAPI` 的 `/ai/*` 方法与 SSE 客户端
- `MainMenu` 的 AI 导航门控（capability + `view-ai`）
- `SettingsTabs` 的 AI tab 门控（capability + `manage-ai`）
- `SettingsAI` 的配置管理流程
- `AssistantView` 的模型选择、流式渲染与工具轨迹展示
- 路由守卫对 `view-ai` / `manage-ai` 的约束

## 3. 详细测试点（建议最小集）

### 3.1 模型配置管理

- 列表接口返回 `items`
- 创建配置：必填字段缺失时返回 400
- `ollama` 创建允许不提供 `api_key`；其他 provider 创建缺少 `api_key` 时失败
- 更新配置：不替换密钥时保持原密钥；`clear_secret=true` 时清除密钥
- 设置新默认模型后，旧默认模型自动取消默认
- 同集群重复 `name` 被拒绝
- disabled 模型不能在对话中被选择

### 3.2 Provider 校验

覆盖至少：

- `openai`、`azure-openai`、`anthropic`、`google`
- `openai-compatible`（含 `qwen` / `deepseek` / `kimi` 走兼容路径）
- `ollama`

### 3.3 权限与门控

- 无 `view-ai`：不能读取 configs、不能对话、不能读取会话
- 无 `manage-ai`：不能创建/更新/删除 configs，不能 validate
- 有 `view-ai` 但无底层权限时不能通过 AI 绕过：
  - 无 `view-jobs`：不能通过工具读 job detail
  - 无 `view-nodes`：不能通过工具读 node detail / node metrics
- `ai.enabled = false` 时，AI 端点应返回不可用（即使 RBAC 允许）

### 3.4 SSE 契约

- 事件序列至少包含：`conversation` -> `content`(多次) -> `complete` -> `done`
- 工具执行时包含：`tool_start` / `tool_end`
- 失败路径包含：`error`，最终仍然 `done`
- `stream_chunk_size` 只影响 chunk 粒度，不应改变事件类型与语义

### 3.5 持久化

- 创建新会话会写入 `ai_conversations`
- 写入 user/assistant 消息到 `ai_messages`
- 每次工具调用写入 `ai_tool_calls`
- 会话列表只返回当前用户
- 其他用户会话详情不可读取

## 4. 手工验证场景（建议）

- 配置 Qwen/DeepSeek/Kimi（兼容路径）、Ollama、本地 OpenAI-compatible 服务
- 在对话页切换模型并确认实际调用配置生效
- 提问作业 ID/节点指标/历史作业，确认 AI 仅通过工具返回事实数据

## 5. 相关测试文件（已存在）

后端：

- `slurmweb/tests/apps/test_agent_ai.py`
- `slurmweb/tests/apps/test_ai_service.py`
- `slurmweb/tests/views/test_agent_ai.py`
- `slurmweb/tests/views/test_gateway_ai.py`

前端：

- `frontend/tests/composables/GatewayAPIAIContract.spec.ts`
- `frontend/tests/components/MainMenuAIContract.spec.ts`
- `frontend/tests/components/settings/SettingsTabsAIContract.spec.ts`
- `frontend/tests/views/settings/SettingsAIAIContract.spec.ts`
- `frontend/tests/views/AssistantViewAIContract.spec.ts`
