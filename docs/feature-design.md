# Slurm-web 功能扩展设计文档

## 1. 概述

在不改变原有架构的前提下，新增两个独立功能：

1. **作业历史持久化**：将作业数据异步写入 PostgreSQL，支持多条件历史查询
2. **节点实时资源监控**：通过 Prometheus 查询 node_exporter 指标，在节点详情页展示实时资源状态

两个功能均通过独立配置开关控制，默认关闭，关闭时对现有功能零影响。

---

## 2. 系统架构（不变）

```
前端 Vue3
    ↓ HTTP
Gateway (Flask)
    ↓ HTTP
Agent (Flask)
    ├── slurmrestd (Slurm REST API)
    ├── Redis Cache (可选)
    ├── Prometheus (可选，已有 metrics 功能)
    ├── [新增] PostgreSQL (可选，作业历史)
    └── [新增] Prometheus node_exporter (可选，节点实时资源)
```

---

## 3. 功能一：作业历史持久化

### 3.1 数据流

```
Agent /jobs 路由（现有，不变）
    ├── 正常返回给前端（不变）
    └── [新增] 异步线程 → 写入 PostgreSQL job_snapshots 表

Agent [新增] /jobs/history 路由
    └── 查询 PostgreSQL → 返回历史数据

Gateway [新增] /api/agents/<cluster>/jobs/history 路由
    └── 透传给 Agent（与现有路由模式完全一致）
```

### 3.2 数据库表结构

```sql
CREATE TABLE IF NOT EXISTS job_snapshots (
    id                 BIGSERIAL PRIMARY KEY,
    snapshot_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    job_id             INTEGER NOT NULL,
    job_name           TEXT,
    job_state          TEXT,
    state_reason       TEXT,
    user_name          TEXT,
    account            TEXT,
    "group"            TEXT,
    partition          TEXT,
    qos                TEXT,
    nodes              TEXT,
    node_count         INTEGER,
    cpus               INTEGER,
    priority           INTEGER,
    tres_req_str       TEXT,
    tres_per_job       TEXT,
    tres_per_node      TEXT,
    gres_detail        TEXT,
    submit_time        TIMESTAMPTZ,
    start_time         TIMESTAMPTZ,
    end_time           TIMESTAMPTZ,
    time_limit_minutes INTEGER,
    exit_code          TEXT,
    working_directory  TEXT,
    command            TEXT
);

CREATE INDEX IF NOT EXISTS idx_js_snapshot_time ON job_snapshots(snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_js_job_id        ON job_snapshots(job_id);
CREATE INDEX IF NOT EXISTS idx_js_user_name     ON job_snapshots(user_name);
CREATE INDEX IF NOT EXISTS idx_js_account       ON job_snapshots(account);
CREATE INDEX IF NOT EXISTS idx_js_partition     ON job_snapshots(partition);
CREATE INDEX IF NOT EXISTS idx_js_job_state     ON job_snapshots(job_state);
```

### 3.3 写入策略

- **活跃作业**（RUNNING/PENDING）：每 `snapshot_interval` 秒（默认60秒）写一次快照
- **终态作业**（COMPLETED/FAILED/CANCELLED/TIMEOUT/NODE_FAIL/DEADLINE/OUT_OF_MEMORY）：
  检测到后写入一条终态记录，后续不再重复写入（通过 `terminal_jobs` 集合去重）
- 写入在**独立后台线程**中执行，不阻塞 `/jobs` 接口响应
- 定期清理超过 `retention_days` 的旧数据（每天执行一次）

### 3.4 历史查询 API

```
GET /v{version}/jobs/history
参数（均可选）：
  start       时间起点（ISO8601，如 2024-01-01T00:00:00）
  end         时间终点（ISO8601）
  user        用户名（精确匹配）
  account     账号（精确匹配）
  partition   分区（精确匹配）
  qos         QOS（精确匹配）
  state       状态（如 COMPLETED，精确匹配）
  job_id      作业ID（精确匹配）
  page        页码（默认1）
  page_size   每页条数（默认100，最大500）

返回：
{
  "total": 12345,
  "page": 1,
  "page_size": 100,
  "jobs": [ {...}, ... ]
}
```

### 3.5 前端控制逻辑

- Gateway `/api/clusters` 接口在集群信息中新增 `persistence: bool` 字段
- Agent `/info` 接口新增 `persistence: bool` 字段
- 前端 `ClusterDescription` 类型新增 `persistence` 字段
- 左侧菜单 Jobs 下的"History"入口：仅当 `cluster.persistence === true` 时显示
- `JobsHistoryView.vue` 路由：`/:cluster/jobs/history`

---

## 4. 功能二：节点实时资源监控

### 4.1 数据流

```
前端 NodeView 页面（现有，5秒轮询）
    └── [新增] 实时资源区块 → 调用新 API

Gateway [新增] /api/agents/<cluster>/node/<name>/metrics 路由
    └── 透传给 Agent

Agent [新增] /node/<name>/metrics 路由
    └── 向 Prometheus 发 PromQL instant query（复用 SlurmwebMetricsDB）
    └── 返回 CPU/内存/网络/磁盘/负载 JSON
```

### 4.2 Prometheus 查询

利用已有标签结构（`hostname="node65"`, `job="BJ-IDC-Linux-IC-HPC-Node"`）：

| 指标 | PromQL |
|---|---|
| CPU 使用率 | `100 - avg(rate(node_cpu_seconds_total{job="...",hostname="node",mode="idle"}[5m])) * 100` |
| 内存使用率 | `(MemTotal - MemAvailable) / MemTotal * 100` |
| 网络收（bytes/s） | `rate(node_network_receive_bytes_total{...,device!="lo"}[5m])` |
| 网络发（bytes/s） | `rate(node_network_transmit_bytes_total{...,device!="lo"}[5m])` |
| 磁盘读（bytes/s） | `rate(node_disk_read_bytes_total{...}[5m])` |
| 磁盘写（bytes/s） | `rate(node_disk_written_bytes_total{...}[5m])` |
| 系统负载 | `node_load1{...}`, `node_load5{...}` |

### 4.3 返回数据格式

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

### 4.4 前端展示

- `node_metrics.enabled = false` 时，NodeView 中实时资源区块不渲染（`v-if`）
- `ClusterDescription` 新增 `node_metrics: bool` 字段（由 Agent `/info` 提供）
- 5秒轮询，与现有节点数据轮询独立

---

## 5. 新增/修改文件清单

### 新增文件

| 文件 | 说明 |
|---|---|
| `slurmweb/persistence/__init__.py` | 持久化模块初始化 |
| `slurmweb/persistence/jobs_store.py` | PostgreSQL 读写逻辑 |
| `conf/init_db.sql` | 数据库初始化 SQL |
| `frontend/src/views/JobsHistoryView.vue` | 历史作业查询页面 |
| `docs/feature-design.md` | 本文档 |
| `docs/deployment-guide.md` | 部署文档 |

### 修改文件（只新增，不改动现有逻辑）

| 文件 | 修改内容 |
|---|---|
| `slurmweb/apps/agent.py` | 新增路由注册；`__init__` 中初始化 persistence 和 node_metrics |
| `slurmweb/views/agent.py` | 新增 `jobs_history`、`node_metrics` 视图函数 |
| `slurmweb/apps/gateway.py` | 新增两条透传路由 |
| `slurmweb/views/gateway.py` | 新增 `jobs_history`、`node_metrics` 视图函数 |
| `slurmweb/metrics/db.py` | 新增 `node_instant_metrics()` 方法 |
| `conf/vendor/agent.yml` | 新增 `persistence`、`node_metrics` 配置节定义 |
| `frontend/src/composables/GatewayAPI.ts` | 新增接口函数和类型 |
| `frontend/src/views/NodeView.vue` | 新增实时资源区块 |
| `frontend/src/router/index.ts` | 注册历史作业路由 |
| `frontend/src/components/MainMenu.vue` | 新增 History 菜单入口（条件显示） |

---

## 6. 配置项说明

### persistence 节（新增）

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enabled` | bool | false | 是否启用作业历史持久化 |
| `host` | str | localhost | PostgreSQL 主机 |
| `port` | int | 5432 | PostgreSQL 端口 |
| `database` | str | slurmweb | 数据库名 |
| `user` | str | slurmweb | 数据库用户 |
| `password` | password | — | 数据库密码 |
| `retention_days` | int | 180 | 数据保留天数 |
| `snapshot_interval` | int | 60 | 活跃作业快照间隔（秒） |

### node_metrics 节（新增）

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enabled` | bool | false | 是否启用节点实时资源监控 |
| `prometheus_host` | uri | http://localhost:9090 | Prometheus 服务地址 |
| `node_exporter_job` | str | — | Prometheus job 名称 |
| `node_hostname_label` | str | hostname | 节点名对应的 Prometheus 标签名 |
