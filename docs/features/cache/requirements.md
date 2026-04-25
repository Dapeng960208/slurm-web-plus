# Cache 功能需求说明

## 1. 范围

Cache 功能当前包括：

- `Settings > Cache`
  - cache 统计
  - reset 统计
  - metrics 视图
- `Settings > LDAP Cache`
  - 数据库缓存的 LDAP 用户列表

## 2. 启用条件

能力启用条件已经收敛为：

- Cache 统计页：
  - 依赖 cache service 自身可用
- Cache metrics：
  - 依赖 cluster metrics 可用
- LDAP Cache：
  - 依赖数据库开启

旧独立 feature flag 不再作为新的业务语义来源。

## 3. 权限要求

当前页面与动作权限如下：

| 页面/动作 | 新规则 |
|---|---|
| `Settings > Cache` 查看 | `settings/cache:view:*` |
| reset 统计 | `settings/cache:edit:*` |
| `Settings > LDAP Cache` 查看 | `settings/ldap-cache:view:*` |

旧权限兼容：

- `cache-view` -> `settings/cache:view:*`
- `cache-reset` -> `settings/cache:edit:*`

说明：

- 为兼容历史测试与旧角色，前端运行时仍接受旧 `actions[]` 推导出的等价规则。

## 4. 降级行为

- cache service 不可用：
  - cache 接口返回 `501`
- metrics 不可用：
  - 页面显示无 metrics 的说明卡片
- 数据库不可用：
  - LDAP Cache 页面显示数据库不可用

## 5. 相关实现

- `frontend/src/views/settings/SettingsCache.vue`
- `frontend/src/components/settings/SettingsCacheStatistics.vue`
- `frontend/src/views/settings/SettingsLdapCache.vue`
