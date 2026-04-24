# Slurm Web Plus 项目说明

## 1. 项目定位

Slurm Web Plus 是一个面向 Slurm HPC 集群的 Web 管理与分析平台。它在保留 Slurm 原生能力边界的前提下，提供：

- 集群实时状态总览
- 作业、节点、资源、账户、QOS、预约等可视化查询
- 历史作业持久化与分析
- 用户分析与集群效率分析
- LDAP 认证与细粒度权限控制
- 可选的 AI 助手能力

它不是 Slurm 的替代品，而是 Slurm、Prometheus、PostgreSQL、LDAP 等能力之上的统一运维与分析入口。

## 2. 系统组成

系统采用三层结构：

- `frontend/`：Vue 3 + TypeScript 单页应用，负责交互界面、路由、图表和设置页。
- `slurmweb/apps/gateway.py`：统一入口，负责认证、JWT、集群发现、权限聚合和请求转发。
- `slurmweb/apps/agent.py`：单集群后端，直接对接 `slurmrestd`、Prometheus、PostgreSQL、缓存与扩展能力。

外部依赖按职责划分如下：

- `slurmrestd`：实时 Slurm 数据源
- Prometheus：历史指标与节点指标数据源
- PostgreSQL：作业历史、用户缓存、访问控制、AI 配置与会话持久化
- LDAP：用户认证和用户基础信息来源
- Redis/缓存服务：可选缓存与命中统计

## 3. 核心能力清单

当前仓库已经覆盖的主能力包括：

- Dashboard：资源和作业状态总览
- Analysis：集群容量、队列阻塞、分区热点和历史压力分析
- Jobs / Jobs History：实时作业与历史作业双路径查询
- Resources / Node：节点、CPU、内存、GPU、拓扑与指标查看
- Accounts / User：账户关联、配额和用户分析
- Settings：账号、AI、访问控制、缓存、LDAP Cache 等配置工作区

能力是按集群动态暴露的。前端不会假设所有集群都支持全部功能，而是依赖 `GET /api/clusters` 返回的 capability 和 permission 决定菜单、路由和页面行为。

## 4. 最新版本重点增强

最近一批提交集中补强了“分析能力 + 权限治理 + AI 助手 + 运维可视化”四条线：

- 数据库持久化的 AI 集群助手
- 基于数据库的自定义角色与权限合并
- 用户分析页面与集群分析工作台
- 历史作业访问控制与 LDAP 用户缓存
- Cache 页面空态和可读性改进

详细说明见 [近期增强能力](./latest-features.md)。

## 5. 代码目录速览

### 后端

- `slurmweb/apps/`：Gateway 和 Agent 应用装配入口
- `slurmweb/views/`：API 视图层
- `slurmweb/slurmrestd/`：Slurm REST 封装与适配
- `slurmweb/metrics/`：Prometheus 导出与查询
- `slurmweb/persistence/`：PostgreSQL 存储层
- `slurmweb/ai/`：AI 提供方封装、工具注册、服务编排、密钥加密
- `slurmweb/alembic/`：数据库迁移

### 前端

- `frontend/src/router/`：页面路由和权限守卫
- `frontend/src/views/`：页面级视图
- `frontend/src/components/`：复用组件
- `frontend/src/composables/`：Gateway API、轮询器、分析逻辑等
- `frontend/src/stores/`：认证、运行时状态和列表状态

### 文档与配置

- `conf/vendor/`：默认配置样例与策略
- `docs/`：内部维护文档与站点资料
- `dev/`：开发环境部署脚本与说明

## 6. 运行与交付关注点

### 启用完整能力时的关键依赖

- 实时页面：需要 `slurmrestd`
- 历史指标：需要 Prometheus
- 作业历史、用户缓存、访问控制、AI：需要 PostgreSQL
- 用户登录：需要 LDAP

### 常见功能开关

- `[metrics] enabled`
- `[database] enabled`
- `[persistence] enabled`
- `[persistence] access_control_enabled`
- `[user_metrics] enabled`
- `[node_metrics] enabled`
- `[ai] enabled`

这些开关主要由 Agent 控制，Gateway 负责把 Agent 的能力暴露给前端。

## 7. 推荐开发/验证命令

后端：

```powershell
.venv\Scripts\python.exe -m pytest
```

前端：

```powershell
npm --prefix frontend run test:unit
npm --prefix frontend run build
```

数据库迁移：

```powershell
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic upgrade head
```

## 8. 文档协作约束

- 后续功能开发必须同步维护 `docs/`。
- 新增能力先更新项目级文档，再更新专项文档。
- 开发过程跟踪必须进入 `docs/tracking/`。
- 后续 AI 必须遵循 [内部文档编写规范](../standards/documentation-standard.md) 与仓库根目录的 `AGENTS.md`。
