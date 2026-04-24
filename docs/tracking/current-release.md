# 当前发布跟踪：中文文档重构与架构补强

## 1. 目标

仅重构内部维护型 Markdown 文档体系（不动 Antora/手册体系 `docs/modules/`、`docs/man/`、`docs/antora.yml`、`docs/update-materials`），并补强交付级架构说明，明确：

- 前端能力门控与路由守卫
- Gateway/Agent 装配边界与代理机制
- 实时与历史数据链路（Prometheus / PostgreSQL）
- 数据库与 Prometheus 依赖、降级边界
- AI / 访问控制 / 用户分析等新增能力的架构边界

## 2. 已完成

### 2.1 文档信息架构重组

- `docs/README.md` 作为唯一索引入口
- 固定目录结构：`docs/overview/`、`docs/guides/`、`docs/features/`、`docs/standards/`、`docs/tracking/`
- 旧根目录专题文档已迁移并删除（不保留双份副本）

### 2.2 架构与总览文档

- 项目总览：`docs/overview/project-overview.md`
- 架构主文档（交付级）：`docs/overview/architecture-overview.md`
- 近期增强能力：`docs/overview/latest-features.md`

### 2.3 规范与协作约束

- 文档规范：`docs/standards/documentation-standard.md`
- 命名规范：`docs/standards/document-naming-convention.md`
- 开发错误复盘标准：`docs/standards/development-error-summary.md`
- 开发错误库入口：`docs/tracking/error-log.md`
- `AGENTS.md` 已写死“禁止向 docs 根目录散写新专题文件”的约束

## 3. 功能专题同步状态（新路径）

| 功能 | 状态 | 总览入口 | 专项文档 |
|---|---|---|---|
| AI 集群助手 | 已同步 | `docs/overview/latest-features.md` | `docs/features/ai/requirements.md` / `docs/features/ai/test-plan.md` |
| 访问控制（自定义角色） | 已同步 | `docs/overview/latest-features.md` | `docs/features/access-control/requirements.md` / `docs/features/access-control/test-plan.md` |
| 用户分析（User Analytics） | 已同步 | `docs/overview/latest-features.md` | `docs/features/user-analytics/backend.md` |
| 历史作业与数据库迁移 | 已同步 | `docs/overview/architecture-overview.md` | `docs/guides/database-migrations.md` / `docs/guides/deployment-guide.md` |
| Cache 页面改进 | 已同步 | `docs/overview/latest-features.md` | `docs/features/cache/requirements.md` / `docs/features/cache/test-plan.md` |
| LDAP Cache | 已同步 | `docs/overview/latest-features.md` | `docs/features/ldap-cache/verification.md` |

## 4. 后续开发必须遵守

- 新功能或行为变更必须先判断是否影响 `docs/overview/` 与 `docs/features/`。
- 任何代码合入前必须更新 `docs/tracking/`（本文件或专题跟踪）。
- 若修改了配置、迁移、权限、API、路由，必须同步更新对应正式文档。
