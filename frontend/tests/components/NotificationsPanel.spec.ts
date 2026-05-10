import { describe, test, beforeEach, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { useRuntimeStore } from '@/stores/runtime'
import { init_plugins } from '../lib/common'
import NotificationsPanel from '@/components/notifications/NotificationsPanel.vue'
import NotificationMessage from '@/components/notifications/NotificationMessage.vue'
import { i18n } from '@/plugins/i18n'

describe('DashboardCharts.vue', () => {
  beforeEach(() => {
    init_plugins()
    i18n.global.locale.value = 'en'
    const cluster = {
      name: 'foo',
      permissions: { roles: ['admin'], actions: ['view-nodes', 'view-jobs'] },
      racksdb: true,
      infrastructure: 'foo',
      metrics: true,
      cache: true
    }
    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [cluster]
    runtimeStore.currentCluster = cluster
  })
  test('should not display notification by default', () => {
    const wrapper = mount(NotificationsPanel)
    // check main div is fixed
    expect(wrapper.find('div').classes('fixed')).toBeTruthy()
    // empty by default
    expect(wrapper.findComponent(NotificationMessage).exists()).toBe(false)
  })
  test('should display reported info/error notifications', async () => {
    const runtimeStore = useRuntimeStore()
    runtimeStore.reportInfo('test info')
    runtimeStore.reportError('test error')
    const wrapper = mount(NotificationsPanel)
    // check presence of 2 notifications
    expect(wrapper.findAllComponents(NotificationMessage).length).toBe(2)
  })

  test('should translate notification type labels', async () => {
    const runtimeStore = useRuntimeStore()
    runtimeStore.reportInfo('test info')
    const wrapper = mount(NotificationsPanel)

    expect(wrapper.text()).toContain('Info')

    i18n.global.locale.value = 'zh-CN'
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('提示')
  })
})
