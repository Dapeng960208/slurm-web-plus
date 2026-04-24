# 访问控制（自定义角色）测试计划

目标：端到端验证“自定义角色 + 用户绑定”的访问控制能力，并确保功能关闭时既有 `policy.ini` 行为保持不变。

## 1. 后端覆盖点

### 1.1 `slurmweb/tests/views/test_agent_permissions.py`

- `/permissions` 返回 `roles`、`actions` 与 `sources`
- 匿名/认证路径权限行为保持正确
- policy 与 custom 的 roles/actions 合并与去重

### 1.2 `slurmweb/tests/views/test_agent.py`

- `/info` 包含 `access_control` 与相关 capability 字段
- `/users/cache` 会刷新 `policy_roles` / `policy_actions`
- 角色管理与用户绑定接口行为正确
- 访问控制关闭时接口返回 `501`

### 1.3 `slurmweb/tests/views/test_gateway.py`

- `/api/clusters` 包含扩展后的集群字段（含 `access_control`）
- Gateway 正确代理 `/permissions`、`/access/roles`、`/access/users`
- query string 转发正确（LDAP cache 与 access users filters）

### 1.4 `slurmweb/tests/apps/test_agent.py`

- 只有数据库可用时才会启用访问控制
- 依赖缺失时能安全降级
- 启用后，Agent 启动会刷新缓存用户的策略快照
- 单用户刷新失败不会阻塞启动

## 2. 前端覆盖点

### 2.1 `frontend/tests/composables/GatewayAPI.spec.ts`

- `permissions` 归一化为 `policy/custom/merged`
- 集群 capability 归一化与 `access_control` 门控
- 角色 CRUD 与用户绑定 API 路径

### 2.2 `frontend/tests/components/settings/SettingsTabs.spec.ts`

- 当前集群支持访问控制时才显示 `Access Control` tab

### 2.3 `frontend/tests/views/settings/SettingsAccount.spec.ts`

- `policy/custom/merged` 权限视图渲染正确

### 2.4 `frontend/tests/views/settings/SettingsAccessControl.spec.ts`

- 当前集群 role/user 数据加载正确
- `roles-manage` 模式支持创建/编辑/删除与保存绑定
- 只读模式限制正确
- feature-disabled 状态覆盖

## 3. 手工验证场景

### 3.1 功能关闭（Feature Flag Off）

1. 设置 `[persistence] access_control_enabled = no`
2. 确认 policy-only 授权路径仍然可用
3. 确认访问控制管理接口返回 `501`

### 3.2 功能开启（Feature Flag On）

1. 数据库迁移升级到 head
2. 设置 `[persistence] access_control_enabled = yes`
3. 创建一个自定义角色并绑定到某个已缓存用户
4. 修改 `policy.ini` 并重启 Agent
5. 确认缓存用户的 `policy_roles/policy_actions` 在启动时被刷新
6. 重新登录并确认 `merged` 权限包含 policy 与 custom 的并集

## 4. 验收用例（最小集）

- 仅 policy 授权：访问生效
- 仅 custom 授权：访问生效
- policy + custom 并存：merged 返回并集
- 删除角色：绑定被级联删除
- 更新用户绑定：下一次 `/permissions` 获取生效

## 5. 执行命令

后端：

```powershell
.venv\Scripts\python.exe -m pytest `
  slurmweb/tests/views/test_agent_permissions.py `
  slurmweb/tests/views/test_agent.py `
  slurmweb/tests/views/test_gateway.py `
  slurmweb/tests/apps/test_agent.py
```

前端：

```powershell
npm --prefix frontend run test:unit -- `
  tests/composables/GatewayAPI.spec.ts `
  tests/components/settings/SettingsTabs.spec.ts `
  tests/views/settings/SettingsAccount.spec.ts `
  tests/views/settings/SettingsAccessControl.spec.ts --run
```
