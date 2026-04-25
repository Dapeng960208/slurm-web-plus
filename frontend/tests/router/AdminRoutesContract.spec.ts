import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const sourcePath = resolve(process.cwd(), 'src/router/index.ts')
const source = readFileSync(sourcePath, 'utf8')

describe('Admin router contract', () => {
  test('registers a cluster-scoped admin route', () => {
    expect(source).toContain("path: 'admin'")
    expect(source).toContain("name: 'admin-system'")
    expect(source).toContain("name: 'admin-ai'")
    expect(source).toContain("name: 'admin-access-control'")
    expect(source).toContain("name: 'admin-cache'")
    expect(source).toContain("name: 'admin-ldap-cache'")
  })

  test('uses admin permission resources instead of legacy settings resources for managed pages', () => {
    expect(source).toContain("'admin/ai'")
    expect(source).toContain("'admin/access-control'")
    expect(source).toContain("'admin/cache'")
    expect(source).toContain("'admin/ldap-cache'")
    expect(source).toContain("name: 'settings-ai'")
    expect(source).toContain("name: 'admin-ai'")
    expect(source).toContain("name: 'settings-cache'")
    expect(source).toContain("name: 'admin-cache'")
  })
})
