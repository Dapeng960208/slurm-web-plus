# Slurm Web Plus 架构概览

## 1. 分层结构

系统保持 Browser -> Gateway -> Agent 的三层结构：

```text
Browser (Vue SPA)
  -> Gateway
     -> Agent
        -> slurmrestd
        -> Prometheus
        -> PostgreSQL
        -> LDAP
        -> Cache Service
```

边界保持不变：

- 浏览器只访问 Gateway
- Gateway 负责认证、集群发现、权限聚合和代理转发
- Agent 是单集群能力边界，负责对接 Slurm、Prometheus、PostgreSQL、LDAP 缓存和可选 AI

## 2. 前端路由与权限架构

前端路由定义集中在 `frontend/src/router/index.ts`。本轮与用户工作台相关的路由变化如下：

- 新增 `/:cluster/me`，路由名 `my-profile`
- 新增 `/forbidden`，路由名 `forbidden`
- `/:cluster/users/:user/analysis` 保留为兼容路由
  - 实际行为改为重定向到 `user`
  - 自动追加 `query.section=analysis`

整页权限拦截改为统一走 `/forbidden`，当前覆盖：

- `ai`
  - 缺少 `view-ai`
- `jobs-history` / `job-history`
  - 缺少 `view-history-jobs`
- `settings-access-control`
  - 缺少 `roles-view`
- `settings-ai`
  - 缺少 `manage-ai`
- `user` / `my-profile`
  - 不满足用户工作台可见性规则

只有 permission 不足才跳 `403`。以下情况仍保持原有降级：

- AI capability 未启用时回 dashboard
- 历史作业 capability 未启用时回 jobs
- settings 的 cluster capability 缺失时回 settings 或 settings-account

## 3. 用户工作台的前端组合

用户工作台统一由 `frontend/src/views/UserView.vue` 实现，权限解析逻辑抽到 `frontend/src/composables/userWorkspace.ts`。

核心判断函数：

- `canViewUserProfile(cluster, user)`
- `canViewUserAnalytics(cluster, user)`
- `resolveUserWorkspaceSections(cluster, user)`

行为规则：

- 查看自己：始终允许进入 `/:cluster/me`
  - 身份与权限摘要始终展示
  - 资料区和分析区按权限与 capability 显示或隐藏
- 查看别人：
  - 有任一可见区块则允许进入
  - 资料区和分析区支持部分可见
  - 两类区块都不可见时跳 `/forbidden`

数据来源：

- 身份摘要：`authStore`
- 用户资料区：`associations`
- 用户分析区：`user_activity_summary`、`user_metrics_history`

## 4. 统一 403 页

`frontend/src/views/ForbiddenView.vue` 提供统一的整页无权限反馈，页面职责固定：

- 显示“当前页面无访问权限”
- 展示缺少的 permission 信息
- 明确提示“请联系管理员申请权限”
- 提供返回上一路由和回 dashboard / clusters 的入口

该页只表达权限不足，不承载 feature disabled、集群不可用或空数据语义。

## 5. 百分比与高频 UI 统一

本轮新增两个共享前端抽象：

- `frontend/src/composables/percentages.ts`
  - 统一格式化百分比数字
- `frontend/src/components/PercentMetric.vue`
  - 统一渲染数字主值 + 百分比图标

已替换的高频位置包括：

- `NodeView.vue`
- `ClusterAnalysisView.vue`
- `NodeMetricsHistoryChart.vue`
- `SettingsCacheStatistics.vue`

图表轴刻度仍可保留数值百分比；卡片、tooltip、列表和表格场景统一采用共享组件。

## 6. 用户分析区重构

用户分析仍复用既有后端 API，但前端结构已调整：

- 分析主容器改为可嵌入的 `UserAnalyticsPanels.vue`
- 工具分析图改为 `UserToolAnalysisChart.vue`
- 展示方式从单一 canvas 柱状图改为 DOM/CSS 横向双指标条

当前图表行为：

- 左侧展示平均最大内存
- 右侧展示作业数
- 默认按平均最大内存降序，同值再按作业数排序
- 每行补充工具名、CPU、Runtime、jobs 标签

## 7. 顶栏用户入口

`ClusterMainLayout.vue` 和 `SettingsLayout.vue` 顶栏统一换成 `UserMenu.vue`。

用户菜单提供：

- `My workspace`
- `Account permissions`
- `Sign out`

`settings` 内部跳转 `my-profile` 时，cluster 解析顺序如下：

1. 当前 `runtime.currentCluster`
2. `beforeSettingsRoute` 对应 cluster
3. 第一个 allowed cluster

## 8. 文档与验证要求

本轮涉及路由、权限、页面结构和 UI 统一，因此必须同步更新：

- `docs/README.md`
- `docs/overview/project-overview.md`
- `docs/overview/architecture-overview.md`
- `docs/overview/latest-features.md`
- `docs/features/user-analytics/backend.md`
- `docs/tracking/current-release.md`

前端验证建议：

```powershell
npm --prefix frontend run type-check
npm --prefix frontend run test:unit -- --run
npm --prefix frontend run build
```
