import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import AdminLayoutView from '@/views/AdminLayoutView.vue'

describe('AdminLayoutView.vue', () => {
  test('provides an internal scroll region for admin child pages', () => {
    const wrapper = mount(AdminLayoutView, {
      props: { cluster: 'foo' },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          RouterView: { template: '<div data-testid="admin-child">admin child</div>' }
        }
      }
    })

    expect(wrapper.find('.ui-scroll-region').classes()).toEqual(
      expect.arrayContaining(['ui-scroll-region', 'min-h-0', 'flex-1', 'pr-1'])
    )
    expect(wrapper.get('[data-testid="admin-child"]').text()).toContain('admin child')
  })
})
