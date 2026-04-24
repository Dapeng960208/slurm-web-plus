# Database Migrations

## Scope

This document describes how to apply and roll back Slurm-web database schema
changes, including the access-control migration added in
`slurmweb/alembic/versions/20260424_0005_access_control_roles.py`.

Gateway does not connect to PostgreSQL directly. Database migrations apply to
agent-side databases only.

## Recommended Sequence

1. Deploy the new application code and Alembic files.
2. Stop `slurm-web-agent` before running schema changes.
3. Confirm `[database] enabled = yes` is configured.
4. Keep `[persistence] enabled = no` during the initial schema upgrade if job
   history is not already running.
5. Enable `[persistence] access_control_enabled = yes` only after the migration
   files are present and the schema upgrade has completed successfully.
6. Run:

```powershell
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic current
```

7. Start `slurm-web-agent`.
8. Verify the APIs and application behavior.
9. Restart `slurm-web-gateway` so the frontend sees fresh capabilities.

## 20260424_0005 Access-Control Migration

Revision: `20260424_0005`

This migration:

- adds `users.policy_roles`
- adds `users.policy_actions`
- adds `users.permission_synced_at`
- creates `roles`
- creates `user_roles`
- creates index `idx_user_roles_role_id`

The migration is written to be idempotent by checking for existing columns,
tables, constraints, and indexes before creating them.

## Verification

Check the active revision:

```powershell
.venv\Scripts\python.exe -m alembic current
```

Example SQL checks:

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name IN ('policy_roles', 'policy_actions', 'permission_synced_at')
ORDER BY column_name;

SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('roles', 'user_roles')
ORDER BY table_name;
```

Functional checks:

- login still works with policy-only access
- `GET /v<version>/permissions` returns `sources.policy` and `sources.custom`
- role creation and user-role binding work when the feature flag is enabled

## Rollback

Stop `slurm-web-agent` first, then run:

```powershell
.venv\Scripts\python.exe -m alembic downgrade -1
```

To roll back to a specific revision:

```powershell
.venv\Scripts\python.exe -m alembic downgrade 20260424_0004
```

Rollback impact for `20260424_0005`:

- drops `user_roles`
- drops `roles`
- drops `users.permission_synced_at`
- drops `users.policy_actions`
- drops `users.policy_roles`

## Risk Notes

- Rolling back after operators start using custom roles removes bindings and
  permission snapshots.
- Rolling back schema without rolling back application code is unsafe.
- Take a database backup before downgrade in production.
