# 开发跟踪文档目录

`docs/tracking/` 用于承接开发过程中的对接和同步记录。这个目录的目标不是替代正式文档，而是保证：

- 变更过程可追溯
- 文档更新责任可追踪
- 后续 AI 和开发者能看到“还有什么没补完”

## 1. 使用规则

- 当前进行中的功能或迭代，统一记录在 [current-release.md](./current-release.md)。
- 新功能如果范围较大，可以从 [feature-template.md](./templates/feature-template.md) 复制一份单独跟踪。
- 每次代码改动完成后，都要回写这里的文档同步状态。

## 2. 推荐目录职责

- `current-release.md`：当前迭代的主跟踪文件
- `error-log.md`：开发过程中遇到的可复现错误库（避免重复踩坑）
- `templates/feature-template.md`：新功能/新专题跟踪模板
- `templates/doc-update-checklist.md`：文档同步检查项

## 3. 什么时候必须更新

以下情况必须更新 `docs/tracking/`：

- 新增功能
- 重大重构
- 配置项变化
- 数据库迁移
- 权限模型调整
- 新页面/路由/API
- 交付前文档补齐

## 4. 与正式文档的关系

- `docs/tracking/` 记录“过程和状态”
- `docs/overview/`、`docs/guides/`、`docs/features/`、`docs/standards/` 记录“稳定事实和说明”

一个功能结束时，两边都要更新，不能只写其一。
