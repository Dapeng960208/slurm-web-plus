# 功能验证清单

## 1. 后端验证

### 1.1 检查配置文件
```bash
# 本次新增功能配置段
grep -A 10 "\[database\]" /etc/slurm-web/agent.ini
grep -A 10 "\[persistence\]" /etc/slurm-web/agent.ini
grep -A 10 "\[node_metrics\]" /etc/slurm-web/agent.ini

# metrics 为已有功能，如本次未启用可不检查
grep -A 10 "\[metrics\]" /etc/slurm-web/agent.ini
```

说明：

- `[database]`、`[persistence]`、`[node_metrics]` 是本次新增能力
- `[metrics]` 是已有 Prometheus 指标功能，不属于数据库迁移必需项
- 即使 `[database] enabled = no`，agent 其他非数据库功能也应继续可用

### 1.2 检查服务状态
```bash
systemctl status slurm-web-agent
systemctl status slurm-web-gateway

# 查看日志
journalctl -u slurm-web-agent -n 50
journalctl -u slurm-web-gateway -n 50
```

### 1.3 验证 API 端点

#### 获取 token
```bash
TOKEN=$(curl -s -X POST http://localhost:5012/login \
  -H "Content-Type: application/json" \
  -d '{"user":"your_user","password":"your_password"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

echo "Token: $TOKEN"
```

#### 检查 /clusters 接口返回的功能标志
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:5012/clusters | python3 -m json.tool
```

**预期输出应包含：**
```json
[
  {
    "name": "your_cluster",
    "persistence": true,    // 如果启用了作业历史
    "node_metrics": true,   // 如果启用了节点监控
    "permissions": {...}
  }
]
```

#### 测试作业历史 API（如果 persistence=true）
```bash
# 获取 API 版本
VERSION=$(slurm-web --version 2>&1 | head -1 | awk '{print $NF}')

# 查询历史作业
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5012/v${VERSION}/jobs/history?page=1&page_size=10" \
  | python3 -m json.tool
```

**预期输出：**
```json
{
  "jobs": [
    {
      "id": 1,
      "job_id": 12345,
      "user_id": 7,
      "job_name": "test_job",
      "user_name": "user1",
      "account": "account1",
      "partition": "compute",
      "job_state": "COMPLETED",
      "node_count": 2,
      "cpus": 48,
      "submit_time": "2024-01-01T10:00:00",
      "start_time": "2024-01-01T10:05:00",
      "end_time": "2024-01-01T11:00:00",
      "time_limit_minutes": 120,
      "exit_code": {
        "return_code": {
          "set": true,
          "infinite": false,
          "number": 0
        },
        "signal": {
          "id": {
            "set": true,
            "infinite": false,
            "number": 0
          },
          "name": "NONE"
        },
        "status": ["SUCCESS"]
      }
    }
  ],
  "total": 150
}
```

- 鍘嗗彶鎺ュ彛鐜板湪浼氬皢 `exit_code` 瑙勮寖鍖栦负瀵硅薄锛屽吋瀹规柊鍐欏叆鐨?JSON 瀛楃涓插拰鏃ф暟鎹?`0:0` 杩欑被瀛楃涓层€?

#### 测试节点实时资源 API（如果 node_metrics=true）
```bash
# 替换 node01 为实际节点名
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5012/v${VERSION}/agents/your_cluster/node/node01/metrics" \
  | python3 -m json.tool
```

**预期输出：**
```json
{
  "cpu_usage": 45.2,
  "memory_usage": 68.5,
  "disk_usage": 72.3
}
```

### 1.4 检查数据库（如果 persistence=true）
```bash
# 检查迁移版本
alembic current

# 检查数据库连接
sudo -u postgres psql -d slurmweb -c "SELECT COUNT(*) FROM job_snapshots;"

# 查看最近的快照
sudo -u postgres psql -d slurmweb -c "
SELECT js.job_id, js.job_name, u.username AS user_name, js.job_state, js.last_seen AS snapshot_time
FROM job_snapshots js
LEFT JOIN users u ON u.id = js.user_id
ORDER BY js.last_seen DESC 
LIMIT 10;"

# 检查数据量和时间范围
sudo -u postgres psql -d slurmweb -c "
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT job_id) as unique_jobs,
  MIN(last_seen) as oldest,
  MAX(last_seen) as newest
FROM job_snapshots;"
```

如果是首次生产部署，至少还应确认：

```bash
sudo -u postgres psql -d slurmweb -c "\dt"
sudo -u postgres psql -d slurmweb -c "\d users"
sudo -u postgres psql -d slurmweb -c "\d job_snapshots"
```

---

## 2. 前端验证

### 2.1 访问 Web 界面
```
http://your-server:5012
```

### 2.2 检查菜单显示

#### 场景 1：persistence = true
- 左侧菜单应显示 "Jobs History" 项（在 "Jobs" 下方，带时钟图标）
- 点击后进入作业历史页面

#### 场景 2：persistence = false
- 左侧菜单不应显示 "Jobs History" 项
- 直接访问 `/cluster_name/jobs/history` 应重定向到 `/cluster_name/jobs`

### 2.3 测试作业历史页面（如果 persistence=true）

1. **页面加载**
   - 页面标题显示"作业历史记录"
   - 自动加载第一页数据

2. **筛选功能**
   - 输入用户名筛选
   - 输入账户筛选
   - 输入分区筛选
   - 输入状态筛选（如 COMPLETED、FAILED）
   - 输入作业 ID 筛选
   - 点击"查询"按钮

3. **数据展示**
   - 表格显示所有字段：作业ID、名称、用户、账户、分区、状态、节点数、CPU数、提交时间、开始时间、结束时间、时间限制、退出码
   - 状态显示不同颜色徽章（COMPLETED=绿色、RUNNING=蓝色、FAILED=红色、CANCELLED=黄色）
   - 时间格式正确（本地化显示）

4. **分页功能**
   - 显示总记录数和当前页码
   - "上一页"按钮在第一页时禁用
   - "下一页"按钮在最后一页时禁用
   - 翻页后数据正确更新

### 2.4 测试节点实时资源（如果 node_metrics=true）

1. **进入节点详情页**
   - 点击 Resources → 选择任意节点

2. **检查实时资源面板**
   - 在节点详情页底部应显示 "Real-time Metrics" 部分
   - 显示 CPU usage、Memory usage、Disk usage (root)
   - 数值每 15 秒自动刷新
   - 超过 90% 的指标显示为红色加粗

3. **场景：node_metrics = false**
   - 节点详情页不显示 "Real-time Metrics" 部分

---

## 3. 常见问题排查

### 问题 1：菜单中没有显示 "Jobs History"

**检查步骤：**
```bash
# 1. 确认配置文件中 persistence.enabled = true
grep "enabled" /etc/slurm-web/agent.ini | grep -A 1 persistence

# 2. 确认服务已重启
systemctl restart slurm-web-agent slurm-web-gateway

# 3. 检查 /clusters API 返回
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:5012/clusters | grep persistence

# 4. 清除浏览器缓存并刷新页面
```

### 问题 2：作业历史 API 返回 404

**检查步骤：**
```bash
# 1. 确认路由已注册
grep "jobs/history" /path/to/slurmweb/views/gateway.py

# 2. 检查 agent 日志
journalctl -u slurm-web-agent -f

# 3. 测试数据库连接
sudo -u postgres psql -d slurmweb -c "\dt"
```

### 问题 3：节点实时资源显示 "Unable to retrieve metrics"

**检查步骤：**
```bash
# 1. 确认 Prometheus 可访问
curl http://your-prometheus:9090/api/v1/query?query=up

# 2. 检查配置
grep "prometheus_host" /etc/slurm-web/agent.ini

# 3. 测试 Prometheus 查询
curl "http://your-prometheus:9090/api/v1/query?query=100-avg(rate(node_cpu_seconds_total{mode='idle',job='your_job',hostname='node01'}[5m]))*100"

# 4. 检查 agent 日志中的错误
journalctl -u slurm-web-agent | grep -i prometheus
```

### 问题 4：数据库中没有数据

**检查步骤：**
```bash
# 1. 确认 database.enabled = yes
grep -A 10 "\[database\]" /etc/slurm-web/agent.ini

# 1. 确认后台线程正在运行
journalctl -u slurm-web-agent | grep "Starting job snapshot thread"

# 2. 检查是否有错误
journalctl -u slurm-web-agent | grep -i error | grep -i persist

# 3. 确认迁移已成功完成
alembic current
sudo -u postgres psql -d slurmweb -c "\dt"

# 4. 检查 users 表是否能缓存 LDAP 登录用户
sudo -u postgres psql -d slurmweb -c \
  "SELECT id, username, fullname, ldap_synced_at FROM users ORDER BY updated_at DESC LIMIT 20;"

# 5. 检查 Slurm 是否有作业
squeue
sacct -S now-1hour
```

---

## 4. 性能验证

### 4.1 数据库性能
```bash
# 检查表大小
sudo -u postgres psql -d slurmweb -c "
SELECT pg_size_pretty(pg_total_relation_size('job_snapshots'));"

# 检查索引使用情况
sudo -u postgres psql -d slurmweb -c "
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE tablename = 'job_snapshots';"
```

### 4.2 API 响应时间
```bash
# 测试历史查询响应时间
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5012/v${VERSION}/jobs/history?page=1&page_size=50" \
  > /dev/null
```

**预期：** < 1 秒

### 4.3 内存占用
```bash
# 检查 agent 进程内存
ps aux | grep slurm-web-agent | grep -v grep
```

---

## 5. 验证通过标准

✅ **后端：**
- [ ] `/clusters` API 返回正确的 `persistence` 和 `node_metrics` 标志
- [ ] `/jobs/history` API 返回数据（如果启用）
- [ ] `/node/{name}/metrics` API 返回数据（如果启用）
- [ ] 数据库中有作业快照数据（如果启用）

✅ **前端：**
- [ ] 菜单根据配置动态显示/隐藏 "Jobs History"
- [ ] 作业历史页面正常加载和筛选
- [ ] 节点详情页显示实时资源（如果启用）
- [ ] 路由守卫正常工作（未启用功能时重定向）

✅ **权限：**
- [ ] 无 `view-jobs` 权限的用户看不到 "Jobs History" 菜单
- [ ] 无 `view-nodes` 权限的用户看不到节点详情

✅ **性能：**
- [ ] 历史查询响应时间 < 1 秒
- [ ] 数据库写入不影响 agent 响应速度
- [ ] Prometheus 查询不阻塞页面加载
### 1.5 历史详情增强字段验证

启用 persistence 后，确认历史详情接口仍返回 JSON，并包含本次新增字段：

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5012/v${VERSION}/jobs/history/1" \
  | python3 -m json.tool
```

返回体应包含：

- `eligible_time`
- `last_sched_evaluation_time`
- `tres_requested`
- `tres_allocated`
- `used_memory_gb`

数据库字段验证：

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'job_snapshots'
  AND column_name IN (
    'eligible_time',
    'last_sched_evaluation_time',
    'tres_requested',
    'tres_allocated',
    'used_memory_gb'
  )
ORDER BY column_name;
```

前端历史详情页应显示：

- 六段式时间线：Submitted、Eligible、Scheduling、Running、Completed、Terminated。
- `Requested` 和 `Allocated` 资源块。
- 不再显示 `Used Memory` 字段；`used_memory_gb` 仅作为兼容字段保留在返回结构中，值应为 `null`。
