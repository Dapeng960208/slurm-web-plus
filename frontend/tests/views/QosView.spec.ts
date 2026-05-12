import { describe, test, expect, beforeEach, vi } from 'vitest'
import { RouterLink } from 'vue-router'
import { flushPromises, mount } from '@vue/test-utils'
import QosView from '@/views/QosView.vue'
import QosHelpModal from '@/components/qos/QosHelpModal.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import { i18n } from '@/plugins/i18n'
import type { ClusterQos } from '@/composables/GatewayAPI'
import qos from '../assets/qos.json'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterQos[]>()
const mockGatewayAPI = {
  save_qos: vi.fn(),
  delete_qos: vi.fn()
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

describe('QosView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    // Reset mockClusterDataPoller unable to its default value before every tests.
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.data.value = qos
    document.body.innerHTML = ''
  })
  test('display qos', () => {
    mockClusterDataPoller.data.value = qos
    // Check at least one QOS is present in test asset or the test is pointless.
    expect(qos.length).toBeGreaterThan(0)
    const wrapper = mount(QosView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.find('.ui-table-scroll').exists()).toBe(true)
    expect(wrapper.find('.ui-results-dock .ui-results-pagination').exists()).toBe(true)
    expect(wrapper.find('.ui-table-shell .ui-results-pagination').exists()).toBe(false)
    // Retrieve table body lines
    const qosTableLines = wrapper.get('main table tbody').findAll('tr')
    // Check one line per qos in table body
    expect(qosTableLines.length).toBe(qos.length)
    // Check name and description of QOS are present
    for (const [i] of qosTableLines.entries()) {
      expect(qosTableLines[i].find('td p.text-base').text()).toBe(qos[i].name)
      expect(qosTableLines[i].find('td p.text-gray-500').text()).toBe(qos[i].description)
    }
  })
  test('show error alert when unable to retrieve QOS', () => {
    mockClusterDataPoller.unable.value = true
    const wrapper = mount(QosView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.getComponent(ErrorAlert).text()).toBe(
      i18n.global.t('pages.qos.unableToRetrieve', { cluster: 'foo' })
    )
  })
  test('show info alert when no QOS defined', () => {
    mockClusterDataPoller.data.value = []
    const wrapper = mount(QosView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.getComponent(InfoAlert).text()).toBe(
      i18n.global.t('pages.qos.noQos', { cluster: 'foo' })
    )
  })
  test('open qos help modal', async () => {
    mockClusterDataPoller.data.value = qos
    const wrapper = mount(QosView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          QosHelpModal: true
        }
      }
    })
    /*
     * Check help modal show property is set to true when help button is clicked in QOS
     * table body.
     */
    const modal = wrapper.getComponent(QosHelpModal)
    expect(modal.props('helpModalShow')).toBeFalsy()
    await wrapper.get('main table tbody button').trigger('click')
    expect(modal.props('helpModalShow')).toBeTruthy()
  })
  test('click qos jobs filter', async () => {
    mockClusterDataPoller.data.value = qos
    const wrapper = mount(QosView, {
      props: {
        cluster: 'foo'
      }
    })
    /*
     * Check link targets of all router links in table body point to jobs view with
     * current qos filter.
     */
    const jobsQosFilterLinks = wrapper.get('main table tbody').findAllComponents(RouterLink)
    for (const [i, value] of jobsQosFilterLinks.entries()) {
      expect(value.props('to')).toStrictEqual({
        name: 'jobs',
        params: { cluster: 'foo' },
        query: { qos: qos[i].name }
      })
    }
  })
  test('creates qos with default common limits', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['qos:view:*', 'qos:edit:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    mockGatewayAPI.save_qos.mockResolvedValue({ operation: 'qos.update' })
    const wrapper = mount(QosView, {
      attachTo: document.body,
      props: {
        cluster: 'foo'
      }
    })

    await wrapper
      .findAll('button')
      .find((button) => button.text() === i18n.global.t('pages.qos.create'))!
      .trigger('click')
    const dialog = wrapper
      .findAllComponents(ActionDialog)
      .find((component) => component.props('title') === 'pages.qos.dialogs.create.title')!

    expect(dialog.props('initialValues')).toStrictEqual({
      max_submit_jobs_per_user: '100',
      max_jobs_per_user: '10',
      max_wall_duration_per_job: '6-00:00:00'
    })
    expect(dialog.props('fields')).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: 'max_submit_jobs_per_user', required: true }),
        expect.objectContaining({ key: 'max_jobs_per_user', required: true }),
        expect.objectContaining({ key: 'max_wall_duration_per_job', required: true })
      ])
    )

    dialog.vm.$emit('submit', {
      name: 'debug',
      description: 'Debug QOS',
      priority: '5',
      max_submit_jobs_per_user: '100',
      max_jobs_per_user: '10',
      max_wall_duration_per_job: '6-00:00:00'
    })
    await flushPromises()

    expect(mockGatewayAPI.save_qos).toHaveBeenCalledWith('foo', {
      name: 'debug',
      description: 'Debug QOS',
      priority: 5,
      max_submit_jobs_per_user: 100,
      max_jobs_per_user: 10,
      max_wall_duration_per_job: 8640
    })
    wrapper.unmount()
  })

  test('edits qos common limits', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['qos:view:*', 'qos:edit:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    mockGatewayAPI.save_qos.mockResolvedValue({ operation: 'qos.update' })
    const wrapper = mount(QosView, {
      attachTo: document.body,
      props: {
        cluster: 'foo'
      }
    })

    await wrapper
      .findAll('button')
      .filter((button) => button.text() === i18n.global.t('pages.qos.actions.edit'))[1]
      .trigger('click')
    const dialog = wrapper
      .findAllComponents(ActionDialog)
      .find((component) => component.props('title') === 'pages.qos.dialogs.edit.title')!

    expect(dialog.props('initialValues')).toMatchObject({
      max_submit_jobs_per_user: '20',
      max_jobs_per_user: '10',
      max_wall_duration_per_job: '0-08:00:00'
    })
    expect(dialog.props('fields')).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: 'max_submit_jobs_per_user', required: true }),
        expect.objectContaining({ key: 'max_jobs_per_user', required: true }),
        expect.objectContaining({ key: 'max_wall_duration_per_job', required: true })
      ])
    )

    dialog.vm.$emit('submit', {
      description: 'Updated QOS',
      priority: '7',
      max_submit_jobs_per_user: '40',
      max_jobs_per_user: '12',
      max_wall_duration_per_job: '6-00:00:00'
    })
    await flushPromises()

    expect(mockGatewayAPI.save_qos).toHaveBeenCalledWith('foo', {
      name: 'study',
      description: 'Updated QOS',
      priority: 7,
      max_submit_jobs_per_user: 40,
      max_jobs_per_user: 12,
      max_wall_duration_per_job: 8640
    })
    wrapper.unmount()
  })

  test('edits qos falls back to frontend defaults when backend limits are unset', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['qos:view:*', 'qos:edit:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    mockClusterDataPoller.data.value = [
      {
        ...qos[1],
        limits: {
          ...qos[1].limits,
          max: {
            ...qos[1].limits.max,
            jobs: {
              ...qos[1].limits.max.jobs,
              per: {
                ...qos[1].limits.max.jobs.per,
                user: { set: false, infinite: true, number: 0 }
              },
              active_jobs: {
                ...qos[1].limits.max.jobs.active_jobs,
                per: {
                  ...qos[1].limits.max.jobs.active_jobs.per,
                  user: { set: false, infinite: true, number: 0 }
                }
              }
            },
            wall_clock: {
              ...qos[1].limits.max.wall_clock,
              per: {
                ...qos[1].limits.max.wall_clock.per,
                job: { set: false, infinite: true, number: 0 }
              }
            }
          }
        }
      }
    ]
    const wrapper = mount(QosView, {
      attachTo: document.body,
      props: {
        cluster: 'foo'
      }
    })

    await wrapper
      .findAll('button')
      .filter((button) => button.text() === i18n.global.t('pages.qos.actions.edit'))[0]
      .trigger('click')
    const dialog = wrapper
      .findAllComponents(ActionDialog)
      .find((component) => component.props('title') === 'pages.qos.dialogs.edit.title')!

    expect(dialog.props('initialValues')).toMatchObject({
      max_submit_jobs_per_user: '100',
      max_jobs_per_user: '10',
      max_wall_duration_per_job: '6-00:00:00'
    })
    wrapper.unmount()
  })

  test('rejects invalid qos wall duration before submitting', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['qos:view:*', 'qos:edit:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    const wrapper = mount(QosView, {
      attachTo: document.body,
      props: {
        cluster: 'foo'
      }
    })

    await wrapper
      .findAll('button')
      .find((button) => button.text() === i18n.global.t('pages.qos.create'))!
      .trigger('click')
    wrapper
      .findAllComponents(ActionDialog)
      .find((component) => component.props('title') === 'pages.qos.dialogs.create.title')!
      .vm.$emit('submit', {
        name: 'debug',
        description: '',
        priority: '',
        max_submit_jobs_per_user: '100',
        max_jobs_per_user: '10',
        max_wall_duration_per_job: 'tomorrow'
      })
    await flushPromises()

    expect(mockGatewayAPI.save_qos).not.toHaveBeenCalled()
    expect(
      wrapper
        .findAllComponents(ActionDialog)
        .find((component) => component.props('title') === 'pages.qos.dialogs.create.title')!
        .props('error')
    ).toBe(i18n.global.t('pages.qos.dialogs.errors.invalidWallDuration'))
    wrapper.unmount()
  })
})
