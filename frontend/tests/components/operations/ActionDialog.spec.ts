import { describe, test, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { init_plugins } from '../../lib/common'

describe('ActionDialog.vue', () => {
  beforeEach(() => {
    init_plugins()
  })

  test('clears stale form values when the dialog is reused for a different action', async () => {
    const wrapper = mount(ActionDialog, {
      global: {
        stubs: {
          Dialog: { template: '<div><slot /></div>' },
          DialogPanel: { template: '<div><slot /></div>' },
          DialogTitle: { template: '<div><slot /></div>' },
          TransitionChild: { template: '<div><slot /></div>' },
          TransitionRoot: { template: '<div><slot /></div>' }
        }
      },
      props: {
        open: true,
        title: 'pages.job.dialogs.edit.title',
        submitLabel: 'common.buttons.saveChanges',
        fields: [
          {
            key: 'comment',
            label: 'pages.jobs.dialogs.edit.fields.comment'
          }
        ],
        initialValues: {
          comment: 'Needs review'
        }
      }
    })

    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[0]).toEqual([{ comment: 'Needs review' }])

    await wrapper.setProps({
      title: 'pages.job.dialogs.cancel.title',
      submitLabel: 'common.buttons.cancel',
      fields: [],
      initialValues: undefined
    })
    await nextTick()

    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[1]).toEqual([{}])
  })

  test('renders select fields and submits selected values', async () => {
    const wrapper = mount(ActionDialog, {
      global: {
        stubs: {
          Dialog: { template: '<div><slot /></div>' },
          DialogPanel: { template: '<div><slot /></div>' },
          DialogTitle: { template: '<div><slot /></div>' },
          TransitionChild: { template: '<div><slot /></div>' },
          TransitionRoot: { template: '<div><slot /></div>' }
        }
      },
      props: {
        open: true,
        title: 'pages.node.dialogs.edit.title',
        submitLabel: 'common.buttons.saveChanges',
        fields: [
          {
            key: 'state',
            label: 'pages.node.dialogs.edit.fields.state',
            type: 'select',
            required: true,
            options: [
              { label: 'DRAIN', value: 'DRAIN' },
              { label: 'RESUME', value: 'RESUME' }
            ]
          }
        ],
        initialValues: {
          state: 'DRAIN'
        }
      }
    })

    expect(wrapper.get('select').element.value).toBe('DRAIN')
    expect(wrapper.findAll('option').map((option) => option.text())).toEqual([
      'Select an option',
      'DRAIN',
      'RESUME'
    ])

    await wrapper.get('select').setValue('RESUME')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]).toEqual([{ state: 'RESUME' }])
  })

  test('does not reset user edits when initial values refresh while dialog stays open', async () => {
    const wrapper = mount(ActionDialog, {
      global: {
        stubs: {
          Dialog: { template: '<div><slot /></div>' },
          DialogPanel: { template: '<div><slot /></div>' },
          DialogTitle: { template: '<div><slot /></div>' },
          TransitionChild: { template: '<div><slot /></div>' },
          TransitionRoot: { template: '<div><slot /></div>' }
        }
      },
      props: {
        open: true,
        title: 'pages.account.dialogs.edit.title',
        submitLabel: 'common.buttons.saveChanges',
        fields: [
          {
            key: 'description',
            label: 'pages.account.dialogs.fields.description'
          }
        ],
        initialValues: {
          description: 'Original'
        }
      }
    })

    await wrapper.get('input').setValue('Typing in progress')
    await wrapper.setProps({
      initialValues: {
        description: 'Refreshed from poller'
      }
    })
    await nextTick()

    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('Typing in progress')

    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[0]).toEqual([{ description: 'Typing in progress' }])
  })

  test('renders datetime-local fields and submits entered timestamps', async () => {
    const wrapper = mount(ActionDialog, {
      global: {
        stubs: {
          Dialog: { template: '<div><slot /></div>' },
          DialogPanel: { template: '<div><slot /></div>' },
          DialogTitle: { template: '<div><slot /></div>' },
          TransitionChild: { template: '<div><slot /></div>' },
          TransitionRoot: { template: '<div><slot /></div>' }
        }
      },
      props: {
        open: true,
        title: 'pages.reservations.dialogs.create.title',
        submitLabel: 'pages.reservations.dialogs.create.submit',
        fields: [
          {
            key: 'start_time',
            label: 'pages.reservations.dialogs.fields.startTime',
            type: 'datetime-local',
            required: true
          },
          {
            key: 'end_time',
            label: 'pages.reservations.dialogs.fields.endTime',
            type: 'datetime-local',
            required: true
          }
        ]
      }
    })

    const inputs = wrapper.findAll('input[type="datetime-local"]')
    expect(inputs).toHaveLength(2)

    await inputs[0].setValue('2026-05-14T10:30')
    await inputs[1].setValue('2026-05-14T12:00')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]).toEqual([
      { start_time: '2026-05-14T10:30', end_time: '2026-05-14T12:00' }
    ])
  })

  test('renders searchable multi select fields and submits serialized values', async () => {
    const wrapper = mount(ActionDialog, {
      global: {
        stubs: {
          Dialog: { template: '<div><slot /></div>' },
          DialogPanel: { template: '<div><slot /></div>' },
          DialogTitle: { template: '<div><slot /></div>' },
          TransitionChild: { template: '<div><slot /></div>' },
          TransitionRoot: { template: '<div><slot /></div>' }
        }
      },
      props: {
        open: true,
        title: 'pages.account.dialogs.edit.title',
        submitLabel: 'common.buttons.saveChanges',
        fields: [
          {
            key: 'qos',
            label: 'pages.account.dialogs.fields.qosCsv',
            type: 'search-multi-select',
            source: {
              search: async () => [
                { value: 'normal', label: 'normal' },
                { value: 'debug', label: 'debug' }
              ]
            }
          }
        ],
        initialValues: {
          qos: 'normal, debug'
        }
      }
    })

    expect(wrapper.findComponent({ name: 'RemoteSearchSelect' }).exists()).toBe(true)
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]).toEqual([{ qos: 'normal, debug' }])
  })
})
