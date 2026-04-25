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
        title: 'Edit job',
        submitLabel: 'Save',
        fields: [
          {
            key: 'comment',
            label: 'Comment'
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
      title: 'Cancel job',
      submitLabel: 'Cancel',
      fields: [],
      initialValues: undefined
    })
    await nextTick()

    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[1]).toEqual([{}])
  })
})
