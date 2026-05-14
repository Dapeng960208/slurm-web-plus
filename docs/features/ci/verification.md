# GitHub CI 验证说明

## 1. 适用范围

适用于验证本轮 GitHub 自动测试与结构化结果链路，包括：

- 后端单元测试自动触发
- 前端单元测试自动触发
- 前端静态检查与构建自动触发
- 手工 triage 聚合结构化 artifact

## 2. 自动 CI 验证

### 2.1 PR 自动触发

创建一个指向 `main` 的测试 PR，确认以下 workflow 自动运行：

- `Backend Tests`
- `Frontend Tests`
- `Frontend Static Analysis`

预期：

- `Backend Tests` 使用矩阵覆盖 `Python 3.9`、`3.10`、`3.11`、`3.12`
- 每个 Python 版本生成独立 job 和 `backend-python-<version>` artifact
- `Backend Tests` 只收集 `slurmweb/tests`
- `Backend Tests` 安装 `.[agent]`、`.[gateway]`、`.[tests]` 后，AI 相关测试可正常导入 `cryptography`
- `Backend Tests` 在未安装 `python-ldap` 的环境下，gateway / ldap 相关测试也不应因 `import ldap.filter` 在 collection 阶段失败
- `Frontend Tests` 固定使用 `Node 18`
- `Frontend Static Analysis` 固定使用 `Node 18`
- `Frontend Static Analysis` 包含：
  - `Frontend ESLint`
  - `Frontend TypeScript type checking`
  - `Frontend production build`
- `Frontend ESLint` 对前端源码中的 `@typescript-eslint/no-unused-vars` 与 `@typescript-eslint/no-empty-object-type` 仅报 warning，不应单独导致 workflow 失败

### 2.2 Push 自动触发

向 `main` 推送一次提交，确认上述 workflow 同样自动运行。

## 3. 结构化结果验证

任选一个 job，进入 GitHub Actions 页面后检查：

- Job Summary 可见
- artifact 可下载
- artifact 中包含：
  - `stdout.log`
  - `result.json`
  - `failure-context.json`

测试类 job 还应包含：

- `junit.xml`

测试类 job 的结构化结果还应包含：

- `result.json.test_stats.tests`
- `result.json.test_stats.failures`
- `result.json.test_stats.errors`
- `result.json.test_stats.skipped`
- `failure-context.json.test_stats`

GitHub Job Summary 应显示测试总数、失败数、错误数和跳过数。

### 3.1 前端失败验证

可以临时制造一个前端单测失败，确认：

- workflow 标红
- `failure-context.json` 的 `status` 为 `failure`
- `failed_step` 为对应 job 标签
- `summary` 含失败摘要

### 3.2 后端失败验证

可以临时在 `slurmweb/tests` 下制造一个后端 pytest 失败，确认同样行为成立。

## 4. Triage workflow 验证

在 GitHub Actions 手工运行 `CI Triage`：

- `run_id`：填一个已有 CI run ID
- `scope`：选择 `all`、`backend` 或 `frontend`

预期：

- workflow 成功下载目标 run 的 artifact
- 输出 `triage-context.json`
- summary 展示 artifact 数量与失败数量
- summary 表格展示每个 artifact 的测试数量
- `scope=backend` 时只聚合 `backend-*` artifact
- `scope=frontend` 时只聚合 `frontend-*` artifact

## 5. 本地 `gh` 拉取脚本验证

前置条件：

- 本机已安装 `gh`
- `gh auth status` 已通过

执行：

- `powershell -ExecutionPolicy Bypass -File scripts/fetch-github-ci-result.ps1 -Workflow "Backend Tests" -Conclusion failure -DownloadArtifacts -ShowFailedLog`
- `powershell -ExecutionPolicy Bypass -File scripts/watch-github-ci.ps1 -Workflow "Backend Tests"`
- `powershell -ExecutionPolicy Bypass -File scripts/continue-from-github-ci.ps1 -Workflow "Backend Tests"`
- `powershell -ExecutionPolicy Bypass -File scripts/push-and-watch-github-ci.ps1 -Workflow "Backend Tests" -SkipPush`

预期：

- 脚本会在 `.ci-results/github/` 下按 `workflow-runid` 创建目录
- 至少生成 `run-summary.json`
- 开启 `-DownloadArtifacts` 时会下载对应 GitHub Actions artifact
- 开启 `-ShowFailedLog` 时会生成 `failed.log`
- `watch-github-ci.ps1` 会轮询到目标 workflow 完成后自动调用抓取脚本
- `watch-github-ci.ps1` 在 completed run 上应继续把 `-RunId` 与 `-OutputRoot` 正确转发给 `fetch-github-ci-result.ps1`，不应再出现 `Conclusion` 参数校验错误
- `continue-from-github-ci.ps1` 会在 run 目录内生成 `codex-autofix-prompt.md`
- 显式追加 `-RunCodex` 时，脚本会调用本机 `codex exec`，并把最终消息写到 `codex-last-message.txt`
- `push-and-watch-github-ci.ps1` 会按当前 `HEAD` commit 追踪对应 run；生产使用时默认执行 `push`，验证时可用 `-SkipPush` 复用已存在的远端 run

## 6. 不在本轮范围

以下内容不作为本轮验收目标：

- AI 自动修复失败测试
- AI 自动创建分支或 PR
- GitHub Checks 之外的仓库内置 UI 查询入口
- 后端 rpm/deb OS 集成矩阵自动触发
