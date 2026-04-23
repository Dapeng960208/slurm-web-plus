import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import PaginationControls from '@/components/PaginationControls.vue'

describe('PaginationControls.vue', () => {
  test('renders default range and emits page size changes', async () => {
    const wrapper = mount(PaginationControls, {
      props: {
        page: 1,
        pageSize: 20,
        total: 80,
        itemLabel: 'job'
      }
    })

    expect(wrapper.text()).toContain('Showing 1 to 20 of 80 jobs')

    await wrapper.get('select').setValue('50')

    expect(wrapper.emitted('update:pageSize')).toStrictEqual([[50]])
  })

  test('emits page change when a page button is clicked', async () => {
    const wrapper = mount(PaginationControls, {
      props: {
        page: 1,
        pageSize: 20,
        total: 80,
        itemLabel: 'record'
      }
    })

    const pageTwoButton = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === '2')

    expect(pageTwoButton).toBeDefined()
    await pageTwoButton!.trigger('click')

    expect(wrapper.emitted('update:page')).toStrictEqual([[2]])
  })
})
