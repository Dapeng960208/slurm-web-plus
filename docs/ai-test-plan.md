# Slurm Web Plus AI Test Plan

## Goal

Validate the cluster AI assistant end to end across agent, gateway, frontend, permissions, persistence, and read-only tool boundaries.

## Backend Coverage

Run backend tests with:

```powershell
.venv\Scripts\python.exe -m pytest
```

Primary coverage areas:
- `/info` exposes `ai` and `capabilities.ai`
- `ai.enabled`, `ai.max_rounds`, `ai.max_history_messages`, and `ai.stream_chunk_size` are the only remaining AI-specific agent configuration inputs
- AI model config CRUD
- default model switching
- provider validation and connection validation
- masked secret responses
- keep/replace/clear secret update paths
- `view-ai` and `manage-ai` authorization
- SSE chat stream contract
- conversation persistence
- tool audit persistence
- read-only tool permission mapping
- read-only fallback rejection for unsupported methods
- gateway proxy routes for `/ai/*`
- derived AI encryption key is stable across restarts for the same `jwt.key`
- AI runtime defaults work through agent-side defaulted settings

## Frontend Coverage

Run frontend tests with:

```powershell
npm --prefix frontend run test:unit
```

Primary coverage areas:
- `GatewayAPI` `/ai/*` methods
- `MainMenu` AI navigation gating
- `SettingsTabs` AI tab gating
- `SettingsAI` config management flow
- `AssistantView` model selection and streaming flow
- route-level guards for `view-ai` and `manage-ai`

## Detailed Test Points

### Model Config Management

- list configs returns `items`
- create config succeeds with required fields
- non-Ollama create fails without `api_key`
- update preserves secret when secret is not replaced
- update clears secret when `clear_secret = true`
- setting a new default clears the previous default
- duplicate config name in the same cluster is rejected
- disabled model is not selectable in chat

### Provider Validation

- `openai`
- `azure-openai`
- `anthropic`
- `google`
- `openai-compatible`
- `ollama`
- `qwen`, `deepseek`, `kimi` through compatible path

### Permission Enforcement

- user without `view-ai` cannot read configs, chat, or conversations
- user without `manage-ai` cannot mutate configs or validate
- user with `view-ai` but without `view-jobs` cannot get job details through AI
- user with `view-ai` but without `view-nodes` cannot get node details through AI
- `ai.enabled = false` disables AI endpoints even if RBAC allows them

### SSE Contract

- stream emits `conversation`
- stream emits one or more `content` events
- tool execution emits `tool_start` and `tool_end`
- completion emits `complete`
- stream always terminates with `done`
- provider or runtime failure emits `error`
- configured `stream_chunk_size` changes chunking behavior without changing event contract

### Persistence

- new conversation row is created
- user message row is created
- assistant message row is created
- tool call row is created for each tool execution
- conversation list returns only the current user's rows
- conversation detail for another user is not returned
- previously stored provider secrets remain decryptable as long as `jwt.key` is unchanged

### Gateway

- `/api/clusters` includes `ai`
- `/api/agents/<cluster>/ai/configs`
- `/api/agents/<cluster>/ai/configs/<id>/validate`
- `/api/agents/<cluster>/ai/chat/stream`
- `/api/agents/<cluster>/ai/conversations`
- `/api/agents/<cluster>/ai/conversations/<id>`

### Frontend

- AI menu appears only when cluster capability is enabled and `view-ai` is present
- AI settings tab appears only when cluster capability is enabled and `manage-ai` is present
- settings page loads config list
- settings page submits create/update/delete/validate actions
- chat page loads enabled configs
- chat page sends `model_config_id`
- chat page renders streamed content
- chat page shows tool trace
- chat page reloads conversation detail after completion
- settings page does not expose runtime tuning fields such as encryption key or stream/history limits

## Manual Scenarios

- create configs for Qwen, DeepSeek, Kimi, Ollama, and OpenAI-compatible local service
- switch between models in the chat page and confirm the selected model is used
- ask for a specific job ID and confirm AI returns job details through read-only tools
- ask which node has the most resources and confirm AI combines node and metrics data
- confirm a user without `view-ai` cannot see or open the AI area
- confirm a user with `view-ai` but without underlying data permissions cannot bypass RBAC through AI

## Test Files

Backend:
- `slurmweb/tests/apps/test_agent_ai.py`
- `slurmweb/tests/apps/test_ai_service.py`
- `slurmweb/tests/views/test_agent_ai.py`
- `slurmweb/tests/views/test_gateway_ai.py`

Frontend:
- `frontend/tests/composables/GatewayAPIAIContract.spec.ts`
- `frontend/tests/components/MainMenuAIContract.spec.ts`
- `frontend/tests/components/settings/SettingsTabsAIContract.spec.ts`
- `frontend/tests/views/settings/SettingsAIAIContract.spec.ts`
- `frontend/tests/views/AssistantViewAIContract.spec.ts`
- updated unit specs for `GatewayAPI`, `MainMenu`, `SettingsTabs`, `SettingsAI`, and `AssistantView`
