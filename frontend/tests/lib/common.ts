import { ref } from 'vue'
import type { Ref } from 'vue'
import { vi } from 'vitest'
import { runtimeConfiguration } from '@/plugins/runtimeConfiguration'
import type { GatewayAnyClusterApiKey } from '@/composables/GatewayAPI'
import { httpPlugin } from '@/plugins/http'
import { createTestingPinia } from '@pinia/testing'
import { setActivePinia } from 'pinia'
import { config, RouterLinkStub } from '@vue/test-utils'
import { createRouterMock, injectRouterMock } from 'vue-router-mock'
import type { RouterMock } from 'vue-router-mock'

export function init_plugins(): RouterMock {
  const pinia = createTestingPinia({
    createSpy: vi.fn,
    stubActions: false
  })
  setActivePinia(pinia)

  config.global.plugins = [
    [
      runtimeConfiguration,
      {
        api_server: 'http://localhost',
        authentication: true
      }
    ],
    httpPlugin,
    pinia
  ]
  config.global.stubs = {
    RouterLink: RouterLinkStub
  }

  const router = createRouterMock({
    spy: {
      create: (fn: (...args: unknown[]) => unknown) => vi.fn(fn),
      reset: (spy: { mockRestore: () => void }) => spy.mockRestore()
    }
  })

  router.reset()
  injectRouterMock(router)

  return router
}

interface MockClusterDataPoller<ResultType> {
  data: Ref<ResultType | undefined>
  unable: Ref<boolean>
  loaded: Ref<boolean>
  initialLoading: Ref<boolean>
  refreshing: Ref<boolean>
  setCluster: (newCluster: string) => void
  setCallback: (newCallback: GatewayAnyClusterApiKey) => void
  setParam: (newOtherParam: string | number) => void
}

export function getMockClusterDataPoller<ResultType>(): MockClusterDataPoller<ResultType> {
  return {
    data: ref(undefined),
    unable: ref(false),
    loaded: ref(true),
    initialLoading: ref(false),
    refreshing: ref(false),
    setCluster: vi.fn(),
    setCallback: vi.fn(),
    setParam: vi.fn()
  }
}
