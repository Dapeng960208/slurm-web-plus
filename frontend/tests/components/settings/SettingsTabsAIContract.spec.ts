import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const sourcePath = resolve(process.cwd(), 'src/components/settings/SettingsTabs.vue')
const source = readFileSync(sourcePath, 'utf8')

describe('SettingsTabs AI contract', () => {
  test('registers the AI settings tab with the new label and route', () => {
    expect(source).toContain("{ name: 'AI', href: 'settings-ai' }")
  })

  test('uses current cluster AI capability instead of legacy assistant flag', () => {
    expect(source).toContain('hasClusterAIAssistant')
    expect(source).not.toContain('AI Assistant')
    expect(source).not.toContain('ai_assistant')
  })
})
