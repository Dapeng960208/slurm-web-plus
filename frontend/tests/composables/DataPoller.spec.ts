import { beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { setActivePinia } from 'pinia'
import { useClusterDataPoller } from '@/composables/DataPoller'
import { useClusterDataGetter } from '@/composables/DataGetter'

const mockGateway = {
  stats: vi.fn(),
  abort: vi.fn(),
  isValidGatewayClusterWithStringAPIKey: vi.fn().mockReturnValue(false),
  isValidGatewayClusterWithNumberAPIKey: vi.fn().mockReturnValue(false)
}

const mockErrorsHandler = {
  reportAuthenticationError: vi.fn(),
  reportPermissionError: vi.fn()
}

vi.mock('@/composables/GatewayAPI', () => ({
  useGatewayAPI: () => mockGateway
}))

vi.mock('@/composables/ErrorsHandler', () => ({
  useErrorsHandler: () => mockErrorsHandler
}))

describe('useClusterDataPoller', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(
      createTestingPinia({
        createSpy: vi.fn,
        stubActions: false
      })
    )
  })

  test('passes structured dashboard query params to gateway methods', async () => {
    mockGateway.stats.mockResolvedValue({ resources: {}, jobs: {} })

    mount(
      defineComponent({
        setup() {
          useClusterDataPoller('foo', 'stats', 10000, { partition: 'gpu' })
          return () => null
        }
      })
    )

    await Promise.resolve()

    expect(mockGateway.stats).toHaveBeenCalledWith('foo', { partition: 'gpu' })
  })

  test('cluster data getter ignores stale responses after cluster switch', async () => {
    let resolveFoo: ((value: { items: string[] }) => void) | null = null
    let resolveBar: ((value: { items: string[] }) => void) | null = null
    mockGateway.stats.mockReset()
    mockGateway.stats.mockImplementation((cluster: string) => {
      return new Promise((resolve) => {
        if (cluster === 'foo') {
          resolveFoo = resolve
        } else {
          resolveBar = resolve
        }
      })
    })

    let getter: ReturnType<typeof useClusterDataGetter<{ items: string[] }>>
    mount(
      defineComponent({
        setup() {
          getter = useClusterDataGetter('foo', 'stats')
          return () => null
        }
      })
    )

    getter!.setCluster('bar')
    resolveBar?.({ items: ['bar'] })
    await Promise.resolve()
    resolveFoo?.({ items: ['foo'] })
    await Promise.resolve()

    expect(getter!.data.value).toStrictEqual({ items: ['bar'] })
  })

  test('cluster data getter skips requests when disabled', async () => {
    mockGateway.stats.mockReset()

    mount(
      defineComponent({
        setup() {
          useClusterDataGetter('foo', 'stats', undefined, false)
          return () => null
        }
      })
    )

    await Promise.resolve()

    expect(mockGateway.stats).not.toHaveBeenCalled()
  })
})
