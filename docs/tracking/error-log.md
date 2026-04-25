# 开发错误库（避免重复踩坑）

本文件用于记录开发过程中遇到的可复现错误、根因与解决方案，目标是让后续开发者与 AI 能快速检索并避免重复踩同一个坑。

写入规则见：`docs/standards/development-error-summary.md`。

## 记录格式（示例）

### 2026-04-24：示例标题（用一句话概括）

- 场景：
- 现象：
- 复现：
- 根因：
- 解决：
- 预防：

## 条目

### 2026-04-25：前端测试夹具只写 `actions[]` 时，新规则页面会被误判为无权限

- 场景：迁移前端页面到 `hasRoutePermission(...)` 后，运行 Settings、AI、用户空间相关单测。
- 现象：页面直接进入“无权限”分支，测试里原本可见的按钮、表格和链接全部消失。
- 复现：在测试里直接给 `runtimeStore.availableClusters` 塞只有 `permissions.actions`、没有 `permissions.rules` 的对象，然后渲染新权限页面。
- 根因：这些测试夹具绕过了 `normalizeClusterPermissions(...)`，而新页面优先按规则判权。
- 解决：在 `runtime.hasRoutePermission(...)` 中增加从旧 `actions[]` 到规则的兼容回退，并逐步为新测试数据补充 `rules[]`。
- 预防：后续前端测试若直接构造 cluster 权限对象，优先写入 `rules[]`，或先经过统一的权限归一化逻辑。

### 2026-04-25：Windows 下执行全量 `pytest -q` 会在收集阶段因平台依赖和旧测试树失败

- 场景：提交前尝试在当前开发机上执行仓库全量后端测试。
- 现象：`pytest -q` 在收集阶段直接失败，典型错误包括 `ModuleNotFoundError: No module named 'pwd'`、`ModuleNotFoundError: No module named 'racksdb'`，以及 `slurmweb4.2` 测试树依赖 `SlurmwebConfSeed` 导入失败。
- 复现：在当前 Windows 环境执行 `.venv\Scripts\python.exe -m pytest -q`。
- 根因：仓库里同时包含 Unix 依赖模块、可选依赖未安装的测试，以及 `slurmweb4.2` 兼容测试树；这些条件在当前 Windows 环境下并不满足。
- 解决：本次改动仅对受影响模块执行定向 pytest，未继续扩大到当前环境无法收集的全量测试树。
- 预防：后续若需要跑全量后端测试，应先按平台拆分测试入口，或在 CI / 文档中明确哪些测试需在 Linux 且装齐可选依赖后执行。

### 2026-04-24：ripgrep 的 look-around 默认不可用导致搜索表达式报错

- 场景：在仓库内用 `rg` 搜索旧文档路径引用时，想用 look-ahead/behind 过滤结果。
- 现象：`rg: regex parse error: look-around ... is not supported`
- 复现：执行包含 `(?=...)` 或 `(?!...)` 的 `rg` 正则（未加参数）。
- 根因：ripgrep 默认正则引擎不支持 look-around，需要启用 PCRE2。
- 解决：对需要 look-around 的搜索加 `--pcre2`，或改写为不依赖 look-around 的多次搜索。
- 预防：在需要复杂正则时优先用 `rg --pcre2`，并把关键搜索命令写入跟踪或指南中。

### 2026-04-24：文档中的 Gateway 端点漏了 `/api` 前缀导致验证命令误用

- 场景：按文档用 curl 获取 token / 查询 clusters。
- 现象：访问 `http://localhost:5012/login`、`http://localhost:5012/clusters` 得到 404 或非预期结果。
- 复现：直接照搬旧文档命令访问不带 `/api` 的路径。
- 根因：Gateway 路由以 `/api/...` 为前缀（例如 `POST /api/login`、`GET /api/clusters`），旧文档残留了不一致路径。
- 解决：统一修正文档命令为 `/api/login`、`/api/anonymous`、`/api/clusters`，集群接口走 `/api/agents/<cluster>/...`。
- 预防：写验证命令时优先对照 `slurmweb/apps/gateway.py` 的路由表，避免凭印象写路径。

### 2026-04-24：网络原因导致无法 push 到 GitHub（已本地 commit）

- 场景：提交完成后执行 `git push origin main`。
- 现象：`Failed to connect to github.com port 443 ... Could not connect to server`。
- 复现：在网络不可达/被防火墙阻断的环境执行 push。
- 根因：网络不可用或访问 GitHub 被阻断（非仓库内容问题）。
- 解决：按规范先完成本地 `git commit`，待网络恢复后再 push。
- 预防：提交前不以 push 成功为前提；若 push 失败，必须在 `docs/tracking/` 留下“已本地提交、待 push”的记录。

### 2026-04-25：PowerShell 环境中不存在 `python` 命令导致临时脚本无法执行

- 场景：为排查文档读取乱码，尝试用内联 Python 脚本按字节解码 Markdown 文件。
- 现象：执行 `@' ... '@ | python -` 时返回 `python : The term 'python' is not recognized as the name of a cmdlet...`。
- 复现：在当前仓库终端直接执行 `python` 或把脚本管道给 `python -`。
- 根因：当前 PowerShell 环境未安装 `python`，或 `python` 未加入 `PATH`。
- 解决：改用纯 PowerShell 方式读取字节并通过 `[System.Text.Encoding]::UTF8.GetString(...)` 解码文件内容。
- 预防：在依赖解释器前先确认命令是否存在；本仓库的简单文件读取、编码排查优先使用 PowerShell 原生命令，避免把 `python` 作为默认前置条件。

### 2026-04-25：CLI 改名后 `test_main.py` 仍按旧默认程序名断言

- 场景：把对外默认 CLI 名称切到 `slurm-web-plus` 后，执行主入口定向测试。
- 现象：`.venv\Scripts\python.exe -m pytest -q slurmweb/tests/exec/test_main.py` 失败 4 条，主要断言仍是 `slurm-web` 帮助输出和版本输出。
- 复现：在当前仓库根目录执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/exec/test_main.py`。
- 根因：运行时代码已默认展示 `slurm-web-plus`，测试基线没有同步兼容命名策略。
- 解决：在 `docs/review/test-review.md` 记录该缺口，后续需要同步更新 `slurmweb/tests/exec/test_main.py`。
- 预防：凡是更改 CLI 对外名称、帮助信息或别名策略时，必须同步检查 `slurmweb/tests/exec/**` 中的字符串断言。

### 2026-04-25：`gen-jwt-key` 修复后 `test_genjwt.py` 仍按旧行为断言

- 场景：为避免 `setfacl` 失败被静默吞掉，以及兼容非 Unix 平台，对 `slurmweb/apps/genjwt.py` 做修复后执行定向测试。
- 现象：`.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py` 失败 3 条，分别涉及 `subprocess.run(..., check=True)` 与新增/已有告警输出不一致。
- 复现：在当前仓库根目录执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py`。
- 根因：测试仍按旧的 `subprocess.run(...)` 调用签名和旧日志集合断言，未跟随后端修复。
- 解决：先在 `docs/review/test-review.md` 记录为测试基线缺口，后续需同步更新 `slurmweb/tests/apps/test_genjwt.py`。
- 预防：后端修复若改变日志集合、外部命令参数或容错分支，必须同步审查对应测试文件，避免把有效修复变成 CI 假失败。

### 2026-04-25：在仓库根目录直接跑前端 Vitest 会因 `@/` 别名解析失败

- 场景：为复查前端剩余失败用例，在仓库根目录直接执行前端测试命令。
- 现象：`tests/composables/GatewayAPI.spec.ts`、`tests/components/user/UserToolAnalysisChart.spec.ts` 报 `Failed to load url @/...`，显示找不到 `@/composables/GatewayAPI`、`@/components/...`。
- 复现：在仓库根目录执行 `npm --prefix frontend exec vitest run tests/composables/GatewayAPI.spec.ts tests/components/user/UserToolAnalysisChart.spec.ts`。
- 根因：Vitest 运行目录不在 `frontend/`，导致前端工程的 Vite 别名配置没有按预期生效。
- 解决：切到 `frontend/` 目录执行 `npx vitest run ...`，按前端项目自身上下文加载配置。
- 预防：凡是使用 `@/` 路径别名的前端测试，优先在 `frontend/` 目录执行，避免把“命令上下文错误”误判成代码缺陷。

### 2026-04-25：Windows PowerShell 读取 UTF-8 无 BOM 中文文档时会出现乱码

- 场景：在当前 Windows 终端直接执行 `Get-Content docs/README.md` 查看中文文档。
- 现象：输出内容出现 `鍐呴儴鏂囨。` 一类乱码，即使先把控制台输出编码切到 UTF-8 也不能恢复正常。
- 复现：在 Windows PowerShell 5 中执行 `Get-Content docs/README.md`，目标文件为 UTF-8 无 BOM。
- 根因：`Get-Content` 默认按本地 ANSI/系统代码页解释无 BOM 文件；问题出在“读取时解码错误”，不在“输出时编码错误”。
- 解决：
  - 在 `AGENTS.md` 写死中文文档读取规则，要求优先使用 `Get-Content -Encoding UTF8 <path>`。
  - 将 `AGENTS.md` 与 `docs/**/*.md` 统一补齐 UTF-8 BOM，兼容 WinPS 5 的默认编码探测。
- 预防：后续 AI 在 Windows PowerShell 中读取中文文档时，不要把裸 `Get-Content <path>` 当成默认做法；若怀疑编码问题，优先按 UTF-8 显式读取。

### 2026-04-25：完整前端 Vitest 仍会被旧页面断言和旧权限契约测试拖红

- 场景：执行 `npx vitest run` 做前端全量回归。
- 现象：`JobHistoryView.spec.ts`、`JobView.spec.ts`、`UserAnalysisView.spec.ts`、`MainMenuAIContract.spec.ts` 失败，表现为旧 DOM 选择器、旧 `permission` 字段断言、旧权限夹具与当前实现不一致。
- 复现：在 `frontend/` 目录执行 `npx vitest run`。
- 根因：页面已切换到 `DetailSummaryStrip` 和新规则权限模型，部分测试仍按旧 overview grid、旧 `view-ai` 菜单配置和旧用户分析授权方式断言。
- 解决：同步更新上述测试到当前 UI 结构和权限模型。
- 预防：前端若重构详情页布局或菜单权限结构，必须同轮同步更新契约测试和页面单测。

### 2026-04-25：用户分析接口权限 scope 在装饰器中错误引用路由用户名

- 场景：扩大后端验证到 `slurmweb/tests/views/test_agent_metrics_requests.py -k user_activity_summary`。
- 现象：访问 `GET /v<version>/user/<username>/activity/summary` 时，权限装饰器在解析 `self` / `*` scope 阶段抛出 `NameError`，后续在修正为传参后又暴露出 lambda 不接收 `username` 关键字参数。
- 复现：执行 `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/views/test_agent_metrics_requests.py -k user_activity_summary`。
- 根因：`permission_required(...)` 的 scope callable 需要在运行时根据路由参数解析，但原实现既没有把路由参数传入 callable，lambda 本身也没声明 `username` 参数。
- 解决：
  - `_resolved_scope(...)` 改为向 callable 透传 `*args, **kwargs`
  - `user_metrics_history` / `user_activity_summary` 的 scope lambda 显式接收 `username`
- 预防：凡是按请求参数动态判定 `self` / `*` 的权限装饰器，都要补对应回归测试，避免闭包或参数绑定错误在运行时才暴露。
