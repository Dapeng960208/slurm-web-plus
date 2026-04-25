# Documentation Rules For Future AI

后续 AI 在本仓库工作时，必须遵守以下要求：

1. 先阅读 `docs/standards/documentation-standard.md`。
2. 任何影响功能、接口、配置、权限、数据库、部署、测试的改动，都必须同步更新 `docs/`。
3. 开发过程的对接和状态必须更新到 `docs/tracking/`，不能只留在对话或提交信息里。
4. 任何影响功能、接口、配置、权限、数据库、部署、测试的改动，除专项文档外，还必须同步在 `docs/overview/` 记录变更摘要；至少更新 `docs/overview/latest-features.md`，必要时同步 `project-overview.md` 与 `architecture-overview.md`。
5. 新增功能时，至少检查并按需更新：
   - `docs/README.md`
   - `docs/overview/project-overview.md`
   - `docs/overview/architecture-overview.md`
   - `docs/overview/latest-features.md`
   - 对应 `docs/features/<feature>/` 专项文档
   - `docs/tracking/current-release.md`
6. 不要把未实现内容写成已完成事实。

如果任务只改小问题，也必须至少判断一次是否需要文档更新；不能默认跳过。

补充约束（本仓库写死）：

- 后续 AI 不允许再向 `docs/` 根目录散写新专题文件；根目录仅保留 `docs/README.md` 作为索引入口。
- 文档命名与放置必须遵循 `docs/standards/document-naming-convention.md`。
- `docs/overview/latest-features.md` 视为面向全局的 change log 入口；只要发生可感知变更，AI 必须补充对应摘要，不能只更新 `docs/features/` 或 `docs/tracking/`。
- AI 开发过程中遇到可复现错误时，必须复盘并写入 `docs/tracking/error-log.md`（标准见 `docs/standards/development-error-summary.md`）。
- AI 进行 Git 提交时必须遵循提交规范，并在每次提交前检查工作区；对未提交改动必须先与开发者确认是否提交（标准见 `docs/standards/ai-development-standard.md`）。
- 本仓库中文文档按 UTF-8 维护；在 Windows PowerShell 中读取 `AGENTS.md`、`docs/**/*.md` 等中文文档时，不允许直接用裸 `Get-Content <path>` 作为默认做法，必须优先使用 `Get-Content -Encoding UTF8 <path>`。
- 如果终端仍出现乱码，必须先设置 `[Console]::InputEncoding`、`[Console]::OutputEncoding` 与 `$OutputEncoding` 为 UTF-8，然后再用 `Get-Content -Encoding UTF8 <path>`，或改用 `[System.IO.File]::ReadAllText(<path>, [System.Text.UTF8Encoding]::new($false))` 按字节读取。
