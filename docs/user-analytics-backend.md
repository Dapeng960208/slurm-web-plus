# User Metrics Backend

This feature adds optional per-user metrics on top of PostgreSQL-backed job
history persistence.

## Configuration

Add the following section to `agent.ini` only when the feature should be
enabled:

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

[user_metrics]
enabled = yes
aggregation_interval = 3600
# tool_mapping_file = /etc/slurm-web/user-tools.yml
```

Notes:

- `user_metrics.enabled = yes` requires `[database]`, `[metrics]`, and job
  persistence.
- The agent still requires `alembic upgrade head` before restart.

## Data Model

Migration `20260424_0004_user_tool_daily_stats.py` creates
`user_tool_daily_stats` for current-day per-user, per-tool rollups.

The agent also reads `job_snapshots` to:

- export per-user submissions in the last minute to Prometheus
- build hour/day/week activity responses for the user detail page

## API

Agent:

- `GET /v<version>/user/<username>/metrics/history?range=hour|day|week`
- `GET /v<version>/user/<username>/activity/summary`
- `GET /v<version>/metrics/users` when both `[metrics]` and
  `[user_metrics]` and database-backed persistence are enabled

Gateway:

- `GET /api/agents/<cluster>/user/<username>/metrics/history?range=hour|day|week`
- `GET /api/agents/<cluster>/user/<username>/activity/summary`

Capability gate:

- `GET /info` returns top-level `user_metrics`
- `GET /api/clusters` forwards the same top-level `user_metrics` boolean

When disabled, the user metrics APIs return HTTP `501` with
`User metrics is disabled`.

## Verification

1. Run `alembic current`.
2. Run `alembic upgrade head`.
3. Verify table `user_tool_daily_stats` exists.
4. Restart the agent.
5. Check `/info` and confirm `user_metrics` is `true`.
6. Query `/api/agents/<cluster>/user/<username>/activity/summary`.
7. Query `/api/agents/<cluster>/user/<username>/metrics/history?range=day`.
8. If Prometheus user metrics are enabled, confirm `/metrics` contains
   `slurmweb_user_submissions_last_minute`.
