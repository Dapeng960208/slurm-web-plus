import { describe, expect, test } from 'vitest'
import {
  QUEUE_WAIT_BASELINE_SECONDS,
  QUEUE_WAIT_DANGER_SECONDS,
  QUEUE_WAIT_WARNING_SECONDS,
  queueWaitColorForSeconds,
  queueWaitGradientStop
} from '@/composables/queueWaitColors'

describe('queueWaitColors', () => {
  test('keeps the theme green before the baseline threshold', () => {
    expect(queueWaitColorForSeconds(QUEUE_WAIT_BASELINE_SECONDS)).toBe('rgba(182, 232, 44, 1)')
    expect(queueWaitColorForSeconds(30, 0.2)).toBe('rgba(182, 232, 44, 0.2)')
  })

  test('blends from green to orange and then to red as wait increases', () => {
    expect(queueWaitColorForSeconds(180)).toBe('rgba(211, 194, 42, 1)')
    expect(queueWaitColorForSeconds(600)).toBe('rgba(228, 115, 60, 1)')
    expect(queueWaitColorForSeconds(1200)).toBe('rgba(216, 75, 80, 1)')
  })

  test('normalizes gradient stops against the visible chart scale', () => {
    expect(queueWaitGradientStop(QUEUE_WAIT_BASELINE_SECONDS, 1800)).toBeCloseTo(0.0333, 3)
    expect(queueWaitGradientStop(QUEUE_WAIT_WARNING_SECONDS, 1800)).toBeCloseTo(0.1667, 3)
    expect(queueWaitGradientStop(QUEUE_WAIT_DANGER_SECONDS, 1800)).toBeCloseTo(0.5, 3)
    expect(queueWaitGradientStop(QUEUE_WAIT_DANGER_SECONDS, 300)).toBe(1)
  })
})
