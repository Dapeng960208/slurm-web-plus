import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const sourcePath = resolve(process.cwd(), 'src/composables/GatewayAPI.ts')
const source = readFileSync(sourcePath, 'utf8')

describe('GatewayAPI admin contract', () => {
  test('maps legacy admin actions to admin permission resources', () => {
    expect(source).toContain("'cache-view'")
    expect(source).toContain('admin/cache:view:*')
    expect(source).toContain('admin/ldap-cache:view:*')
    expect(source).toContain("'cache-reset'")
    expect(source).toContain('admin/cache:edit:*')
    expect(source).not.toContain("'edit-own-jobs'")
    expect(source).not.toContain("'roles-view'")
    expect(source).not.toContain("'roles-manage'")
    expect(source).not.toContain("'manage-ai'")
    expect(source).toContain("'admin-manage'")
    expect(source).toContain('*:*:*')
    expect(source).not.toContain('settings/cache:view:*')
    expect(source).not.toContain('settings/access-control:view:*')
    expect(source).not.toContain('settings/ai:edit:*')
  })

  test('declares analysis diag and ping endpoints and avoids bulk operation helpers', () => {
    expect(source).toContain('/agents/${cluster}/analysis/diag')
    expect(source).toContain('/agents/${cluster}/analysis/ping')
    expect(source).not.toContain('/agents/${cluster}/admin/system/')
    expect(source).not.toContain('function admin_licenses')
    expect(source).not.toContain('function admin_reconfigure')
    expect(source).toContain('/agents/${cluster}/job/${jobId}/update')
    expect(source).toContain('/agents/${cluster}/job/${jobId}/cancel')
    expect(source).toContain('/agents/${cluster}/node/${encodedNodeName}/update')
    expect(source).toContain('/agents/${cluster}/node/${encodedNodeName}/delete')
    expect(source).toContain('/agents/${cluster}/reservation/${encodedReservation}/delete')
    expect(source).toContain('/agents/${cluster}/account/${encodeURIComponent(accountName)}/delete')
    expect(source).toContain('/agents/${cluster}/user/${encodeURIComponent(username)}/delete')
    expect(source).toContain('/agents/${cluster}/qos/${encodeURIComponent(qosName)}/delete')
    expect(source).not.toContain('cancel_jobs')
    expect(source).not.toContain('bulk')
  })
})
