# Documentation Rules For Future AI

后续 AI 在本仓库工作时，必须遵守以下要求：

1. 先阅读 `docs/standards/documentation-standard.md`。
2. 任何影响功能、接口、配置、权限、数据库、部署、测试的改动，都必须同步更新 `docs/`。
3. 开发过程的对接和状态必须更新到 `docs/tracking/`，不能只留在对话或提交信息里。
4. 新增功能时，至少检查并按需更新：
   - `docs/README.md`
   - `docs/overview/project-overview.md`
   - `docs/overview/architecture-overview.md`
   - `docs/overview/latest-features.md`
   - 对应 `docs/features/<feature>/` 专项文档
   - `docs/tracking/current-release.md`
5. 不要把未实现内容写成已完成事实。

如果任务只改小问题，也必须至少判断一次是否需要文档更新；不能默认跳过。

补充约束（本仓库写死）：

- 后续 AI 不允许再向 `docs/` 根目录散写新专题文件；根目录仅保留 `docs/README.md` 作为索引入口。
- 文档命名与放置必须遵循 `docs/standards/document-naming-convention.md`。
- AI 开发过程中遇到可复现错误时，必须复盘并写入 `docs/tracking/error-log.md`（标准见 `docs/standards/development-error-summary.md`）。
