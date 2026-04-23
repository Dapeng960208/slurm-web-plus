import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ResourcesDiagramThumbnail from '@/components/resources/ResourcesDiagramThumbnail.vue'
import ResourcesFiltersBar from '@/components/resources/ResourcesFiltersBar.vue'
import ResourcesView from '@/views/resources/ResourcesView.vue'
import { init_plugins, getMockClusterDataPoller } from '../../lib/common'
import type { RouterMock } from 'vue-router-mock'
import { useRuntimeStore } from '@/stores/runtime'
import type { ClusterNode } from '@/composables/GatewayAPI'
import ErrorAlert from '@/components/ErrorAlert.vue'
import nodes from '../../assets/nodes.json'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterNode[]>()

let router: RouterMock

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

describe('ResourcesView.vue', () => {
  beforeEach(() => {
    router = init_plugins()
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
    mockClusterDataPoller.data.value = undefined
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
  })
  test('display resources', () => {
    mockClusterDataPoller.data.value = nodes
    mockClusterDataPoller.loaded.value = true
    const wrapper = mount(ResourcesView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          ResourcesDiagramThumbnail: true
        }
      }
    })
    // Diagram is hidden by default until explicitly toggled by the user.
    expect(wrapper.findComponent(ResourcesDiagramThumbnail).exists()).toBe(false)
    expect(wrapper.text()).toContain('Show Rack Diagram')
    // Check presence of ResourcesFiltersBar component
    wrapper.getComponent(ResourcesFiltersBar)
    // Check presence of table
    wrapper.get('main table')
  })
  test('table without diagram when racksdb is disabled', () => {
    mockClusterDataPoller.data.value = nodes
    // Disable racksdb on a dedicated cluster to avoid shared-state leakage.
    useRuntimeStore().availableClusters = [
      {
        ...useRuntimeStore().availableClusters[0],
        name: 'bar',
        infrastructure: 'bar',
        racksdb: false
      }
    ]
    const wrapper = mount(ResourcesView, {
      props: {
        cluster: 'bar'
      },
      global: {
        stubs: {
          ResourcesDiagramThumbnail: true
        }
      }
    })
    expect(wrapper.text()).not.toContain('Show Rack Diagram')
    expect(wrapper.findComponent(ResourcesDiagramThumbnail).exists()).toBe(false)
    // Check presence of table
    wrapper.get('main table')
  })
  test('show error alert when unable to retrieve nodes', () => {
    mockClusterDataPoller.unable.value = true
    const wrapper = mount(ResourcesView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          ResourcesDiagramThumbnail: true
        }
      }
    })
    expect(wrapper.getComponent(ErrorAlert).text()).toBe(
      'Unable to retrieve nodes from cluster foo'
    )
    // Check absence of main table
    expect(wrapper.find('main table').exists()).toBeFalsy()
  })
  test('passes loading state to ResourcesDiagramThumbnail', async () => {
    mockClusterDataPoller.data.value = nodes
    mockClusterDataPoller.loaded.value = false // Data is loading
    mockClusterDataPoller.initialLoading.value = true
    const wrapper = mount(ResourcesView, {
      props: { cluster: 'foo' },
      global: { stubs: { ResourcesDiagramThumbnail: true } }
    })
    const toggleButton = wrapper
      .findAll('button[type="button"]')
      .find((button) => button.text().includes('Show Rack Diagram'))
    if (!toggleButton) {
      throw new Error('Show Rack Diagram button not found')
    }
    await toggleButton.trigger('click')
    // Check that loading prop is passed correctly (should be true when loaded
    // is false)
    const thumbnail = wrapper.getComponent(ResourcesDiagramThumbnail)
    expect(thumbnail.props('loading')).toBe(true)
  })

  test('toggles rack diagram visibility', async () => {
    mockClusterDataPoller.data.value = nodes
    const wrapper = mount(ResourcesView, {
      props: { cluster: 'foo' },
      global: { stubs: { ResourcesDiagramThumbnail: true } }
    })

    const showButton = wrapper
      .findAll('button[type="button"]')
      .find((button) => button.text().includes('Show Rack Diagram'))
    if (!showButton) {
      throw new Error('Show Rack Diagram button not found')
    }
    await showButton.trigger('click')
    expect(wrapper.findComponent(ResourcesDiagramThumbnail).exists()).toBe(true)
    expect(wrapper.text()).toContain('Hide Rack Diagram')
  })
  test('syncs filters with URL on mount', async () => {
    mockClusterDataPoller.data.value = nodes
    mount(ResourcesView, {
      props: { cluster: 'foo' },
      global: { stubs: { ResourcesDiagramThumbnail: true } }
    })
    // onMounted should push initial query when none is set
    expect(router.push).toHaveBeenCalled()
  })

  test('uses the shared primary style for add filters button', () => {
    mockClusterDataPoller.data.value = nodes

    const wrapper = mount(ResourcesView, {
      props: { cluster: 'foo' },
      global: { stubs: { ResourcesDiagramThumbnail: true } }
    })

    const addFiltersButton = wrapper
      .findAll('button[type="button"]')
      .find((button) => button.text().includes('Add filters'))

    if (!addFiltersButton) {
      throw new Error('Add filters button not found')
    }
    expect(addFiltersButton.classes()).toContain('ui-button-primary')
  })
})
