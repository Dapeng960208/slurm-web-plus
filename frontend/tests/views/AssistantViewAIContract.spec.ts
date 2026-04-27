import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const sourcePath = resolve(process.cwd(), 'src/views/AssistantView.vue')
const source = readFileSync(sourcePath, 'utf8')

describe('AI chat view contract', () => {
  test('uses the cluster AI route semantics', () => {
    expect(source).toContain('menu-entry="ai"')
    expect(source).not.toContain('menu-entry="assistant"')
    expect(source).not.toContain('AI Assistant')
  })

  test('loads model configs and conversation data from the new AI APIs', () => {
    expect(source).toContain('ai_configs')
    expect(source).toContain('ai_conversations')
    expect(source).toContain('ai_conversation')
    expect(source).toContain('stream_ai_chat')
  })

  test('renders model selection and SSE event handling affordances', () => {
    expect(source).toContain('model_config_id')
    expect(source).toContain('onToolStart')
    expect(source).toContain('onToolEnd')
    expect(source).toContain('interface_key')
    expect(source).toContain('status_code')
    expect(source).toContain('onContent')
    expect(source).toContain('onComplete')
  })
})
