# Access Control Development Requirements

## Scope

This feature adds database-backed custom roles on top of the existing
policy-based RBAC flow.

- `users` remains the anchor table for cached LDAP users.
- `roles` stores custom role definitions.
- `user_roles` stores user-to-role bindings.
- The frontend `Access Control` page is scoped to the current cluster only.
- Effective permissions are:
  `policy.ini derived actions UNION database custom-role actions`
  when `[persistence] access_control_enabled = yes`.

## Data Model

### `users`

Add:

- `policy_roles JSONB NOT NULL DEFAULT []`
- `policy_actions JSONB NOT NULL DEFAULT []`
- `permission_synced_at TIMESTAMPTZ NULL`

### `roles`

Add table with:

- `id`
- `name` unique
- `description`
- `actions JSONB`
- `created_at`
- `updated_at`

### `user_roles`

Add table with:

- `user_id`
- `role_id`
- `created_at`
- primary key `(user_id, role_id)`
- foreign keys with `ON DELETE CASCADE`

## Configuration and Policy

- Add `[persistence] access_control_enabled = yes|no`
- Default value: `no`
- Add policy actions:
  - `roles-view`
  - `roles-manage`
- Keep default vendor/site `policy.ini` behavior unchanged unless the feature
  flag is enabled and operators configure extra permissions

## Backend Requirements

### Permission resolution

- Keep file policy as the base source through existing RBAC policy handling.
- When access control is enabled and the database is available:
  - load custom roles from `user_roles -> roles.actions`
  - merge file-policy and custom-role actions by set union
  - deduplicate actions and roles

### `/permissions`

Return:

- `roles`
- `actions`
- `sources.policy.roles`
- `sources.policy.actions`
- `sources.custom.roles`
- `sources.custom.actions`

### `/users/cache`

When caching the authenticated user:

- refresh LDAP user basics
- refresh `policy_roles`
- refresh `policy_actions`
- refresh `permission_synced_at`

### Agent startup policy refresh

- When `[persistence] access_control_enabled = yes` and database support is
  available, agent startup refreshes policy snapshots for users already present
  in `users`
- refresh uses cached `username`, `fullname`, and `groups` only
- refresh updates:
  - `policy_roles`
  - `policy_actions`
  - `permission_synced_at`
- refresh does not:
  - create new users
  - query LDAP
  - modify `user_roles`
- per-user failures are logged and do not block startup

### Agent APIs

Add:

- `GET /v{version}/access/roles`
- `POST /v{version}/access/roles`
- `PATCH /v{version}/access/roles/<id>`
- `DELETE /v{version}/access/roles/<id>`
- `GET /v{version}/access/users`
- `GET /v{version}/access/users/<username>/roles`
- `PUT /v{version}/access/users/<username>/roles`

Authorization:

- read endpoints require `roles-view`
- write endpoints require `roles-manage`
- when feature disabled, endpoints return `501`

### Gateway APIs

Proxy:

- `GET /api/agents/<cluster>/permissions`
- `GET/POST /api/agents/<cluster>/access/roles`
- `PATCH/DELETE /api/agents/<cluster>/access/roles/<id>`
- `GET /api/agents/<cluster>/access/users`
- `GET/PUT /api/agents/<cluster>/access/users/<username>/roles`

Expose `access_control` in:

- agent `/info`
- gateway `/api/clusters`
- frontend cluster capability data

## Frontend Requirements

- Add `Access Control` settings tab only for clusters with access-control
  capability
- Do not aggregate by cluster
- Provide:
  - custom role list
  - create/edit/delete role form
  - cached-user search/list
  - user-role assignment editor
- Permission states:
  - no `roles-view`: deny message
  - `roles-view` only: read-only mode
  - `roles-manage`: editing enabled
- `SettingsAccount` must display policy/custom/merged permission views

## Migration Requirements

- Add Alembic revision `20260424_0005_access_control_roles.py`
- Migration must be idempotent against partially updated databases
- `downgrade()` must remove the fields and tables introduced here

## Delivery

- backend implementation
- frontend implementation
- migration script
- development requirements document
- test plan document
- automated backend and frontend regression coverage
