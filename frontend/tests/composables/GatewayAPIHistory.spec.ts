import { describe, expect, test } from 'vitest'
import { splitJobHistoryState } from '@/composables/GatewayAPI'

describe('splitJobHistoryState', () => {
  test('splits comma-separated history states into badge tokens', () => {
    expect(splitJobHistoryState('RUNNING,COMPLETING')).toStrictEqual(['RUNNING', 'COMPLETING'])
  })

  test('falls back to UNKNOWN when history state is absent', () => {
    expect(splitJobHistoryState(null)).toStrictEqual(['UNKNOWN'])
  })
})
