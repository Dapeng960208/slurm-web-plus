# GitHub CI 自动测试与结构化结果

## 1. 背景与目标

当前仓库已经有前后端 GitHub Actions，但原先主要依赖手工 `workflow_dispatch`，且测试结果主要停留在零散控制台日志中，不利于日常 PR 把关，也不利于后续 AI 或脚本稳定消费失败上下文。

本轮目标是：

- 将核心前后端检查切到 `main` 分支的自动触发
- 收敛为单版本快速反馈 CI
- 为每个 job 统一生成结构化结果产物
- 提供手工 triage 入口，按指定 run 聚合结果

## 2. 功能范围

本轮纳入自动 CI 的 workflow：

- `.github/workflows/python-ci.yml`
  - 后端单元测试
  - 固定 `Python 3.12`
  - 测试入口固定为 `pytest slurmweb/tests`
  - 依赖安装固定包含 `.[agent]`、`.[gateway]`、`.[tests]`，其中 `cryptography` 由 `agent/tests` extras 提供
- `.github/workflows/frontend-ci.yml`
  - 前端单元测试
  - 固定 `Node 18`
- `.github/workflows/frontend-static.yml`
  - 前端 `ESLint`
  - 前端 `TypeScript type-check`
  - 前端 `build`
  - 固定 `Node 18`

本轮保留为手工触发的 workflow：

- `.github/workflows/python-os-ci.yml`
  - rpm OS 集成矩阵
  - deb OS 集成矩阵
  - 测试入口同样固定为 `slurmweb/tests`
- `.github/workflows/ci-triage.yml`
  - 按指定 `run_id` 聚合结构化 CI artifact

## 3. 触发条件

自动 CI 触发条件：

- `pull_request` 到 `main`
- `push` 到 `main`
- 保留 `workflow_dispatch`

手工 triage 触发条件：

- 仅 `workflow_dispatch`
- 输入：
  - `run_id`
  - `scope`：`backend` / `frontend` / `all`

## 4. 结果产物契约

每个自动 CI job 无论成功失败，都尝试上传统一 artifact 目录，至少包含：

- `stdout.log`
- `result.json`
- `failure-context.json`

测试类 job 额外输出：

- `junit.xml`

`failure-context.json` 固定字段：

- `workflow`
- `job`
- `run_id`
- `sha`
- `ref`
- `command`
- `status`
- `artifact_names`
- `primary_log`
- `summary`
- `failed_step`

`result.json` 额外补充运行时细节，例如：

- `label`
- `artifact_name`
- `exit_code`
- `started_at`
- `finished_at`
- `duration_ms`
- `junit_path`
- `output_excerpt`

## 5. 页面与接口影响

本轮不新增产品 UI 页面，也不新增仓库运行时 API。

新增的对外操作入口是 GitHub Actions workflow：

- 自动查看：GitHub Checks + Job Summary + artifacts
- 手工聚合：`CI Triage` workflow

## 6. AI 能力边界

本轮只实现“AI 可消费的结构化测试结果”，不实现“AI 自动修复并提交”。

明确边界：

- 仓库内置 AI 当前仍只能调用集群只读工具
- 它不能直接读取 GitHub Actions run
- 它不能自动改代码、建分支或提 PR

当前建议链路是：

1. CI 自动产出结构化结果
2. `CI Triage` 聚合某次 run 的 artifact
3. 后续独立接入外部 AI / agent 读取 `triage-context.json`

## 7. 降级与边界

- 若 job 在主命令前失败，`ensure-ci-result` 会补最小失败结果，避免 artifact 缺失
- 若 triage 指定的 run 没有结构化 artifact，`triage-context.json` 仍会生成空结果摘要
- OS 集成矩阵不再参与日常 PR / push 自动反馈，避免拉长主线 CI
- 后端主线测试依赖 AI 加密模块导入链，`cryptography` 属于自动 CI 的必需 Python 依赖
