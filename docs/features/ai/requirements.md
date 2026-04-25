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

- 旧 `ai.enabled` 仅保留兼容占位定义，不再作为实际业务语义来源。
- 数据库不可用时，AI 不会对外暴露能力。
- 如果站点配置里显式写了 `[ai] enabled = yes`，但数据库初始化失败，Agent 会额外输出 “AI assistant is enabled but database support is unavailable” 告警，便于排障。

## 3. 权限要求

当前页面与接口权限如下：

| 页面/接口 | 新规则 |
|---|---|
| `/:cluster/ai` | `ai:view:*` |
| `/:cluster/admin/ai` 查看 | `admin/ai:view:*` |
| `/:cluster/admin/ai` 新增/修改 | `admin/ai:edit:*` |
| `/:cluster/admin/ai` 删除 | `admin/ai:delete:*` |

旧权限兼容：

- `view-ai` -> `ai:view:*` + `admin/ai:view:*`
- `manage-ai` -> `admin/ai:view:*` + `admin/ai:edit:*` + `admin/ai:delete:*`

由于 `edit` 自动满足 `view`，只有编辑权限的用户仍可打开设置页。

## 4. 能力暴露

前端通过以下字段判断 AI 状态：

- Agent `/info.ai`
- Agent `/info.capabilities.ai`
- Gateway `/api/clusters[].ai`
- Gateway `/api/clusters[].capabilities.ai`

## 5. 运行约束

当前仍然保持：

- 仅允许白名单只读工具
- 工具执行继续受底层权限控制
- 密钥只返回掩码和配置状态
- 会话默认仅允许当前用户读取自己的记录

## 6. 相关实现

- 后端接口：`slurmweb/views/agent.py`
- 前端设置页：`frontend/src/views/settings/SettingsAI.vue`
- 前端对话页：`frontend/src/views/AssistantView.vue`
