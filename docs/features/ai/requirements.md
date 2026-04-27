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

当前仍然保持：

- 仅允许白名单只读工具
- 工具执行继续受底层权限控制
- 密钥只返回掩码和配置状态
- 会话默认仅允许当前用户读取自己的记录

## 6. 相关实现

- 后端接口：`slurmweb/views/agent.py`
- 前端设置页：`frontend/src/views/settings/SettingsAI.vue`
- 前端对话页：`frontend/src/views/AssistantView.vue`
