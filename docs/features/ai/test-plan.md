# AI 测试计划（端到端）

目标：验证集群侧 AI 助手在 Agent、Gateway、前端、权限与持久化层面端到端可用，并且严格遵守“查询与写接口都按当前用户的 Agent 接口权限执行”的边界。

## 1. 后端覆盖点

执行：

```powershell
.venv\Scripts\python.exe -m pytest
```

重点覆盖：

- Agent `/info` 暴露 `ai` 与 `capabilities.ai`
- Agent 配置项对 AI 行为的影响边界：
  - `ai.max_rounds`
  - `ai.max_history_messages`
  - `ai.stream_chunk_size`
- 模型配置 CRUD、默认模型切换、provider 校验、连接校验
- 密钥掩码返回与 keep/replace/clear 的更新路径
- `ai:view:*` 与 `admin/ai:view|edit|delete:*` 授权边界
- SSE 事件契约与透传一致性
- 会话/消息/工具调用审计的数据库持久化
- AI 工具层改为经 `slurmweb/ai/agent_interfaces.py` 访问 Agent 接口语义，而不是在工具注册表内直连底层实现
- 查询接口权限映射与拒绝逻辑（不允许通过 AI 绕过 `self` / `*` 规则）
- 写接口继续复用 Agent 现有接口权限与 owner-aware 逻辑，拒绝结果要回传给 AI
- 同一 `jwt.key` 下派生出的 AI secret 加密密钥跨重启保持稳定

## 2. 前端覆盖点

执行：

```powershell
npm --prefix frontend run test:unit
```

重点覆盖：

- `GatewayAPI` 的 `/ai/*` 方法、`tool_calls` 详情结构与 SSE 客户端
- `MainMenu` 的 AI 导航门控（capability + `ai:view:*`）
- `SettingsTabs` 的 AI tab 门控（capability + `admin/ai:view:*` / `admin/ai:edit:*`）
- `SettingsAI` 的配置管理流程
- `AssistantView` 的模型选择、流式渲染、历史 trace 回放与折叠式工具轨迹展示
- 路由守卫对 `ai:view:*` / `admin/ai:*` 的约束

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

- 无 `ai:view:*`：不能对话、不能读取会话
- 无 `admin/ai:view:*`：不能读取模型配置列表
- 无 `admin/ai:edit:*` / `admin/ai:delete:*`：不能创建、更新、删除 configs，也不能 validate
- 有 `ai:view:*` 但无底层权限时不能通过 AI 绕过：
  - 无 `jobs:view:*|self`：不能通过 AI 读不允许访问的 live jobs
  - 无 `jobs-history:view:*`：不能通过 AI 读历史作业
  - 无 `resources:view:*`：不能通过 AI 读 node detail / node metrics
- 有写权限的用户可通过 AI 调对应写接口：
  - 例如 `admin` 默认 `*:edit:*` 可执行 `edit` 类 AI 写接口
  - `delete` 仍需显式 `*:delete:*` 或对应资源删除权限
- 仅有 `self` 写权限时：
  - 可操作自己的作业
  - 不能越权操作其他用户对象
- 无对应写权限时，AI 工具调用应返回权限拒绝而不是静默隐藏接口
- 数据库不可用或 AI stores 初始化失败时，AI 端点应返回不可用（即使 RBAC 允许）

### 3.4 SSE 契约

- 事件序列至少包含：`conversation` -> `content`(多次) -> `complete` -> `done`
- 工具执行时包含：`tool_start` / `tool_end`
- `tool_start` / `tool_end` 都带 `interface_key`
- `tool_end` 带 `status_code`
- 失败路径包含：`error`，最终仍然 `done`
- `stream_chunk_size` 只影响 chunk 粒度，不应改变事件类型与语义

### 3.5 多接口串联

- 同一问题允许模型连续调用多个接口后再回答
- 典型最小场景：
  - 先调 `job`
  - 再调 `jobs/history`
  - 最后汇总 live + history 信息
- 若第二个接口仍不足，允许继续追加，但总轮次仍受 `ai.max_rounds` 控制

### 3.6 持久化

- 创建新会话会写入 `ai_conversations`
- 写入 user/assistant 消息到 `ai_messages`
- 每次工具调用写入 `ai_tool_calls`
- `ai_tool_calls` 记录 `interface_key` 与 `status_code`
- 会话列表只返回当前用户
- 会话详情返回历史 `tool_calls`
- 其他用户会话详情不可读取

## 4. 手工验证场景（建议）

- 配置 Qwen/DeepSeek/Kimi（兼容路径）、Ollama、本地 OpenAI-compatible 服务
- 在对话页切换模型并确认实际调用配置生效
- 提问作业 ID / 节点指标 / 历史作业，确认 AI 仅通过 Agent 接口返回事实数据
- 提问单个作业详情时，确认 AI 可以按需串联 `job` + `jobs/history`
- 检查执行轨迹默认仅展示接口名 / 状态码 / 耗时，点击后才显示参数和摘要

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
