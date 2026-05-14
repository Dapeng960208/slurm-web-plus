# Cache 功能需求说明

## 1. 范围

Cache 功能当前包括：

- `Settings > Cache`
  - cache 统计
  - reset 统计
  - metrics 视图
- `Admin > Users`
  - 数据库缓存的 LDAP 用户列表
- Agent Redis 运行时缓存
  - 实时作业全量结果 `jobs`
  - Dashboard / Analysis 使用的 `stats`
  - Analysis 辅助接口 `analysis/node-hotspots`

## 2. 启用条件

能力启用条件已经收敛为：

- Cache 统计页：
  - 依赖 cache service 自身可用
- Cache metrics：
  - 依赖 cluster metrics 可用
- Users：
  - 依赖数据库开启

旧独立 feature flag 不再作为新的业务语义来源。

## 3. 权限要求

当前页面与动作权限如下：

| 页面/动作 | 新规则 |
|---|---|
| `/:cluster/admin/cache` 查看 | `admin/cache:view:*` |
| reset 统计 | `admin/cache:edit:*` |
| `/:cluster/admin/ldap-users` 查看 | `admin/ldap-users:view:*` |

旧权限兼容：

- `cache-view` -> `admin/cache:view:*` + `admin/ldap-users:view:*`
- `cache-reset` -> `admin/cache:edit:*`

说明：

- 为兼容历史测试与旧角色，前端运行时仍接受旧 `actions[]` 推导出的等价规则。

## 4. 降级行为

- cache service 不可用：
  - cache 接口返回 `501`
  - Agent 业务接口继续走原有实时链路，不使用 Redis 缓存
- metrics 不可用：
  - 页面显示无 metrics 的说明卡片
- 数据库不可用：
  - Users 页面显示数据库不可用

## 5. Agent 运行时缓存范围

Agent 缓存用于降低高频页面对 `slurmrestd` 和 metrics 数据库的重复请求压力。

| 接口 | 缓存 key | 默认 TTL | 说明 |
|---|---|---:|---|
| `GET /jobs` | `jobs` | `cache.jobs=30` | 不带 query 时缓存全量实时作业；带 `users/states/accounts/qos/partitions` 时优先复用全量缓存并在 Agent 内存中过滤 |
| `GET /stats` | `stats` | `cache.stats=60` | Dashboard / Analysis 统计摘要 |
| `GET /stats?partition=<name>` | `stats-partition-<name>`，归类为 `stats` | `cache.stats=60` | 按分区独立缓存统计摘要 |
| `GET /analysis/node-hotspots?start=<start>&end=<end>` | `analysis-node-hotspots-<start>-<end>`，归类为 `analysis` | `cache.analysis=60` | 按时间窗独立缓存节点热点结果；接口内部只从持久化节点样本重建，不再回退到实时 Prometheus 查询 |

新增配置项：

- `cache.stats`：Dashboard / Analysis summary `stats` 缓存 TTL，默认 `60` 秒。
- `cache.analysis`：Analysis 辅助接口缓存 TTL，默认 `60` 秒。

实时作业写操作完成后会失效相关作业缓存：

- `POST /jobs/submit`
- `POST /job/<id>/update`
- `DELETE /job/<id>/cancel`

边界说明：

- Redis 未启用时，上述接口不使用缓存，仍按原实时链路查询。
- `analysis/ping` 与 `analysis/diag` 不纳入缓存，保持诊断实时性。
- `user/tools/analysis` 本轮不纳入 Redis 缓存；该接口依赖数据库聚合且 key 维度更复杂，后续按卡顿证据单独评估。

## 6. 相关实现

- `frontend/src/views/settings/SettingsCache.vue`
- `frontend/src/components/settings/SettingsCacheStatistics.vue`
- `frontend/src/views/settings/SettingsLdapCache.vue`
- `slurmweb/slurmrestd/__init__.py`
- `slurmweb/views/agent.py`

## 7. 相关验证

- `slurmweb/tests/slurmrestd/test_slurmrestd_filtered_cached.py`
- `slurmweb/tests/views/test_agent.py`
- `slurmweb/tests/views/test_agent_operations.py`
- `slurmweb/tests/views/test_gateway.py`
