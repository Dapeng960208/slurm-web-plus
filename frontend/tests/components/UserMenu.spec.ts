import { beforeEach, describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { i18n } from '@/plugins/i18n'
import { useAuthStore } from '@/stores/auth'
import UserMenu from '@/components/UserMenu.vue'
import { createRouterMock, injectRouterMock } from 'vue-router-mock'

describe('UserMenu.vue', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'en'
    const router = createRouterMock()
    injectRouterMock(router)
  })

  test('allows switching locale from the user menu', async () => {
    const wrapper = mount(UserMenu, {
      props: {
        cluster: 'foo'
      },
      global: {
        plugins: [i18n, createTestingPinia({ stubActions: false })],
        stubs: {
          Menu: {
            template: '<div><slot /></div>'
          },
          MenuButton: {
            template: '<button><slot /></button>'
          },
          MenuItems: {
            template: '<div><slot /></div>'
          },
          MenuItem: {
            template: '<div><slot :active="false" /></div>'
          },
          RouterLink: {
            template: '<a><slot /></a>'
          }
        }
      }
    })

    const authStore = useAuthStore()
    authStore.username = 'jdoe'
    authStore.fullname = 'John Doe'

    expect(wrapper.text()).toContain('Account permissions')

    await wrapper.get('select').setValue('zh-CN')

    expect(i18n.global.locale.value).toBe('zh-CN')
    expect(wrapper.text()).toContain('账户权限')
  })
})
