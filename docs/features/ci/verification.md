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

- `Backend Tests` 固定使用 `Python 3.12`
- `Backend Tests` 只收集 `slurmweb/tests`
- `Frontend Tests` 固定使用 `Node 18`
- `Frontend Static Analysis` 固定使用 `Node 18`
- `Frontend Static Analysis` 包含：
  - `Frontend ESLint`
  - `Frontend TypeScript type checking`
  - `Frontend production build`

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
- `scope=backend` 时只聚合 `backend-*` artifact
- `scope=frontend` 时只聚合 `frontend-*` artifact

## 5. 不在本轮范围

以下内容不作为本轮验收目标：

- AI 自动修复失败测试
- AI 自动创建分支或 PR
- GitHub Checks 之外的仓库内置 UI 查询入口
- 后端 rpm/deb OS 集成矩阵自动触发
