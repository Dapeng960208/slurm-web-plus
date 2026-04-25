# 最新功能

## 1. 路由权限系统切换为规则模型

当前权限模型已经从单一 `actions[]` 扩展为 `resource:operation:scope`：

- 支持主路由资源和子资源，例如 `settings/cache`
- 支持前缀资源，例如 `settings/*:view:*`
- 支持 `self` 场景，例如 `user/profile:view:self`
- 支持全局最高权限 `*:*:*`

同时保留旧权限名兼容层，`view-ai`、`roles-manage`、`cache-reset` 等历史动作会自动映射到新规则。

## 2. Access Control 页面改为资源矩阵

`Settings > Access Control` 已从 action 复选框切换为目录驱动的权限矩阵：

- 页面通过 `GET /access/catalog` 获取全部资源目录
- 角色编辑以 `permissions[]` 为主
- 同时展示兼容 `actions[]`
- 支持首次空角色表自动预置 `user`、`admin`、`super-admin`

## 3. Agent 能力开关收敛

系统当前的业务能力按基础依赖自动推导：

- 数据库开启后，自动提供：
  - LDAP Cache
  - Jobs History
  - Access Control
  - AI
- Prometheus 开启后，自动提供：
  - metrics
  - node metrics
- 数据库和 Prometheus 同时开启后，自动提供：
  - user metrics
  - user analytics

旧 feature flag 仅保留兼容占位定义，不再作为实际产品语义来源。

## 4. AI、Cache、用户空间全部接入新权限

以下页面和入口已经按新规则判定：

- `/:cluster/ai` 使用 `ai:view:*`
- `Settings > AI` 使用 `settings/ai:view|edit|delete:*`
- `Settings > Cache` 使用 `settings/cache:view|edit:*`
- `Settings > LDAP Cache` 使用 `settings/ldap-cache:view:*`
- 用户空间使用 `user/profile:view:*|self` 与 `user/analysis:view:*|self`

## 5. 本轮验证结果

已完成的定向验证包括：

- `npm --prefix frontend run type-check`
- `npx vitest run tests/stores/runtime.spec.ts tests/views/settings/SettingsAccessControl.spec.ts`
- `.venv\Scripts\python.exe -m pytest slurmweb/tests/views/test_agent_permissions.py -q`
- `.venv\Scripts\python.exe -m pytest slurmweb/tests/apps/test_agent.py -q`
