# 内部文档索引

`docs/` 用于维护本仓库的开发、配置、权限、数据库、测试与 AI 协作文档。

## 总览

- [项目概览](./overview/project-overview.md)
- [架构概览](./overview/architecture-overview.md)
- [最新功能](./overview/latest-features.md)

## 指南

- [部署指南](./guides/deployment-guide.md)
- [数据库迁移](./guides/database-migrations.md)
- [控制台日志排查](./guides/troubleshooting-console-logs.md)
- [验证清单](./guides/verification-checklist.md)

## 功能专题

- AI
  - [需求说明](./features/ai/requirements.md)
  - [测试计划](./features/ai/test-plan.md)
- 访问控制
  - [需求说明](./features/access-control/requirements.md)
  - [测试计划](./features/access-control/test-plan.md)
- Cache
  - [需求说明](./features/cache/requirements.md)
  - [测试计划](./features/cache/test-plan.md)
- Management Center
  - [需求说明](./features/management-center/requirements.md)
  - [测试计划](./features/management-center/test-plan.md)
- 用户分析
  - [后端与页面契约](./features/user-analytics/backend.md)
- LDAP Cache
  - [验证说明](./features/ldap-cache/verification.md)

## 规范

- [文档规范](./standards/documentation-standard.md)
- [文档命名规范](./standards/document-naming-convention.md)
- [AI 开发规范](./standards/ai-development-standard.md)

## 跟踪

- [跟踪目录说明](./tracking/README.md)
- [当前发布跟踪](./tracking/current-release.md)
- [错误日志](./tracking/error-log.md)
- [功能跟踪模板](./tracking/templates/feature-template.md)
- [文档更新检查清单](./tracking/templates/doc-update-checklist.md)

## Review

- [Review 索引](./review/README.md)
- [前端代码审查](./review/frontend-review.md)
- [后端代码审查](./review/backend-review.md)
- [测试审查](./review/test-review.md)

## 本轮重点

本轮已落地的重点包括：

- 基于现有业务页面增强 Slurm 管理能力，补齐单对象创建、编辑、删除、取消。
- 新增集群级 `/:cluster/admin`，统一承载 `System`、`AI`、`LDAP Cache`、`Cache`、`Access Control`。
- `jobs` 资源正式落地 `self` scope，普通用户默认只读非 `admin/*` 页面，并允许查看、编辑、取消自己的作业。
- 默认 `admin` 角色改为全局 `view/edit`，但不默认拥有全局 `delete`。
- `analysis` 页面新增 `Slurm ping` 与 `diag` 面板。

补充说明：

- 旧权限名如 `cache-view`、`roles-manage`、`admin-manage`、`edit-own-jobs`、`view-ai` 仍可通过内置映射自动转换为新规则。
- 旧能力开关目前仅保留兼容占位定义，不再作为实际功能语义来源。
