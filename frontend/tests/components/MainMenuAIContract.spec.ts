import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const sourcePath = resolve(process.cwd(), 'src/components/MainMenu.vue')
const source = readFileSync(sourcePath, 'utf8')

describe('MainMenu AI contract', () => {
  test('binds AI menu entry to the new route and permission gate', () => {
    expect(source).toContain("name: 'AI'")
    expect(source).toContain("route: 'ai'")
    expect(source).toContain("permission: 'view-ai'")
    expect(source).toContain("feature: 'ai'")
  })

  test('does not rely on legacy assistant navigation flags', () => {
    expect(source).not.toContain("route: 'assistant'")
    expect(source).not.toContain("feature: 'ai_assistant'")
    expect(source).not.toContain('AI Assistant')
  })
})
