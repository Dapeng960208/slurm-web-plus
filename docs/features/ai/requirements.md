# AI 功能需求说明

## 1. 范围

AI 功能当前覆盖：

- `/:cluster/admin/ai`
  - 管理模型配置
  - 设置默认模型
  - 连接校验
  - 查看所有用户 AI 会话审计记录
  - 按用户名和摘要关键字过滤审计记录，点击记录后加载详情
- `/:cluster/ai`
  - 多轮对话
  - 个人会话历史
  - 会话逻辑删除
  - 用户消息与 assistant 回复复制
  - 输入区展示 token 估算和超限提示
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

由于 `edit` 自动满足 `view`，只有编辑权限的用户仍可打开管理页。

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
- `user/tools/analysis`

其中 `user/tools/analysis` 现在明确用于承载用户维度的聚合资源证据，例如：

- `totals.avg_max_memory_mb`
- `totals.avg_cpu_cores`
- `totals.avg_runtime_seconds`
- `tool_breakdown[].avg_max_memory_mb`
- `tool_breakdown[].avg_cpu_cores`
- `tool_breakdown[].avg_runtime_seconds`

因此当问题是“某个用户常用工具推荐多少内存/CPU/运行时”这类推荐题时，AI 应优先把它视为直接证据源；只有聚合证据不足时，才继续补查 `jobs/history` 等原始历史接口。

边界：

- 不向 AI 暴露 `/ai/*` 自身、`/permissions`、登录、静态资源、二进制绘图等递归或无意义接口
- 查询接口权限继续复用 Agent 现有规则与 owner-aware 逻辑
- 写接口也走 Agent 接口层的实时权限校验：
  - `admin` 默认的 `*:edit:*` 可通过 AI 执行对应 `edit` 类写接口
  - `delete`、`self` 等边界继续按当前用户实际规则与 owner-aware 逻辑判断
  - 普通用户若没有对应接口权限，AI 调用会收到拒绝响应，不能绕过接口层限制
- 密钥只返回掩码和配置状态
- 会话默认仅允许当前用户读取自己的记录
- 普通对话页不展示模型、stream、persistence 等运行配置；模型配置查看与维护统一收口到 `/:cluster/admin/ai`
- 普通对话页发送请求时继续使用后端默认模型或当前会话已有模型，不把配置项作为页面主控件暴露给用户
- 普通用户会话列表和详情只返回本人且未逻辑删除的会话
- 管理员审计接口返回所有用户会话，包含已逻辑删除会话
- 用户逻辑删除会话后只写入删除状态，不物理删除会话、消息或工具调用记录
- AI 对话页 token 数为前端估算值，包含模型 `system_prompt`、当前会话历史消息与输入草稿；限制优先读取模型配置 `extra_options.max_context_tokens`、`context_limit`、`token_limit`、`max_tokens`，否则使用默认 `8192`
- 当前后端不返回真实 provider token usage，前端估算不等同于供应商计费或精确 tokenizer 结果

## 6. 相关实现

- 后端接口：`slurmweb/views/agent.py`
- Gateway AI 代理：`slurmweb/views/gateway.py`
- AI 接口适配层：`slurmweb/ai/agent_interfaces.py`
- AI 工具编排：`slurmweb/ai/tools.py`
- 前端设置页：`frontend/src/views/settings/SettingsAI.vue`
- 前端对话页：`frontend/src/views/AssistantView.vue`

当前 `AssistantView` 的消息展示规则为：

- `assistant` 消息按安全 Markdown 渲染
- `user` 消息也按安全 Markdown 渲染
- 渲染链路固定为“Markdown 解析 -> HTML 清洗 -> 前端渲染”
- 工具成功后只会把“工具结果提示”写回模型上下文，不会把内部 `tool_request` / `interface_key` / `arguments` envelope 直接当作最终回答透传给用户
- 最终用户可见回答必须是 `{"type":"final","content":"..."}` 语义；若模型错误回显内部 envelope，服务端会继续纠正并要求其输出合法 `final`
- 原始 HTML 片段不是受支持输入：
  - 不会作为真实 HTML 节点插入页面
  - 不允许通过消息内容注入脚本或事件属性
- Markdown 链接默认新标签打开，并带 `rel="noopener noreferrer"`
- 用户消息与 assistant 回复都提供复制按钮，复制内容为原始消息正文。
- 用户可逻辑删除自己的会话；删除后普通列表与普通详情不再展示该会话，管理员审计仍可查看。
- 输入区显示当前估算 token 用量；超过限制时显示提示、禁用发送按钮，并阻止提交流式请求。

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

## 8. 管理员会话审计

`/:cluster/admin/ai` 现在除模型配置外，还提供 Conversation Audit 区域：

- 列出当前集群所有 AI 会话
- 展示 `username`、标题、创建/更新时间、删除状态
- 可按用户名过滤审计摘要
- 可按标题或最后消息关键字过滤审计摘要
- 默认不自动打开第一条记录，需点击会话后才加载详情
- 可打开会话详情查看消息与工具调用记录
- 已删除会话显示 `deleted_at` 与 `deleted_by`

对应接口：

- `GET /api/agents/<cluster>/ai/admin/conversations`
- `GET /api/agents/<cluster>/ai/admin/conversations/<conversation_id>`

这两个接口要求 `admin/ai:view:*`，不能用普通 `ai:view:*` 访问。

## 9. `association/update` 写入边界

AI 写接口调用 `association/update` 时继续复用 Agent 写接口权限，典型权限为 `accounts:edit:*`。

本轮修复了两类导致“接口返回成功但账户页和集群管理端未体现”的问题：

- association payload 缺少 `cluster` 时，`slurmrestd` 适配层会按当前集群补齐。
- account/user/association/qos 写入或删除后，缓存层会失效 `accounts` 与 `associations` 等相关 key，避免后续页面读取旧缓存。
