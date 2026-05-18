# Dashboard 队列筛选接口测试计划

## 1. 测试目标

验证 Dashboard 相关 Agent/Gateway 接口对 `partition` query 的契约行为：

- Agent `stats` 按队列聚合。
- Agent `metrics` 透传队列并保持旧签名兼容。
- Gateway 对 `stats` 与 `metrics` 原样透传 query。
- 队列详情页图表复用同一套队列 query。
- 队列详情页平均排队时间曲线复用同一个时间组件，并按当前队列过滤历史作业。
- 作业与历史作业页面中的队列字段作为队列详情入口。
- 现有默认行为、权限和错误路径不回归。

## 2. Agent 测试点

### 2.1 `stats`

- `partition` 缺失时，继续返回全局统计。
- `partition=debug` 时：
  - `slurmrestd.jobs(query={"partition": "debug"})` 被调用。
  - `slurmrestd.nodes_unfiltered(query={"partition": "debug"})` 被调用。
  - 返回值使用队列结果重新计算 `jobs` 与 `resources`。

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

### 4.1 队列详情页

- `/:cluster/partitions/:partition` 页面显示实时图表区块。
- 传给 dashboard 图表的 query 固定带当前 `partition`。
- 平均排队时间曲线会请求 `jobs/history`，请求固定携带当前 `partition`、`state=COMPLETED`、`sort=submit_time`、`order=desc`。
- 平均排队时间曲线复用队列详情页时间组件；切换 `range` 或自定义 `start/end` 后，历史请求使用同一窗口。
- `jobs/history` 多页返回时，前端会拉取全部页面后再按 `submit_time -> start_time` 聚合为秒级平均排队时间。
- 当前用户无 `jobs-history:view:*` / `view-history-jobs` 权限，或历史接口失败、无样本时，实时图表仍显示，平均排队时间区域展示空态。
- 队列详情页切换资源图表类型时，路由仍保持在 `partition`，不跳回 `dashboard`。
- 顶部摘要卡片展示资源容量字段后，下方详情区不再重复展示节点数、总 CPU、已分配 CPU、总内存和 GPU。

### 4.2 队列跳转入口

- `JobView` 的连续详情列表中，`partition` 字段可点击跳转到队列详情页。
- `JobHistoryView` 的连续详情列表中，`partition` 字段可点击跳转到队列详情页。
- `JobsView` 列表中的 `partition` 列渲染为队列详情入口。
- `JobsHistoryView` 列表中的 `partition` 列渲染为队列详情入口。
- `ClusterAnalysisView` 的 `Partition Hotspots` 队列名称渲染为队列详情入口。

## 5. 自动化命令

```powershell
.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent.py slurmweb/tests/views/test_agent_metrics_requests.py slurmweb/tests/views/test_gateway.py
```

前端定向验证：

```powershell
cd frontend
npx vitest run tests/views/PartitionView.spec.ts tests/views/JobView.spec.ts tests/views/JobHistoryView.spec.ts tests/views/JobsView.spec.ts tests/views/JobsHistoryView.spec.ts tests/components/dashboard/ChartResourcesHistory.spec.ts tests/components/dashboard/DashboardCharts.spec.ts
```

队列平均排队时间定向验证：

```powershell
cd frontend
npx vitest run tests/views/PartitionView.spec.ts tests/composables/queueWaitHistory.spec.ts
```

## 6. 手工关注点

- 如果后续核心 `metrics_db.request` 真正升级为支持 `partition`，需要补充更低层测试验证指标源是否按队列过滤，而不仅是视图层透传。
