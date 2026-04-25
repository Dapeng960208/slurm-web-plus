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

## 本轮重点

本轮已落地的重点是两件事：

- 路由权限模型切换为 `resource:operation:scope`，支持精细资源、前缀资源、`self` 和 `*:*:*`。
- Agent 能力开关收敛为自动推导：
  - 数据库开启后自动提供 LDAP Cache、Jobs History、Access Control、AI。
  - Prometheus 开启后自动提供 metrics、node metrics。
  - 数据库和 Prometheus 同时开启后自动提供 user metrics / user analytics。

补充说明：

- 旧权限名如 `cache-view`、`roles-manage`、`view-ai` 仍可通过内置映射自动转换为新规则。
- 旧能力开关目前仅保留兼容占位定义，不再作为实际功能语义来源。
