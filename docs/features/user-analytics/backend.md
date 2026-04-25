# 用户分析后端与页面契约

## 1. 启用条件

用户分析当前按基础依赖自动推导：

- 数据库开启
- metrics 开启

两者同时满足时，Agent 会对外暴露：

- `user_metrics`
- `user_analytics`

旧 `persistence.enabled` 与 `user_metrics.enabled` 不再作为新的业务语义来源。

## 2. 数据来源

当前仍复用既有接口与聚合数据：

- `GET /api/agents/<cluster>/user/<username>/activity/summary`
- `GET /api/agents/<cluster>/user/<username>/metrics/history`
- `GET /api/agents/<cluster>/associations`

## 3. 权限要求

用户空间当前按区块控制：

| 区块 | 新规则 |
|---|---|
| 用户资料区 | `user/profile:view:self` 或 `user/profile:view:*`，也兼容 `accounts:view:*` |
| 用户分析区 | `user/analysis:view:self` 或 `user/analysis:view:*`，也兼容 `jobs:view:*` |
| 历史作业快捷入口 | `jobs-history:view:*` |

说明：

- 查看自己时优先使用 `self`
- 查看他人时需要 `*`
- 历史 `view-jobs` 与 `associations-view` 通过旧权限映射继续兼容
- Agent 端点在运行时会根据 URL 中的 `<username>` 解析 `self` / `*` scope，避免把他人请求误判成自己的权限范围，也避免因装饰器闭包取值错误导致接口直接报错

## 4. 路由契约

相关入口：

- `/:cluster/users/:user`
- `/:cluster/me`
- `/:cluster/users/:user/analysis`
  - 当前仅作为兼容入口，重定向到 `user?section=analysis`

## 5. 降级行为

- 用户分析 capability 不可用：
  - 隐藏分析区，不视为权限错误
- 权限不足：
  - 对他人页面统一跳转 `/forbidden`
- 数据请求失败：
  - 只在对应区块显示错误
