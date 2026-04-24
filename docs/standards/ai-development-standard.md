# AI 开发规范（Git 工作流强制要求）

本规范用于约束 AI 在本仓库进行开发与提交时的 Git 工作流，目标是：

- 所有提交信息可追溯、可审计、符合约定格式
- 避免把无关/意外改动混入提交
- 在网络不可用时仍能完成本地提交并留下可追踪记录

适用范围：本仓库所有代码与内部维护型文档的变更提交。

## 1. 提交信息规范（强制）

所有 Git 提交必须遵循仓库既有约定格式（与 Conventional Commits 一致）：

```text
type(scope): subject
```

示例：

- `feat(ai): add db-backed cluster assistant`
- `fix(frontend): align dashboard memory states`
- `chore(docs): refactor internal docs tree`

要求：

- `type` 使用：`feat`、`fix`、`chore`、`docs`、`refactor`、`test`、`ci` 等
- `scope` 必须有意义（例如 `docs`、`gateway`、`agent`、`frontend`、`assets`）
- `subject` 用英文，简短描述本次改动的核心意图
- 复杂提交应使用 body（`git commit -m ... -m ...`）写清关键影响与验证方式

## 2. 每次提交前的工作区检查（强制）

在每次 `git add` / `git commit` 前，必须先执行并检查：

```text
git status --porcelain
```

要求：

- 若工作区存在未提交改动（包含 untracked、modified、deleted、renamed 等）：
  - 必须先与开发者确认“哪些改动要提交、哪些不提交”
  - 不允许 AI 擅自把所有改动一把梭提交
- 若工作区改动包含与当前任务无关的文件：
  - 必须拆分提交或先恢复无关改动（`git restore ...` / `git restore --staged ...`）

## 3. 暂存策略（强制）

- 优先使用“按路径/按主题”暂存：`git add <path>`、`git add -p`（如需）
- 避免使用 `git add .` 把无关变更一起提交
- 同一次提交尽量保持单一主题（例如“只改 docs”或“只改 gateway”）

## 4. 网络不可用时的处理（必须可追溯）

当网络原因导致无法 push（例如 GitHub 连接失败、认证失败、代理问题）：

1. 仍然必须完成本地 `git commit`（保证改动可追溯、可回滚）
2. 不强行重试到阻塞工作流；将 push 作为后续动作
3. 必须写入跟踪记录：
   - `docs/tracking/error-log.md`：记录现象/根因/解决方案（可复现错误）
   - `docs/tracking/current-release.md`：记录“已本地提交，待 push”状态（如影响交付节奏）

## 5. 最小执行清单

每次准备提交前至少自查：

- [ ] `git status --porcelain` 已检查
- [ ] 未提交改动已与开发者确认范围
- [ ] 暂存集只包含本次任务相关改动
- [ ] 提交信息符合 `type(scope): subject`
- [ ] 若 push 失败，已本地 commit 并写入 `docs/tracking/`
