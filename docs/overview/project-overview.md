# Slurm Web Plus 项目概览

## 1. 项目定位

Slurm Web Plus 是面向 Slurm HPC 集群的 Web 管理与分析平台。它在不替代 Slurm 原生能力的前提下，提供统一的监控、查询、分析和权限入口。

当前仓库主要覆盖：

- 集群实时概览与分析
- 作业、历史作业、节点、资源、账户、用户、QOS、预约查询
- 基于 PostgreSQL 的历史作业持久化与用户分析
- LDAP 登录、用户缓存和访问控制
- 可选的 AI 助手能力

## 2. 当前前端核心入口

前端采用 `Vue 3 + TypeScript + Vue Router + Pinia`，高频入口分为两类：

- 全局入口
  - `/clusters`
  - `/settings`
  - `/login`
  - `/anonymous`
  - `/signout`
  - `/forbidden`
- 集群范围入口
  - `/:cluster/dashboard`
  - `/:cluster/analysis`
  - `/:cluster/jobs`
  - `/:cluster/jobs/history`
  - `/:cluster/resources`
  - `/:cluster/accounts`
  - `/:cluster/users/:user`
  - `/:cluster/me`
  - `/:cluster/ai`

## 3. 用户工作台

本轮把用户相关入口统一收口到“用户工作台”：

- 主入口：`/:cluster/users/:user`
- 自助入口：`/:cluster/me`
- 兼容入口：`/:cluster/users/:user/analysis`
  - 该旧路由保留，但会重定向到 `user` 路由并附带 `query.section=analysis`

用户工作台由三个区块组成：

- 我的身份与权限摘要
  - 仅 `my-profile` 自助入口始终可见
  - 数据来自 `authStore` 和当前 cluster 的 merged permissions
- 用户资料区
  - 依赖 `associations-view`
  - 展示账户关联、配额和历史作业快捷入口
- 用户分析区
  - 依赖 `view-jobs`
  - 同时要求当前 cluster `user_metrics=true`
  - 展示提交趋势、工具分析和统计卡片

## 4. 权限与降级原则

系统同时依赖 capability 和 permission：

- capability 解决“当前集群是否支持该能力”
- permission 解决“当前用户是否被授权访问该页面或动作”

本轮新增的统一规则如下：

- 整页级权限不足统一跳转 `/forbidden`
- capability 缺失或功能未启用，仍保留原有降级逻辑，不混成权限错误
- 多集群聚合型 settings 页面继续采用页内局部提示，不强制整页拦截

## 5. 全站表达统一

本轮对高频 UI 做了统一收口：

- 百分比展示统一为数字主值 + 百分比图标组件
- Jobs / History / Account / LDAP Cache 等页面中的用户名统一改为用户工作台链接
- 顶栏右上角用户名改为可点击的用户菜单，提供 `My workspace`、`Account permissions`、`Sign out`
- 用户分析中的工具图改为双指标横向条，重点展示平均最大内存和作业数

## 6. 开发与验证入口

前端常用命令：

```powershell
npm --prefix frontend run type-check
npm --prefix frontend run test:unit -- --run
npm --prefix frontend run build
```

后端常用命令：

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m alembic upgrade head
```
