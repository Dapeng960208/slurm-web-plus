import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const sourcePath = resolve(process.cwd(), 'src/composables/GatewayAPI.ts')
const source = readFileSync(sourcePath, 'utf8')

describe('GatewayAPI AI contract', () => {
  test('exposes /ai/* gateway methods instead of legacy assistant methods', () => {
    expect(source).toContain('async function ai_configs')
    expect(source).toContain('async function create_ai_config')
    expect(source).toContain('async function update_ai_config')
    expect(source).toContain('async function delete_ai_config')
    expect(source).toContain('async function validate_ai_config')
    expect(source).toContain('async function ai_conversations')
    expect(source).toContain('async function ai_conversation')
    expect(source).toContain('function stream_ai_chat')
    expect(source).not.toContain('/assistant')
  })

  test('targets the new AI gateway routes', () => {
    expect(source).toContain('/agents/${cluster}/ai/configs')
    expect(source).toContain('/agents/${cluster}/ai/chat/stream')
    expect(source).toContain('/agents/${cluster}/ai/conversations')
  })

  test('uses fetchEventSource for SSE chat streaming', () => {
    expect(source).toContain('fetchEventSource')
    expect(source).toContain('text/event-stream')
    expect(source).toContain('tool_start')
    expect(source).toContain('tool_end')
    expect(source).toContain('complete')
    expect(source).toContain('done')
  })

  test('reads new cluster AI capability shape', () => {
    expect(source).toContain('normalizeClusterAICapability')
    expect(source).toContain('capabilities?.ai')
    expect(source).toContain('cluster.ai')
  })
})
