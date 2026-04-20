# Alembic 迁移说明

本文档说明数据库 schema 的开发方式、发布方式和运行时行为。

本文特别区分两类场景：

- 开发环境：可以执行 `alembic init`、`alembic revision --autogenerate`
- 生产环境：只执行已经随版本发布的迁移，即 `alembic upgrade head`

如果生产环境当前还没有创建数据库或表，也仍然只执行 `alembic upgrade head`，不要手工写 SQL 建表。

## 1. 目录结构

- `alembic.ini`
- `slurmweb/alembic/env.py`
- `slurmweb/alembic/script.py.mako`
- `slurmweb/alembic/versions/`
- `slurmweb/models/db.py`
- `slurmweb/models/modes.py`

其中：

- `slurmweb/models/modes.py` 是 Alembic 元数据来源
- `slurmweb/models/db.py` 负责构造 SQLAlchemy URL 和 psycopg2 连接参数

## 2. 开发阶段命令

初始化标准 Alembic 目录：

```bash
alembic init slurmweb/alembic
```

根据模型自动生成迁移：

```bash
alembic revision --autogenerate -m "your message"
```

查看历史：

```bash
alembic history
```

查看当前版本：

```bash
alembic current
```

执行升级：

```bash
alembic upgrade head
```

执行回滚：

```bash
alembic downgrade -1
```

## 3. 生产阶段命令

生产环境只执行：

```bash
alembic upgrade head
```

默认情况下，Alembic CLI 会优先读取 `agent.ini` 中 `[database]` 的连接信息，而不是依赖 `alembic.ini` 里的占位 URL。
默认路径如下：

- 配置文件：`/etc/slurm-web/agent.ini`
- 配置定义：`/usr/share/slurm-web/conf/agent.yml`

如需覆盖默认路径，可在执行前设置：

```bash
export SLURMWEB_AGENT_INI=/path/to/agent.ini
export SLURMWEB_AGENT_SETTINGS_DEFINITION=/path/to/agent.yml
alembic upgrade head
```

不要在生产环境执行：

- `alembic init`
- `alembic revision --autogenerate`

这些命令应在开发环境完成，生成后的 revision 文件随发布包一起发布。

对于首次上线数据库功能的生产环境，建议顺序为：

1. 在 PostgreSQL 中创建数据库和账号
2. 部署带有 `alembic.ini` 与 `slurmweb/alembic/versions/` 的版本
3. 在 `agent.ini` 中启用 `[database]`
4. 执行 `alembic upgrade head`
5. 再启动或重启 agent

## 4. 运行时行为

当 agent 启动时：

1. 读取 `agent.ini`
2. 检查 `[database] enabled`
3. 若启用，则初始化本地 `users` 表访问能力
4. 若同时 `[persistence] enabled = yes`，则启动作业历史写入线程

注意：

- agent 启动时不会自动执行 `alembic upgrade head`
- 数据库迁移需要由运维或部署流程显式执行
- 若未先执行迁移，作业历史线程可能启动，但相关数据库操作会在运行时报错

如果数据库未启用或数据库访问初始化失败：

- 不影响 agent 其他功能
- 作业历史接口不可用
- 用户缓存接口不可用

配置段边界如下：

- `[database]`：新增，负责 PostgreSQL 连接和迁移
- `[persistence]`：新增，负责作业历史写入
- `[node_metrics]`：新增，负责节点实时资源采集
- `[metrics]`：已有 Prometheus 指标功能，不属于数据库迁移的一部分

## 5. 推荐发布流程

1. 修改 `slurmweb/models/modes.py`
2. 生成新的 revision
3. 本地执行 `alembic upgrade head`
4. 在测试环境验证
5. 将 migration 文件随版本一起发布
6. 生产环境执行 `alembic upgrade head`

## 6. 验证

```bash
alembic current
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "\dt"
```

检查核心表：

```bash
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "\d users"
psql -h 127.0.0.1 -U slurmweb -d slurmweb -c "\d job_snapshots"
```

空库首次执行成功后，通常至少应看到：

- `alembic_version`
- `users`
- `job_snapshots`
