# Dashboard 分区筛选接口契约需求

## 1. 背景与目标

本专题聚焦 Dashboard 相关后端接口的分区筛选契约补齐。

当前页面和 Gateway 已经允许通过 query 传递筛选条件，但 `stats` 与 `metrics` 两类接口在 Agent 侧没有统一落实 `partition` 语义，导致前端即使携带分区参数，也可能继续读取全局统计。

本轮目标：

- 让 `GET /v<agent-version>/stats` 支持 `partition` query。
- 让 `GET /v<agent-version>/metrics/<metric>` 支持 `partition` query 透传。
- 让 Gateway 保持 query 原样透传，不为 `partition` 增加特判逻辑。
- 让前端分区详情页复用同一套 dashboard 指标 query，并固定携带当前分区名。
- 让作业与历史作业页面中的分区字段统一作为分区详情入口。
- 让集群分析页 `Partition Hotspots` 模块中的分区名称也统一作为分区详情入口。
- 通过测试把接口契约固定下来，避免后续回归。

## 2. 功能范围

### 2.1 Agent `stats`

- 接口：`GET /v<agent-version>/stats`
- 新增可选 query：`partition=<name>`
- 当 `partition` 存在时：
  - 作业统计只聚合该分区返回的作业。
  - 资源统计只聚合该分区返回的节点。
- 当 `partition` 缺失时：
  - 保持现有全局统计行为不变。

### 2.2 Agent `metrics/<metric>`

- 接口：`GET /v<agent-version>/metrics/<metric>`
- 继续支持 `range=hour|day|week`
- 新增可选 query：`partition=<name>`
- 当 `partition` 存在时：
  - Agent 需要把该参数继续传给 `metrics_db.request(...)`。
- 当 `partition` 缺失时：
  - 保持现有 `metric + range` 两参调用行为不变。

### 2.3 Gateway 透传

- 接口：
  - `GET /api/agents/<cluster>/stats`
  - `GET /api/agents/<cluster>/metrics/<metric>`
- Gateway 不新增 query 重写逻辑。
- 只要求继续把原始 query string 原样拼到 Agent URL。

### 2.4 分区详情与分区入口

- 路由：`/:cluster/partitions/:partition`
- 分区详情页除核心摘要外，还需复用 dashboard 的实时资源与作业曲线：
  - 时间范围继续复用 dashboard 现有 `range / start / end`
  - query 固定带当前 `partition`
  - 图表切换资源类型时，仍需停留在当前分区详情路由，不得跳回 `dashboard`
- 分区详情页顶部摘要卡片负责展示节点数、总 CPU、已分配 CPU、总内存和 GPU；下方详情区不得重复展示这些资源容量字段，只保留名称、已分配节点、空闲节点等补充信息。
- 以下页面中的 `partition` 展示统一改为可点击入口，跳转到 `/:cluster/partitions/:partition`：
  - `/:cluster/job/:id`
  - `/:cluster/jobs`
  - `/:cluster/jobs-history`
  - `/:cluster/jobs-history/:id`
- 分区入口统一使用芯片式可点击样式，避免和普通文本字段混淆。

## 3. 启用条件

- `stats` 依赖 Agent 已配置 `slurmrestd`。
- `metrics` 依赖 Agent 已启用 metrics 数据源。
- `partition` 为可选参数；未提供时不改变现有行为。

## 4. 接口与参数

### 4.1 Agent

- `GET /v<agent-version>/stats`
  - 可选 query：`partition`
- `GET /v<agent-version>/metrics/<metric>`
  - 可选 query：`range`
  - 可选 query：`partition`

### 4.2 Gateway

- `GET /api/agents/<cluster>/stats`
  - 可选 query：`partition`
- `GET /api/agents/<cluster>/metrics/<metric>`
  - 可选 query：`range`
  - 可选 query：`partition`

## 5. 权限要求

- `stats` 继续要求：
  - `dashboard:view:*` 或
  - `analysis:view:*`
- `metrics/<metric>` 继续沿用原有 metric 对应权限，不因 `partition` 新增额外权限。

## 6. 依赖与边界

- `stats` 复用现有 `slurmrestd.jobs(query=...)` 与 `slurmrestd.nodes_unfiltered(query=...)` 契约。
- `metrics` 复用现有 `metrics_db.request(...)`，但需要兼容尚未升级到 `partition` 参数签名的实现。
- 本轮不修改：
  - collector
  - metrics DB 核心实现
  - slurmrestd 核心实现

## 7. 降级行为

- 如果底层 `metrics_db.request` 仍是旧签名，只接受 `(metric, range)`：
  - Agent 不得因多传 `partition` 直接报 `TypeError`。
  - Agent 允许继续走旧行为返回全局指标。
- 这类兼容分支只用于避免合并顺序导致接口报错，不代表底层指标源已经完成分区过滤。

## 8. 相关测试入口

- `slurmweb/tests/views/test_agent.py`
- `slurmweb/tests/views/test_agent_metrics_requests.py`
- `slurmweb/tests/views/test_gateway.py`
