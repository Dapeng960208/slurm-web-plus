# Deployment Guide

## Scope

This guide covers rollout of the access-control feature set:

- database migration
- access-control feature flag
- agent and gateway API changes
- frontend settings page behavior

## Rollout Order

1. Back up the database and deployment configuration.
2. Deploy the new code to agent and gateway hosts.
3. Apply Alembic migrations on each agent-side database.
4. Restart `slurm-web-agent`.
5. Verify the agent APIs.
6. Restart `slurm-web-gateway`.
7. Verify frontend behavior.

## Required Configuration

Example agent settings:

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
access_control_enabled = yes
```

Notes:

- `access_control_enabled` defaults to `no`
- when disabled, current `policy.ini` behavior remains unchanged
- when enabled, effective permissions are the union of:
  - file policy actions
  - database custom-role actions
- when enabled, restarting `slurm-web-agent` refreshes `policy.ini` snapshots
  for users already present in `users`

## Required Migration

Run from the repository root on the agent host:

```powershell
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic upgrade head
```

This release depends on:
`slurmweb/alembic/versions/20260424_0005_access_control_roles.py`

## Post-Deployment Verification

### Agent

- `GET /info` includes:
  - `access_control`
  - `capabilities.access_control`
- `GET /v<version>/permissions` returns:
  - `roles`
  - `actions`
  - `sources.policy`
  - `sources.custom`
- `GET /v<version>/access/roles` works for users with `roles-view`
- `PUT /v<version>/access/users/<username>/roles` works for users with
  `roles-manage`
- after `policy.ini` changes and agent restart, cached users in `users` get
  refreshed `policy_roles/policy_actions`

### Gateway

- `GET /api/clusters` includes cluster-level `access_control`
- `GET /api/agents/<cluster>/permissions` proxies successfully
- `GET/POST/PATCH/DELETE /api/agents/<cluster>/access/roles` proxy successfully
- `GET/PUT /api/agents/<cluster>/access/users/<username>/roles` proxy
  successfully

### Frontend

- `Access Control` tab appears only for clusters with access-control capability
- the page manages the current cluster only
- users with `roles-view` can inspect
- users with `roles-manage` can edit roles and assignments
- `SettingsAccount` shows policy/custom/merged permissions

## Backend Test Command

Use the required backend interpreter:

```powershell
.venv\Scripts\python.exe -m pytest `
  slurmweb/tests/views/test_agent_permissions.py `
  slurmweb/tests/views/test_agent.py `
  slurmweb/tests/views/test_gateway.py `
  slurmweb/tests/apps/test_agent.py
```

## Rollback

If you need to disable the feature quickly:

1. Set `[persistence] access_control_enabled = no`
2. Restart `slurm-web-agent`

If schema rollback is also required:

```powershell
.venv\Scripts\python.exe -m alembic downgrade -1
```

Take a backup first. Rolling back removes custom-role tables and permission
snapshot columns.
