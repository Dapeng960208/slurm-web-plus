# 部署指南（统一覆盖：数据库、历史作业、访问控制、AI、用户分析）

本指南用于部署 Slurm Web Plus 的 Gateway/Agent 以及可选增强能力的开关与依赖顺序。

说明：

- Gateway 不直接连接 PostgreSQL；数据库迁移仅作用于 Agent 侧数据库。
- 能力是否可用由 Agent 暴露、Gateway 聚合、前端消费；不要在前端硬编码“所有集群都支持某能力”。

## 1. 适用范围

覆盖能力：

- 数据库支持（用户缓存、LDAP Cache）
- 历史作业持久化（Jobs History）
- 访问控制（自定义角色）
- 用户分析（User Analytics / User Metrics）
- AI 集群助手（模型配置、会话、工具审计）
- 节点实时/历史指标（Node Metrics）

## 2. 推荐部署顺序（生产）

1. 备份
   - 备份数据库（PostgreSQL）
   - 备份 `agent.ini`/`gateway.ini` 与策略文件（`policy.ini` 等）
2. 部署代码
   - 先部署所有 Agent（一个集群一个 Agent 或多个 Agent 实例）
   - 再部署 Gateway
3. 迁移数据库（每个启用 `[database] enabled = yes` 的 Agent 对应数据库都要执行）
4. 重启 Agent 并验证 `/info` 与 `/permissions`
5. 重启 Gateway 并验证 `/api/clusters` 能力聚合
6. 验证前端能力门控、路由守卫与设置页

## 3. Agent 配置开关与依赖关系

下面开关均来自 Agent（`slurmweb/apps/agent.py`）的装配逻辑，依赖满足时启用，不满足时会降级并在日志中给出原因。

### 3.1 数据库（基础能力）

数据库是以下能力的基础依赖：用户缓存、LDAP Cache、历史作业、访问控制、AI、用户分析。

```ini
[database]
enabled = yes
host = 127.0.0.1
port = 5432
database = slurmweb
user = slurmweb
password = REPLACE_ME
```

验证点：

- Agent `/info` 中 `database` 为 `true`（意味着用户存储 `users_store` 初始化成功）

### 3.2 历史作业（persistence）

```ini
[persistence]
enabled = yes
snapshot_interval = 60
retention_days = 180
```

依赖：

- `[database] enabled = yes` 且可连接

验证点：

- Agent `/info` 中 `persistence` 为 `true`（意味着 `jobs_store` 初始化成功）
- 前端 Jobs History 入口需要 capability + 权限双门控（见 `docs/overview/architecture-overview.md`）

### 3.3 访问控制（自定义角色）

访问控制不再有独立 feature flag；数据库可用后会自动启用。

依赖：

- 数据库可用（`database = true`）

验证点：

- Agent `/info` 中 `access_control` 为 `true`
- Agent `/v{version}/permissions` 返回 `sources.policy` / `sources.custom` / `sources.merged`

### 3.4 用户分析（user_metrics）

```ini
[user_metrics]
aggregation_interval = 3600
# tool_mapping_file = /etc/slurm-web/user-tools.yml
```

依赖（当前实现事实）：

- 数据库可用（`database = true`）
- metrics 开启（`[metrics] enabled = yes`）
- 历史作业持久化已启用且 `jobs_store` 可用（`persistence = true`）

验证点：

- Agent `/info` 中 `user_metrics` 为 `true`
- `GET /api/agents/<cluster>/user/<username>/activity/summary` 可用

### 3.5 AI 集群助手（ai）

```ini
[ai]
max_rounds = 4
max_history_messages = 24
stream_chunk_size = 32
```

依赖（当前实现事实）：

- 数据库可用（AI 相关 stores 与会话/审计都落库）
- `jwt.key` 用于派生 AI secret 加密密钥（不在前端暴露）

验证点：

- Agent `/info` 中 `ai.enabled = true` 且 `capabilities.ai.enabled = true`
- 前端 AI 菜单/设置页受 capability + 权限门控：
  - `ai:view:*`：进入 `/:cluster/ai`
  - `admin/ai:view:*` / `admin/ai:edit:*`：进入 `/:cluster/admin/ai`

### 3.6 节点指标（node_metrics）

```ini
[node_metrics]
prometheus_host = http://prometheus:9090
node_exporter_job = node-exporter
node_hostname_label = instance
```

依赖：

- Prometheus 可访问且具有节点指标（node_exporter）

验证点：

- `GET /api/agents/<cluster>/node/<name>/metrics`
- `GET /api/agents/<cluster>/node/<name>/metrics/history?range=hour|day|week`

## 4. 数据库迁移（必须）

迁移说明见：[`docs/guides/database-migrations.md`](./database-migrations.md)。

典型命令（在 Agent 所在主机仓库根目录执行）：

```powershell
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic current
```

## 5. 部署后验证（最小集）

建议优先通过 Gateway 验证（浏览器实际访问路径）：

1. 获取 token：`POST /api/login`（或认证关闭时 `GET /api/anonymous`）
2. `GET /api/clusters`：确认每个集群的 `persistence`、`access_control`、`user_metrics`、`node_metrics`、`ai` 等能力字段符合预期
3. `GET /api/agents/<cluster>/permissions`：确认权限返回结构与 `sources` 合并
4. 按需抽查专题接口：
   - 历史作业：`GET /api/agents/<cluster>/jobs/history`
   - 访问控制：`GET /api/agents/<cluster>/access/roles`
   - AI：`GET /api/agents/<cluster>/ai/configs`

## 6. 快速回滚边界

只回滚开关（最推荐的“快速止血”）：

- 历史作业 / 访问控制 / AI：`[database] enabled = no`
- 用户分析：去掉 `[user_metrics]` 段或停用 `[metrics] enabled`
- 节点指标：去掉 `node_metrics.prometheus_host`

回滚数据库 schema（高风险）：

```powershell
.venv\Scripts\python.exe -m alembic downgrade -1
```

注意：

- schema 回滚会删除对应表/字段，可能导致已写入数据不可恢复。
- schema 回滚必须与应用代码版本匹配，不要只回滚其中一边。
