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

`tools/analysis` 的工具分类统计以 `user_tool_daily_stats` 为返回来源。接口收到 `start` / `end` 后，会先把时间窗覆盖到的 UTC 自然日从 `job_snapshots` 重新聚合写入 `user_tool_daily_stats`，再从该表读取并汇总返回。

`user_tool_daily_stats` 按 `(activity_date, user_id, tool)` 保存每日工具统计：

- `jobs_count`
- `avg_max_memory_gb`
- `avg_cpu_cores`
- `avg_runtime_seconds`
- `memory_samples`
- `cpu_samples`
- `runtime_samples`

其中 `memory_samples` / `cpu_samples` / `runtime_samples` 用于跨多日聚合时按真实样本数加权，避免只有部分作业存在资源数据时平均值被 `jobs_count` 拉偏。

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
  - `avg_max_memory_gb`
  - `avg_max_memory_mb`
  - `avg_cpu_cores`
  - `avg_runtime_hours`
  - `avg_runtime_seconds`
  - `busiest_tool`
  - `busiest_tool_jobs`
- `tool_breakdown`

统计口径：

- 只统计已完成或终态作业。
- `tools/analysis` 会按 `start` / `end` 覆盖到的 UTC 日期读取日聚合表；该接口的工具统计粒度为日。
- 内存均值优先按 `job_snapshots.used_memory_gb` 计算；若历史行该字段为空，回退到 `usage_stats.memory.value_gb`。接口同时保留 `avg_max_memory_mb` 作为前端兼容字段。
- CPU 均值优先按 `job_snapshots.used_cpu_cores_avg` 计算；兼容历史行中的 `used_cpu_core_avg`，若顶层字段为空，回退到 `usage_stats.cpu.estimated_cores_avg`。
- 运行时间优先按 `end_time - start_time` 计算，并返回 `avg_runtime_hours`；兼容保留 `avg_runtime_seconds`。
- 终态判断按 `UPPER(job_state)` 匹配，避免 `completed` / `COMPLETED` 大小写差异导致统计为空。

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

`submissions` 默认按 `submit_time` 过滤；如果历史数据缺少 `submit_time`，会回退使用 `start_time`，再回退 `last_seen`，避免旧快照在自定义时间窗下完全不展示。

当显式传 `start` / `end` 时，bucket 规则固定为：

- `<= 48h`
  - 按小时 bucket
- `> 48h 且 <= 62d`
  - 按天 bucket
- `> 62d`
  - 按周 bucket

自定义窗口的 bucket 统一按 UTC 对齐。后端 SQL 会先把 `TIMESTAMPTZ` 转成 UTC 时间再 `date_trunc`，Python 侧也用 UTC epoch milliseconds 匹配 bucket，避免数据库 session timezone 与前端 UTC 窗口不一致时，`7 days`、`15 days`、`1 month` 这类 day bucket 序列全部显示为 0。

工具名归类可通过 `[user_metrics].tool_mapping_file` 指定 YAML 规则文件。仓库内置示例位于 `conf/vendor/user-tools.yml`，规则格式为有序列表：

```yaml
- pattern: '^(blast|blastn|blastp)$'
  tool: blast
```

规则从上到下匹配，先命中的规则生效；匹配对象为规范化后的 `job_name`，若缺失则回退到 `command` / `submit_line` 的第一个可执行 token。

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
- 用户名由页面标题承载，分析面板内部不再重复展示独立用户名卡片。
- LDAP 姓名、组和更新时间压缩展示在时间范围栏的轻量上下文标签中。
- 用户分析页顶部统一使用共享时间窗按钮：
  - `start`
  - `end`
- 点击按钮后弹出时间选择框，起止输入精确到时分；该交互与节点详情页 `Real Metrics` 保持一致
- 时间选择框内置快捷窗口：
  - `1 day`
  - `3 days`
  - `7 days`
  - `15 days`
  - `1 month`
- 页面首次进入时若 query 缺失或非法，会自动回填“当天 00:00 -> 当前时间”
- 前端发送请求前会把本地 `datetime-local` 转成带时区的 UTC ISO 8601
- `Tool Analysis`、`Top Tools`、`Usage Profile` 与趋势图共用同一时间窗
- `start >= end` 时前端直接 inline 报错且不发请求
