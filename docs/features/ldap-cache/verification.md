# Users 页面验证说明（Admin > Users）

本文档补充说明当前 `Users` 管理页的验证方式，适用于以下变更：

- gateway 登录成功后，显式向 agent 发送 `username`、`fullname`、`groups`
- agent `GET /users/cache` 支持 `username`、`page`、`page_size`
- `/:cluster/admin/ldap-users` 页面支持按用户名搜索和分页
- 多 cluster 下，搜索和分页状态按 cluster 独立维护
- 旧 `/settings/ldap-cache`、`/settings/ldap-users` 与 `/:cluster/admin/ldap-cache` 仅保留为重定向兼容入口

## 1. API 验证

先获取登录 token：

```bash
TOKEN=$(curl -s -X POST http://localhost:5012/api/login \
  -H "Content-Type: application/json" \
  -d '{"user":"your_user","password":"your_password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

查询 users cache 首页：

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5012/api/agents/your_cluster/users/cache?page=1&page_size=10" \
  | python3 -m json.tool
```

预期返回：

```json
{
  "items": [
    {
      "username": "alice",
      "fullname": "Alice Doe"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

按用户名过滤：

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5012/api/agents/your_cluster/users/cache?page=1&page_size=10&username=alice" \
  | python3 -m json.tool
```

预期行为：

- 仅按 `username` 过滤
- 不按 `fullname` 过滤
- 排序固定为 `username ASC`

## 2. 数据库验证

完成一次正常 LDAP 登录后，检查本地用户缓存：

```bash
sudo -u postgres psql -d slurmweb -c \
  "SELECT id, username, fullname, ldap_synced_at FROM users ORDER BY updated_at DESC LIMIT 20;"
```

预期结果：

- 最近登录用户出现在 `users` 表
- `fullname` 在 LDAP 有该属性时不应为空
- `ldap_synced_at` 被刷新到最近登录时间附近

如果用户确实有 LDAP 全名，但数据库里仍为空，优先检查：

1. gateway 登录请求是否成功
2. gateway 到 agent 的 `POST /users/cache` 是否返回 2xx
3. agent 日志中是否出现用户缓存 warning

## 3. 页面验证

登录 Web 页面后，进入 `Admin -> Users`，逐项确认：

1. 页面继续按 cluster 分块展示。
2. 每个 cluster 都显示独立的搜索框、Search、Reset 和分页栏。
3. 在某个 cluster 中输入用户名并点击 Search，只影响当前 cluster。
4. 点击 Reset 后，当前 cluster 的搜索条件清空并回到第一页。
5. 当记录数超过 20 时，分页栏生效。
6. 翻页只影响当前 cluster，不影响其他 cluster。
7. `fullname` 为空的用户显示为 `-`。
8. 每个 cluster 卡片内部的表格区域独立滚动，长结果不会把整页持续撑高。
9. 每个 cluster 的分页栏固定在各自结果卡片底部，不固定到浏览器底部，也不会串到其他 cluster 卡片。
10. 访问旧 `/settings/ldap-cache`、`/settings/ldap-users` 或 `/:cluster/admin/ldap-cache` 时，会重定向到正式 `Users` 页面。

## 4. 多 Agent 验证

当一个 gateway 对接多个 agent 时，额外确认：

- 各 cluster 的 users cache 数据彼此独立
- 某一个 agent 不可用时，不影响其他 agent 的 users cache 查询
- 某一个 cluster 的搜索词和页码不会串到其他 cluster

## 5. 通过标准

- [ ] LDAP 登录后，`users.fullname` 正常写入
- [ ] `/api/agents/<cluster>/users/cache` 返回分页对象
- [ ] Users 页面支持用户名搜索
- [ ] Users 页面支持分页
- [ ] 多 cluster 状态互不影响
