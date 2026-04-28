# AI 审计与指标时间窗优化需求

## 1. 背景与目标

本轮开发目标是收敛两类用户可感知问题：

- 指标时间窗选择需要从页面内常驻输入框改为按钮触发的弹框，并在节点详情与用户工具分析页面保持一致。
- AI 对话需要降低普通用户页面配置噪音，补充管理员审计能力、逻辑删除能力、消息复制能力，并修复 `association/update` 写入返回成功但集群未生效的问题。

本文为本轮开发需求与实现说明。当前代码已落地本页描述的行为，验证入口见同目录 `test-plan.md`。

## 2. 功能范围

### 2.1 指标时间窗弹框

- `/:cluster/node/:nodeName` 右侧 `Real Metrics` 区域新增时间选择按钮。
- 点击按钮后弹出时间范围选择框，用户可指定起止时间。
- 起止时间输入精确到时分。
- 应用后刷新节点实时指标历史数据，并把 `start` / `end` 同步到 URL query。
- 用户工具分析页面使用同一交互形态：
  - 点击按钮打开弹框。
  - 起止时间精确到时分。
  - 弹框内置 `1 day`、`3 days`、`7 days`、`15 days`、`1 month` 快捷窗口。
  - 应用后刷新 `Submission Activity`、`Usage Profile`、`Tool Analysis` 与 `Top Tools`。

### 2.2 AI 对话页面精简

- 普通 `/:cluster/ai` 对话页顶部不再展示模型、stream 等运行配置。
- 相关配置保留在 `/:cluster/admin/ai` 页面查看和维护。
- 右侧工具调用记录的接口名、状态、耗时、参数摘要等文本不得堆叠或重叠。

### 2.3 AI 会话审计

- `/:cluster/admin/ai` 管理页可查看所有用户的 AI 对话记录。
- 管理员审计视图应能区分会话所属用户、创建/更新时间、删除状态与消息/工具调用详情。
- 普通用户仍只能查看自己的未删除会话。

### 2.4 AI 会话逻辑删除

- 用户可对自己的 AI 会话执行逻辑删除。
- 逻辑删除不物理删除数据库记录。
- 普通用户会话列表和详情不展示已由用户逻辑删除的内容。
- 管理员审计视图展示逻辑删除内容，并标识删除状态。

### 2.5 AI 消息复制

- AI 对话中用户消息与 AI 回复都提供复制快捷操作。
- 复制内容应以原始消息文本为准，不复制页面装饰文本。

### 2.6 AI 配置页交互优化

- `/:cluster/admin/ai` 的模型配置创建与编辑通过点击按钮打开弹窗完成。
- 已有配置在管理页以紧凑标签/胶囊式条目展示，减少卡片网格和表单常驻占用。
- 每个配置标签展示 provider、配置名、模型名、启用状态、默认状态、密钥掩码和校验状态等核心信息。
- 配置标签支持编辑、设置默认、校验连接和删除。
- 删除配置仍要求 `admin/ai:delete:*` 权限。

### 2.7 AI 审计搜索与详情加载

- `/:cluster/admin/ai` 的 Conversation Audit 支持按用户名和关键字搜索。
- 当前实现为前端本地过滤，关键字匹配已加载审计摘要中的会话标题与最后消息；未新增后端全文检索参数。
- 审计详情不再默认自动展开首条记录；只有点击某条对话后才加载并展示详情。
- 搜索条件变化后，如果当前详情不在筛选结果中，会清空当前详情，避免误以为正在查看筛选结果中的第一条。

### 2.8 AI 对话 token 计数与超限提示

- 普通 `/:cluster/ai` 对话输入区展示前端估算 token 数量。
- 估算范围包含当前模型 `system_prompt`、当前会话历史消息和输入框草稿。
- 限制优先读取模型配置 `extra_options` 中的 `max_context_tokens`、`context_limit`、`token_limit`、`max_tokens`，否则使用前端默认 `8192`。
- 当估算上下文超过限制时，前端给出明确提示，并禁用发送；提交事件也会阻止请求。
- 当前后端 SSE 与会话记录尚未返回真实 provider token usage，因此页面展示的是估算值而非供应商计费值。

### 2.9 `association/update` 写入修复

- 定位 AI 调用 `association/update` 给 `ip-user` 添加 `guojianpeng` 后未在账户页和集群管理端生效的根因。
- 判断问题属于：
  - 接口 payload 与 SlurmDB API 契约不一致。
  - 写接口返回结果判断不严格。
  - 写入成功后缺少缓存刷新或核心后续步骤。
  - 其他后端适配缺陷。
- 已定位根因并修复：
  - AI 通过 Agent 写入 `association/update` 时，模型生成的 payload 可能缺少 SlurmDB association 写入所需的 `cluster` 上下文。
  - 写入后 `accounts` / `associations` 缓存未失效时，账户页可能继续展示旧数据。
- 修复后，后端会为 association 写入 payload 补齐当前集群，并在 account/user/association/qos 写入或删除后失效相关缓存。

## 3. 启用条件

- 指标时间窗依赖现有 metrics / user analytics capability。
- AI 审计、逻辑删除与会话记录依赖数据库与 AI stores 可用。
- 管理员审计入口依赖 `admin/ai:view:*`。

## 4. 页面与接口

- 用户 AI 对话页：`/:cluster/ai`
- 管理员 AI 页：`/:cluster/admin/ai`
- 节点详情页：`/:cluster/node/:nodeName`
- 用户页面与分析锚点：`/:cluster/users/:user`、`/:cluster/me`
- AI 用户接口：
  - `GET /api/agents/<cluster>/ai/conversations`
  - `GET /api/agents/<cluster>/ai/conversations/<conversation_id>`
  - `DELETE /api/agents/<cluster>/ai/conversations/<conversation_id>`
  - `POST /api/agents/<cluster>/ai/chat/stream`
- AI 管理员审计接口：
  - `GET /api/agents/<cluster>/ai/admin/conversations`
  - `GET /api/agents/<cluster>/ai/admin/conversations/<conversation_id>`
- AI 配置接口：
  - `GET /api/agents/<cluster>/ai/configs`
  - `POST /api/agents/<cluster>/ai/configs`
  - `PUT /api/agents/<cluster>/ai/configs/<config_id>`
  - `DELETE /api/agents/<cluster>/ai/configs/<config_id>`
- 节点指标历史接口：
  - `GET /api/agents/<cluster>/node/<node>/metrics/history`
  - 支持 `range=hour|day|week`
  - 支持 `start` / `end` ISO 8601 自定义窗口

## 5. 权限要求

- 普通对话：`ai:view:*`
- 管理员 AI 配置与审计查看：`admin/ai:view:*`
- 管理员 AI 配置变更：`admin/ai:edit:*`
- 管理员 AI 配置删除：`admin/ai:delete:*`
- `association/update` 继续复用 `accounts:edit:*` 权限，不允许通过 AI 绕过底层接口权限。

## 6. 数据模型或依赖

- AI 会话、消息、工具调用继续使用现有数据库 store。
- 逻辑删除在 `ai_conversations` 记录：
  - `deleted_at`
  - `deleted_by`
- 审计视图不得依赖前端隐藏实现安全边界，后端查询必须按普通用户与管理员场景区分。
- `association/update` 继续走 Agent 接口适配层和 `slurmrestd` 写接口：
  - association 写入 payload 会按当前集群补齐 `cluster`
  - 写入成功后会失效 `accounts` 与 `associations` 缓存

## 7. 降级行为与边界

- 数据库不可用时 AI 会话、审计与逻辑删除不可用。
- 管理员没有 `admin/ai:view:*` 时不能进入审计视图。
- 普通用户删除会话后不再看到该会话，但管理员审计仍可看到。
- Conversation Audit 搜索当前只过滤已加载的会话摘要；若未来需要搜索全部消息正文，应扩展管理员审计接口的查询参数与后端检索能力。
- AI token 计数是前端估算，不替代后端 provider usage，也不代表最终账单 token。
- 指标时间窗非法时前端会阻止提交或显示明确错误，不发送无效请求；后端也会对非法 `start` / `end` 返回 `400`。
- 如果 `association/update` 底层写入未被 SlurmDB 接受，接口不得把 warning/error 伪装成业务成功；写入后的缓存必须失效，避免页面读取旧状态。

## 8. 相关测试入口

- 前端组件与页面测试：`frontend/tests/**`
- AI 后端测试：`slurmweb/tests/apps/test_ai_service.py`、`slurmweb/tests/views/test_agent_ai.py`、`slurmweb/tests/views/test_gateway_ai.py`
- Slurm REST 写入适配测试：`slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py`
- 缓存失效测试：`slurmweb/tests/test_cache.py`
