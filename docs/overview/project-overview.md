# Slurm Web Plus 项目概览

## 1. 项目定位

Slurm Web Plus 是面向 Slurm HPC 集群的 Web 管理与分析平台。它在不替代 Slurm 原生能力的前提下，提供统一的监控、查询、分析、权限和设置入口。

当前仓库覆盖的核心能力包括：

- 集群实时概览与分析
- 作业、历史作业、节点、资源、账户、用户、QOS、预约查询与单对象管理；历史作业可跳转实时作业详情，作业编辑支持每 CPU 内存申请
- reservation 创建与更新已支持 `groups`、`qos`、`allowed_partitions` 等访问控制字段，并在前端本地拦截访问控制字段全空的非法提交
- 基于 PostgreSQL 的历史作业持久化、LDAP 用户缓存、访问控制和 AI 配置持久化
- 基于 Prometheus 的集群指标、节点指标和用户分析
- 节点与用户分析支持按钮触发的自定义起止时间窗口，精确到时分
- 集群分析支持默认近 3 天节点热点概览、基于 `submit_time -> start_time` 的秒级平均排队时长曲线，以及仅展示核心 `diag` 指标
- 前端支持浏览器语言优先的中英文切换，并将语言偏好持久化到本地 `localStorage`
- 中英文切换当前覆盖登录页、共享壳层和核心业务页面主体的前端静态文案与前端生成提示，不覆盖后端原始错误文本和业务实体值
- 基于 `resource:operation:scope` 的细粒度权限控制
- 集群级 `Admin` 页面统一管理 AI、Cache、Users 与 Access Control；AI 管理页同时提供所有用户会话审计
- 普通 AI 对话页支持基于只读模型摘要接口切换已启用模型，但不暴露管理员配置细节
- 用户和 account-user association 管理支持默认 QOS 与分配 QOS 维护
- 用户名、QOS、分区、节点相关表单输入统一为可搜索下拉；用户名走远程搜索，QOS/分区/节点走远端列表加载后搜索
- 账户详情页“Add user”会先确保用户实体存在，再写 account-user association，并在刷新后验证关联真实可见
- 面向 `main` 分支协作的 GitHub 自动测试与结构化 CI 结果产物
- 本地可通过 `gh` + PowerShell 脚本主动拉取最新 GitHub Actions 测试结果
- 本地可显式调用 `codex exec` 基于失败 artifact 继续修复
- 本地可按当前提交 `push` 后自动追踪对应 GitHub Actions run

## 2. 当前主要入口

全局入口：

- `/clusters`
- `/settings`
- `/login`
- `/anonymous`
- `/signout`
- `/forbidden`

集群范围入口：

- `/:cluster/dashboard`
- `/:cluster/analysis`
- `/:cluster/admin`
- `/:cluster/ai`
- `/:cluster/jobs`
- `/:cluster/jobs/history`
- `/:cluster/resources`
- `/:cluster/partitions/:partition`
- `/:cluster/qos`
- `/:cluster/reservations`
- `/:cluster/accounts`
- `/:cluster/users/:user`
- `/:cluster/me`

## 3. 权限模型

当前有效权限模型为 `resource:operation:scope`：

- `resource` 采用“主路由 + 子资源”形式，例如 `admin/ai`、`user/profile`、`jobs/filter-qos`
- `operation` 当前支持 `view`、`edit`、`delete`
- `scope` 当前支持 `*` 和 `self`

已实现的规则特性：

- 精确资源匹配，例如 `jobs:view:*`
- 前缀资源匹配，例如 `admin/*:view:*`
- 全局通配，例如 `*:*:*`
- owner-aware 规则，例如 `jobs:view:self`、`user/profile:view:self`
- `edit` / `delete` 自动满足 `view`

当前与管理扩展直接相关的关键规则包括：

- `jobs:view|edit|delete:*|self`
- `resources:view|edit|delete:*`
- `reservations:view|edit|delete:*`
- `accounts:view|edit|delete:*`
- `users-admin:view|edit|delete:*`
- `qos:view|edit|delete:*`
- `analysis:view:*`
- `admin/ai:view|edit|delete:*`
- `admin/cache:view|edit:*`
- `admin/ldap-users:view|edit:*`
- `admin/access-control:view|edit|delete:*`

补充说明：

- 当前主工作路径是 `/:cluster/admin/*`
- `/settings/ai`、`/settings/access-control`、`/settings/cache`、`/settings/ldap-users` 只是兼容重定向入口

## 4. 能力启用条件

系统当前按基础依赖自动推导能力，不再依赖独立业务开关：

| 基础条件 | 自动启用能力 |
|---|---|
| `[database] enabled = yes` | Users、Jobs History、Access Control、AI |
| `[metrics] enabled = yes` | cluster metrics |
| `node_metrics.prometheus_host` 已配置 | node metrics |
| 数据库 + metrics | user metrics、user analytics |

说明：

- 已删除旧配置项 `persistence.enabled`、`persistence.access_control_enabled`、`user_metrics.enabled`、`node_metrics.enabled`、`ai.enabled`。
- 前端和 `/info` 看到的是推导后的能力状态。
- AI 会话审计、逻辑删除与模型配置同样依赖数据库能力。
- 队列详情页 `/:cluster/partitions/:partition` 当前除了核心摘要外，还复用 dashboard 图表展示该队列的实时资源与作业趋势；作业和历史作业页面中的队列字段统一可跳转到该详情页。

## 5. 角色模型

数据库支持开启后，如果 `roles` 表为空，系统会自动预置三个角色：

- `user`
  - 默认包含非 `admin/*` 页面只读权限
  - 作业默认使用 `jobs:view:self`
  - 默认允许 `jobs:edit:self`
  - 默认允许 `jobs:delete:self`
  - 默认允许 `user/analysis:view:self`
- `admin`
  - 默认包含 `*:view:*`
  - 默认包含 `*:edit:*`
  - 默认不包含 `*:delete:*`
- `super-admin`
  - 直接使用 `*:*:*`

这些角色只会在首次空表时写入，后续允许通过页面继续编辑。

## 7. 发布命名说明

当前仓库的对外发布名已经切换为 `slurm-web-plus`，但为了降低升级风险，代码层仍保留一部分兼容命名：

- 对外品牌名、前端页面标题、包名入口以 `slurm-web-plus` 为主
- Python 包目录与导入名继续保持 `slurmweb`
- 现有 systemd service、默认配置目录、运行时目录仍大量保留 `slurm-web` 兼容前缀

因此，当前状态更准确地说是“发布名已切换，部署层兼容迁移未完全结束”，后续发布需要同时审阅 `conf/**`、`lib/**` 和运维脚本命名策略。

## 6. 旧权限兼容

新权限启用后，仍保留少量旧动作兼容映射：

- `cache-view` -> `admin/cache:view:*` + `admin/ldap-users:view:*`
- `cache-reset` -> `admin/cache:edit:*`
- `admin-manage` -> `*:*:*`

收口说明：

- `view-ai` -> `ai:view:*`
- `view-own-jobs`、`edit-own-jobs`、`cancel-own-jobs`、`roles-view`、`roles-manage`、`manage-ai` 已彻底失效，不再作为可配置动作入口，也不再参与兼容推导。
- 普通用户默认的 `jobs:view|edit|delete:self` 与 `user/analysis:view:self` 来自数据库种子角色 `user`，不再来自 vendor policy 动作。
- 当新权限系统不可用时，普通用户也不再获得自有 Jobs 的旧动作兜底。

## 8. GitHub CI 交付基线

当前仓库的 GitHub 自动验证基线为：

- `pull_request` 到 `main`
- `push` 到 `main`

自动检查固定版本：

- 后端：`Python 3.9`、`3.10`、`3.11`、`3.12`
- 前端：`Node 18`

自动检查范围：

- 后端单元测试
- 前端单元测试
- 前端 `ESLint`
- 前端 `TypeScript type-check`
- 前端生产构建

后端自动 CI 的 `pytest` 入口固定为 `slurmweb/tests`，不把仓库内历史 `slurmweb4.2/tests` 兼容树纳入当前主线验证。测试类 CI artifact 会从 `junit.xml` 解析并输出 `test_stats`，用于查看每个 job 的测试用例数量。

手工检查范围：

- rpm / deb OS 集成矩阵
- `CI Triage` 结构化结果聚合
- 本地 `fetch-github-ci-result.ps1` / `watch-github-ci.ps1` 拉取和轮询
- 本地 `continue-from-github-ci.ps1` 生成或执行修复提示词
- 本地 `push-and-watch-github-ci.ps1` 按 `HEAD` 提交推送并接管 Actions 结果
