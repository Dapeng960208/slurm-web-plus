import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'
import PartitionView from '@/views/PartitionView.vue'
import { init_plugins } from '../lib/common'

const mockPartitions = ref([
  { name: 'normal', node_sets: 'cn[1-4],gpu[1-2]' }
])
const mockNodes = ref([
  {
    alloc_cpus: 64,
    alloc_idle_cpus: 0,
    cores: 32,
    cpus: 64,
    gres: '',
    gres_used: '',
    name: 'cn1',
    partitions: ['normal'],
    real_memory: 131072,
    reason: '',
    sockets: 2,
    state: ['ALLOCATED']
  },
  {
    alloc_cpus: 0,
    alloc_idle_cpus: 64,
    cores: 32,
    cpus: 64,
    gres: 'gpu:h100:4',
    gres_used: '',
    name: 'gpu1',
    partitions: ['normal'],
    real_memory: 131072,
    reason: '',
    sockets: 2,
    state: ['IDLE']
  }
])

vi.mock('@/composables/DataGetter', () => ({
  useClusterDataGetter: (_cluster: string, key: string) =>
    key === 'partitions'
      ? { data: mockPartitions }
      : { data: mockNodes }
}))

describe('PartitionView.vue', () => {
  beforeEach(() => {
    init_plugins()
    useRuntimeStore().dashboard.reset()
    useRuntimeStore().dashboard.range = 'day'
  })

  test('renders partition summary, non-duplicated details, and node set chips', () => {
    const wrapper = mount(PartitionView, {
      props: {
        cluster: 'foo',
        partition: 'normal'
      },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          RouterLink: { template: '<a><slot /></a>' },
          DashboardCharts: {
            props: ['cluster', 'metricsQuery', 'routeTargetName'],
            template:
              '<div data-testid="partition-dashboard-props">{{ cluster }}|{{ routeTargetName }}|{{ JSON.stringify(metricsQuery) }}</div>'
          }
        }
      }
    })

    expect(wrapper.text()).toContain('Partition Details')
    expect(wrapper.findAll('.ui-summary-strip .ui-summary-item')).toHaveLength(5)
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Nodes')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Total CPU')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Allocated CPU')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Total Memory')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('GPU')
    expect(wrapper.find('.ui-detail-list').text()).toContain('Allocated Nodes')
    expect(wrapper.find('.ui-detail-list').text()).toContain('Idle Nodes')
    expect(wrapper.find('.ui-detail-list').text()).not.toContain('Total CPU')
    expect(wrapper.find('.ui-detail-list').text()).not.toContain('Allocated CPU')
    expect(wrapper.find('.ui-detail-list').text()).not.toContain('Total Memory')
    expect(wrapper.find('.ui-detail-list').text()).not.toContain('GPU')
    expect(wrapper.text()).toContain('cn[1-4]')
    expect(wrapper.text()).toContain('gpu[1-2]')
    expect(wrapper.get('[data-testid="partition-dashboard-charts"]').text()).toContain(
      'Partition live metrics'
    )
    expect(wrapper.get('[data-testid="partition-dashboard-props"]').text()).toContain('foo|partition|')
    expect(wrapper.get('[data-testid="partition-dashboard-props"]').text()).toContain(
      JSON.stringify({ range: 'day', partition: 'normal' })
    )
  })

  test('renders not found state when partition is missing', () => {
    const wrapper = mount(PartitionView, {
      props: {
        cluster: 'foo',
        partition: 'missing'
      },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' }
        }
      }
    })

    expect(wrapper.text()).toContain('Partition missing is not available on this cluster.')
  })
})
