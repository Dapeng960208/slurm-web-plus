# 最新功能

## 1. 用户工作台合并

本轮前端把“用户信息页”“用户分析页”“右上角我的入口”合并成一个统一的用户工作台。

涉及路由：

- `/:cluster/users/:user`
- `/:cluster/me`
- `/:cluster/users/:user/analysis`
  - 保留旧入口
  - 自动重定向到 `user` 路由并附带 `query.section=analysis`

页面结构固定为三类区块：

- 我的身份与权限摘要
- 用户资料区
- 用户分析区

权限矩阵：

| 场景 | `associations-view` | `view-jobs` + `user_metrics` | 结果 |
|---|---|---|---|
| 查看自己 | 否 | 否 | 可进入，只显示身份与权限摘要 |
| 查看自己 | 是 | 否 | 显示摘要和资料区 |
| 查看自己 | 否 | 是 | 显示摘要和分析区 |
| 查看别人 | 是 | 否 | 仅显示资料区 |
| 查看别人 | 否 | 是 | 仅显示分析区 |
| 查看别人 | 否 | 否 | 跳 `/forbidden` |

## 2. 统一 403 无权限拦截页

新增 `/forbidden` 整页拦截页，用于所有整页级权限不足的场景。

页面固定包含：

- 当前页面无访问权限
- 缺少的 permission 说明
- 请联系管理员申请权限
- 返回上一路由
- 回 dashboard / clusters 的快捷入口

当前已经接入统一 403 的页面：

- `/:cluster/ai`
- `/:cluster/jobs/history`
- `/:cluster/jobs/history/:id`
- `/settings/access-control`
- `/settings/ai`
- 用户工作台相关页面

## 3. 全站百分比统一样式

新增共享百分比展示组件，统一约束为：

- 主值始终显示数字
- 搭配百分比图标
- 不能只靠颜色表达状态
- 空值和 `0` 值有稳定渲染

已替换的高频页面：

- `NodeView.vue`
- `ClusterAnalysisView.vue`
- `NodeMetricsHistoryChart.vue`
- `SettingsCacheStatistics.vue`

## 4. 用户分析工具图升级

用户分析里的工具模块已经改为双指标横向条，不再使用单一 canvas 柱状图。

新行为：

- 按平均最大内存降序
- 同时展示平均最大内存和作业数
- 每行附带 CPU、Runtime、jobs 标签
- 配色沿用现有绿灰风格变量，不引入新的主色体系

## 5. 高频 UI 补强

为了保持站点整体风格一致，本轮只做共享层增强，不做大面积重排：

- 顶栏用户名改为带图标的用户菜单
- Jobs / History / Account / LDAP Cache 中的用户名改为统一链接样式
- filter chips 改为更贴近现有绿灰玻璃风格
- 空状态、无权限态、统计卡片和分区标题补充轻量图标与统一微样式

## 6. 本轮验证

已完成：

- `npm --prefix frontend run type-check`
- 关键改动相关的 Vitest 定向用例
- `npm --prefix frontend run build`

说明：

- `npm --prefix frontend run test:unit -- --run` 在当前环境中运行超过 300 秒后超时中断，尚未得到完整结果。
