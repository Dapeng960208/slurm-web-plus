import { describe, test, beforeEach, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import DashboardView from '@/views/DashboardView.vue'
import { useRuntimeStore } from '@/stores/runtime'
import type { ClusterJob, ClusterNode, ClusterPartition, ClusterStats } from '@/composables/GatewayAPI'
import ErrorAlert from '@/components/ErrorAlert.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import stats from '../assets/stats.json'
import jobs from '../assets/jobs.json'
import nodes from '../assets/nodes.json'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterStats>()
const mockPartitionsGetter = {
  data: ref([{ name: 'debug', node_sets: 'a' }, { name: 'gpu', node_sets: 'b' }] as ClusterPartition[]),
  unable: ref(false),
  loaded: ref(true),
  setCluster: vi.fn()
}
const mockNodesGetter = {
  data: ref(nodes as ClusterNode[]),
  unable: ref(false),
  loaded: ref(true),
  setCluster: vi.fn()
}
const mockJobsGetter = {
  data: ref(jobs as ClusterJob[]),
  unable: ref(false),
  loaded: ref(true),
  setCluster: vi.fn()
}

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

vi.mock('@/composables/DataGetter', () => ({
  useClusterDataGetter: ((cluster: string, callback: string) => {
    if (callback === 'partitions') return mockPartitionsGetter
    if (callback === 'nodes') return mockNodesGetter
    if (callback === 'jobs') return mockJobsGetter
    return mockPartitionsGetter
  }) as typeof import('@/composables/DataGetter').useClusterDataGetter
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
    ;(mockNodesGetter.setCluster as ReturnType<typeof vi.fn>).mockClear()
    ;(mockJobsGetter.setCluster as ReturnType<typeof vi.fn>).mockClear()
    mockPartitionsGetter.data.value = [
      { name: 'debug', node_sets: 'a' },
      { name: 'gpu', node_sets: 'b' }
    ]
    mockPartitionsGetter.loaded.value = true
    mockNodesGetter.data.value = nodes as ClusterNode[]
    mockJobsGetter.data.value = jobs as ClusterJob[]
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: ['view-partitions'],
          rules: ['jobs/filter-partitions:view:*']
        },
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
    expect(wrapper.get('[data-testid="dashboard-header-tools"]').text()).toContain('Total Jobs')
    expect(wrapper.get('[data-testid="dashboard-header-tools"]').text()).toContain(
      stats.jobs.total.toString()
    )
    expect(wrapper.find('[data-testid="dashboard-header-tools"] .ui-button-primary').exists()).toBe(
      true
    )
    expect(wrapper.html()).toContain('dashboard-charts-stub')
  })

  test('restores partition query and shows partition selector without redundant toolbar copy', async () => {
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
    expect(wrapper.text()).not.toContain('Realtime Metrics')
    expect(wrapper.find('.ui-toolbar-copy').exists()).toBe(false)
    expect(wrapper.findAll('.ui-toolbar-field-label').map((node) => node.text())).toEqual([
      'Partition / Queue'
    ])
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

  test('recomputes visible stat cards from partition scoped nodes and jobs', async () => {
    mockPartitionsGetter.data.value = [{ name: 'normal', node_sets: 'cn[1-8]' }]

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

    await wrapper.get('#dashboard-partition').setValue('normal')
    await flushPromises()

    expect(wrapper.get('span#metric-nodes').text()).toBe('4')
    expect(wrapper.get('span#metric-cores').text()).toBe('256')
    expect(wrapper.get('span#metric-jobs-running').text()).toBe('7')
    expect(wrapper.get('span#metric-jobs-total').text()).toBe('14')
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
    expect(wrapper.find('.ui-toolbar-field-label').exists()).toBe(false)
  })

  test('renders a cardless toolbar with partition and time range controls', () => {
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

    const toolbar = wrapper.get('[data-testid="dashboard-toolbar"]')
    expect(toolbar.text()).toContain('Partition / Queue')
    expect(toolbar.findAll('.ui-toolbar-field-label')).toHaveLength(1)
    expect(wrapper.find('[data-testid="metric-range-custom-button"]').exists()).toBe(true)
    expect(toolbar.findAll('.ui-inline-field')).toHaveLength(0)
    expect(wrapper.findAll('.dashboard-surface').length).toBe(9)
    expect(wrapper.find('.dashboard-surface.mt-6').exists()).toBe(false)
  })

  test('wraps dashboard content in an internal scroll region', () => {
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

    expect(wrapper.find('.ui-scroll-region').classes()).toEqual(
      expect.arrayContaining(['ui-scroll-region', 'min-h-0', 'flex-1', 'pr-1'])
    )
  })

  test('should not display charts when metrics are disabled', () => {
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
    expect(wrapper.getComponent(ErrorAlert).text()).toContain(
      'Unable to retrieve statistics from cluster foo'
    )
  })

  test('updates partition source when cluster prop changes', async () => {
    runtimeStore.availableClusters.push({
      name: 'bar',
      permissions: {
        roles: [],
        actions: ['view-partitions'],
        rules: ['jobs/filter-partitions:view:*']
      },
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
    expect(mockNodesGetter.setCluster).toHaveBeenCalledWith('bar')
    expect(mockJobsGetter.setCluster).toHaveBeenCalledWith('bar')
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
