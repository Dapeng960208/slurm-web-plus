# 后端代码审查报告

## 1. 审查范围

本次仅审查后端范围内文件：

- `slurmweb/**`
- `lib/**`
- `conf/**`
- 顶层后端打包/入口相关文件（本次主要观察 `pyproject.toml`）

重点检查项：

- 明显 bug 与低风险可修复问题
- 权限、接口、配置、数据库、发布阻塞项
- 对外暴露仍为 `slurm-web` 的后端命名点

## 2. 已直接修复的问题

### 2.1 `gen-jwt-key` 在非 Unix 平台导入阶段直接失败

- 文件：`slurmweb/apps/genjwt.py`
- 问题：模块顶层直接导入 `pwd`，在 Windows 等非 Unix 平台会在导入阶段抛出 `ModuleNotFoundError`，导致命令与相关测试无法继续。
- 修复：
  - 为 `pwd` 增加兼容降级逻辑，避免模块导入即失败。
  - 为缺失 `os.geteuid()` 的平台提供兼容兜底，避免运行期再次中断。
- 影响：降低平台相关导入失败风险，不改变 Linux 主路径行为。

### 2.2 `setfacl` 失败时原逻辑不会真正报错

- 文件：`slurmweb/apps/genjwt.py`
- 问题：`subprocess.run(cmd)` 未启用 `check=True`，即使 `setfacl` 失败也不会进入 `CalledProcessError` 分支，ACL 设置失败可能被静默忽略。
- 修复：改为 `subprocess.run(cmd, check=True)`。
- 影响：JWT key ACL 设置失败时能够被记录，避免发布后权限问题被静默吞掉。

### 2.3 AI 显式启用但数据库初始化失败时缺少专门告警

- 文件：`slurmweb/apps/__init__.py`、`slurmweb/apps/agent.py`
- 问题：当站点配置里显式写了 `[ai] enabled=yes`，但数据库连接初始化失败时，日志只会出现数据库失败告警，缺少 AI 依赖链断裂的明确提示。
- 修复：
  - 在基础应用初始化时保留站点配置文件路径。
  - Agent 启动时回读原始 INI，识别是否显式请求 AI。
  - 若请求 AI 且数据库不可用，补充明确告警。
- 影响：发布和排障时更容易识别 “AI 不可用的根因是数据库不可用”。

## 3. 发布阻塞项

### 3.1 后端命名迁移到 `slurm-web-plus` 仍未完成

当前工作区里 Python 包元数据已开始切到 `slurm-web-plus`，但后端仍有大量对外暴露点保留旧名 `slurm-web`，发布会出现命名割裂：

- 配置默认路径仍是旧前缀：
  - `conf/vendor/agent.yml`
  - `conf/vendor/gateway.yml`
  - `slurmweb/apps/_defaults.py`
- systemd/uWSGI/兼容脚本仍是旧服务名与旧命令名：
  - `lib/systemd/slurm-web-agent.service`
  - `lib/systemd/slurm-web-gateway.service`
  - `lib/wsgi/**`
  - `lib/exec/slurm-web-compat`
  - `lib/sysusers/slurm-web.conf`
- CLI 与应用展示名仍为旧名：
  - `slurmweb/apps/agent.py`
  - `slurmweb/apps/gateway.py`
  - `slurmweb/apps/connect.py`
  - `slurmweb/apps/ldap.py`
  - `slurmweb/apps/showconf.py`
  - `slurmweb/apps/genjwt.py`
  - `slurmweb/exec/agent.py`
  - `slurmweb/exec/gateway.py`
  - `slurmweb/exec/connect.py`
  - `slurmweb/exec/ldap.py`
  - `slurmweb/exec/showconf.py`
  - `slurmweb/exec/genjwt.py`
- 包项目链接仍指向旧仓库命名：
  - `pyproject.toml`

结论：后端还不能宣称“已完整切换为 `slurm-web-plus`”，当前最多是“包元数据开始迁移，运行时/部署层未完成同步”。

### 3.2 发布验证环境仍应以 Linux 为准

本地验证是在 Windows PowerShell 下完成，后端测试中存在大量 POSIX 假设：

- `pwd`
- `setfacl`
- `/dev/null`
- `/var/lib/slurm-web/...`
- Unix 权限位与符号链接能力

这意味着：

- Windows 下的部分失败不能直接认定为后端业务缺陷。
- 正式发布前必须在 Linux CI 或 Linux 构建机上完成后端测试与打包验证。

## 4. 风险点

### 4.1 系统用户与目录命名迁移未定稿

`gen-jwt-key`、systemd unit、uWSGI 配置、默认 JWT 路径仍围绕 `slurm-web` 用户和目录：

- `slurmweb/apps/genjwt.py`
- `lib/systemd/*.service`
- `lib/wsgi/**/*.ini`
- `conf/vendor/*.yml`

如果发布目标是彻底更名为 `slurm-web-plus`，需要确认以下迁移策略：

- 系统用户是否仍保留 `slurm-web`
- `/etc/slurm-web`、`/usr/share/slurm-web`、`/var/lib/slurm-web` 是否保留兼容路径
- 旧服务名是否保留别名或软链接

未定稿前，不建议直接替换所有默认路径，否则会破坏现有部署升级。

### 4.2 兼容包装脚本仍以旧统一命令为中心

- 文件：`lib/exec/slurm-web-compat`
- 现状：仍把旧命令族转发到 `slurm-web`
- 风险：若发布后主命令实际变成 `slurm-web-plus`，该兼容脚本会把用户继续引向旧命令，命名策略会自相矛盾。

### 4.3 测试基线尚未跟随命名迁移

已观察到测试中仍大量断言旧 CLI 名称和旧路径，例如：

- `slurmweb/tests/exec/test_main.py`
- `slurmweb/tests/views/test_gateway_ui.py`
- `slurmweb/tests/slurmrestd/test_auth.py`

说明：

- `slurmweb/tests/exec/test_main.py` 已在本轮同步修正并通过。
- 仍需继续检查更大范围测试树中是否还有旧命名硬编码。

## 5. 待确认项

### 5.1 `slurm-web-plus` 的兼容策略

需要明确以下策略后，后端才能继续批量改名：

- 是否同时保留 `slurm-web-plus` 与 `slurm-web` 两个 CLI
- 是否保留旧 systemd service 名称
- 是否保留旧配置目录和数据目录
- `pyproject.toml` 中 `Homepage` / `Bug Tracker` 是否也要切到新仓库地址

### 5.2 发布物命名范围

需要确认“更名”覆盖到什么层级：

- 仅 PyPI 包名
- CLI 名
- systemd/unit 文件名
- sysusers 用户名
- `/etc`、`/usr/share`、`/var/lib` 路径

如果范围不明确，后端只能做局部迁移，无法保证发布成品一致。

## 6. 需前端/测试跟进

### 6.1 需要测试侧跟进

- 更新后端测试基线，覆盖：
  - `slurm-web-plus` 新命令名
  - `gen-jwt-key` 现在会校验 `setfacl` 返回码
  - Linux/Windows 差异场景要么分平台断言，要么限制到 Linux CI

### 6.2 需要前端侧确认

- 网关 UI 对外展示名、页面文案、静态资源路径是否也要统一迁移到 `slurm-web-plus`
- 若 UI 对 API 根路径、品牌名、下载说明仍写旧名，需要与前端文档一起同步

## 7. 本次涉及文件

本次我实际修改的后端文件：

- `slurmweb/apps/__init__.py`
- `slurmweb/apps/agent.py`
- `slurmweb/apps/genjwt.py`
- `docs/review/backend-review.md`

本次重点核查但未直接改动的发布相关文件：

- `pyproject.toml`
- `conf/vendor/agent.yml`
- `conf/vendor/gateway.yml`
- `slurmweb/apps/_defaults.py`
- `lib/systemd/*`
- `lib/wsgi/*`
- `lib/exec/slurm-web-compat`

## 8. 验证记录

已执行：

- `.\.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_agent_ai.py -k database_support_missing`
- `.\.venv\Scripts\python.exe -m pytest -q slurmweb/tests/exec/test_main.py`
- `.\.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_genjwt.py`
- `.\.venv\Scripts\python.exe -m pytest -q slurmweb/tests/apps/test_load_ldap_password_from_file.py slurmweb/tests/apps/test_showconf.py slurmweb/tests/test_ui.py`
- `.\.venv\Scripts\python.exe -m compileall slurmweb/apps`

结果：

- AI 告警补丁对应测试已通过。
- CLI 改名兼容与 `gen-jwt-key` 新行为对应测试已通过。
- `slurmweb/apps` 编译通过。
