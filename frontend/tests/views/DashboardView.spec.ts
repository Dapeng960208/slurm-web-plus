import { describe, test, beforeEach, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import DashboardView from '@/views/DashboardView.vue'
import { useRuntimeStore } from '@/stores/runtime'
import type { ClusterPartition, ClusterStats } from '@/composables/GatewayAPI'
import ErrorAlert from '@/components/ErrorAlert.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import stats from '../assets/stats.json'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterStats>()
const mockPartitionsGetter = {
  data: ref([{ name: 'debug', node_sets: 'a' }, { name: 'gpu', node_sets: 'b' }] as ClusterPartition[]),
  unable: ref(false),
  loaded: ref(true),
  setCluster: vi.fn()
}

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

vi.mock('@/composables/DataGetter', () => ({
  useClusterDataGetter: () => mockPartitionsGetter
}))

describe('DashboardView.vue', () => {
  let router: ReturnType<typeof init_plugins>
  let runtimeStore: ReturnType<typeof useRuntimeStore>

  beforeEach(() => {
    router = init_plugins()
    runtimeStore = useRuntimeStore()
    mockClusterDataPoller.data.value = stats
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.refreshing.value = false
    ;(mockClusterDataPoller.setCluster as ReturnType<typeof vi.fn>).mockClear()
    ;(mockClusterDataPoller.setParam as ReturnType<typeof vi.fn>).mockClear()
    ;(mockPartitionsGetter.setCluster as ReturnType<typeof vi.fn>).mockClear()
    mockPartitionsGetter.data.value = [
      { name: 'debug', node_sets: 'a' },
      { name: 'gpu', node_sets: 'b' }
    ]
    mockPartitionsGetter.loaded.value = true
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['view-partitions'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    runtimeStore.dashboard.reset()
  })
  test('should display dashboard with metrics', () => {
    const wrapper = mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })
    // Check presence of metrics and values.
    expect(wrapper.findAll('.ui-stat-label').map((element) => element.text())).toStrictEqual([
      'Nodes',
      'Cores',
      'Total Memory',
      'Allocated Memory',
      'Available Memory',
      'GPU',
      'Running Jobs',
      'Total Jobs'
    ])
    expect(wrapper.get('span#metric-nodes').text()).toBe(stats.resources.nodes.toString())
    expect(wrapper.get('span#metric-cores').text()).toBe(stats.resources.cores.toString())
    expect(wrapper.get('span#metric-jobs-running').text()).toBe(stats.jobs.running.toString())
    expect(wrapper.get('span#metric-jobs-total').text()).toBe(stats.jobs.total.toString())
    expect(wrapper.html()).toContain('dashboard-charts-stub')
  })
  test('restores partition query and shows partition selector', async () => {
    await router.setQuery({ partition: 'gpu' })

    const wrapper = mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })

    await flushPromises()

    expect(runtimeStore.dashboard.partition).toBe('gpu')
    expect((wrapper.get('#dashboard-partition').element as HTMLSelectElement).value).toBe('gpu')
    expect(wrapper.text()).toContain('Realtime Metrics')
    expect(wrapper.text()).toContain('Time Range')
  })

  test('keeps a valid partition query until partitions finish loading', async () => {
    mockPartitionsGetter.loaded.value = false
    mockPartitionsGetter.data.value = []
    await router.setQuery({ partition: 'gpu' })

    mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })

    await flushPromises()
    expect(runtimeStore.dashboard.partition).toBe('gpu')

    mockPartitionsGetter.data.value = [{ name: 'gpu', node_sets: 'b' }]
    mockPartitionsGetter.loaded.value = true
    await flushPromises()

    expect(runtimeStore.dashboard.partition).toBe('gpu')
  })

  test('changing partition refreshes stats and syncs query', async () => {
    const wrapper = mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })

    await wrapper.get('#dashboard-partition').setValue('debug')

    expect(mockClusterDataPoller.setParam).toHaveBeenCalledWith({ partition: 'debug' })
    expect(router.push).toHaveBeenCalledWith({
      name: 'dashboard',
      query: { partition: 'debug' }
    })

    await wrapper.get('#dashboard-partition').setValue('')

    expect(mockClusterDataPoller.setParam).toHaveBeenCalledWith(undefined)
    expect(router.push).toHaveBeenLastCalledWith({
      name: 'dashboard',
      query: {}
    })
  })

  test('hides partition selector and ignores partition query without permission', async () => {
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await router.setQuery({ partition: 'gpu' })

    const wrapper = mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.find('#dashboard-partition').exists()).toBe(false)
    expect(runtimeStore.dashboard.partition).toBe('')
    expect(wrapper.text()).toContain('Time Range')
  })

  test('renders partition and time range controls in the same panel', () => {
    const wrapper = mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })

    const panels = wrapper.findAll('.ui-panel.ui-section')
    expect(panels).toHaveLength(1)
    expect(panels[0].text()).toContain('Partition / Queue')
    expect(panels[0].text()).toContain('Time Range')
  })

  test('should not display charts when metrics are disabled', () => {
    // Disable metrics on cluster foo
    runtimeStore.availableClusters[0].metrics = false
    const wrapper = mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })
    // Check absence of charts component
    expect(wrapper.html()).not.toContain('dashboard-charts-stub')
  })
  test('should display error when unable to get cluster stats', () => {
    mockClusterDataPoller.unable.value = true
    const wrapper = mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })
    // Check error is displayed when data poller is unable to retrieved data.
    expect(wrapper.getComponent(ErrorAlert).text()).toContain(
      'Unable to retrieve statistics from cluster foo'
    )
  })

  test('updates partition source when cluster prop changes', async () => {
    runtimeStore.availableClusters.push({
      name: 'bar',
      permissions: { roles: [], actions: ['view-partitions'] },
      racksdb: true,
      infrastructure: 'bar',
      metrics: true,
      cache: true
    })
    const wrapper = mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })

    await wrapper.setProps({ cluster: 'bar' })
    await flushPromises()

    expect(mockClusterDataPoller.setCluster).toHaveBeenCalledWith('bar')
    expect(mockPartitionsGetter.setCluster).toHaveBeenCalledWith('bar')
  })

  test('clears partition selection when switching to a cluster without permission', async () => {
    runtimeStore.availableClusters.push({
      name: 'bar',
      permissions: { roles: [], actions: [] },
      racksdb: true,
      infrastructure: 'bar',
      metrics: true,
      cache: true
    })
    runtimeStore.availableClusters[0].permissions.actions = []
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    runtimeStore.dashboard.partition = 'gpu'

    const wrapper = mount(DashboardView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          DashboardCharts: true
        }
      }
    })

    await wrapper.setProps({ cluster: 'bar' })
    await flushPromises()

    expect(wrapper.find('#dashboard-partition').exists()).toBe(false)
    expect(runtimeStore.dashboard.partition).toBe('')
  })
})
