# 访问控制测试计划

## 1. 目标

验证新的 `resource:operation:scope` 权限系统、旧权限兼容映射、预置角色种子和前端资源矩阵在数据库启用与关闭两种模式下都行为正确。

## 2. 后端测试

### 2.1 规则匹配

覆盖以下场景：

- 精确资源匹配
- 前缀资源匹配
- `*:view:*` / `*:edit:*`
- `*:*:*`
- `self`
- `edit` / `delete` 满足 `view`
- 旧权限映射到新规则
- `cache-reset` -> `admin/cache:edit:*`
- `admin-manage` -> `*:*:*`

对应重点：

- `slurmweb/permission_rules.py`
- `slurmweb/tests/test_permission_rules.py`
- `slurmweb/tests/test_access_control_policy.py`
- `slurmweb/tests/views/test_agent_permissions.py`

### 2.2 能力推导

覆盖以下场景：

- 数据库开启后自动启用：
  - LDAP Cache
  - Jobs History
  - Access Control
  - AI
- Prometheus 开启后自动启用：
  - metrics
  - node metrics
- 数据库 + Prometheus 开启后自动启用：
  - user metrics
  - user analytics

对应重点：

- `slurmweb/tests/apps/test_agent.py`

### 2.3 数据库存储

覆盖以下场景：

- `roles.permissions` 迁移生效
- 角色新旧字段双读双写
- 旧角色只有 `actions[]` 时可推导出 `permissions[]`
- 历史 `roles.actions` 中的 7 个已移除旧动作会在启动时迁入 `permissions[]` 后清理
- 历史 `roles.actions` 中的 `admin-manage` 会在启动时补齐 `*:*:*`
- 角色表为空时自动写入 `user`、`admin`、`super-admin`
- `user` 默认值为“非 admin 页面只读 + jobs:view|edit|delete:self + user/analysis:view:self”
- `admin` 默认值为 `*:view:*` + `*:edit:*`

## 3. 前端测试

### 3.1 运行时权限

覆盖以下场景：

- `hasRoutePermission(...)` 能正确匹配规则
- 旧 `actions[]` 测试夹具仍能通过兼容回退参与判定
- `self` 场景下 `/me` 与 `/users/:user` 行为正确

### 3.2 页面与导航

覆盖以下场景：

- 主菜单按新规则显示主路由
- 路由守卫按新规则跳转 `/forbidden`
- Settings Tabs 按新规则显示
- `SettingsAI`、`SettingsCache`、`SettingsLdapCache`
- `AssistantView`
- `UserView`

### 3.3 Access Control 页面

覆盖以下场景：

- `GET /access/catalog` 成功加载
- 角色权限矩阵回填正确
- 保存时提交 `permissions[]`
- 兼容动作 `actions[]` 可回显
- 只读模式不可编辑
- 用户角色绑定保存正确

## 4. 端到端场景

最少验证以下组合：

1. 仅数据库开启
2. 仅 Prometheus 开启
3. 数据库 + Prometheus 同时开启
4. 旧角色只有 `actions[]`，启用新权限后页面仍可访问

## 5. 本轮矩阵审查结论

已确认并已补/修正的关键断言：

- 普通用户默认权限不是 `jobs:view:*`，而是非 `admin/*` 页面只读 + `jobs:view|edit|delete:self`
- `admin` 默认角色不是全量 delete，而是 `*:view:*` + `*:edit:*`
- `admin` 子树不再使用 `settings/ai|cache|ldap-cache|access-control` 资源名，统一切到 `admin/*`
- 7 个已移除旧动作不会再出现在 `legacy_map`、`/permissions.actions` 和前端角色页
- `admin-manage` 只在 `*:*:*` 场景下回显，`admin` 默认角色不会推出该动作

仍待主线程继续补齐的缺口：

- 前端只读模式矩阵仍需继续覆盖 `Admin` 页面下各 tab 的禁用/隐藏细节
- 仍有部分前端测试夹具以旧 `actions[]` 为主，需要逐步收敛到 `rules[]`
- Windows 本地环境不适合直接用全量后端 pytest 作为唯一验收结论

## 6. 已执行的定向验证

已通过：

- `npm --prefix frontend run type-check`
- `npx vitest run tests/stores/runtime.spec.ts tests/views/settings/SettingsAccessControl.spec.ts`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_access_control_policy.py`
- `.venv\Scripts\python.exe -m pytest -q slurmweb/tests/test_access_control_store.py`
- `.venv\Scripts\python.exe -m pytest slurmweb/tests/views/test_agent_permissions.py -q`
- `.venv\Scripts\python.exe -m pytest slurmweb/tests/apps/test_agent.py -q`

未在本次变更中完整重跑：

- 全量前端 Vitest
- 全量后端 pytest
