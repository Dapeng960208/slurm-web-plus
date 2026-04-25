# 数据库迁移说明（Alembic）

本文说明 Slurm Web Plus 在 Agent 侧数据库（PostgreSQL）上的 schema 迁移体系、推荐升级流程、近期 revision 影响范围与回滚边界。

重要边界（实现事实）：

- Gateway 不直接连接 PostgreSQL。
- 迁移只作用于 Agent 侧数据库（也就是启用 `[database]` 的集群侧）。

## 1. 迁移体系与执行位置

- 迁移框架：Alembic（迁移脚本位于 `slurmweb/alembic/versions/`）。
- 迁移执行位置：在部署了 Agent 的主机上、仓库根目录中执行。
- 数据库连接：Alembic 会从 Agent 配置加载数据库连接信息（见 `slurmweb/alembic/env.py`）。

## 2. 推荐升级顺序（生产）

1. 备份数据库与配置（必做）。
2. 部署新版本代码（包含最新 Alembic scripts）。
3. 停止 `slurm-web-agent`（避免迁移期间写入冲突）。
4. 确认 Agent 配置中 `[database] enabled = yes` 且连接信息正确。
5. 执行迁移：

```powershell
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic current
```

6. 启动 `slurm-web-agent`，观察日志中数据库初始化、可选能力启用/降级原因。
7. 重启 `slurm-web-gateway`，让前端从 `/api/clusters` 获取到最新能力聚合。

## 3. 近期 revision 与影响范围（按依赖链）

> revision 名称以 `slurmweb/alembic/versions/*.py` 为准；下述内容直接对应当前脚本行为。

### 3.1 `20260420_0001`：基础表与作业快照分区

主要引入：

- `users`（缓存 LDAP 用户信息与后续权限快照）
- `job_snapshots`（历史作业快照，按 `submit_time` 做 RANGE 分区）
- 索引：`idx_js_job_submit`、`idx_js_last_seen`、`idx_js_user_id` 等

### 3.2 `20260420_0002`：历史作业详情增强字段

在 `job_snapshots` 上增加：

- `eligible_time`
- `last_sched_evaluation_time`
- `tres_requested` / `tres_allocated`（JSONB）
- `used_memory_gb`

### 3.3 `20260422_0003`：历史作业 usage 统计字段

在 `job_snapshots` 上增加：

- `usage_stats`（JSONB）
- `used_cpu_cores_avg`

### 3.4 `20260424_0004`：用户工具日聚合表

引入：

- `user_tool_daily_stats`
- 索引：`idx_user_tool_daily_stats_user_id_date`

该表用于用户分析的“工具维度”汇总（见 `docs/features/user-analytics/backend.md`）。

### 3.5 `20260424_0005`：访问控制（自定义角色）

引入：

- `users.policy_roles`、`users.policy_actions`、`users.permission_synced_at`
- `roles`、`user_roles`
- 索引：`idx_user_roles_role_id`

### 3.6 `20260424_0006`：AI 集群助手持久化

引入：

- `ai_model_configs`
- `ai_conversations`
- `ai_messages`
- `ai_tool_calls`
- 相关索引（按 cluster、conversation、username 等维度）

## 4. 迁移验证（最小集）

1. Alembic revision：

```powershell
.venv\Scripts\python.exe -m alembic current
```

2. API 行为（建议走 Gateway）：

- `GET /api/clusters`：确认 `persistence`、`access_control`、`user_metrics`、`ai` 等能力字段
- `GET /api/agents/<cluster>/jobs/history`：确认历史作业接口可用（当 `persistence = true`）
- `GET /api/agents/<cluster>/access/roles`：确认访问控制接口可用（当 `access_control = true`）
- `GET /api/agents/<cluster>/ai/configs`：确认 AI 配置列表可用（当 `ai.enabled = true`）

## 5. 回滚边界与风险

### 5.1 只回滚功能开关（优先）

多数情况下应通过关闭 Agent 能力开关回滚（见 `docs/guides/deployment-guide.md`），避免 schema 回滚带来的不可逆数据丢失。

### 5.2 schema 回滚（高风险）

先停止 `slurm-web-agent`，再执行：

```powershell
.venv\Scripts\python.exe -m alembic downgrade -1
```

风险与边界：

- 回滚会删除对应表/字段，已写入数据可能不可恢复（尤其是 AI 会话、访问控制绑定）。
- schema 回滚必须与应用代码版本匹配；不要只回滚 schema 或只回滚应用。
- 生产环境在 downgrade 前必须做数据库备份。
