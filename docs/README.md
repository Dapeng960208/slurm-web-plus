# 内部文档索引

`docs/` 用于维护仓库内的开发、测试、部署和 AI 协作文档。根目录只保留本文件作为稳定入口，不在根目录散写新专题。

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

本轮前端改造重点集中在三个主题：

- 用户入口统一为“用户工作台”，覆盖 `/:cluster/users/:user`、`/:cluster/me` 和旧的 `/:cluster/users/:user/analysis` 兼容入口。
- 全站整页级权限不足统一跳转 `/forbidden`，并明确提示“请联系管理员申请权限”。
- 高频百分比展示统一改为数字主值加百分比图标样式，避免不同页面各写一套。

## 建议阅读顺序

1. `docs/overview/project-overview.md`
2. `docs/overview/architecture-overview.md`
3. `docs/overview/latest-features.md`
4. 对应 `docs/features/<feature>/` 专题
5. `docs/tracking/current-release.md`
