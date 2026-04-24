# 内部文档命名与放置规范

本规范用于约束仓库内部维护型 Markdown 文档的命名、目录位置与文件组织方式。

本规范不覆盖 Antora/手册体系（`docs/modules/`、`docs/man/`、`docs/antora.yml`、`docs/update-materials`）。

## 1. 统一规则（强制）

- 文件名与目录名统一使用英文 `kebab-case`。
- 文档内容统一使用简体中文。
- 禁止中文文件名与中文目录名。
- 禁止无语义命名：`new.md`、`temp.md`、`final-v2.md` 等。
- 禁止在 `docs/` 根目录散写新专题文件；根目录仅保留 `docs/README.md` 作为索引入口。

## 2. 固定目录结构

内部维护型文档固定放置在以下目录树中：

```text
docs/
  README.md
  overview/
  guides/
  features/
  standards/
  tracking/
```

放置规则：

- 项目总览与架构：放 `docs/overview/`
- 交付/运维/部署/迁移/排障/验收：放 `docs/guides/`
- 单功能专题：放 `docs/features/<feature>/`
- 规范：放 `docs/standards/`
- 开发过程跟踪：放 `docs/tracking/`

## 3. 同类文档固定命名

在 `docs/features/<feature>/` 下，优先使用固定文件名：

- `requirements.md`
- `test-plan.md`
- `verification.md`
- `backend.md`

在 `docs/guides/` 下，优先使用固定文件名：

- `deployment-guide.md`
- `database-migrations.md`
- `troubleshooting-console-logs.md`
- `verification-checklist.md`

## 4. Feature 目录命名建议

`docs/features/<feature>/` 的 `<feature>` 建议使用稳定英文名，例如：

- `ai`
- `access-control`
- `cache`
- `user-analytics`
- `ldap-cache`

## 5. 链接规则

- 文档内部链接优先使用相对路径。
- 迁移/重命名文件时，必须全仓搜索旧路径引用并同步更新。
