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

`tools/analysis` 的工具分类统计以 `user_tool_daily_stats` 为返回来源。接口收到 `start` / `end` 后，只按时间窗覆盖到的 UTC 自然日读取 `user_tool_daily_stats` 并汇总返回；查询多天时，内存与 CPU 均值按 `sum(day.avg * day.jobs_count) / sum(day.jobs_count)` 合并。该请求路径不实时扫描 `job_snapshots` 或 SlurmDB。历史错误日表可通过维护脚本 `slurmweb/scripts/repair-user-tool-daily-stats.py` 按日期范围和可选用户重建。

后台线程按 `[user_metrics].aggregation_interval` 配置周期执行，启动时先执行一次，然后按间隔重算并替换当天 UTC 自然日的统计。后台聚合与维护脚本现在共用同一条“历史作业读取 -> Python 分组聚合 -> 写入日表”链路：先按 `submit_time` 当天起止范围读取 `job_state = COMPLETED` 的作业，再按 `activity_date + user_id + tool` 在 Python 中分类汇总，避免 `user_tool_daily_stats` 再维护独立原生 SQL 聚合口径；重算当天数据时会先删除当天旧行，再写入新的有效统计，避免旧脏行残留。

`user_tool_daily_stats` 按 `(activity_date, user_id, tool)` 保存每日工具统计：

- `jobs_count`
- `avg_memory_gb`
- `max_memory_gb`
- `median_memory_gb`
- `avg_cpu_cores`
- `avg_runtime_seconds`

`tools/analysis` 跨多日返回的 `avg_memory_gb` 与 `avg_cpu_cores` 始终按每日 `jobs_count` 加权。当前 `jobs_count` 的语义是“提交时间落在该 UTC 日期内、状态为 `COMPLETED`、且 `used_memory_gb > 0` 的作业数”。`max_memory_gb` 取时间窗内日峰值的最大值；`median_memory_gb` 在直接作业聚合时返回精确中位数，在跨多日读取日表时返回按 `jobs_count` 加权的日中位数近似值。

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
  - `avg_memory_gb`
  - `avg_max_memory_gb`
  - `avg_max_memory_mb`
  - `max_memory_gb`
  - `median_memory_gb`
  - `avg_cpu_cores`
  - `avg_runtime_hours`
  - `avg_runtime_seconds`
  - `busiest_tool`
  - `busiest_tool_jobs`
- `tool_breakdown`

统计口径：

- 只统计 `job_state = COMPLETED` 的作业。
- `tools/analysis` 会按 `start` / `end` 覆盖到的 UTC 日期读取日聚合表；该接口的工具统计粒度为日，且请求时不实时重建日聚合表。
- 日聚合写入会过滤没有 `user_id` 或没有 `submit_time` 的作业；目标日期按 `submit_time` 的 UTC 日期计算。
- 当天日聚合按 `activity_date + user_id + tool` 分组，只统计提交时间落在当天范围内且状态为 `COMPLETED` 的作业；写入的 `activity_date` 固定为本轮统计日期的年月日。
- 当天 `jobs_count` 只统计该组中 `used_memory_gb > 0` 的作业；`avg_memory_gb`、`max_memory_gb`、`median_memory_gb` 基于同一批正内存样本计算；`avg_cpu_cores` 以 `jobs_count` 为分母，缺失或非法 `used_cpu_cores_avg` 按 `0` 计入。
- 写入 `user_tool_daily_stats` 前，`avg_memory_gb`、`max_memory_gb`、`median_memory_gb`、`avg_cpu_cores`、`avg_runtime_seconds` 会统一四舍五入到两位小数再入库。
- 跨多天查询按日表行合并：`avg_memory_gb = sum(day.avg_memory_gb * day.jobs_count) / sum(day.jobs_count)`；`avg_cpu_cores` 使用同一 `jobs_count` 加权口径；`max_memory_gb` 取时间窗内各日 `max_memory_gb` 的最大值；`median_memory_gb` 按 `sum(day.median_memory_gb * day.jobs_count) / sum(day.jobs_count)` 近似。
- 当整个时间窗内没有任何 `used_memory_gb > 0` 的 `COMPLETED` 作业时，跨天返回该资源均值为 `null`，`completed_jobs` 为 `0`，工具列表为空。
- 运行时间优先按 `end_time - start_time` 计算，并返回 `avg_runtime_hours`；兼容保留 `avg_runtime_seconds`。日表写入时 `avg_runtime_seconds` 也以 `jobs_count` 为分母，缺失运行时间按 `0` 计入。
- 状态判断按 `UPPER(job_state) = 'COMPLETED'` 匹配，避免 `completed` / `COMPLETED` 大小写差异导致统计为空。
- 后台聚合线程每轮刷新会输出汇总日志，记录扫描作业数、纳入统计作业数、缺身份跳过数、缺内存跳过数、缺 CPU 样本数、运行时样本数和写入日行数，便于排查 `tools/analysis` 返回空或 CPU 均值缺失。

维护脚本：

```powershell
.venv\Scripts\python.exe slurmweb\scripts\repair-user-tool-daily-stats.py --start 2026-05-01 --end 2026-05-06 --dry-run
.venv\Scripts\python.exe slurmweb\scripts\repair-user-tool-daily-stats.py --start 2026-05-01 --end 2026-05-06 --user alice
```

脚本默认删除目标日期范围内的旧 `user_tool_daily_stats`，再按当前口径从 `job_snapshots` 重建；`--dry-run` 只输出将处理的作业数、将删除的旧行数和将写入的新行数，不写数据库。

全表重建脚本 `slurmweb/scripts/rebuild-user-tool.py` 现在默认输出逐条重建明细日志。脚本逐日调用 `JobsStore.completed_job_rows_for_activity_date(<date>)` 读取提交时间落在该 UTC 日期内的 `COMPLETED` 作业，并在聚合前把源行 `activity_date` 固定为正在重建的年月日，避免源行携带的旧日期或测试 mock 影响最终写库日期。每个 `activity_date + user_id + tool` 日聚合行在写库前都会打印单行日志，至少包含：

- `activity_date`
- `user_id`
- `username`
- `tool`
- `jobs_count`
- `avg_memory_gb`
- `max_memory_gb`
- `median_memory_gb`
- `avg_cpu_cores`
- `avg_runtime_seconds`

脚本同时会按日打印 `source_jobs` 与将写入的聚合行数，并在全表写入前打印总预览摘要。由于默认总是输出逐条明细，全量历史重建时日志量会显著增加，主要用于核对关键时间、用户、工具和资源统计是否符合预期。

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
- 页面将原 `Tool Analysis` 与 `Top Tools` 合并为 `Completed Job Tool Analysis` 栏目，集中展示已完成作业的工具维度数据分析；该栏目与 `Usage Profile`、趋势图共用同一时间窗。
- `start >= end` 时前端直接 inline 报错且不发请求
