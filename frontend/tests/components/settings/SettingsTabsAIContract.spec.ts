import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const sourcePath = resolve(process.cwd(), 'src/components/settings/SettingsTabs.vue')
const source = readFileSync(sourcePath, 'utf8')

describe('SettingsTabs admin migration contract', () => {
  test('does not register admin-managed tabs in the settings workspace', () => {
    expect(source).not.toContain("{ name: 'AI', href: 'settings-ai' }")
    expect(source).not.toContain("{ name: 'Access Control', href: 'settings-access-control' }")
    expect(source).not.toContain("{ name: 'Cache', href: 'settings-cache' }")
    expect(source).not.toContain("{ name: 'LDAP Cache', href: 'settings-ldap-cache' }")
  })

  test('does not use legacy settings permission resources for admin-managed tabs', () => {
    expect(source).not.toContain("'settings/ai'")
    expect(source).not.toContain("'settings/access-control'")
    expect(source).not.toContain("'settings/cache'")
    expect(source).not.toContain("'settings/ldap-cache'")
  })
})
