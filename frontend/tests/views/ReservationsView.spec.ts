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
  delete_reservation: vi.fn()
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
    // Reset mockClusterDataPoller unable to its default value before every tests.
    mockClusterDataPoller.unable.value = false
  })
  test('display reservations', () => {
    mockClusterDataPoller.data.value = reservations
    // Check at least one reservation is present in test asset or the test is pointless.
    expect(reservations.length).toBeGreaterThan(0)
    const wrapper = mount(ReservationsView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.find('.ui-table-scroll').exists()).toBe(true)
    expect(wrapper.find('.ui-results-dock .ui-results-pagination').exists()).toBe(true)
    expect(wrapper.find('.ui-table-shell .ui-results-pagination').exists()).toBe(false)
    // Retrieve table body lines
    const reservationsTableLines = wrapper.get('main table tbody').findAll('tr')
    // Check one line per reservation in table body
    expect(reservationsTableLines.length).toBe(reservations.length)
    /* For all reservations defined in test asset, check:
     * - name in 1st cell
     * - users in 5th cell
     * - account in 6th cell
     * - flags in 7th cell
     */
    for (const [i] of reservationsTableLines.entries()) {
      const reservationCells = reservationsTableLines[i].findAll('td')
      expect(reservationCells[0].text()).toBe(reservations[i].name)
      // if users in reservations, check all li items else check li absence
      if (reservations[i].users.length)
        expect(reservationCells[4].findAll('li').map((element) => element.text())).toStrictEqual(
          reservations[i].users.split(',')
        )
      else expect(() => reservationCells[4].get('li')).toThrowError()
      // if accounts in reservations, check all li items else check li absence
      if (reservations[i].accounts.length)
        expect(reservationCells[5].findAll('li').map((element) => element.text())).toStrictEqual(
          reservations[i].accounts.split(',')
        )
      else expect(() => reservationCells[5].get('li')).toThrowError()
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

  test('submits reservation create payload with required time fields', async () => {
    mockClusterDataPoller.data.value = reservations
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
      partition: 'gpu',
      users: 'alice,bob',
      accounts: 'science'
    })
    await flushPromises()

    expect(mockGatewayAPI.save_reservation).toHaveBeenCalledWith('foo', {
      name: 'maint-weekend',
      node_list: 'cn001,cn002',
      partition: 'gpu',
      users: ['alice', 'bob'],
      accounts: ['science'],
      start_time: {
        set: true,
        number: Math.floor(new Date('2026-05-14T10:30').getTime() / 1000)
      },
      end_time: {
        set: true,
        number: Math.floor(new Date('2026-05-14T12:00').getTime() / 1000)
      }
    })
  })

  test('shows local validation error when create reservation end time is missing', async () => {
    mockClusterDataPoller.data.value = reservations

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
      name: 'maint-window',
      node_list: 'cn003',
      start_time: '2026-05-14T10:30',
      end_time: '',
      partition: '',
      users: '',
      accounts: ''
    })
    await flushPromises()

    expect(mockGatewayAPI.save_reservation).not.toHaveBeenCalled()
    expect(wrapper.findAllComponents(ActionDialog)[0].props('error')).toBe(
      i18n.global.t('pages.reservations.errors.endTimeRequired')
    )
  })
})
