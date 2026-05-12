import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
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
  })

  test('renders partition summary and node set chips', () => {
    const wrapper = mount(PartitionView, {
      props: {
        cluster: 'foo',
        partition: 'normal'
      },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          RouterLink: { template: '<a><slot /></a>' }
        }
      }
    })

    expect(wrapper.text()).toContain('Partition Details')
    expect(wrapper.text()).toContain('Nodes')
    expect(wrapper.text()).toContain('Allocated Nodes')
    expect(wrapper.text()).toContain('Idle Nodes')
    expect(wrapper.text()).toContain('GPU')
    expect(wrapper.text()).toContain('cn[1-4]')
    expect(wrapper.text()).toContain('gpu[1-2]')
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
