# Slurm-web 功能扩展部署指南

## 1. 前提条件

| 组件 | 要求 |
|---|---|
| Slurm-web | 已通过 dnf 安装并正常运行 |
| PostgreSQL | 需新安装（作业历史功能） |
| Prometheus | 已部署，node_exporter 正在采集节点数据（节点实时资源功能） |
| python3-psycopg2 | 需新安装（作业历史功能） |

---

## 2. 安装 PostgreSQL（作业历史功能）

```bash
# 安装 PostgreSQL 和 Python 驱动
dnf install -y postgresql-server postgresql-contrib python3-psycopg2

# 初始化数据库
postgresql-setup --initdb

# 启动并设置开机自启
systemctl enable --now postgresql

# 创建数据库用户和数据库
# 切换到 postgres 用户执行
sudo -u postgres psql -c "CREATE USER slurmweb WITH PASSWORD 'slurmweb';"
sudo -u postgres psql -c "CREATE DATABASE slurmweb OWNER slurmweb;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE slurmweb TO slurmweb;"

# 配置 PostgreSQL 允许密码认证（解决 ident 认证失败问题）
PG_HBA=$(sudo -u postgres psql -t -c "SHOW hba_file;" | tr -d ' ')
# local（Unix socket）连接也需要 md5，否则报 "Ident authentication failed"
echo "local   slurmweb   slurmweb               md5" | sudo tee -a $PG_HBA
echo "host    slurmweb   slurmweb   127.0.0.1/32   md5" | sudo tee -a $PG_HBA
echo "host    slurmweb   slurmweb   ::1/128        md5" | sudo tee -a $PG_HBA
sudo systemctl reload postgresql
```

---

## 3. 初始化数据库表结构

```bash
# 将 init_db.sql 复制到服务器后执行
sudo -u postgres psql -d slurmweb -f  /etc/slurm-web/init_db.sql

# 验证表已创建
sudo -u postgres psql -d slurmweb -c "\dt"
```

---

## 4. 数据库表结构说明（job_snapshots）

`job_snapshots` 表存储 agent 定时从 slurmrestd 采集的作业快照，字段与作业列表页核心字段对齐：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | BIGSERIAL PK | 自增主键，用于历史详情页跳转 |
| snapshot_time | TIMESTAMPTZ | 快照写入时间（每次 UPSERT 更新） |
| job_id | INTEGER | Slurm 作业 ID |
| job_name | TEXT | 作业名称 |
| job_state | TEXT | 作业状态（RUNNING / COMPLETED / FAILED …） |
| state_reason | TEXT | 状态原因 |
| user_name | TEXT | 提交用户 |
| account | TEXT | 账户 |
| group | TEXT | 用户组 |
| partition | TEXT | 分区 |
| qos | TEXT | QOS |
| nodes | TEXT | 节点列表字符串 |
| node_count | INTEGER | 节点数 |
| cpus | INTEGER | CPU 数 |
| priority | INTEGER | 优先级 |
| tres_req_str | TEXT | TRES 请求字符串 |
| tres_per_job | TEXT | 每作业 TRES |
| tres_per_node | TEXT | 每节点 TRES |
| gres_detail | TEXT | GRES 详情 |
| submit_time | TIMESTAMPTZ | 提交时间（与 job_id 组成唯一键） |
| start_time | TIMESTAMPTZ | 开始时间 |
| end_time | TIMESTAMPTZ | 结束时间 |
| time_limit_minutes | INTEGER | 时间限制（分钟） |
| exit_code | TEXT | 退出码 |
| working_directory | TEXT | 工作目录 |
| command | TEXT | 提交命令 |

> 这些字段与作业列表页（`/jobs`）展示的核心字段完全对应，保证历史数据与实时数据的一致性。

### 唯一约束与 UPSERT 策略

`(job_id, submit_time)` 组成复合唯一索引。Agent 每次采集时执行 **UPSERT**：
- 若该作业记录已存在，则更新 `job_state`、`end_time`、`exit_code` 等可变字段，并刷新 `snapshot_time`。
- 若不存在，则插入新行。

这样每个作业在数据库中只保留一条最新状态记录，避免重复写入。

### 定时采集机制

Agent 启动后会在后台线程中按 `snapshot_interval`（默认 60 秒）定时调用 slurmrestd 获取全量作业列表并执行 UPSERT。无需依赖前端页面访问触发写入。

---

## 5. 替换后端代码

### 5.1 确认安装路径

```bash
# 查找 slurmweb 安装路径
SLURMWEB_PATH=$(python3 -c "import slurmweb; import os; print(os.path.dirname(slurmweb.__file__))")
echo "安装路径: $SLURMWEB_PATH"
```

### 5.2 备份原有文件

```bash
# 备份将要修改的文件
cp $SLURMWEB_PATH/apps/agent.py    $SLURMWEB_PATH/apps/agent.py.bak
cp $SLURMWEB_PATH/apps/gateway.py  $SLURMWEB_PATH/apps/gateway.py.bak
cp $SLURMWEB_PATH/views/agent.py   $SLURMWEB_PATH/views/agent.py.bak
cp $SLURMWEB_PATH/views/gateway.py $SLURMWEB_PATH/views/gateway.py.bak
cp $SLURMWEB_PATH/metrics/db.py    $SLURMWEB_PATH/metrics/db.py.bak
cp /usr/share/slurm-web/conf/agent.yml /usr/share/slurm-web/conf/agent.yml.bak
```

### 5.3 替换修改的文件

```bash
# 替换核心文件
cp /root/slurmweb/apps/agent.py    $SLURMWEB_PATH/apps/agent.py
cp /root/slurmweb/apps/gateway.py  $SLURMWEB_PATH/apps/gateway.py
cp /root/slurmweb/views/agent.py   $SLURMWEB_PATH/views/agent.py
cp /root/slurmweb/views/gateway.py $SLURMWEB_PATH/views/gateway.py
cp /root/slurmweb/metrics/db.py    $SLURMWEB_PATH/metrics/db.py

# 新增 persistence 模块
mkdir -p $SLURMWEB_PATH/persistence
cp /root/slurmweb/persistence/__init__.py   $SLURMWEB_PATH/persistence/
cp /root/slurmweb/persistence/jobs_store.py $SLURMWEB_PATH/persistence/

# 替换配置定义文件（必须执行，否则启动时报错：
# "Section persistence loaded in settings overrides is not defined in settings definition"）
cp conf/vendor/agent.yml /usr/share/slurm-web/conf/agent.yml
```

---

## 6. 更新 Agent 配置文件

编辑 `/etc/slurm-web/agent.ini`，在文件末尾追加以下内容：

```ini
# ── 作业历史持久化（新增）────────────────────────────
[persistence]
enabled = true
host = localhost
port = 5432
database = slurmweb
user = slurmweb
password = your_password_here
retention_days = 180
snapshot_interval = 60

# ── 节点实时资源监控（新增）──────────────────────────
[node_metrics]
enabled = true
prometheus_host = http://your-prometheus-server:9090
node_exporter_job = BJ-IDC-Linux-IC-HPC-Node
node_hostname_label = hostname
```

> **注意**：
> - 如果只需要其中一个功能，将对应的 `enabled = false` 即可
> - `prometheus_host` 填写你们实际的 Prometheus 服务地址
> - `node_exporter_job` 填写 Prometheus 中 node_exporter 的 job 名称

---

## 7. 构建并替换前端代码

### 7.1 构建前端

```bash
cd frontend
npm install
npm run build
```

### 7.2 查找前端静态文件路径

```bash
# 方式一：通过 gateway 配置查找
grep -r "ui" /etc/slurm-web/gateway.ini | grep path

# 方式二：查找 index.html 位置
find /usr -name "index.html" -path "*slurm*" 2>/dev/null
```

### 7.3 备份并替换前端文件

```bash
FRONTEND_PATH=/usr/share/slurm-web/html   # 根据实际路径修改

# 备份
cp -r $FRONTEND_PATH ${FRONTEND_PATH}.bak

# 替换
cp -r frontend/dist/* $FRONTEND_PATH/
```

---

## 8. 重启服务

```bash
systemctl restart slurm-web-agent
systemctl restart slurm-web-gateway

# 确认服务正常运行
systemctl status slurm-web-agent
systemctl status slurm-web-gateway
```

---

## 9. 前端调试日志

前端已内置详细的控制台日志，用于诊断功能是否正常启用。

### 9.1 查看浏览器控制台

1. 打开浏览器开发者工具（F12 或右键 → 检查）
2. 切换到 "Console"（控制台）标签
3. 访问 Slurm-web 界面

### 9.2 功能启用状态检查

**集群列表加载时**，会显示每个集群的功能状态：
```
[GatewayAPI] 集群列表已加载:
[GatewayAPI]   集群 "cluster1": persistence=true, node_metrics=true
```

**访问作业历史页面时**，会显示：
```
[JobsHistory] 📊 作业历史页面已挂载
[JobsHistory] 功能说明: 此功能需要后端启用 persistence 配置
[JobsHistory] 检查项:
[JobsHistory]   1. /etc/slurm-web/agent.ini 中 [persistence] enabled = true
[JobsHistory]   2. PostgreSQL 数据库已安装并配置
[JobsHistory]   3. 数据库表 job_snapshots 已创建
[JobsHistory]   4. Agent 服务已重启
[JobsHistory] 开始获取作业历史数据...
[JobsHistory] 集群: cluster1
[JobsHistory] ✅ 成功获取数据
[JobsHistory] 返回记录数: 50
[JobsHistory] 总记录数: 1234
```

**访问节点详情页面时**，会显示：
```
[NodeView] 🖥️ 节点详情页面已挂载
[NodeView] 节点名称: node01
[NodeView] ✅ 节点实时监控功能已启用
[NodeView] 功能说明: 从 Prometheus 获取节点实时资源使用情况
[NodeView] 检查项:
[NodeView]   1. /etc/slurm-web/agent.ini 中 [node_metrics] enabled = true
[NodeView]   2. prometheus_host 配置正确
[NodeView]   3. Prometheus 中有对应节点的 node_exporter 数据
[NodeView]   4. Agent 服务已重启
[NodeView] 刷新间隔: 15秒
[NodeMetrics] 开始获取节点实时指标...
[NodeMetrics] ✅ 成功获取实时指标
[NodeMetrics] CPU使用率: 45.2 %
[NodeMetrics] 内存使用率: 67.8 %
[NodeMetrics] 磁盘使用率: 32.1 %
```

### 9.3 常见错误信息

**功能未启用**：
```
[JobsHistory] ❌ 获取数据失败: Error: Request failed with status code 404
```
→ 检查后端配置中 `[persistence] enabled = true`

**数据库连接失败**：
```
[JobsHistory] ❌ 获取数据失败: Error: Request failed with status code 500
```
→ 检查 PostgreSQL 是否运行，数据库连接配置是否正确

**Prometheus 连接失败**：
```
[NodeMetrics] ❌ 获取实时指标失败: Error: Request failed with status code 500
```
→ 检查 prometheus_host 配置，确认 Prometheus 可访问

---

## 10. API 验证

### 10.1 验证作业历史 API

```bash
# 获取 token（替换为实际用户名密码）
TOKEN=$(curl -s -X POST http://localhost:5012/login \
  -H "Content-Type: application/json" \
  -d '{"user":"admin","password":"xxx"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 查询历史作业
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5012/v$(slurm-web --version 2>&1 | head -1 | awk '{print $NF}')/jobs/history?page=1&page_size=10"
```

### 10.2 验证节点实时资源 API

```bash
# 查询节点实时资源（替换 node01 为实际节点名）
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5012/v.../node/node01/metrics"
```

### 10.3 验证数据库写入

```bash
# 等待约 60 秒后检查数据库
sudo -u postgres psql -d slurmweb -c \
  "SELECT COUNT(*), MIN(snapshot_time), MAX(snapshot_time) FROM job_snapshots;"
```

---

## 11. 日常维护

### 查看数据量

```bash
sudo -u postgres psql -d slurmweb -c "
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT job_id) as unique_jobs,
  MIN(snapshot_time) as oldest,
  MAX(snapshot_time) as newest,
  pg_size_pretty(pg_total_relation_size('job_snapshots')) as table_size
FROM job_snapshots;"
```

### 手动清理旧数据

```bash
# 清理 180 天前的数据（程序会自动执行，此命令用于手动触发）
sudo -u postgres psql -d slurmweb -c \
  "DELETE FROM job_snapshots WHERE snapshot_time < NOW() - INTERVAL '180 days';"
```

---

## 12. 回滚方案

如需回滚到原版本：

```bash
# 1. 停止服务
systemctl stop slurm-web-agent slurm-web-gateway

# 2. 还原后端文件
cp $SLURMWEB_PATH/apps/agent.py.bak    $SLURMWEB_PATH/apps/agent.py
cp $SLURMWEB_PATH/apps/gateway.py.bak  $SLURMWEB_PATH/apps/gateway.py
cp $SLURMWEB_PATH/views/agent.py.bak   $SLURMWEB_PATH/views/agent.py
cp $SLURMWEB_PATH/views/gateway.py.bak $SLURMWEB_PATH/views/gateway.py
cp $SLURMWEB_PATH/metrics/db.py.bak    $SLURMWEB_PATH/metrics/db.py
cp /usr/share/slurm-web/conf/agent.yml.bak /usr/share/slurm-web/conf/agent.yml

# 3. 还原前端
cp -r ${FRONTEND_PATH}.bak/* $FRONTEND_PATH/

# 4. 从配置文件中删除 [persistence] 和 [node_metrics] 节

# 5. 重启服务
systemctl start slurm-web-agent slurm-web-gateway
```

> PostgreSQL 数据库和数据不受回滚影响，可保留供后续重新启用。
