# Dashboard 分区筛选接口测试计划

## 1. 测试目标

验证 Dashboard 相关 Agent/Gateway 接口对 `partition` query 的契约行为：

- Agent `stats` 按分区聚合。
- Agent `metrics` 透传分区并保持旧签名兼容。
- Gateway 对 `stats` 与 `metrics` 原样透传 query。
- 分区详情页图表复用同一套分区 query。
- 作业与历史作业页面中的分区字段作为分区详情入口。
- 现有默认行为、权限和错误路径不回归。

## 2. Agent 测试点

### 2.1 `stats`

- `partition` 缺失时，继续返回全局统计。
- `partition=debug` 时：
  - `slurmrestd.jobs(query={"partition": "debug"})` 被调用。
  - `slurmrestd.nodes_unfiltered(query={"partition": "debug"})` 被调用。
  - 返回值使用分区结果重新计算 `jobs` 与 `resources`。

### 2.2 `metrics`

- `partition` 缺失时，继续调用 `metrics_db.request(metric, range)`。
- `partition=debug` 且底层方法支持该参数时：
  - 调用 `metrics_db.request(metric, range, partition="debug")`。
- `partition=debug` 但底层方法仍是旧两参签名时：
  - 请求不报错。
  - 继续调用旧签名 `metrics_db.request(metric, range)`。

### 2.3 既有回归点

- metrics 禁用时仍返回 `501`。
- 权限不足时仍返回 `403`。
- 指标名不存在时仍返回 `404`。
- metrics DB 抛出 `SlurmwebMetricsDBError` 时仍返回 `500`。

## 3. Gateway 测试点

### 3.1 `stats`

- `GET /api/agents/<cluster>/stats?partition=debug`
  - Agent URL 应为 `/stats?partition=debug`

### 3.2 `metrics`

- `GET /api/agents/<cluster>/metrics/jobs?range=day&partition=debug`
  - Agent URL 应为 `/metrics/jobs?range=day&partition=debug`

### 3.3 既有回归点

- 其他 metrics history、node metrics history 等 query 透传测试继续保留。
- Gateway 不新增专门的 `partition` 业务分支。

## 4. 前端测试点

### 4.1 分区详情页

- `/:cluster/partitions/:partition` 页面显示实时图表区块。
- 传给 dashboard 图表的 query 固定带当前 `partition`。
- 分区详情页切换资源图表类型时，路由仍保持在 `partition`，不跳回 `dashboard`。
- 顶部摘要卡片展示资源容量字段后，下方详情区不再重复展示节点数、总 CPU、已分配 CPU、总内存和 GPU。

### 4.2 分区跳转入口

- `JobView` 的 summary strip 中 `partition` 可点击跳转到分区详情页。
- `JobView` 的详情区 `partition` 字段使用统一分区芯片入口。
- `JobHistoryView` 的 summary strip 中 `partition` 可点击跳转到分区详情页。
- `JobsView` 列表中的 `partition` 列渲染为分区详情入口。
- `JobsHistoryView` 列表中的 `partition` 列渲染为分区详情入口。
- `ClusterAnalysisView` 的 `Partition Hotspots` 分区名称渲染为分区详情入口。

## 5. 自动化命令

```powershell
.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent.py slurmweb/tests/views/test_agent_metrics_requests.py slurmweb/tests/views/test_gateway.py
```

前端定向验证：

```powershell
cd frontend
npx vitest run tests/views/PartitionView.spec.ts tests/views/JobView.spec.ts tests/views/JobHistoryView.spec.ts tests/views/JobsView.spec.ts tests/views/JobsHistoryView.spec.ts tests/components/dashboard/ChartResourcesHistory.spec.ts tests/components/dashboard/DashboardCharts.spec.ts
```

## 6. 手工关注点

- 如果后续核心 `metrics_db.request` 真正升级为支持 `partition`，需要补充更低层测试验证指标源是否按分区过滤，而不仅是视图层透传。
