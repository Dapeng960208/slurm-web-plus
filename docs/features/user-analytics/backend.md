# 用户分析后端与页面契约

## 1. 启用条件

用户分析当前按基础依赖自动推导：

- 数据库开启
- metrics 开启

两者同时满足时，Agent 会对外暴露：

- `user_metrics`
- `user_analytics`

`persistence.enabled` 与 `user_metrics.enabled` 已从 Agent 配置契约中删除，用户分析能力只按数据库 + metrics 自动推导。

## 2. 数据来源

当前仍复用既有接口与聚合数据：

- `GET /api/agents/<cluster>/user/<username>/tools/analysis`
- `GET /api/agents/<cluster>/user/<username>/metrics/history`
- `GET /api/agents/<cluster>/associations`

`tools/analysis` 当前固定要求：

- `start`
- `end`

两者都必须是 ISO 8601 时间；缺失、非法或 `start >= end` 时返回 `400`。

`tools/analysis` 当前返回：

- `username`
- `profile`
- `generated_at`
- `window`
  - `start`
  - `end`
- `totals`
  - `completed_jobs`
  - `active_tools`
  - `avg_max_memory_mb`
  - `avg_cpu_cores`
  - `avg_runtime_seconds`
  - `busiest_tool`
  - `busiest_tool_jobs`
- `tool_breakdown`

`metrics/history` 当前返回：

- `window`
  - `start`
  - `end`
- `totals`
  - `submitted_jobs`
  - `completed_jobs`
- `submissions`
  - 按所选时间范围聚合的提交作业数序列
- `completions`
  - 按所选时间范围聚合的完成作业数序列

`metrics/history` 同时支持两种时间输入：

- 旧 `range=hour|day|week`
- 新 `start` / `end`

当显式传 `start` / `end` 时，bucket 规则固定为：

- `<= 48h`
  - 按小时 bucket
- `> 48h 且 <= 62d`
  - 按天 bucket
- `> 62d`
  - 按周 bucket

## 3. 权限要求

用户空间当前按区块控制：

| 区块 | 新规则 |
|---|---|
| 用户资料区 | `user/profile:view:self` 或 `user/profile:view:*`，也兼容 `accounts:view:*` |
| 用户分析区 | `user/analysis:view:self` 或 `user/analysis:view:*`，也兼容 `jobs:view:*` |
| 历史作业快捷入口 | `jobs-history:view:*` |

说明：

- 查看自己时优先使用 `self`
- 查看他人时需要 `*`
- 历史 `view-jobs` 与 `associations-view` 通过旧权限映射继续兼容
- Agent 端点在运行时会根据 URL 中的 `<username>` 解析 `self` / `*` scope，避免把他人请求误判成自己的权限范围，也避免因装饰器闭包取值错误导致接口直接报错

## 4. 路由契约

相关入口：

- `/:cluster/users/:user`
- `/:cluster/me`
- `/:cluster/users/:user/analysis`
  - 当前仅作为兼容入口，重定向到 `user?section=analysis`

## 5. 降级行为

- 用户分析 capability 不可用：
  - 隐藏分析区，不视为权限错误
- 权限不足：
  - 对他人页面统一跳转 `/forbidden`
- 数据请求失败：
  - 只在对应区块显示错误

## 6. 当前前端展示约定

- 用户分析页实时曲线同时展示：
  - 提交作业数
  - 完成作业数
- 用户分析页顶部统一使用共享时间窗：
  - `start`
  - `end`
- 页面输入控件为 `datetime-local`
- 页面首次进入时若 query 缺失或非法，会自动回填“当天 00:00 -> 当前时间”
- 前端发送请求前会把本地 `datetime-local` 转成带时区的 UTC ISO 8601
- `Tool Analysis`、`Top Tools`、`Usage Profile` 与趋势图共用同一时间窗
- `start >= end` 时前端直接 inline 报错且不发请求
