# 当前发布跟踪：用户工作台、403 拦截页与百分比统一

## 1. 当前主题

本轮发布聚焦把“用户入口、权限反馈、数据表达”统一掉，避免继续在各页面做分散修补。

目标包括：

- 合并用户信息页、用户分析页和我的入口为统一用户工作台
- 新增统一 `403` 无权限拦截页
- 把全站高频百分比展示收口到共享组件
- 重做用户分析中的工具使用图
- 补强顶栏、链接态、空状态和高频交互的小图标与微样式

## 2. 已完成

- 新增 `/:cluster/me`，复用统一用户工作台
- 新增 `/forbidden`，整页权限不足统一跳转到该页
- 旧路由 `/:cluster/users/:user/analysis` 保留并重定向到 `user?section=analysis`
- `UserView.vue` 改造成统一用户工作台
- `UserAnalyticsPanels.vue` 调整为可嵌入工作台的分析区
- `UserToolAnalysisChart.vue` 改为双指标横向条
- `ClusterMainLayout.vue` 与 `SettingsLayout.vue` 顶栏接入 `UserMenu.vue`
- Jobs / History / Account / LDAP Cache 等高频用户名入口改为统一用户链接
- 新增 `PercentMetric.vue` 与 `percentages.ts`
- `NodeView.vue`、`ClusterAnalysisView.vue`、`NodeMetricsHistoryChart.vue`、`SettingsCacheStatistics.vue` 已切到统一百分比展示
- 全站补充 `ui-inline-link`、`ui-user-link`、`ui-percent-badge`、`ui-empty-state`、`ui-forbidden-panel` 等共享微样式
- 已同步更新本轮要求的文档入口和专题文档

## 3. 进行中

- 无额外功能开发项

## 4. 风险与阻塞

- `npm --prefix frontend run test:unit -- --run` 在当前环境中执行超过 300 秒后超时中断，尚未拿到完整结果
- 关键改动相关的定向 Vitest 用例已通过，当前没有发现构建级阻塞

## 5. 需要同步的正式文档

本轮已经同步：

- `docs/README.md`
- `docs/overview/project-overview.md`
- `docs/overview/architecture-overview.md`
- `docs/overview/latest-features.md`
- `docs/features/user-analytics/backend.md`
- `docs/tracking/current-release.md`

## 6. 验证状态

已通过：

- `npm --prefix frontend run type-check`
- 关键改动相关 Vitest 定向用例
- `npm --prefix frontend run build`

补充说明：

- 本轮新增用例覆盖了 `ForbiddenView` 和 `userWorkspace` 权限解析
- `UserView` 相关单测已修复 analytics 组件未隔离导致的真实请求问题
