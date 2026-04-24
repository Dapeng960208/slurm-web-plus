# Access Control Test Plan

## Goal

Validate the custom-role access-control feature end to end.

- Existing `policy.ini` behavior must remain unchanged when the feature flag is off.
- When enabled, effective permissions must be the union of file policy and
  database custom roles.
- Backend APIs, gateway proxies, frontend settings pages, and migrations must
  all be covered.

## Backend Coverage

### `slurmweb/tests/views/test_agent_permissions.py`

- `/permissions` returns `roles`, `actions`, and `sources`
- anonymous and authenticated permission flows still behave correctly
- policy roles/actions and custom roles/actions are merged and deduplicated
- custom values are exposed under `sources.custom`

### `slurmweb/tests/views/test_agent.py`

- `/info` includes `access_control` and updated capabilities
- `/users/cache` refreshes `policy_roles` and `policy_actions`
- role management endpoints behave correctly
- user-role query and replacement endpoints behave correctly
- disabled access-control mode returns `501`

### `slurmweb/tests/views/test_gateway.py`

- `/api/clusters` includes extended cluster metadata
- gateway proxies `/permissions`
- gateway proxies `/access/roles`
- gateway proxies `/access/users`
- gateway forwards query strings for LDAP cache and access-user filters
- Windows-safe handling is used for tests that depend on `os.geteuid`

### `slurmweb/tests/apps/test_agent.py`

- agent startup enables access control only when database support is available
- agent startup degrades safely when access-control dependencies are missing
- agent startup refreshes policy snapshots for cached users when enabled
- startup refresh failures are logged without blocking startup

## Frontend Coverage

### `frontend/tests/composables/GatewayAPI.spec.ts`

- permission payload normalization into `policy/custom/merged`
- cluster capability normalization for `access_control`
- role CRUD endpoint paths
- access-user query and role-assignment endpoint paths
- LDAP cache compatibility and query-string forwarding

### `frontend/tests/components/settings/SettingsTabs.spec.ts`

- `Access Control` tab appears only when the current cluster exposes the feature

### `frontend/tests/views/settings/SettingsAccount.spec.ts`

- policy/custom/merged permissions render correctly

### `frontend/tests/views/settings/SettingsAccessControl.spec.ts`

- current-cluster role and user data load correctly
- manage mode supports role creation and user-role assignment save
- read-only mode shows the correct restrictions
- feature-disabled state is covered

## Manual Verification

### Feature Flag Off

1. Set `[persistence] access_control_enabled = no`.
2. Confirm existing policy-only access still works.
3. Confirm access-control management APIs return `501`.

### Feature Flag On

1. Run the database migration to head.
2. Set `[persistence] access_control_enabled = yes`.
3. Create a custom role.
4. Bind the role to a cached user.
5. Modify `policy.ini` for a cached user and restart the agent.
6. Confirm `users.policy_roles/policy_actions` are refreshed after restart.
7. Re-login as that user.
8. Confirm merged permissions contain both policy and database actions.

## Acceptance Cases

- Only `policy.ini` grants permission: access works.
- Only database custom roles grant permission: access works.
- Both sources grant permission: merged permissions are returned.
- Deleting a role removes related bindings by cascade.
- Updating user-role assignments takes effect on the next permission fetch.

## Commands

Backend:

```powershell
.venv\Scripts\python.exe -m pytest `
  slurmweb/tests/views/test_agent_permissions.py `
  slurmweb/tests/views/test_agent.py `
  slurmweb/tests/views/test_gateway.py `
  slurmweb/tests/apps/test_agent.py
```

Frontend:

```powershell
npm --prefix frontend run test:unit -- `
  tests/composables/GatewayAPI.spec.ts `
  tests/components/settings/SettingsTabs.spec.ts `
  tests/views/settings/SettingsAccount.spec.ts `
  tests/views/settings/SettingsAccessControl.spec.ts --run
```
