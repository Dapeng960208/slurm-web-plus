# 前端审查报告

## 1. 审查范围

本次前端审查聚焦以下主题：

- 权限消费是否与当前 `resource:operation:scope` 模型一致
- `Admin` 与兼容 `Settings` 路由是否按当前真实入口工作
- 页面局部按钮、筛选区和共享控件是否复用既有样式 token
- 与本轮修复点直接相关的前端测试是否覆盖

重点核对文件：

- `frontend/src/stores/runtime.ts`
- `frontend/src/router/index.ts`
- `frontend/src/views/DashboardView.vue`
- `frontend/src/views/NodeView.vue`
- `frontend/src/components/jobs/JobsFiltersPanel.vue`
- `frontend/src/components/dashboard/DashboardCharts.vue`
- `frontend/src/components/resources/ResourcesFiltersPanel.vue`
- `frontend/src/composables/userWorkspace.ts`

## 2. 当前结论

- 当前前端权限主口径已经是 `runtimeStore.hasRoutePermission(...)` 与 `hasRoutePermissionAnyScope(...)`。
- 主菜单、路由守卫和大部分业务页已按规则模型工作，但共享筛选区和局部图表仍残留少量旧 `actions[]` 判断。
- 当前真实管理入口是 `/:cluster/admin/*`；`/settings/ai`、`/settings/access-control`、`/settings/cache`、`/settings/ldap-users` 只是兼容重定向入口，旧 `/settings/ldap-cache` 仅保留为重定向兼容，不应再写成主要操作路径。
- 全局设计 token 已集中在 `frontend/src/style.css`，按钮语义也已有 `ui-button-primary|warning|danger|secondary|ghost`；本轮样式问题主要是个别组件仍在局部硬编码 segmented button、输入框和 badge 视觉。

## 3. 已确认并修复的问题

### 3.1 共享权限消费点仍依赖旧 `actions[]`

已修复：

- `DashboardView` 分区筛选改为按 `jobs/filter-partitions:view:*` 或 `resources/filter-partitions:view:*`
- `NodeView` 节点作业轮询改为按 `jobs:view:*`
- `JobsFiltersPanel` 的 `Accounts / QOS / Partitions` 筛选改为按对应 filter resource
- `DashboardCharts` 改为按 `resources:view:*` 与 `jobs:view:*`
- `ResourcesFiltersPanel` 的分区筛选改为按 `resources/filter-partitions:view:*`

影响：

- 菜单、路由和页内局部控件的权限口径更一致
- 前端不再要求旧 `view-partitions`、`view-qos`、`view-accounts` 等动作必须同时存在才能显示新规则已允许的内容

### 3.2 `userWorkspace` 默认参数与当前调用方式不一致

已修复：

- `canViewUserProfile()` 与 `canViewUserAnalytics()` 的 `self` 参数改为默认 `false`

影响：

- 保持现有调用点和测试夹具语义稳定
- 仍保留必要的 legacy fallback，但不会因为缺少显式第四个参数而把普通用户误判成 `self`

### 3.3 局部控件样式仍有明显硬编码分叉

已修复：

- `ResourcesDiagramNavigation` 与 `ChartResourcesHistogram` 改为共享 segmented 控件样式
- `AccountFilterSelector`、`QosFilterSelector`、`UserFilterSelector` 改为共享 combobox 输入与下拉样式
- `ResourcesFiltersBar`、`QosHelpModal`、`AccountTreeNode` 改为复用现有 `ui-panel-soft`、`ui-chip` 和 `ui-button-secondary`

影响：

- 同类按钮和筛选控件的颜色、圆角、阴影和 hover 反馈已统一到现有设计系统
- 后续同类控件可直接复用共享类，避免继续散落局部 Tailwind 组合

## 4. 当前剩余风险

### 4.1 `runtime.ts` 仍保留 `hasPermission()` / `hasClusterPermission()`

- 这两个接口仍被兼容逻辑和少量 fallback 使用。
- 目前它们不是主鉴权入口，但如果后续继续扩展页面功能，新增代码应优先使用 `hasRoutePermission(...)`。

### 4.2 前端仍存在少量 action 级测试夹具

- 当前主路径测试已经开始向 `rules[]` 收口。
- 仓库里仍有部分旧夹具继续依赖 `actions[]`，后续扩大回归时应逐步迁移，避免形成新的双口径测试基线。

## 5. 建议

- 新增页面或按钮显示条件时，默认先从资源名反推路由规则，不再先找旧 action 名。
- 兼容入口文档统一写成“旧 Settings 路由重定向到 `/:cluster/admin/*`”，避免使用者误解为两个并行管理中心。
- 前端样式继续优先复用 `ui-button-*`、`ui-panel-soft`、`ui-input-field`，不要在筛选器和局部导航上重复定义一套按钮视觉。

## 6. 验证记录

已通过：

- `npm --prefix frontend run type-check`
- `cd frontend && npx vitest run tests/views/DashboardView.spec.ts tests/views/NodeView.spec.ts tests/components/jobs/JobsFiltersPanel.spec.ts tests/components/dashboard/DashboardCharts.spec.ts tests/composables/userWorkspace.spec.ts`
- `cd frontend && npx vitest run tests/components/resources/ResourcesDiagramNavigation.spec.ts tests/components/accounts/AccountTreeNode.spec.ts tests/components/jobs/UserFilterSelector.spec.ts`

说明：

- 上述验证覆盖了本轮修复的共享权限消费点。
- 全量 `vitest` 未在本轮第一阶段作为唯一验收条件；后续样式修复和测试审查完成后再继续补跑定向集。
