# 用户分析后端说明（User Metrics / User Analytics）

本文说明“用户分析”相关后端能力：它建立在 PostgreSQL 的历史作业持久化之上，提供可选的用户维度聚合（提交趋势、工具分析、日级汇总等）。

## 1. 启用条件（实现事实）

要启用用户分析能力，需要同时满足：

- `[database] enabled = yes` 且数据库可连接（Agent `database=true`）
- `[persistence] enabled = yes` 且作业历史持久化已启动（Agent `persistence=true`）
- `[metrics] enabled = yes`（用户指标聚合依赖 Prometheus 路径）
- `[user_metrics] enabled = yes`

注意：

- 仅开启 `[user_metrics] enabled = yes` 不等于能力一定可用；Agent 会根据依赖是否满足决定是否真正启用，并在日志中说明降级原因。
- 启用前必须完成 `alembic upgrade head`。

## 2. 配置示例（agent.ini）

```ini
[database]
enabled = yes
host = 127.0.0.1
port = 5432
database = slurmweb
user = slurmweb
password = REPLACE_ME

[persistence]
enabled = yes
snapshot_interval = 60
retention_days = 180

[metrics]
enabled = yes

[user_metrics]
enabled = yes
aggregation_interval = 3600
# tool_mapping_file = /etc/slurm-web/user-tools.yml
```

## 3. 工具映射文件（tool_mapping_file）

`tool_mapping_file` 可选，用于把“检测到的工具候选值”归一化为稳定的 tool 标签，写入 `user_tool_daily_stats.tool` 并在 API 汇总中返回。

文件格式：

- YAML 根节点为 list
- 每项包含：
  - `pattern`：Python 正则表达式（匹配工具候选值）
  - `tool`：归一化后的标签
- 自上而下匹配，首个命中规则生效

示例：

```yaml
- pattern: "^bwa(-mem2)?$"
  tool: "bwa"

- pattern: "^samtools$"
  tool: "samtools"

- pattern: "^python[0-9.]*$"
  tool: "python"

- pattern: ".*"
  tool: "unknown"
```

示例文件位置：

- `docs/modules/conf/examples/user-tools.yml`

工具候选值检测顺序（实现事实）：

1. 优先使用 `job_name`
2. `job_name` 为空时，使用 `command` 的第一个 token 的 basename
3. `command` 为空时，使用 `submit_line` 的第一个 token 的 basename
4. 无法推导则使用 `unknown`

## 4. 数据模型

迁移 `20260424_0004_user_tool_daily_stats.py` 引入：

- `user_tool_daily_stats`：日级、用户级、工具级 rollup

历史作业快照表：

- `job_snapshots`：用于提交趋势、运行时与资源使用统计的样本来源

## 5. 接口

### 5.1 Agent 接口

- `GET /v<version>/user/<username>/metrics/history?range=hour|day|week`
- `GET /v<version>/user/<username>/activity/summary`
- `GET /v<version>/metrics/users`
  - 仅当 `[metrics]` + `[user_metrics]` + 数据库持久化均可用时才可用

### 5.2 Gateway 代理接口

- `GET /api/agents/<cluster>/user/<username>/metrics/history?range=hour|day|week`
- `GET /api/agents/<cluster>/user/<username>/activity/summary`

### 5.3 能力门控

- Agent `/info` 返回顶层 `user_metrics` 布尔值
- Gateway `/api/clusters` 会透传同名字段用于前端门控

禁用时行为（实现事实）：

- 用户分析相关接口返回 HTTP `501`，错误信息为 `User metrics is disabled`

## 6. 验证步骤（最小集）

1. `alembic current`
2. `alembic upgrade head`
3. 确认表存在：`user_tool_daily_stats`
4. 重启 Agent
5. 访问 Agent `/info`，确认 `user_metrics=true`
6. 通过 Gateway 查询：
   - `/api/agents/<cluster>/user/<username>/activity/summary`
   - `/api/agents/<cluster>/user/<username>/metrics/history?range=day`
7. 若启用 Prometheus user metrics，确认 Agent `/metrics` 包含 `slurmweb_user_submissions_last_minute`
