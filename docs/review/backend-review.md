# 后端审查报告

## 1. 审查范围

本次后端审查聚焦以下主题：

- 权限规则解析、兼容映射和数据库角色合并是否与当前实现一致
- `Admin` / `Settings` / `AI` 等资源的真实后端权限口径
- 旧 `actions[]` 兼容残留是否仍会影响当前授权结果
- 与权限链路直接相关的后端测试覆盖是否到位

重点核对文件：

- `slurmweb/permission_rules.py`
- `slurmweb/access_control.py`
- `slurmweb/persistence/access_control_store.py`
- `slurmweb/tests/test_permission_rules.py`
- `slurmweb/tests/test_access_control_policy.py`
- `slurmweb/tests/test_access_control_store.py`
- `slurmweb/tests/views/test_agent_permissions.py`
- `slurmweb/tests/views/test_gateway_permissions.py`
- `slurmweb/tests/apps/test_ai_service.py`

## 2. 当前结论

- 当前后端真实权限模型已经是 `resource:operation:scope`，最终判定入口在 `AccessControlPolicyManager.allowed_user_permission()`。
- 文件策略层仍可提供旧 `actions[]`，但会先通过 `legacy_permission_map` 转成 `rules[]` 再参与合并。
- 数据库角色当前主字段是 `roles.permissions`，`roles.actions` 只作为兼容输入继续读取。
- 当前主管理资源是 `admin/ai`、`admin/access-control`、`admin/cache`、`admin/ldap-cache`；`settings/ai`、`settings/access-control`、`settings/cache`、`settings/ldap-cache` 不再是主资源名。

## 3. 已确认实现正确的关键点

### 3.1 规则匹配逻辑与当前设计一致

`slurmweb/permission_rules.py` 当前已覆盖：

- 精确资源匹配
- `admin/*` 这类前缀资源匹配
- `*:*:*` 全局通配
- `edit` / `delete` 自动满足 `view`
- `self` scope
- 默认种子角色 `user` / `admin` / `super-admin`

其中普通用户默认不拥有 `jobs:view:*`，而是：

- 非 `admin/*` 页面只读
- `jobs:view:self`
- `jobs:edit:self`
- `jobs:delete:self`
- `user/profile:view:self`
- `user/analysis:view:self`

### 3.2 文件策略与数据库角色的合并口径一致

`slurmweb/access_control.py` 当前真实链路是：

1. 文件策略读出 `roles + actions`
2. 旧动作通过 `legacy_actions_to_rules()` 转成 `rules`
3. 数据库角色返回 `roles + actions + permissions`
4. 两侧统一合并为：
   - `roles`
   - `actions`
   - `rules`
   - `sources.policy/custom/merged`

说明：

- 当前前端应优先消费 `rules` 或 `sources.merged.rules`
- `actions` 继续存在，主要用于兼容旧页面、旧测试数据和角色展示

### 3.3 数据库存储层的兼容迁移仍在正常工作

`slurmweb/persistence/access_control_store.py` 当前会：

- 优先使用 `permissions`
- 当 `permissions` 为空时，从 `actions` 推导
- 启动时清理 7 个已移除旧动作
- 把历史 `admin-manage` 归一为 `*:*:*`
- 在空表时自动种子 `user` / `admin` / `super-admin`

## 4. 当前风险

### 4.1 文档和测试仍容易把 `Settings` 管理页误写成主资源

- 路由兼容入口仍然存在，容易让文档误把 `/settings/ai` 等路径写成正式管理入口。
- 但后端目录与前端主菜单口径已经转到 `admin/*`。

### 4.2 兼容层仍然存在，新增代码若继续消费 `actions[]` 会重新制造双口径

- 当前兼容层是必要的，但它不应该继续成为新功能的默认实现路径。
- 新增鉴权应直接围绕资源规则编写，并让测试夹具优先提供 `rules[]`。

## 5. 建议

- 继续把页面、测试夹具和说明文档统一到 `admin/*` 与 `resource:operation:scope`。
- 对 `self` 场景的前端判定只做辅助显示，最终安全边界仍以后端 owner-aware 校验为准。
- 后续如果继续清理 legacy 权限，优先从前端未迁移消费点和旧测试夹具入手，而不是先删兼容字段。

## 6. 验证记录

已通过：

- `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/test_permission_rules.py`
- `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/test_access_control_policy.py`
- `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/test_access_control_store.py`
- `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/views/test_agent_permissions.py`
- `.venv\\Scripts\\python.exe -m pytest -q slurmweb/tests/views/test_gateway_permissions.py`

说明：

- 以上验证覆盖了规则解析、策略合并、数据库兼容和网关/Agent 权限主链路。
- `slurmweb/tests/apps/test_ai_service.py` 仅在涉及 AI 权限映射改动时需要追加执行；本轮前端权限消费收口未改动 AI 后端授权逻辑。
