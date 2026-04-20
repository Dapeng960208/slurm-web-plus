# Slurm-web 功能扩展设计文档

## 1. 概述

本次设计在不破坏现有 Gateway / Agent 架构的前提下，引入三项可选增强能力：

1. **数据库基础能力**：在 agent 侧接入 PostgreSQL，并使用 Alembic 管理 schema 创建与迁移。
2. **作业历史持久化 + LDAP 用户缓存**：将作业历史写入 PostgreSQL，用户维度拆到独立 `users` 表，由 agent 本地缓存 LDAP 用户信息。
3. **节点实时资源监控**：通过 Prometheus 查询 node_exporter 指标，在节点详情页展示实时资源状态。

这些能力均通过 `agent.ini` 中独立配置开关控制，默认关闭。即使数据库未启用或迁移失败，也不应影响 agent 其他非数据库功能继续工作。

需要特别区分：

- `[database]`：本次新增，负责 PostgreSQL 连接、Alembic 自动迁移、`users` 表访问。
- `[persistence]`：本次新增，负责作业历史写入与查询。
- `[node_metrics]`：本次新增，负责节点实时资源查询。
- `[metrics]`：已有功能，用于 Slurm-web 指标导出和 Prometheus 查询，不属于本次数据库迁移能力。

---

## 2. 系统架构

```
前端 Vue3
    ↓ HTTP
Gateway (Flask)
    ├── LDAP 认证（现有）
    └── 将登录成功用户异步通知各 Agent 缓存
          ↓ HTTP
Agent (Flask)
    ├── slurmrestd (Slurm REST API)
    ├── Redis Cache (可选，现有)
    ├── Prometheus metrics (可选，现有 [metrics])
    ├── [新增] PostgreSQL (可选，[database] + [persistence])
    │     ├── users
    │     └── job_snapshots
    └── [新增] Prometheus node_exporter (可选，[node_metrics])
```

关键边界：

- `gateway` 不直连 PostgreSQL。
- 数据库配置只存在于 `agent.ini`，不要求 `gateway.ini` 配置数据库。
- 数据库 schema 只通过 Alembic 管理，不再通过原始 SQL 初始化。
- agent 启动时不会自动执行 `alembic upgrade head`。

---

## 3. 数据库与迁移设计

### 3.1 Alembic 目录结构

数据库模型与迁移文件采用以下结构：

- `alembic.ini`
- `slurmweb/alembic/env.py`
- `slurmweb/alembic/script.py.mako`
- `slurmweb/alembic/versions/`
- `slurmweb/models/db.py`
- `slurmweb/models/modes.py`

职责划分：

- `slurmweb/models/modes.py`：SQLAlchemy 元数据来源，作为 Alembic autogenerate 的模型输入。
- `slurmweb/models/db.py`：构造 SQLAlchemy URL 和运行时 `psycopg2` 连接参数。

### 3.2 开发与生产边界

开发阶段：

- 初始化 Alembic：`alembic init slurmweb/alembic`
- 基于模型生成迁移：`alembic revision --autogenerate -m "message"`
- 在开发或测试环境执行：`alembic upgrade head`

生产阶段：

- 只部署随版本发布的 migration 文件
- 只执行：`alembic upgrade head`
- 不在生产环境执行 `alembic init` 或 `alembic revision --autogenerate`

### 3.3 Agent 启动时的数据库行为

当 agent 启动时：

1. 读取 `agent.ini`
2. 检查 `[database] enabled`
3. 若启用，则初始化 `UsersStore`
4. 若同时 `[persistence] enabled = yes`，则初始化 `JobsStore` 并启动后台写入线程

说明：

- Alembic 迁移由部署流程手工执行，不在 agent 启动时自动执行
- `JobsStore` 的启用不再依赖 agent 启动阶段执行 Alembic

异常处理约束：

- 数据库访问初始化失败时记录 warning，不阻断整个 agent 进程启动
- `UsersStore` 初始化失败时，本地用户缓存不可用
- `JobsStore` 初始化失败时，作业历史不可用
- 其他非数据库功能继续可用

---

## 4. 功能一：作业历史持久化与用户拆表

### 4.1 设计目标

该功能包含两层能力：

1. **用户维度拆表**：不再把 `user_name` 直接冗余写在 `job_snapshots` 中，而是拆到独立 `users` 表，通过 `user_id` 关联。
2. **LDAP 用户缓存**：作业历史查询和详情页只从本地 `users` 表读取用户名与用户属性，不再在查询路径中实时访问 LDAP。

### 4.2 用户缓存数据流

```
Gateway /login
    ├── LDAP 认证成功
    ├── 返回 token 给前端
    └── [新增] 异步请求各 Agent: POST /v{version}/users/cache

Agent /users/cache
    └── 将 request.user.login / fullname / groups UPSERT 到 users 表
```

这个链路的含义是：

- `gateway` 仍然负责 LDAP 认证
- `gateway` 不写数据库，只通知 agent 缓存当前认证用户
- `agent` 成为唯一的数据库写入方

### 4.3 作业快照数据流

```
Agent 后台作业快照线程
    ├── 从 slurmrestd 拉取作业列表
    ├── _extract() 提取中间字段，包括 user_name
    ├── _ensure_users() 按 username 确保 users 记录存在
    │     └── 若缺失，则插入占位用户：username + groups=[]
    └── _flush() 将 job_snapshots.user_id 写入数据库

Agent /jobs/history
    └── 查询 job_snapshots LEFT JOIN users

Gateway /api/agents/<cluster>/jobs/history
    └── 透传给 Agent
```

写入与读取路径都以 agent 为中心，不在 gateway 侧访问 PostgreSQL。

### 4.4 数据表设计

#### `users`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGSERIAL PK | 用户主键 |
| `username` | TEXT UNIQUE NOT NULL | 登录名，唯一键 |
| `fullname` | TEXT NULL | LDAP 全名缓存 |
| `groups` | JSONB NOT NULL DEFAULT `[]` | LDAP 组列表缓存 |
| `ldap_synced_at` | TIMESTAMPTZ NULL | 最近一次 LDAP 同步时间 |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | 创建时间 |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | 更新时间 |

行为约束：

- 首次由作业快照遇到未知用户时，可创建占位记录，仅填充 `username`
- 用户真正登录后，由 `/users/cache` 把 `fullname`、`groups`、`ldap_synced_at` 补全
- `groups` 固定存储为 `JSONB`

#### `job_snapshots`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGINT | 历史记录主键组成部分 |
| `job_id` | INTEGER NOT NULL | Slurm 作业 ID |
| `submit_time` | TIMESTAMPTZ NOT NULL | 提交时间，也是分区键 |
| `first_seen` | TIMESTAMPTZ NOT NULL | 首次观测时间 |
| `last_seen` | TIMESTAMPTZ NOT NULL | 最近一次观测时间 |
| `job_name` | TEXT | 作业名 |
| `job_state` | TEXT | 当前状态 |
| `state_reason` | TEXT | 状态原因 |
| `user_id` | BIGINT NULL FK `users.id` | 用户外键 |
| `account` | TEXT | 账户 |
| `group` | TEXT | 用户组字符串 |
| `partition` | TEXT | 分区 |
| `qos` | TEXT | QOS |
| `nodes` | TEXT | 节点列表 |
| `node_count` | INTEGER | 节点数 |
| `cpus` | INTEGER | CPU 数 |
| `priority` | INTEGER | 优先级 |
| `tres_req_str` | TEXT | TRES 请求 |
| `tres_per_job` | TEXT | 每作业 TRES |
| `tres_per_node` | TEXT | 每节点 TRES |
| `gres_detail` | TEXT | GRES 详情 |
| `start_time` | TIMESTAMPTZ | 开始时间 |
| `end_time` | TIMESTAMPTZ | 结束时间 |
| `time_limit_minutes` | INTEGER | 时间限制 |
| `exit_code` | TEXT | 退出码 |
| `working_directory` | TEXT | 工作目录 |
| `command` | TEXT | 提交命令 |

索引与约束：

- 主键：`(id, submit_time)`
- 唯一索引：`(job_id, submit_time)`
- 索引：`last_seen DESC`、`user_id`、`account`、`partition`、`job_state`
- 分区：按 `submit_time` 做 PostgreSQL RANGE 分区
- 默认分区：`job_snapshots_default`
- agent 运行时会自动确保当前月与下个月分区存在

兼容性约束：

- `job_snapshots` 已不再使用 `user_name` 列
- 旧数据不做回填
- 历史接口继续返回 `user_name`，但它来自 `users.username`

### 4.5 写入策略

- **活跃作业**：每 `snapshot_interval` 秒写一次当前状态
- **终态作业**：通过内部去重逻辑避免重复写入终态快照
- 写入在独立后台线程中执行，不阻塞 `/jobs` 接口
- 定期清理超过 `retention_days` 的旧数据
- 批量写入前先执行 `_ensure_users()`，为每一行补齐 `user_id`

### 4.6 查询策略

查询时统一采用：

```text
job_snapshots js
LEFT JOIN users u ON u.id = js.user_id
```

由此保证：

- 列表和详情都能同时返回 `user_id` 与 `user_name`
- 历史筛选中的 `user` 条件按 `users.username` 精确匹配
- 不需要在查询路径中实时访问 LDAP

### 4.7 历史查询 API

#### 列表接口

```text
GET /v{version}/jobs/history
```

参数：

- `start`
- `end`
- `user`
- `account`
- `partition`
- `qos`
- `state`
- `job_id`
- `page`
- `page_size`

返回示例：

```json
{
  "total": 12345,
  "page": 1,
  "page_size": 100,
  "jobs": [
    {
      "id": 1,
      "job_id": 12345,
      "user_id": 7,
      "user_name": "user1",
      "job_name": "test_job",
      "job_state": "COMPLETED"
    }
  ]
}
```

#### 详情接口

```text
GET /v{version}/jobs/history/<id>
```

返回单条历史记录，字段与列表接口一致，但用于详情页展示。

### 4.8 前端控制逻辑

- Gateway `/api/clusters` 在集群信息中新增 `persistence: bool`
- Agent `/info` 返回 `persistence: bool`
- 前端 `ClusterDescription` 新增 `persistence`
- 前端 `JobHistoryRecord` 新增 `user_id: number | null`
- 历史页面仍然使用 `user_name` 展示用户名
- 左侧菜单 Jobs 下的 “History” 入口仅在 `cluster.persistence === true` 时显示

---

## 5. 功能二：节点实时资源监控

### 5.1 数据流

```
前端 NodeView 页面
    └── 调用节点实时资源 API

Gateway /api/agents/<cluster>/node/<name>/metrics
    └── 透传给 Agent

Agent /node/<name>/metrics
    └── 通过 SlurmwebMetricsDB 向 Prometheus 发起 instant query
```

### 5.2 Prometheus 查询

依赖 `node_metrics` 配置段中的：

- `prometheus_host`
- `node_exporter_job`
- `node_hostname_label`

典型指标：

| 指标 | PromQL |
|---|---|
| CPU 使用率 | `100 - avg(rate(node_cpu_seconds_total{job="...",hostname="node",mode="idle"}[5m])) * 100` |
| 内存使用率 | `(MemTotal - MemAvailable) / MemTotal * 100` |
| 网络收（bytes/s） | `rate(node_network_receive_bytes_total{...,device!="lo"}[5m])` |
| 网络发（bytes/s） | `rate(node_network_transmit_bytes_total{...,device!="lo"}[5m])` |
| 磁盘读（bytes/s） | `rate(node_disk_read_bytes_total{...}[5m])` |
| 磁盘写（bytes/s） | `rate(node_disk_written_bytes_total{...}[5m])` |
| 系统负载 | `node_load1{...}`, `node_load5{...}` |

### 5.3 返回数据格式

```json
{
  "cpu_usage_percent": 73.2,
  "mem_used_bytes": 12884901888,
  "mem_total_bytes": 68719476736,
  "mem_usage_percent": 18.75,
  "net_rx_bps": 524288,
  "net_tx_bps": 131072,
  "disk_read_bps": 1048576,
  "disk_write_bps": 2097152,
  "load1": 12.5,
  "load5": 10.3
}
```

### 5.4 前端展示

- `node_metrics.enabled = false` 时，NodeView 不渲染实时资源区块
- `ClusterDescription` 新增 `node_metrics: bool`
- 前端按固定轮询周期拉取节点实时资源

---

## 6. 配置设计

### 6.1 `[database]` 节（新增）

只在 `agent.ini` 中配置。

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enabled` | bool | false | 是否启用 PostgreSQL 相关能力 |
| `host` | str | localhost | PostgreSQL 主机 |
| `port` | int | 5432 | PostgreSQL 端口 |
| `database` | str | slurmweb | 数据库名 |
| `user` | str | slurmweb | 数据库用户名 |
| `password` | password | — | 数据库密码 |

语义：

- 控制 Alembic 自动迁移是否执行
- 控制 `UsersStore` 是否启用
- 是 `[persistence]` 的前置条件

### 6.2 `[persistence]` 节（新增）

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enabled` | bool | false | 是否启用作业历史持久化 |
| `retention_days` | int | 180 | 数据保留天数 |
| `snapshot_interval` | int | 60 | 活跃作业采样周期（秒） |

语义：

- 只控制作业历史写入与查询
- 不再重复配置数据库连接参数
- 依赖 `[database] enabled = yes`

### 6.3 `[node_metrics]` 节（新增）

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enabled` | bool | false | 是否启用节点实时资源监控 |
| `prometheus_host` | uri | http://localhost:9090 | Prometheus 服务地址 |
| `node_exporter_job` | str | node | node_exporter 对应 job 名称 |
| `node_hostname_label` | str | hostname | 节点名对应的 Prometheus 标签名 |

### 6.4 `[metrics]` 节（已有）

这是已有功能，不属于本次数据库能力设计。

它负责：

- 导出 Slurm-web 自身指标
- 查询 Prometheus 中 Slurm 指标

因此文档和部署时需要避免混淆：

- `[metrics]` 不等于 `[node_metrics]`
- `[metrics]` 也不等于 `[database]` / `[persistence]`

---

## 7. 接口与前端类型变更

### 7.1 Agent 新增接口

| 接口 | 说明 |
|---|---|
| `GET /v{version}/jobs/history` | 分页查询作业历史 |
| `GET /v{version}/jobs/history/<id>` | 查询单条历史详情 |
| `POST /v{version}/users/cache` | 缓存当前已认证用户到 `users` 表 |
| `GET /v{version}/node/<name>/metrics` | 查询节点实时资源 |

### 7.2 Gateway 新增或扩展接口

| 接口 | 说明 |
|---|---|
| `POST /login` | LDAP 登录成功后异步通知各 Agent 缓存用户 |
| `GET /api/agents/<cluster>/jobs/history` | 透传历史列表 |
| `GET /api/agents/<cluster>/jobs/history/<id>` | 透传历史详情 |
| `GET /api/agents/<cluster>/node/<name>/metrics` | 透传节点实时资源 |
| `GET /clusters` | 返回 `persistence`、`node_metrics` 能力标志 |

### 7.3 前端类型扩展

| 类型 | 变更 |
|---|---|
| `ClusterDescription` | 新增 `persistence`、`node_metrics` |
| `JobHistoryRecord` | 新增 `user_id: number | null`，保留 `user_name: string | null` |

---

## 8. 新增/修改文件清单

### 8.1 新增文件

| 文件 | 说明 |
|---|---|
| `alembic.ini` | Alembic 主配置 |
| `slurmweb/alembic/env.py` | Alembic 环境入口 |
| `slurmweb/alembic/script.py.mako` | Alembic revision 模板 |
| `slurmweb/alembic/versions/*.py` | 版本迁移脚本 |
| `slurmweb/models/db.py` | 数据库 URL 与连接参数构造 |
| `slurmweb/models/modes.py` | SQLAlchemy 模型元数据 |
| `slurmweb/persistence/users_store.py` | LDAP 用户缓存写入 |
| `docs/database-migrations.md` | 迁移说明文档 |
| `docs/deployment-guide.md` | 生产部署文档 |

### 8.2 修改文件

| 文件 | 修改内容 |
|---|---|
| `slurmweb/apps/agent.py` | agent 启动时执行 Alembic 迁移，初始化 users/persistence/node_metrics |
| `slurmweb/views/agent.py` | 新增 `jobs_history`、`job_history_detail`、`cache_authenticated_user`、`node_metrics` |
| `slurmweb/views/gateway.py` | 登录后通知 agent 缓存 LDAP 用户；新增历史与节点监控透传 |
| `slurmweb/persistence/jobs_store.py` | 改为写入 `user_id`，查询时联表 `users` |
| `slurmweb/persistence/migrations.py` | 封装运行时 Alembic 迁移 |
| `conf/vendor/agent.yml` | 新增 `database`、`persistence`、`node_metrics` 配置节定义 |
| `frontend/src/composables/GatewayAPI.ts` | 扩展 `JobHistoryRecord.user_id` 和相关 API |
| `frontend/src/views/JobsHistoryView.vue` | 历史列表页使用新接口 |
| `frontend/src/views/JobHistoryView.vue` | 历史详情页使用新接口 |
| `frontend/src/views/NodeView.vue` | 节点实时资源区块 |
| `frontend/src/router/index.ts` | 注册历史作业路由 |
| `frontend/src/components/MainMenu.vue` | 条件显示 History 菜单入口 |

---

## 9. 失败场景与容错策略

### 9.1 数据库未启用

当 `[database] enabled = no`：

- agent 不执行 Alembic 迁移
- `users` 缓存不可用
- 作业历史持久化不可用
- node metrics 和其他既有功能仍可工作

### 9.2 数据库迁移失败

当 `alembic upgrade head` 失败：

- 记录 warning
- agent 继续启动
- `UsersStore` / `JobsStore` 按初始化结果决定是否可用

### 9.3 gateway 先于 agent 完成数据库准备

若 gateway 已成功登录用户，但 agent 侧表尚未创建：

- 登录本身不受影响
- `/users/cache` 可能返回失败并记录 warning
- 待 agent 完成迁移后，后续登录会恢复缓存能力

---

## 10. 结论

本设计将“数据库接入”“用户缓存”“作业历史”“节点实时资源”拆成互相独立但可协同工作的能力层：

- `gateway` 负责认证和转发，不直连数据库
- `agent` 负责数据库迁移、用户缓存、历史写入与查询
- `users` 与 `job_snapshots` 分表后，历史查询不再依赖实时 LDAP 查询
- 数据库生命周期统一交由 Alembic 管理
- 即使数据库不可用，也不影响 agent 其他功能继续提供服务
### 4.9 历史详情字段富化

历史详情页需要比历史列表更多的数据。`job_snapshots` 在基础快照字段之外新增以下可空字段：

- `eligible_time`：作业进入 eligible 的时间。
- `last_sched_evaluation_time`：最后一次调度评估时间，历史时间线的 scheduling 阶段优先使用该字段。
- `tres_requested`：单作业详情中的 `tres.requested`，JSONB 保存。
- `tres_allocated`：单作业详情中的 `tres.allocated`，JSONB 保存。
- `used_memory_gb`：已完成作业的实际使用内存，来源于 `steps[*].tres.consumed.total` 的 memory TRES；该值单位为 KB，按 `KB / 1024^2` 转为 GB。

数据来源分为两层：

- 列表快照 `_extract()` 只保持轻量写入，额外提取 `eligible_time` 和 `last_sched_evaluation_time`，不从列表接口硬拼结构化资源。
- 单作业详情 `_extract_detail()` 负责提取结构化 TRES、完整时间字段和已完成作业内存。

富化策略：

- 后台缺失活动作业对账时，如果当前列表没有某个非终态历史记录，先调用 `job(job_id)` 补查；补查成功则按真实详情 UPSERT，补查不到再兜底写 `COMPLETED`。
- 历史详情接口返回前，如果记录缺少详情字段，会按需调用 `job(job_id)` 补查一次；只有 `(job_id, submit_time)` 与当前记录一致时才允许回写。
- 运行中作业通常没有完整 `steps[*].tres.consumed.total`，因此 `used_memory_gb` 为 `null` 是正常结果。
