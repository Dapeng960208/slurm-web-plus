# Dashboard 分区筛选后端实现说明

## 1. 设计原则

本轮只在接口契约层补齐 `partition`，不改动 collector、metrics DB 或 `slurmrestd` 核心实现。

实现原则：

- 优先复用现有 query 通道。
- 保持默认行为不变。
- 对尚未同步升级的底层签名做兼容，避免因合并顺序不同导致接口直接报错。

## 2. Agent `stats`

### 2.1 请求处理

- 从 `request.args` 读取 `partition`。
- 当存在 `partition` 时，组装：

```python
query = {"partition": "<name>"}
```

### 2.2 作业聚合

- 有 `partition` 时调用：

```python
current_app.slurmrestd.jobs(query=query)
```

- 无 `partition` 时保持原有 `slurmrest("jobs")`。

### 2.3 资源聚合

- 优先复用现有 `nodes_unfiltered()` 契约，因为 `stats` 需要完整节点字段计算内存与 GPU。
- 有 `partition` 且存在 `nodes_unfiltered` 时调用：

```python
current_app.slurmrestd.nodes_unfiltered(query=query)
```

- 否则回退到 `current_app.slurmrestd.nodes(query=query)` 或原有 `slurmrest("nodes")`。

## 3. Agent `metrics/<metric>`

### 3.1 请求处理

- 读取：
  - `range`
  - `partition`

### 3.2 兼容透传

- 通过 `inspect.signature()` 检查 `current_app.metrics_db.request` 是否支持：
  - 显式 `partition` 参数，或
  - `**kwargs`

- 若支持，则调用：

```python
metrics_db.request(metric, metric_range, partition=partition)
```

- 若不支持，则继续调用旧签名：

```python
metrics_db.request(metric, metric_range)
```

### 3.3 兼容目的

这样做的目的不是掩盖底层未实现分区过滤，而是保证在多 Agent 并行开发、合并顺序不固定的情况下：

- 新视图层可先合并。
- 旧 metrics DB 实现不会因此报 `TypeError`。

## 4. Gateway

- Gateway 已在统一 `request_agent()` / `proxy_stream_agent()` 中拼接原始 `request.query_string`。
- 因此 `partition` 不需要新增任何业务逻辑。
- 本轮只补测试，证明 `/stats` 与 `/metrics/<metric>` 也遵守这条统一契约。

## 5. 风险与边界

- 当前 `stats` 的分区过滤依赖底层 `slurmrestd.jobs(query=...)` 与 `nodes_unfiltered(query=...)` 返回的就是分区结果。
- 当前 `metrics` 的分区过滤只在底层 `metrics_db.request` 真正支持该参数时才能生效。
- 因为本轮不允许修改 metrics DB 核心实现，所以这里明确区分：
  - 接口契约已支持
  - 底层指标源是否已完整实现，需依赖后续或并行改动
