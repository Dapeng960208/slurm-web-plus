import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const sourcePath = resolve(process.cwd(), 'src/views/settings/SettingsAI.vue')
const source = readFileSync(sourcePath, 'utf8')

describe('SettingsAI view contract', () => {
  test('manages model configs through the new /ai config APIs', () => {
    expect(source).toContain('ai_configs')
    expect(source).toContain('create_ai_config')
    expect(source).toContain('update_ai_config')
    expect(source).toContain('delete_ai_config')
    expect(source).toContain('validate_ai_config')
  })

  test('renders multi-provider and secret-management capabilities', () => {
    expect(source).toContain('provider')
    expect(source).toContain('is_default')
    expect(source).toContain('secret_mask')
    expect(source).toContain('secret_configured')
  })

  test('does not use legacy assistant status-only flow', () => {
    expect(source).not.toContain('assistant_status')
    expect(source).not.toContain('Open chat')
    expect(source).not.toContain('AI Assistant')
  })
})
