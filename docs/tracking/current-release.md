# 当前发布跟踪：路由权限系统与配置收敛

## 1. 当前主题

本轮发布聚焦两条主线：

- 权限系统切换为 `resource:operation:scope`
- Agent 能力配置收敛为数据库与 Prometheus 自动推导

## 2. 已完成项

- 后端新增权限规则模型、匹配器、旧权限映射与 `self` 判定
- `AccessControlPolicyManager` 统一产出 `roles/actions/rules`
- 角色表新增 `permissions`
- 新增 `GET /access/catalog`
- 数据库首次空角色表自动写入 `user`、`admin`、`super-admin`
- 主菜单、路由守卫、Settings Tabs、AI/Cache/LDAP Cache、用户空间切到新规则
- `Settings > Access Control` 改为资源矩阵
- 数据库能力自动启用：
  - LDAP Cache
  - Jobs History
  - Access Control
  - AI
- Prometheus 与数据库组合自动启用：
  - node metrics
  - user metrics
  - user analytics
- 文档已同步到 overview、feature 和 tracking

## 3. 进行中项

- 无额外开发中的功能项

## 4. 风险与阻塞

- 全量前端 Vitest 未在本次变更中完整重跑
- 全量后端 pytest 未在本次变更中完整重跑
- 已完成的定向验证未发现当前实现阻塞项

## 5. 已同步文档

- `docs/README.md`
- `docs/overview/project-overview.md`
- `docs/overview/architecture-overview.md`
- `docs/overview/latest-features.md`
- `docs/features/access-control/requirements.md`
- `docs/features/access-control/test-plan.md`
- `docs/features/ai/requirements.md`
- `docs/features/cache/requirements.md`
- `docs/features/user-analytics/backend.md`
- `docs/tracking/current-release.md`

## 6. 验证状态

已通过：

- `npm --prefix frontend run type-check`
- `npx vitest run tests/stores/runtime.spec.ts tests/views/settings/SettingsAccessControl.spec.ts`
- `.venv\Scripts\python.exe -m pytest slurmweb/tests/views/test_agent_permissions.py -q`
- `.venv\Scripts\python.exe -m pytest slurmweb/tests/apps/test_agent.py -q`
