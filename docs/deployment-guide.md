# Slurm-web 新增数据库功能生产部署指南

本文档面向生产环境，说明如何将“作业历史持久化 + LDAP 用户缓存”这一新增功能安全部署到服务器。

当前假设生产环境还没有创建 PostgreSQL 数据库，因此本文档按“首次上线数据库能力”的方式编写。

## 1. 适用范围

适用于以下场景：

- 现有 Slurm-web 已在生产运行
- 本次上线新增 PostgreSQL、Alembic 迁移、作业历史持久化、用户缓存
- 希望即使数据库不可用，也不影响 agent 其他非数据库功能

本文默认：

- `gateway` 不直连数据库
- 数据库配置只在 `agent.ini` 中启用
- 生产库结构由 Alembic 管理
- agent 启动时不会自动执行 `alembic upgrade head`

本次上线涉及的配置段边界如下：

- `[database]`：新增，用于启用 PostgreSQL 连接和 Alembic 自动迁移
- `[persistence]`：新增，用于启用作业历史持久化写入
- `[node_metrics]`：新增，用于启用节点实时资源监控
- `[metrics]`：已有功能，用于 Slurm-web 指标导出和 Prometheus 查询，不属于本次数据库迁移功能的必需项

## 2. 上线前准备

上线前建议先确认以下事项：

- 已评估本次发布窗口，建议在低峰期执行
- 已备份生产环境的 `agent.ini`、`gateway.ini`、前端静态文件和当前发布包
- 已准备 PostgreSQL 实例
- 已准备回滚方案
- 已在测试或预发布环境完成一次完整演练

建议记录当前版本：

```bash
slurm-web --version
systemctl status slurm-web-agent --no-pager
systemctl status slurm-web-gateway --no-pager
```

## 3. 生产发布总流程

推荐顺序如下：

1. 备份当前应用和配置
2. 安装新增依赖
3. 创建 PostgreSQL 数据库和账号
4. 部署新版本代码
5. 更新 `agent.ini` 中的数据库与持久化配置
6. 手工执行一次 `alembic upgrade head`
7. 重启 `slurm-web-agent`
8. 验证数据库迁移和历史功能
9. 重启 `slurm-web-gateway`
10. 验证登录、页面和日志

agent 启动时不会自动执行迁移，因此生产环境需要在重启前手工执行一次 `alembic upgrade head`。

如果你当前的生产环境“还没有数据库、也没有任何历史表”，推荐按下面的最短路径执行：

1. 安装并启动 PostgreSQL
2. 创建 `slurmweb` 数据库和数据库账号
3. 部署包含 `alembic.ini`、`slurmweb/alembic/`、`slurmweb/models/` 的新版本
4. 在 `agent.ini` 中配置 `[database]`
5. 先保持 `[persistence] enabled = no`
6. 手工执行 `alembic upgrade head`
7. 重启 `slurm-web-agent`
8. 验证 `users`、`job_snapshots` 等表已创建
9. 验证 LDAP 登录后 `users` 表能缓存用户
10. 最后再开启 `[persistence] enabled = yes`

## 4. 备份

至少备份以下内容：

```bash
BACKUP_DIR=/root/slurm-web-backup-$(date +%F-%H%M%S)
mkdir -p "$BACKUP_DIR"

cp -a /etc/slurm-web "$BACKUP_DIR"/etc-slurm-web
cp -a /usr/share/slurm-web "$BACKUP_DIR"/usr-share-slurm-web
cp -a /usr/lib/python*/site-packages/slurmweb "$BACKUP_DIR"/slurmweb-python || true
```

如果已存在 PostgreSQL 数据库，建议同时备份：

```bash
sudo -u postgres pg_dump -Fc slurmweb > "$BACKUP_DIR"/slurmweb.dump
```

## 5. 安装新增依赖

如果是 RPM/系统包部署，确认目标环境已经具备 PostgreSQL 客户端库和 Python 依赖。

最少需要：

```bash
dnf install -y postgresql-server postgresql-contrib
python -m pip install alembic sqlalchemy psycopg2-binary
```

如果你们是通过内部制品或虚拟环境部署，请确保以下 Python 依赖已进入最终运行环境：

- `alembic`
- `sqlalchemy`
- `psycopg2-binary`

## 6. 初始化 PostgreSQL

如果生产上还没有 PostgreSQL：

```bash
postgresql-setup --initdb
systemctl enable --now postgresql
```

创建数据库和账号：

```bash
sudo -u postgres psql -c "CREATE USER slurmweb WITH PASSWORD 'REPLACE_ME';"
sudo -u postgres psql -c "CREATE DATABASE slurmweb OWNER slurmweb;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE slurmweb TO slurmweb;"
```

如果启用了密码认证，确认 `pg_hba.conf` 已允许本机访问：

```bash
local   slurmweb   slurmweb               md5
host    slurmweb   slurmweb   127.0.0.1/32   md5
host    slurmweb   slurmweb   ::1/128        md5
```

修改后重载：

```bash
systemctl reload postgresql
```

验证连接：

```bash
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "SELECT 1;"
```

## 7. 部署新版本代码

将新版本部署到生产服务器后，确认以下文件已存在：

- `alembic.ini`
- `slurmweb/alembic/env.py`
- `slurmweb/alembic/script.py.mako`
- `slurmweb/alembic/versions/*.py`
- `slurmweb/models/db.py`
- `slurmweb/models/modes.py`

验证 Alembic 文件是否完整：

```bash
find /usr -path "*slurmweb/alembic*" | sort
```

## 8. 配置 agent.ini

数据库功能只在 `agent.ini` 启用，不需要在 `gateway.ini` 添加数据库配置。

示例：

```ini
[database]
enabled = yes
host = 127.0.0.1
port = 5432
database = slurmweb
user = slurmweb
password = REPLACE_ME

[persistence]
enabled = yes
snapshot_interval = 60
retention_days = 180

[node_metrics]
enabled = no
prometheus_host = http://127.0.0.1:9090
node_exporter_job = node
node_hostname_label = hostname

[metrics]
enabled = no
restrict =
  127.0.0.0/24
  ::1/128
host = http://127.0.0.1:9090
job = slurm
```

说明：

- `[database]` 是本次新增配置段，负责 PostgreSQL 连接、Alembic 迁移、用户缓存前置能力
- `[database] enabled = no` 时，agent 不会启用本地用户缓存
- `[persistence]` 是本次新增配置段，依赖 `[database]`，负责将作业历史写入 PostgreSQL
- `[persistence] enabled = no` 时，即使数据库可用，也不会写入作业历史
- `[node_metrics]` 是本次新增配置段，负责从 Prometheus 查询节点实时资源
- `[metrics]` 不是本次新增数据库能力的一部分，它是已有的指标导出/查询功能；数据库迁移和作业历史上线不要求必须启用它
- 即使数据库表尚未准备好，也不阻塞 agent 其他非数据库功能启动

建议生产首发时先采用下面的灰度配置：

```ini
[database]
enabled = yes
host = 127.0.0.1
port = 5432
database = slurmweb
user = slurmweb
password = REPLACE_ME

[persistence]
enabled = no

[node_metrics]
enabled = no
```

先确认数据库连接、迁移、LDAP 用户缓存都正常，再单独把 `[persistence] enabled` 改成 `yes`。

## 9. Alembic 生产迁移

### 9.1 生产环境执行方式

在生产环境只需要执行：

```bash
alembic upgrade head
```

该命令默认会读取 `/etc/slurm-web/agent.ini` 中 `[database]` 的连接参数，因此生产环境不需要再把数据库密码重复写入 `alembic.ini`。
如果你的配置文件不在默认位置，可先设置：

```bash
export SLURMWEB_AGENT_INI=/path/to/agent.ini
export SLURMWEB_AGENT_SETTINGS_DEFINITION=/path/to/agent.yml
alembic upgrade head
```

不要在生产环境执行以下开发态命令：

```bash
alembic init ...
alembic revision --autogenerate ...
```

这些命令只用于开发阶段生成或更新迁移脚本。生产环境只负责执行已经随发布包带上的迁移。

对于“生产环境目前还没有数据库表”的首次部署场景，`alembic upgrade head` 会直接从空库创建完整 schema，不需要手工执行任何建表 SQL。

### 9.2 迁移前检查

```bash
alembic current
alembic history
```

### 9.3 执行迁移

```bash
alembic upgrade head
```

### 9.4 迁移后验证

```bash
alembic current
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "\dt"
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "\d users"
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "\d job_snapshots"
```

首次建库时，至少应看到：

- `users`
- `job_snapshots`
- `alembic_version`

## 10. 重启顺序

推荐先重启 agent，再重启 gateway：

```bash
systemctl restart slurm-web-agent
systemctl status slurm-web-agent --no-pager

systemctl restart slurm-web-gateway
systemctl status slurm-web-gateway --no-pager
```

原因：

- 应先保证数据库迁移已经手工执行成功
- gateway 登录成功后会通知 agent 缓存 LDAP 用户
- 若 gateway 先启动、agent 侧表尚未准备好，用户登录仍然成功，但 agent 侧缓存可能会打 warning

## 11. 生产验证清单

### 11.1 应用状态

```bash
journalctl -u slurm-web-agent -n 100 --no-pager
journalctl -u slurm-web-gateway -n 100 --no-pager
```

关注以下日志：

- 数据库迁移成功
- Job history persistence enabled
- 用户缓存相关 warning 是否持续出现

### 11.2 数据库对象

```bash
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "SELECT COUNT(*) FROM users;"
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "SELECT COUNT(*) FROM job_snapshots;"
```

### 11.3 登录验证

验证一次正常 LDAP 登录，检查 `users` 表是否有缓存记录：

```bash
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c \
  "SELECT id, username, fullname, ldap_synced_at FROM users ORDER BY updated_at DESC LIMIT 20;"
```

### 11.4 作业历史验证

等待一个采集周期后检查：

```bash
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c \
  "SELECT job_id, user_id, job_state, submit_time, last_seen FROM job_snapshots ORDER BY last_seen DESC LIMIT 20;"
```

联表检查：

```bash
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "
SELECT
  js.job_id,
  u.username,
  js.job_state,
  js.submit_time,
  js.last_seen
FROM job_snapshots js
LEFT JOIN users u ON u.id = js.user_id
ORDER BY js.last_seen DESC
LIMIT 20;"
```

## 12. 失败场景说明

### 12.1 数据库不可用

现象：

- `alembic upgrade head` 失败
- agent 日志出现数据库迁移 warning

影响：

- 作业历史不可用
- LDAP 用户缓存不可用
- agent 其他非数据库接口仍应保持可用

这意味着即使生产上暂时不启用 `[database]`，或者数据库在首发时仍未准备好，agent 其他功能也不应因此停服。

### 12.2 只启用 database，未启用 persistence

现象：

- `users` 表可正常缓存登录用户
- `job_snapshots` 不会持续写入作业历史

适合：

- 先灰度数据库连接和迁移，再单独开启历史持久化

### 12.3 gateway 早于 agent 完成迁移

现象：

- 用户可正常登录
- gateway 或 agent 可能出现一次用户缓存失败 warning

影响：

- 不影响登录
- agent 完成迁移后后续登录可恢复缓存

## 13. 回滚方案

### 13.1 应用回滚

```bash
systemctl stop slurm-web-gateway slurm-web-agent
```

恢复应用文件与配置备份后：

```bash
systemctl start slurm-web-agent
systemctl start slurm-web-gateway
```

### 13.2 数据库回滚

如果只是应用回滚，不一定要立即回滚数据库。

如果确需回滚数据库 schema：

```bash
alembic downgrade -1
```

或回滚到指定 revision：

```bash
alembic downgrade <revision_id>
```

生产环境执行 downgrade 前，建议先做数据库备份。

### 13.3 最保守回滚

如果需要快速恢复业务：

1. 将 `agent.ini` 中 `[database] enabled = no`
2. 将 `[persistence] enabled = no`
3. 重启 agent

这样可直接关闭所有数据库相关能力，同时保留 agent/gateway 其他功能继续服务。

## 14. 开发与生产职责边界

开发阶段：

- 修改 `slurmweb/models/modes.py`
- 执行 `alembic revision --autogenerate -m "xxx"`
- 提交生成的 migration 文件

生产阶段：

- 部署发布包中已存在的 migration 文件
- 只执行 `alembic upgrade head`

## 15. 推荐上线策略

建议分两步上线：

### 第一步：只启用数据库

```ini
[database]
enabled = yes

[persistence]
enabled = no
```

目的：

- 验证 PostgreSQL 连接
- 验证 Alembic 迁移
- 验证登录后用户缓存

### 第二步：启用持久化

```ini
[persistence]
enabled = yes
```

目的：

- 开始写入作业历史
- 观察数据库容量、写入性能和日志

这种方式更适合生产首发。
## 16. 历史详情字段升级补充

如果本次发布包含历史作业详情补全功能，还需要执行并验证 `20260420_0002` 迁移。该迁移会在 `job_snapshots` 上新增以下字段：

- `eligible_time`
- `last_sched_evaluation_time`
- `tres_requested`
- `tres_allocated`
- `used_memory_gb`

推荐生产升级顺序：

1. 备份数据库。
2. 停止 `slurm-web-agent`，或先将 `[persistence] enabled = no`。
3. 执行 `alembic current`。
4. 执行 `alembic upgrade head`。
5. 执行下面的 SQL 验证新增字段。
6. 重启 `slurm-web-agent`。
7. 验证 `/jobs/history/<id>` 返回 JSON 且包含新增字段。
8. 最后再恢复 `[persistence] enabled = yes`。

验证 SQL：

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

如果需要回滚本次 schema 变更：

```bash
alembic downgrade 20260420_0001
```

回滚前同样先停止 agent 或关闭 `[persistence]`。该回滚会删除本次新增字段，因此不建议在新代码仍在线时单独回滚数据库。
