import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent } from 'vue'
import { enableAutoUnmount, mount } from '@vue/test-utils'
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

enableAutoUnmount(afterEach)

describe('useClusterDataPoller', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false
    })
    setActivePinia(
      createTestingPinia({
        createSpy: vi.fn,
        stubActions: false
      })
    )
  })

  afterEach(() => {
    vi.useRealTimers()
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

  test('pauses polling when page is hidden and refreshes when visible again', async () => {
    vi.useFakeTimers()
    mockGateway.stats.mockResolvedValue({ resources: {}, jobs: {} })

    mount(
      defineComponent({
        setup() {
          useClusterDataPoller('foo', 'stats', 10000)
          return () => null
        }
      })
    )
    await Promise.resolve()
    expect(mockGateway.stats).toHaveBeenCalledTimes(1)

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: true
    })
    document.dispatchEvent(new Event('visibilitychange'))
    expect(mockGateway.abort).toHaveBeenCalled()

    Object.defineProperty(document, 'hidden', {
      configurable: true,
      value: false
    })
    document.dispatchEvent(new Event('visibilitychange'))
    await Promise.resolve()

    expect(mockGateway.stats).toHaveBeenCalledTimes(2)
  })

  test('exposes a manual refresh method', async () => {
    mockGateway.stats.mockResolvedValue({ resources: {}, jobs: {} })
    let poller: ReturnType<typeof useClusterDataPoller<{ resources: object; jobs: object }>>
    mount(
      defineComponent({
        setup() {
          poller = useClusterDataPoller('foo', 'stats', 10000)
          return () => null
        }
      })
    )
    await Promise.resolve()

    await poller!.refresh()

    expect(mockGateway.stats).toHaveBeenCalledTimes(2)
  })

  test('keeps data reference stable when polling returns unchanged content', async () => {
    mockGateway.stats
      .mockResolvedValueOnce({ resources: { nodes: 2 }, jobs: { running: 1 } })
      .mockResolvedValueOnce({ resources: { nodes: 2 }, jobs: { running: 1 } })
    let poller: ReturnType<typeof useClusterDataPoller<{ resources: object; jobs: object }>>
    mount(
      defineComponent({
        setup() {
          poller = useClusterDataPoller('foo', 'stats', 10000)
          return () => null
        }
      })
    )
    await Promise.resolve()
    const firstData = poller!.data.value

    await poller!.refresh()

    expect(mockGateway.stats).toHaveBeenCalledTimes(2)
    expect(poller!.data.value).toBe(firstData)
  })

  test('defers automatic polling while a text input is focused', async () => {
    vi.useFakeTimers()
    mockGateway.stats.mockResolvedValue({ resources: {}, jobs: {} })
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()

    mount(
      defineComponent({
        setup() {
          useClusterDataPoller('foo', 'stats', 10000)
          return () => null
        }
      })
    )
    await Promise.resolve()
    expect(mockGateway.stats).not.toHaveBeenCalled()

    input.blur()
    document.body.removeChild(input)
    await vi.advanceTimersByTimeAsync(10000)

    expect(mockGateway.stats).toHaveBeenCalledTimes(1)
  })

  test('manual refresh still runs while a text input is focused', async () => {
    mockGateway.stats.mockResolvedValue({ resources: {}, jobs: {} })
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()
    let poller: ReturnType<typeof useClusterDataPoller<{ resources: object; jobs: object }>>

    mount(
      defineComponent({
        setup() {
          poller = useClusterDataPoller('foo', 'stats', 10000)
          return () => null
        }
      })
    )
    await Promise.resolve()
    await poller!.refresh()

    expect(mockGateway.stats).toHaveBeenCalledTimes(1)
    input.blur()
    document.body.removeChild(input)
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
