import { beforeEach, describe, expect, test, vi } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import type { RouterMock } from 'vue-router-mock'
import ForbiddenView from '@/views/ForbiddenView.vue'
import { i18n } from '@/plugins/i18n'
import { init_plugins } from '../lib/common'

let router: RouterMock

describe('ForbiddenView.vue', () => {
  beforeEach(() => {
    router = init_plugins()
    i18n.global.locale.value = 'zh-CN'
    document.documentElement.lang = 'zh-CN'
  })

  test('shows permission details and dashboard shortcut', async () => {
    await router.setQuery({ cluster: 'foo', permission: 'ai:view:*' })

    const wrapper = mount(ForbiddenView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub
        }
      }
    })

    expect(wrapper.text()).toContain('当前页面访问受限')
    expect(wrapper.text()).toContain('缺少所需权限：ai:view:*')
    expect(wrapper.text()).toContain('请联系管理员申请访问权限。')

    const dashboardLink = wrapper.findComponent(RouterLinkStub)
    expect(dashboardLink.props('to')).toEqual({
      name: 'dashboard',
      params: { cluster: 'foo' }
    })
  })

  test('goes back when the back button is clicked', async () => {
    const backSpy = vi.spyOn(router, 'back')
    const wrapper = mount(ForbiddenView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub
        }
      }
    })

    await wrapper.get('button').trigger('click')

    expect(backSpy).toHaveBeenCalled()
  })
})
