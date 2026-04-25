# 用户分析后端与页面契约

本文说明用户分析能力的启用条件、后端数据来源，以及当前前端用户工作台如何消费这些数据。

## 1. 启用条件

用户分析能力要求以下条件同时满足：

- `[database] enabled = yes`
- `[persistence] enabled = yes`
- `[metrics] enabled = yes`
- `[user_metrics] enabled = yes`

同时还需要 Agent 实际完成相关依赖装配：

- 历史作业持久化可用
- Prometheus 查询可用
- 用户分析聚合 store 可用

仅打开 `[user_metrics] enabled = yes` 不代表功能一定可用。Agent 会根据依赖状态决定是否真正对外暴露 `user_metrics=true`。

## 2. 数据来源

当前实现不新增后端用户详情聚合接口，仍复用现有能力：

- 用户资料区
  - `associations`
- 用户分析区摘要
  - `GET /api/agents/<cluster>/user/<username>/activity/summary`
- 用户分析区趋势图
  - `GET /api/agents/<cluster>/user/<username>/metrics/history?range=hour|day|week`
- 我的身份与权限摘要
  - 前端本地 `authStore`
  - 当前 cluster merged permissions

后端聚合表和依赖仍保持不变：

- `job_snapshots`
- `user_tool_daily_stats`
- Prometheus 用户指标

## 3. 路由契约

前端用户分析现已并入统一用户工作台，相关路由如下：

- `/:cluster/users/:user`
  - 统一用户工作台主路由
- `/:cluster/me`
  - 当前登录用户自助入口
- `/:cluster/users/:user/analysis`
  - 兼容旧链接
  - 会重定向到 `user` 并附带 `query.section=analysis`

因此，后端仍只需要保证原有 `associations`、`user_activity_summary`、`user_metrics_history` 三类数据源稳定可用。

## 4. 权限矩阵

用户工作台按区块做权限控制：

| 页面区块 | 依赖 permission | 依赖 capability |
|---|---|---|
| 我的身份与权限摘要 | 无 | 无 |
| 用户资料区 | `associations-view` | 无 |
| 用户分析区 | `view-jobs` | `cluster.user_metrics=true` |

整页进入规则：

- 查看自己时始终允许进入 `/:cluster/me`
- 查看别人时，只要资料区或分析区至少有一个可见，就允许进入
- 查看别人时两个区块都不可见，前端统一跳 `/forbidden`

## 5. 用户分析区页面行为

用户分析区由 `UserAnalyticsPanels.vue` 负责渲染，关键行为如下：

- 提交趋势支持 `hour`、`day`、`week` 切换
- 工具分析默认取内存最高的前若干工具
- 工具图改为双指标横向条
  - 左侧：平均最大内存
  - 右侧：作业数
- 每一行同时展示工具名、CPU、Runtime、jobs

排序规则：

1. 按 `avg_max_memory_mb` 降序
2. 内存相同按 `jobs` 降序

## 6. 降级行为

前端区分 capability 缺失与 permission 缺失：

- `user_metrics` 未启用
  - 不当作权限错误
  - 用户工作台只隐藏分析区
- 缺少 `view-jobs`
  - 分析区不渲染
  - 若查看别人且同时也没有资料区权限，则跳 `/forbidden`
- `associations` 请求失败
  - 仅资料区显示错误提示
- `user_activity_summary` 或 `user_metrics_history` 请求失败
  - 仅分析区显示错误或降级提示

## 7. 百分比与图表输出约束

用户分析本轮没有新增百分比 API，但页面层面的信息表达有统一要求：

- 百分比场景统一用数字值和图标组件表达
- 工具分析不再依赖单一 canvas 文本绘制
- 图表可访问文本优先，保证列表信息和视觉图能同时独立理解

## 8. 验证建议

最小验证步骤：

1. 确认 Agent `/info` 返回 `user_metrics=true`
2. 访问 `/:cluster/users/:user`
3. 访问 `/:cluster/me`
4. 访问旧链接 `/:cluster/users/:user/analysis`
5. 校验旧链接已重定向到 `user?section=analysis`
6. 校验无权限用户进入用户工作台时是否跳 `/forbidden`
7. 校验分析区工具图是否同时展示内存和作业数

前端验证命令：

```powershell
npm --prefix frontend run type-check
npm --prefix frontend run test:unit -- --run
npm --prefix frontend run build
```
