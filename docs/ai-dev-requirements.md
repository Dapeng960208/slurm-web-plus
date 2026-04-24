# Slurm Web Plus AI Development Requirements

## Scope

This delivery adds a cluster-scoped AI assistant to Slurm Web Plus.

Included:
- `Settings > AI` for per-cluster model configuration management
- `/:cluster/ai` for multi-turn chat with model selection and history
- database-backed model configs and conversation persistence
- gateway and agent `/ai/*` APIs
- RBAC actions `view-ai` and `manage-ai`
- read-only AI tool access to Slurm REST and Prometheus-backed data

Out of scope for v1:
- cross-cluster aggregation
- conversation delete/export
- admin access to other users' conversations
- arbitrary raw API execution

## Core Rules

- AI model configs are managed from the frontend and stored in the database.
- Config scope is per cluster. There is no global inheritance.
- A cluster can have multiple model configs.
- Only enabled configs of the current cluster can be selected in chat.
- A cluster can have at most one default model.
- Provider secrets are encrypted in the database and only returned as masked summaries.
- AI can only perform read-only queries.
- AI tool calls must respect user RBAC and be audited.
- Agent configuration controls whether AI is enabled for the cluster.
- AI runtime limits remain agent-side settings with default values and are not exposed as frontend-configurable settings.

## RBAC

New actions:
- `view-ai`: show AI menu entry, access chat page, read model list, read own conversations
- `manage-ai`: create/update/delete model configs, set default model, enable/disable configs, run validation

UI and route guards must not rely on menu hiding alone. Backend RBAC remains authoritative.

## Supported Providers

First release provider list:
- `openai`
- `azure-openai`
- `anthropic`
- `google`
- `qwen`
- `deepseek`
- `kimi`
- `openai-compatible`
- `ollama`

Mapping rules:
- `qwen`, `deepseek`, `kimi`, and generic local compatible endpoints use the OpenAI-compatible client path
- `ollama` is handled as a dedicated provider
- frontend renders provider-specific fields
- backend validates provider-specific constraints

## Database Model

### `ai_model_configs`

Fields:
- `cluster`
- `name`
- `provider`
- `model`
- `display_name`
- `enabled`
- `is_default`
- `sort_order`
- `base_url`
- `deployment`
- `api_version`
- `request_timeout`
- `temperature`
- `system_prompt`
- `extra_options`
- encrypted secret fields
- validation timestamps and last validation error

Constraints:
- unique `cluster + name`
- unique default config per cluster

### `ai_conversations`

Fields:
- `cluster`
- `username`
- `title`
- `model_config_id`
- timestamps

### `ai_messages`

Fields:
- `conversation_id`
- `role`
- `content`
- `model_config_id`
- `metadata`
- timestamp

### `ai_tool_calls`

Fields:
- `conversation_id`
- `message_id`
- `cluster`
- `username`
- `tool_name`
- `permission`
- `input_payload`
- `result_summary`
- `status`
- `error`
- `duration_ms`
- timestamp

## Backend API Contract

Agent endpoints:
- `GET /v{version}/ai/configs`
- `POST /v{version}/ai/configs`
- `PATCH /v{version}/ai/configs/<id>`
- `DELETE /v{version}/ai/configs/<id>`
- `POST /v{version}/ai/configs/<id>/validate`
- `POST /v{version}/ai/chat/stream`
- `GET /v{version}/ai/conversations`
- `GET /v{version}/ai/conversations/<id>`

Gateway mirrors these under:
- `/api/agents/<cluster>/ai/...`

`/info` must expose:
- top-level `ai`
- `capabilities.ai`

Required capability fields:
- `enabled`
- `configurable`
- `streaming`
- `persistence`
- `available_models_count`
- `default_model_id`
- `providers`
- `tool_mode`

## Agent Runtime Defaults

- `ai.enabled` remains the feature switch used to expose AI APIs and UI capability.
- AI secret encryption key is derived internally from the existing `jwt.key` file.
- Runtime limits remain defined in agent configuration with vendor defaults:
  - `max_rounds = 4`
  - `max_history_messages = 24`
  - `stream_chunk_size = 32`
- These values are not editable from the frontend and are not stored in the database.

## Chat Request and SSE

Chat request payload:

```json
{
  "message": "Which node has the most free resources?",
  "conversation_id": 12,
  "model_config_id": 3
}
```

SSE events:
- `conversation`
- `content`
- `tool_start`
- `tool_end`
- `complete`
- `error`
- `done`

Frontend behavior:
- stream incremental assistant content from `content`
- show tool trace from `tool_start` and `tool_end`
- refresh conversation detail after `done`
- always send explicit `model_config_id` when a model is selected

## Read-Only Tool Boundary

Allowed white-listed tools:
- cluster stats
- job list/detail
- node list/detail
- node instant/history metrics
- partitions
- qos
- reservations
- accounts
- associations
- job history when enabled

Fallback rules:
- fallback can call only a strict internal read-only whitelist
- no raw slurmrestd URL passthrough
- no raw PromQL passthrough
- no write, patch, delete, submit, cancel, or mutate operations

## Frontend Requirements

### Settings Page

`/settings/ai` must support:
- config list
- create dialog
- edit dialog
- provider-specific form fields
- enable/disable
- set default
- validate connection
- masked secret editing with keep/replace/clear modes
- link to the current cluster chat page

### Chat Page

`/:cluster/ai` must support:
- model selector
- conversation list
- conversation resume
- new conversation
- SSE streaming
- tool trace display
- retry after failure

### Route and Navigation

- main menu item name: `AI`
- cluster route name: `ai`
- legacy `/:cluster/assistant` may redirect to `/:cluster/ai`
- settings tab name: `AI`

## Delivery Split

DEV owns:
- this document
- backend models, stores, migration, crypto, AI service, tool registry, gateway proxy
- frontend `GatewayAPI`, menu, route, settings page, chat page

Test owns:
- `docs/ai-test-plan.md`
- backend pytest
- frontend Vitest

## Acceptance

- AI config management works end to end for a single cluster
- multiple provider configs can coexist in one cluster
- one default model per cluster is enforced
- secrets are encrypted at rest and masked in responses
- chat page selects enabled cluster models only
- SSE chat and tool trace work through the gateway
- AI cannot bypass underlying RBAC on jobs, nodes, metrics, or history
- only the current user's conversations are visible
- no provider or model list is sourced from agent config; only the AI switch and runtime limits remain agent-side
