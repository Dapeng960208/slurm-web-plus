# 内部文档索引（稳定入口）

本目录用于维护仓库内部开发/交付/测试/AI 协作所需的稳定文档入口。

本轮只重构内部维护型 Markdown 文档，不动 Antora/手册体系：`docs/modules/`、`docs/man/`、`docs/antora.yml`、`docs/update-materials`。

## 总览

- [项目总览](./overview/project-overview.md)
- [架构总览（交付级）](./overview/architecture-overview.md)
- [近期增强能力](./overview/latest-features.md)

## 指南

- [部署指南](./guides/deployment-guide.md)
- [数据库迁移](./guides/database-migrations.md)
- [控制台日志排查](./guides/troubleshooting-console-logs.md)
- [验证清单](./guides/verification-checklist.md)

## 功能专题

- AI：
  - [需求说明](./features/ai/requirements.md)
  - [测试计划](./features/ai/test-plan.md)
- 访问控制：
  - [需求说明](./features/access-control/requirements.md)
  - [测试计划](./features/access-control/test-plan.md)
- Cache：
  - [需求说明](./features/cache/requirements.md)
  - [测试计划](./features/cache/test-plan.md)
- 用户分析：
  - [后端说明](./features/user-analytics/backend.md)
- LDAP Cache：
  - [验证说明](./features/ldap-cache/verification.md)

## 规范

- [内部文档编写规范](./standards/documentation-standard.md)
- [内部文档命名规范](./standards/document-naming-convention.md)

## 跟踪

- [跟踪目录说明](./tracking/README.md)
- [当前发布跟踪](./tracking/current-release.md)
- [开发错误库](./tracking/error-log.md)
- [功能跟踪模板](./tracking/templates/feature-template.md)
- [文档更新检查清单](./tracking/templates/doc-update-checklist.md)

## 建议阅读顺序

第一次接手仓库，建议按以下顺序阅读：

1. `docs/overview/project-overview.md`
2. `docs/overview/architecture-overview.md`
3. `docs/overview/latest-features.md`
4. `docs/standards/documentation-standard.md`
5. 对应功能专题与交付指南

## 目录职责边界

- `docs/`：内部维护型文档（本索引覆盖的内容）。
- `docs/tracking/`：开发过程跟踪与状态同步区。
- `docs/modules/`、`docs/man/`、`docs/utils/`：对外站点/手册资料与生成脚本，本轮不重构。
