# AI 审计与指标时间窗优化测试计划

## 1. 测试目标

验证本轮指标时间窗、AI 页面精简、AI 审计、逻辑删除、消息复制与 `association/update` 修复在前端、后端、权限和持久化层面行为一致。

本文测试点已按本轮实现同步。自动化验证命令见第 5 节。

## 2. 前端测试点

### 2.1 节点 Real Metrics 时间窗

- 页面显示时间范围按钮，而不是常驻的起止时间输入框。
- 点击按钮后弹出选择框。
- 起止时间输入精确到时分。
- 点击应用后：
  - 关闭弹框。
  - 更新 URL query `start` / `end`。
  - 触发节点 metrics history 重新请求。
- 输入 `start >= end` 时：
  - 显示错误。
  - 不触发请求。
- 重置或快捷范围仍能恢复到默认范围。

### 2.2 用户工具分析时间窗

- 用户分析页面使用与节点页面一致的时间范围按钮与弹框。
- 弹框内快捷窗口 `1 day`、`3 days`、`7 days`、`15 days`、`1 month` 可回填起止时间。
- 点击应用后同时刷新：
  - `Submission Activity`
  - `Usage Profile`
  - `Tool Analysis`
  - `Top Tools`
- 首次进入无 query 时仍默认回填当天 `00:00` 到当前时间。
- 刷新页面后保留已应用的起止时间。

### 2.3 AI 对话页展示

- 普通 AI 对话页顶部不展示 model、stream 等配置状态。
- 对话页仍可正常开始新会话、加载会话历史和流式追加回复。
- 工具调用记录中接口名、状态码、耗时、参数摘要不堆叠、不重叠。
- 用户消息与 AI 回复均展示复制按钮。
- 点击复制按钮时写入对应消息原文。

### 2.4 管理员 AI 审计视图

- `/:cluster/admin/ai` 可进入对话审计区域。
- 审计列表展示所有用户会话，而不是仅当前用户。
- 审计列表展示已逻辑删除会话并标识删除状态。
- 默认不自动打开第一条审计详情。
- 点击审计记录后才加载并展示消息与工具调用记录。
- 可按用户名过滤审计列表。
- 可按关键字过滤审计列表，当前匹配已加载摘要中的标题或最后消息。
- 筛选条件排除当前选中会话后，详情区域回到“选择一条记录”状态。

### 2.4.1 管理员 AI 配置视图

- 模型配置创建和编辑通过弹窗完成。
- 配置列表以紧凑标签/胶囊式条目展示已有配置。
- 配置标签展示 provider、配置名、模型名、启用状态、默认状态、密钥掩码和校验状态。
- 配置标签支持编辑、设置默认、校验连接和删除。
- 无 `admin/ai:delete:*` 时不显示或不可用删除操作。

### 2.5 普通用户逻辑删除

- 普通用户可删除自己的会话。
- 删除后会话从普通列表消失。
- 再次访问已删除会话详情时不展示内容或返回不可访问状态。
- 管理员审计视图仍能看到该会话。

### 2.6 AI 对话 token 计数

- 普通 AI 对话输入区展示 token 估算数量。
- 空输入时 token 数为 0。
- 输入内容变化时 token 数同步更新。
- 超过限制时展示明确提示。
- token 限制优先读取模型配置 `extra_options` 中的 `max_context_tokens`、`context_limit`、`token_limit`、`max_tokens`，否则使用默认 `8192`。
- 超限状态下发送按钮不可用，提交事件也会阻止 `stream_ai_chat` 请求。

## 3. 后端测试点

### 3.1 会话列表与详情权限

- 普通 `ai:view:*` 用户只能列出自己的未删除会话。
- 普通用户不能读取其他用户会话。
- 普通用户不能读取自己已逻辑删除的会话。
- 管理员 `admin/ai:view:*` 可列出所有会话，包含逻辑删除会话。
- 管理员可读取逻辑删除会话详情。

### 3.2 逻辑删除持久化

- 删除接口只更新删除状态，不物理删除 `ai_conversations`、`ai_messages`、`ai_tool_calls`。
- 删除状态包含足够审计信息，至少能判断是否已删除。
- 重复删除同一会话应幂等或返回明确错误。

### 3.3 SSE 与消息持久化

- 删除逻辑不影响新会话创建与流式事件顺序。
- 新消息仍写入当前会话。
- 已删除会话不应继续作为普通用户默认上下文继续追加消息。

### 3.4 `association/update` 修复

- AI 接口适配层传入的 payload 与 Agent `/associations` 写接口一致。
- 给 account `ip-user` 添加 user `guojianpeng` 的 payload 应符合 SlurmDB associations 写入契约。
- 底层 SlurmDB 返回 warning/error 时，接口结果不得标记为无条件成功。
- association 写入 payload 缺少 `cluster` 时，适配层应按当前集群补齐。
- 成功写入后，`accounts` 与 `associations` 缓存应失效，后续查询应重新读取底层状态。

## 4. 权限测试点

- 无 `ai:view:*` 不能进入普通 AI 对话页或调用普通会话接口。
- 无 `admin/ai:view:*` 不能调用审计列表与审计详情。
- `admin/ai:view:*` 不自动授予模型配置编辑或删除能力。
- `association/update` 仍要求 `accounts:edit:*`。

## 5. 建议自动化命令

前端定向测试：

```powershell
cd frontend
npx vitest run tests/components/MetricRangeSelector.spec.ts tests/views/AssistantView.spec.ts tests/views/settings/SettingsAI.spec.ts tests/views/NodeView.spec.ts tests/views/UserAnalysisView.spec.ts tests/components/user/UserToolAnalysisChart.spec.ts tests/composables/GatewayAPI.spec.ts
```

本次 AI 配置、审计搜索与 token 估算定向验证：

```powershell
cd frontend
npx vitest run tests/views/settings/SettingsAI.spec.ts tests/views/AssistantView.spec.ts
```

前端类型检查：

```powershell
npm --prefix frontend run type-check
```

后端定向测试：

```powershell
.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_ai_service.py slurmweb/tests/apps/test_user_analytics_store.py slurmweb/tests/views/test_agent_ai.py slurmweb/tests/views/test_gateway_ai.py slurmweb/tests/views/test_agent_metrics_requests.py slurmweb/tests/slurmrestd/test_slurmrestd_write_operations.py slurmweb/tests/test_cache.py
```

## 6. 手工验收场景

- 在节点详情页选择一个自定义起止时间，刷新页面后确认 metrics 范围保持一致。
- 在用户工具分析页选择相同时间窗，确认统计卡、趋势图和工具列表共同变化。
- 普通用户创建 AI 会话后删除，确认普通列表不可见。
- 管理员进入 `Admin > AI`，确认能看到上述已删除会话。
- 让 AI 执行“给 `ip-user` 添加用户 `guojianpeng`”，确认接口返回、账户页面和集群管理端结果一致。
