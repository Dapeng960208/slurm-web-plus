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
