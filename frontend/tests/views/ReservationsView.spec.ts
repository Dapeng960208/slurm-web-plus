import { describe, test, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import ReservationsView from '@/views/ReservationsView.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import { i18n } from '@/plugins/i18n'
import type { ClusterReservation } from '@/composables/GatewayAPI'
import reservations from '../assets/reservations.json'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterReservation[]>()
const mockGatewayAPI = {
  save_reservation: vi.fn(),
  update_reservation: vi.fn(),
  delete_reservation: vi.fn(),
  nodes: vi.fn(),
  partitions: vi.fn(),
  qos: vi.fn()
}

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('ReservationsView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['reservations:view:*', 'reservations:edit:*', 'reservations:delete:*']
        },
        infrastructure: 'foo',
        metrics: true,
        racksdb: false,
        cache: false
      }
    ]
    mockClusterDataPoller.data.value = reservations
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockGatewayAPI.nodes.mockResolvedValue([{ name: 'cn001', partitions: ['gpu'], alloc_cpus: 0, alloc_idle_cpus: 0, cores: 0, cpus: 0, gres: '', gres_used: '', real_memory: 0, sockets: 0, state: [], reason: '' }])
    mockGatewayAPI.partitions.mockResolvedValue([{ name: 'gpu', node_sets: 'cn[1-4]' }])
    mockGatewayAPI.qos.mockResolvedValue([{ name: 'debug', description: 'Debug', flags: [], limits: {} }])
  })

  test('display reservations', () => {
    expect(reservations.length).toBeGreaterThan(0)
    const wrapper = mount(ReservationsView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.find('.ui-table-scroll').exists()).toBe(true)
    expect(wrapper.find('.ui-results-dock .ui-results-pagination').exists()).toBe(true)
    expect(wrapper.find('.ui-table-shell .ui-results-pagination').exists()).toBe(false)
    const reservationsTableLines = wrapper.get('main table tbody').findAll('tr')
    expect(reservationsTableLines.length).toBe(reservations.length)
    for (const [i] of reservationsTableLines.entries()) {
      const reservationCells = reservationsTableLines[i].findAll('td')
      expect(reservationCells[0].text()).toBe(reservations[i].name)
      if (reservations[i].users.length) {
        expect(reservationCells[4].findAll('li').map((element) => element.text())).toStrictEqual(
          reservations[i].users.split(',')
        )
      } else {
        expect(() => reservationCells[4].get('li')).toThrowError()
      }
      if (reservations[i].accounts.length) {
        expect(reservationCells[5].findAll('li').map((element) => element.text())).toStrictEqual(
          reservations[i].accounts.split(',')
        )
      } else {
        expect(() => reservationCells[5].get('li')).toThrowError()
      }
      expect(reservationCells[6].findAll('span').map((element) => element.text())).toStrictEqual(
        reservations[i].flags
      )
    }
  })

  test('show error alert when unable to retrieve reservations', () => {
    mockClusterDataPoller.unable.value = true
    const wrapper = mount(ReservationsView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.getComponent(ErrorAlert).text()).toBe(
      i18n.global.t('pages.reservations.unableToRetrieve', { cluster: 'foo' })
    )
  })

  test('show info alert when no reservation defined', () => {
    mockClusterDataPoller.data.value = []
    const wrapper = mount(ReservationsView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.getComponent(InfoAlert).text()).toBe(
      i18n.global.t('pages.reservations.noReservations', { cluster: 'foo' })
    )
  })

  test('submits reservation create payload with normalized access fields', async () => {
    mockGatewayAPI.save_reservation.mockResolvedValue({ result: 'ok' })

    const wrapper = mount(ReservationsView, {
      props: {
        cluster: 'foo'
      }
    })

    await wrapper.get('button.ui-button-primary').trigger('click')
    await nextTick()
    const createDialog = wrapper.findAllComponents(ActionDialog)[0]
    expect(createDialog.props('open')).toBe(true)
    createDialog.vm.$emit('submit', {
      name: 'maint-weekend',
      node_list: 'cn001,cn002',
      start_time: '2026-05-14T10:30',
      end_time: '2026-05-14T12:00',
      allowed_partitions: 'gpu, batch',
      users: 'alice,bob',
      groups: 'ops, support',
      accounts: 'science',
      qos: 'debug, normal'
    })
    await flushPromises()

    expect(mockGatewayAPI.save_reservation).toHaveBeenCalledWith('foo', {
      name: 'maint-weekend',
      node_list: 'cn001,cn002',
      users: ['alice', 'bob'],
      groups: ['ops', 'support'],
      accounts: ['science'],
      qos: ['debug', 'normal'],
      allowed_partitions: ['gpu', 'batch'],
      start_time: {
        set: true,
        number: Math.floor(new Date('2026-05-14T10:30').getTime() / 1000)
      },
      end_time: {
        set: true,
        number: Math.floor(new Date('2026-05-14T12:00').getTime() / 1000)
      }
    })
    expect(mockClusterDataPoller.refresh).toHaveBeenCalledOnce()
  })

  test('shows local validation error when all access control fields are empty', async () => {
    const wrapper = mount(ReservationsView, {
      props: {
        cluster: 'foo'
      }
    })

    await wrapper.get('button.ui-button-primary').trigger('click')
    await nextTick()
    const createDialog = wrapper.findAllComponents(ActionDialog)[0]
    createDialog.vm.$emit('submit', {
      name: 'maint-window',
      node_list: 'cn003',
      start_time: '2026-05-14T10:30',
      end_time: '2026-05-14T12:00',
      allowed_partitions: '',
      users: '',
      groups: '',
      accounts: '',
      qos: ''
    })
    await flushPromises()

    expect(mockGatewayAPI.save_reservation).not.toHaveBeenCalled()
    expect(wrapper.findAllComponents(ActionDialog)[0].props('error')).toBe(
      i18n.global.t('pages.reservations.errors.accessControlRequired')
    )
  })

  test('shows local validation error when create reservation end time is missing', async () => {
    const wrapper = mount(ReservationsView, {
      props: {
        cluster: 'foo'
      }
    })

    await wrapper.get('button.ui-button-primary').trigger('click')
    await nextTick()
    const createDialog = wrapper.findAllComponents(ActionDialog)[0]
    createDialog.vm.$emit('submit', {
      name: 'maint-window',
      node_list: 'cn003',
      start_time: '2026-05-14T10:30',
      end_time: '',
      allowed_partitions: 'gpu',
      users: '',
      groups: '',
      accounts: '',
      qos: ''
    })
    await flushPromises()

    expect(mockGatewayAPI.save_reservation).not.toHaveBeenCalled()
    expect(wrapper.findAllComponents(ActionDialog)[0].props('error')).toBe(
      i18n.global.t('pages.reservations.errors.endTimeRequired')
    )
  })

  test('shows local validation error when end time is before start time', async () => {
    const wrapper = mount(ReservationsView, {
      props: {
        cluster: 'foo'
      }
    })

    await wrapper.get('button.ui-button-primary').trigger('click')
    await nextTick()
    const createDialog = wrapper.findAllComponents(ActionDialog)[0]
    createDialog.vm.$emit('submit', {
      name: 'maint-window',
      node_list: 'cn003',
      start_time: '2026-05-14T12:30',
      end_time: '2026-05-14T10:30',
      allowed_partitions: 'gpu',
      users: '',
      groups: '',
      accounts: '',
      qos: ''
    })
    await flushPromises()

    expect(mockGatewayAPI.save_reservation).not.toHaveBeenCalled()
    expect(wrapper.findAllComponents(ActionDialog)[0].props('error')).toBe(
      i18n.global.t('pages.reservations.errors.invalidTimeRange')
    )
  })

  test('refreshes reservations after delete succeeds', async () => {
    mockGatewayAPI.delete_reservation.mockResolvedValue({ result: 'ok' })
    const wrapper = mount(ReservationsView, {
      props: {
        cluster: 'foo'
      }
    })

    const deleteButton = wrapper
      .findAll('button')
      .find((button) => button.text() === i18n.global.t('pages.reservations.actions.delete'))
    expect(deleteButton).toBeTruthy()
    await deleteButton!.trigger('click')
    await nextTick()
    const deleteDialog = wrapper.findAllComponents(ActionDialog)[2]
    expect(deleteDialog.props('open')).toBe(true)

    deleteDialog.vm.$emit('submit', {})
    await flushPromises()

    expect(mockGatewayAPI.delete_reservation).toHaveBeenCalledWith('foo', reservations[0].name)
    expect(mockClusterDataPoller.refresh).toHaveBeenCalledOnce()
    expect(wrapper.findAllComponents(ActionDialog)[2].props('open')).toBe(false)
  })
})
