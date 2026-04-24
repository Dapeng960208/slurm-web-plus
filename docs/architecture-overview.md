# Slurm Web Plus 整体架构文档

## 1. 文档目标

本文档基于当前仓库中的前后端实现，说明 Slurm Web Plus 的整体架构、模块职责、核心数据流和主要扩展点。目标不是描述理想化设计，而是帮助开发者直接从代码结构理解系统如何工作。

适用范围：

- 前端 SPA 应用
- Gateway 服务
- Agent 服务
- Slurmrestd 适配层
- Prometheus 指标链路
- PostgreSQL 持久化链路

---

## 2. 系统总览

Slurm Web Plus 采用“前端 SPA + Gateway + 多 Agent”的分层架构。

```text
Browser (Vue SPA)
  -> Gateway API
     -> Cluster Agent A
        -> slurmrestd
        -> Prometheus
        -> PostgreSQL
        -> Redis/Cache
     -> Cluster Agent B
        -> ...
```

其中：

- 前端只访问 Gateway，不直接访问 Agent。
- Gateway 负责认证、集群发现、权限探测和请求代理。
- 每个 Agent 绑定一个 Slurm 集群，负责把 Slurm、指标库、缓存和持久化能力封装为统一 API。
- Agent 对 Slurm 的直接依赖是 `slurmrestd`，对历史指标的依赖是 Prometheus，对历史作业的依赖是 PostgreSQL。

核心入口代码：

- Gateway 应用入口：`slurmweb/apps/gateway.py`
- Agent 应用入口：`slurmweb/apps/agent.py`
- 前端入口：`frontend/src/main.ts`
- 前端路由：`frontend/src/router/index.ts`

---

## 3. 分层拓扑

### 3.1 浏览器前端层

前端是基于 Vue 3、Pinia、Vue Router、Vite 的单页应用，主要职责是：

- 渲染 Dashboard、Jobs、Resources、Accounts、Node Detail、Settings 等页面
- 管理登录态、当前集群、运行时配置和页面错误
- 通过 Gateway API 获取集群数据
- 对部分页面数据进行轮询刷新

关键代码：

- 应用启动：`frontend/src/main.ts`
- 路由定义：`frontend/src/router/index.ts`
- 运行时状态：`frontend/src/stores/runtime.ts`
- API 客户端：`frontend/src/composables/RESTAPI.ts`
- Gateway 封装：`frontend/src/composables/GatewayAPI.ts`
- 轮询器：`frontend/src/composables/DataPoller.ts`

### 3.2 Gateway 层

Gateway 是面向浏览器的统一 API 入口，不直接承载 Slurm 业务计算，主要负责：

- 用户认证与 JWT 签发
- 匿名访问模式处理
- 集群 Agent 发现与刷新
- 基于 JWT 向 Agent 请求集群权限
- 将 `/api/agents/<cluster>/...` 请求代理到目标 Agent
- 承载前端静态资源

关键代码：

- 应用和路由注册：`slurmweb/apps/gateway.py`
- Gateway 视图实现：`slurmweb/views/gateway.py`

### 3.3 Agent 层

Agent 是单集群后端服务，直接与 Slurm 及各类后端依赖交互。它负责：

- 查询 Slurm 作业、节点、分区、QOS、账户、关联关系、预约等
- 聚合 cluster stats
- 提供历史指标查询接口
- 提供作业历史查询接口
- 提供节点实时/历史指标接口
- 暴露 Prometheus exporter

关键代码：

- 应用初始化与可选组件装配：`slurmweb/apps/agent.py`
- Agent API 视图：`slurmweb/views/agent.py`

### 3.4 后端依赖层

后端依赖按职责可分为四类：

- Slurm 实时数据：`slurmrestd`
- 历史指标数据：Prometheus
- 持久化历史作业：PostgreSQL
- 缓存和命中统计：Redis/缓存服务

相关代码：

- Slurm 抽象层：`slurmweb/slurmrestd/__init__.py`
- Prometheus exporter：`slurmweb/metrics/collector.py`
- Prometheus 查询客户端：`slurmweb/metrics/db.py`
- 作业历史持久化：`slurmweb/persistence/jobs_store.py`
- 用户缓存存储：`slurmweb/persistence/users_store.py`

---

## 4. 后端架构

## 4.1 Gateway 服务职责

Gateway 通过 `SlurmwebAppGateway` 注册一组前端可见 API，典型路由包括：

- `/api/version`
- `/api/login`
- `/api/anonymous`
- `/api/clusters`
- `/api/agents/<cluster>/stats`
- `/api/agents/<cluster>/metrics/<metric>`
- `/api/agents/<cluster>/jobs`
- `/api/agents/<cluster>/jobs/history`
- `/api/agents/<cluster>/node/<name>/metrics`

这些路由在 `slurmweb/apps/gateway.py` 中注册，在 `slurmweb/views/gateway.py` 中实现。

Gateway 的典型工作方式：

1. 根据配置发现可用 Agent。
2. 通过 Agent `/info` 获取能力信息。
3. 通过 Agent `/permissions` 获取当前用户在每个集群上的动作权限。
4. 将前端集群级请求转发给对应 Agent。

Gateway 是“聚合和转发层”，不是 Slurm 业务逻辑主承载层。

## 4.2 Agent 服务职责

Agent 通过 `SlurmwebAppAgent` 暴露版本化 API，例如：

- `/v{version}/stats`
- `/v{version}/jobs`
- `/v{version}/nodes`
- `/v{version}/metrics/<metric>`
- `/v{version}/jobs/history`
- `/v{version}/node/<name>/metrics`
- `/v{version}/node/<name>/metrics/history`

Agent 在启动时按配置装配以下能力：

- `SlurmrestdFilteredCached`
- `CachingService`
- `SlurmWebMetricsCollector`
- `SlurmwebMetricsDB`
- `UsersStore`
- `JobsStore`
- Node metrics 查询能力
- 可选 RacksDB blueprint

这部分装配逻辑在 `slurmweb/apps/agent.py` 中完成。

## 4.3 Slurm 访问抽象层

`slurmweb/slurmrestd/__init__.py` 提供统一的 Slurm 访问封装，职责包括：

- 发现可用 slurmrestd API 版本
- 对不同 Slurm 版本做适配链处理
- 提供 `jobs()`、`nodes()`、`node()`、`accounts()`、`qos()`、`reservations()` 等统一方法
- 提供 `jobs_states()` 和 `resources_states()` 这类聚合统计能力

这个层的价值在于：

- 屏蔽 slurmrestd 版本差异
- 将视图层与底层 API 结构解耦
- 为缓存、过滤、聚合留出稳定接口

## 4.4 指标链路

指标链路分成“采集导出”和“历史查询”两段。

### 采集导出

`slurmweb/metrics/collector.py` 中的 `SlurmWebMetricsCollector` 通过读取 `slurmrestd.resources_states()` 和 `jobs_states()` 生成 Prometheus 指标，例如：

- `slurm_nodes{state=...}`
- `slurm_cores{state=...}`
- `slurm_gpus{state=...}`
- `slurm_memory{state=...}`
- `slurm_jobs{state=...}`
- `slurmweb_cache_hit_total`
- `slurmweb_cache_miss_total`

Agent 启用 metrics 时，会把 `/metrics` 挂载到 WSGI 应用上。

### 历史查询

`slurmweb/metrics/db.py` 中的 `SlurmwebMetricsDB` 不做采集，只负责向 Prometheus 发起 `query` 或 `query_range` 请求，并把结果转换成前端适合消费的时间序列结构。

当前 `memory` 指标的语义已经收敛为两段：

- `allocated`
- `idle`

这与 dashboard 当前展示保持一致。

## 4.5 作业历史持久化

`slurmweb/persistence/jobs_store.py` 提供后台线程式作业快照持久化能力，主要特征：

- 周期性抓取当前作业快照
- 通过 UPSERT 写入 PostgreSQL
- 保留历史查询、详情查询和保留期清理能力
- 主请求链路不直接阻塞在快照写入上

这套机制服务于：

- 历史作业列表
- 历史作业详情
- 已结束作业的追溯查询

## 4.6 缓存与用户缓存

Agent 可选接入缓存服务，主要用途包括：

- Slurm 查询结果缓存
- 缓存命中/未命中统计
- 登录后把认证用户信息缓存到支持数据库的 Agent

用户缓存同步逻辑在 `slurmweb/views/gateway.py` 中，Gateway 在用户登录成功后会尝试把用户信息推送到各 Agent。

---

## 5. 前端架构

## 5.1 应用启动与运行时配置

前端入口在 `frontend/src/main.ts`，负责：

- 创建 Vue 应用
- 注册 Pinia
- 注册 Router
- 加载运行时配置插件

运行时配置用于控制：

- 是否启用认证
- 网关地址与 API 基础行为
- 其他环境级 UI/功能配置

## 5.2 路由结构

前端路由在 `frontend/src/router/index.ts` 中统一定义，分为三类：

- 公共路由：`/login`、`/anonymous`、`/clusters`
- 全局设置路由：`/settings/...`
- 集群范围路由：`/:cluster/dashboard`、`/:cluster/jobs`、`/:cluster/resources`、`/:cluster/node/:nodeName` 等

路由守卫负责：

- 根据认证开关决定是否跳转登录页
- 同步当前路由到运行时 store
- 根据 `cluster` 参数切换当前集群上下文

## 5.3 API 访问层

前端 API 访问分成两层：

### `RESTAPI.ts`

负责底层 HTTP 请求能力，通常封装：

- Axios 实例
- Token 注入
- 请求取消
- 统一错误处理基础能力

### `GatewayAPI.ts`

负责把 Gateway 接口映射成前端可直接调用的 typed API，例如：

- `clusters()`
- `stats(cluster)`
- `jobs(cluster)`
- `job(cluster, id)`
- `metrics(cluster, metric, range)`
- `jobHistory(cluster, ...)`
- `nodeMetrics(cluster, nodeName)`

这层同时定义了前端广泛使用的接口类型，如：

- `ClusterDescription`
- `ClusterStats`
- `ClusterJob`
- `ClusterIndividualJob`

## 5.4 轮询模型

很多页面使用 `frontend/src/composables/DataPoller.ts` 中的 `useClusterDataPoller()` 做定时刷新。

这个轮询器统一处理：

- 首次加载态
- 刷新态
- 权限失败态
- 认证失败态
- 请求取消

典型页面如 Dashboard，会以固定间隔轮询 `/stats`。

## 5.5 布局与页面壳

主集群页面共享 `frontend/src/components/ClusterMainLayout.vue`，负责：

- 左侧侧边导航
- 顶部导航和 breadcrumb
- 集群切换入口
- 用户信息和登出入口
- 统一内容容器样式

设置页使用独立的 `SettingsLayout`，但现在也保持和主界面一致的侧边栏/顶部导航风格。

布局层的目标是：

- 保持跨页面一致导航体验
- 让 cluster 上下文在 UI 中始终可见
- 为页面内容提供统一的间距、容器和视觉主题

## 5.6 视图层组织

视图主要位于 `frontend/src/views/`，例如：

- `DashboardView.vue`
- `JobsView.vue`
- `JobView.vue`
- `JobsHistoryView.vue`
- `JobHistoryView.vue`
- `NodeView.vue`
- `AccountsView.vue`
- `AccountView.vue`

组件层则放在 `frontend/src/components/` 下，承担：

- 布局壳
- 页面级图表
- 表格与状态徽章
- 公共 header、alert、summary 组件

---

## 6. 核心数据流

## 6.1 Dashboard 统计流

Dashboard 顶部卡片的请求链路如下：

```text
DashboardView.vue
  -> useClusterDataPoller('stats')
  -> GatewayAPI.stats(cluster)
  -> GET /api/agents/:cluster/stats
  -> Gateway proxy
  -> Agent /v{version}/stats
  -> slurmrestd.jobs() + slurmrestd.nodes()
  -> 聚合 resources/jobs
```

当前 Dashboard 内存统计的语义是：

- `memory`: 集群总内存，来源于所有节点 `real_memory` 汇总
- `memory_allocated`: 集群已申请内存，来源于所有节点 `alloc_memory` 汇总，并限制不超过 `real_memory`
- `memory_available`: 集群可用内存，等于 `memory - memory_allocated`

也就是说，Dashboard 当前展示的是“总量 / 已申请 / 可用”，不是操作系统层面的实际占用内存。

## 6.2 Dashboard 资源历史图流

Dashboard 的 `Resource Status` 图表链路如下：

```text
DashboardCharts.vue / ChartResourcesHistogram.vue
  -> GatewayAPI.metrics(cluster, 'memory', range)
  -> GET /api/agents/:cluster/metrics/memory
  -> Gateway proxy
  -> Agent /v{version}/metrics/memory
  -> SlurmwebMetricsDB.request('memory', range)
  -> Prometheus query/query_range
```

当前 Memory 历史图只保留两个状态：

- `allocated`
- `idle`

并满足：

`allocated + idle = total memory`

## 6.3 作业详情流

实时作业详情链路：

```text
JobView.vue
  -> GatewayAPI.job(cluster, id)
  -> Gateway /api/agents/:cluster/job/:id
  -> Agent /v{version}/job/:id
  -> slurmrestd job query
```

历史作业详情链路：

```text
JobHistoryView.vue
  -> GatewayAPI.jobHistoryDetail(cluster, recordId)
  -> Gateway /api/agents/:cluster/jobs/history/:recordId
  -> Agent /v{version}/jobs/history/:recordId
  -> JobsStore PostgreSQL query
```

因此，实时作业和历史作业虽然页面展示接近，但数据源不同：

- 实时详情来自 Slurm
- 历史详情来自 PostgreSQL 快照

## 6.4 节点详情流

节点详情包含两类数据：

1. Slurm 节点基础属性
2. Node exporter 指标

链路分别是：

```text
NodeView.vue
  -> GatewayAPI.node(cluster, nodeName)
  -> Agent /node/:name
  -> slurmrestd.node(nodeName)
```

```text
Node metrics chart
  -> GatewayAPI.nodeMetrics / nodeMetricsHistory
  -> Agent /node/:name/metrics(/history)
  -> SlurmwebMetricsDB.node_instant_metrics / node_history_metrics
  -> Prometheus node_exporter queries
```

---

## 7. 当前关键领域模型

## 7.1 集群与权限模型

前端首先通过 `/api/clusters` 获取当前用户可见集群列表。每个集群对象不仅包含名字，还包含能力开关和权限信息，例如：

- 是否启用 metrics
- 是否启用 cache
- 是否启用 database
- 是否启用 persistence
- 是否启用 node metrics
- 当前用户 roles/actions

这让前端可以根据集群能力动态启用或隐藏页面和功能。

## 7.2 Dashboard 资源模型

当前 dashboard 使用的 stats 资源模型已经收敛为：

- `nodes`
- `cores`
- `memory`
- `memory_allocated`
- `memory_available`
- `gpus`

旧的 dashboard 内存兼容字段已经被清理，前后端围绕同一套语义工作。

## 7.3 指标模型

Prometheus 历史查询返回的结构本质上是：

```text
{
  state_or_key: [
    [timestamp_ms, value],
    ...
  ]
}
```

其中：

- `nodes`、`cores`、`gpus`、`memory`、`jobs` 等指标通常以状态名作为 key
- `cache` 指标则以 `hit`、`miss` 作为 key

## 7.4 历史作业模型

历史作业记录的主键并不是 Slurm job id 本身，而是数据库中的快照记录 id。这样可以支持：

- 相同 job id 的历史版本管理
- 统一的分页和排序
- 基于数据库字段的过滤检索

---

## 8. 可选能力与配置开关

系统不是所有模块都强依赖，许多能力由配置决定是否启用。

Agent 侧常见可选项：

- `metrics.enabled`
- `cache.enabled`
- `database.enabled`
- `persistence.enabled`
- `node_metrics.enabled`
- `racksdb.enabled`

这意味着部署时可以形成多个能力组合：

- 仅实时查询模式
- 实时查询 + Prometheus 历史指标
- 实时查询 + PostgreSQL 历史作业
- 全能力模式

前端通过 Gateway 返回的 cluster capability 字段感知这些功能是否可用。

---

## 9. 一致性设计点

当前代码中比较明确的统一设计有三类。

### 9.1 API 层次统一

- 浏览器永远请求 Gateway
- Gateway 永远按 cluster 路由到 Agent
- Agent 永远负责对接 Slurm/Prometheus/DB

这种设计让前端不需要知道集群服务真实地址，也降低了跨集群接入复杂度。

### 9.2 UI 壳层统一

- 集群页面共享主壳布局
- 设置页也收敛到一致的侧边导航和顶部导航模式
- 页面间距、卡片间距、头部结构逐步统一

### 9.3 Dashboard 内存语义统一

近期内存展示已经从混杂语义收敛为：

- 顶部卡片：总内存、申请内存、可用内存
- 历史图：申请内存、可用内存

前端、`/stats`、`metrics/memory` 和 Prometheus exporter 保持同一语义。

---

## 10. 扩展点

从当前代码看，主要扩展点包括：

### 10.1 新增 Agent 能力

如果需要接入新的集群级能力，通常路径是：

1. 在 Agent 侧增加视图与业务封装
2. 在 Gateway 侧代理该接口
3. 在 `GatewayAPI.ts` 中增加 typed client
4. 在页面中接入轮询或一次性请求

### 10.2 新增指标

Prometheus 指标链路扩展通常需要同时改三层：

1. `metrics/collector.py` 导出指标
2. `metrics/db.py` 增加查询映射
3. 前端图表组件增加状态映射和配色

### 10.3 新增持久化视图

如果需要新增可检索的历史类页面，应优先复用：

- `JobsStore` 的查询模式
- Gateway cluster proxy 模式
- 前端 DataPoller 或 typed API 模式

### 10.4 新增集群上下文页面

新的集群页面应挂在 `/:cluster/...` 路由下，并复用：

- `ClusterMainLayout.vue`
- `PageHeader.vue`
- 统一的 page/card gap 样式

---

## 11. 当前架构的主要优势

- 多集群能力清晰，Gateway 和 Agent 解耦明确
- Slurm 实时数据、历史指标、历史作业分层明确
- 前端 API、轮询和布局模式已经形成较稳定的复用结构
- 大量后端能力可按配置启停，适合不同部署规模
- Dashboard、Job、Node 等核心页面都能映射到明确的数据来源

---

## 12. 当前架构需要注意的点

### 12.1 Gateway 与 Agent 的接口版本耦合

Gateway 会校验 Agent 版本并拼接 `/v{version}` 路径，因此前后端升级时要注意版本兼容窗口。

### 12.2 指标语义必须保持端到端一致

Dashboard 这类聚合页面很容易出现“页面文案、Agent 聚合逻辑、Prometheus 状态定义”不一致的问题。内存指标已经发生过这类调整，后续新增指标时要同步检查：

- Agent `/stats`
- `resources_states()`
- Prometheus exporter
- `metrics/db.py`
- 前端类型和图表文案

### 12.3 实时数据与历史数据并非同源

作业详情与历史作业详情、节点详情与节点实时指标，在数据源上是分开的。页面设计上如果希望统一视觉，需要接受“展示层统一，数据延迟特性不同”这一事实。

### 12.4 可选模块较多，测试需要覆盖组合

由于 metrics、database、persistence、node_metrics 都可开关，回归测试要特别注意不同部署组合下的：

- 页面入口是否正确隐藏
- Gateway capability 是否正确返回
- 前端是否对不可用能力做降级处理

---

## 13. 建议的阅读顺序

如果要快速理解系统，建议按下面顺序读代码：

1. `slurmweb/apps/gateway.py`
2. `slurmweb/views/gateway.py`
3. `slurmweb/apps/agent.py`
4. `slurmweb/views/agent.py`
5. `slurmweb/slurmrestd/__init__.py`
6. `slurmweb/metrics/collector.py`
7. `slurmweb/metrics/db.py`
8. `slurmweb/persistence/jobs_store.py`
9. `frontend/src/router/index.ts`
10. `frontend/src/composables/GatewayAPI.ts`
11. `frontend/src/composables/DataPoller.ts`
12. `frontend/src/components/ClusterMainLayout.vue`
13. `frontend/src/views/DashboardView.vue`

---

## 14. 总结

Slurm Web Plus 当前是一个以 Gateway 为统一入口、以 Agent 为集群边界、以 Slurmrestd/Prometheus/PostgreSQL 为后端数据源的多层系统。

从实现上看，系统已经形成了比较稳定的三条主线：

- 实时 Slurm 查询链路
- Prometheus 历史指标链路
- PostgreSQL 历史作业链路

前端则围绕统一布局壳、typed API 和轮询机制来消费这些能力。后续无论是继续增强 dashboard、扩展节点监控，还是增加历史分析页面，都建议继续沿用这套分层边界，而不是让前端直接耦合到底层数据源细节。
