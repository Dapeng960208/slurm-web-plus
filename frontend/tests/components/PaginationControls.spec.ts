import { beforeEach, describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import { i18n } from '@/plugins/i18n'
import PaginationControls from '@/components/PaginationControls.vue'

describe('PaginationControls.vue', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'en'
  })

  test('renders default range and emits page size changes', async () => {
    const wrapper = mount(PaginationControls, {
      global: {
        plugins: [i18n]
      },
      props: {
        page: 1,
        pageSize: 20,
        total: 80,
        itemLabel: 'job'
      }
    })

    expect(wrapper.text()).toContain('Showing 1 to 20 of 80 jobs')
    expect(wrapper.classes()).toContain('ui-results-pagination')

    await wrapper.get('select').setValue('50')

    expect(wrapper.emitted('update:pageSize')).toStrictEqual([[50]])
  })

  test('emits page change when a page button is clicked', async () => {
    const wrapper = mount(PaginationControls, {
      global: {
        plugins: [i18n]
      },
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

  test('translates summary and page-size labels', async () => {
    const wrapper = mount(PaginationControls, {
      global: {
        plugins: [i18n]
      },
      props: {
        page: 1,
        pageSize: 20,
        total: 80,
        itemLabel: 'job'
      }
    })

    i18n.global.locale.value = 'zh-CN'
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('每页')
    expect(wrapper.text()).toContain('显示')
  })
})
