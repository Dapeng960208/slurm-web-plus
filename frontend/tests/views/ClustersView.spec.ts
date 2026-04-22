import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import ClustersView from '@/views/ClustersView.vue'
import clusters from '../assets/clusters.json'
import { init_plugins } from '../lib/common'
import type { ClusterDescription } from '@/composables/GatewayAPI'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import ClusterListItem from '@/components/clusters/ClustersListItem.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import { APIServerError, AuthenticationError } from '@/composables/HTTPErrors'
import { useAuthStore } from '@/stores/auth'

const mockGatewayAPI = {
  clusters: vi.fn()
}

vi.mock('@/composables/GatewayAPI', () => ({
  useGatewayAPI: () => mockGatewayAPI
}))

let router

describe('ClustersView.vue', () => {
  beforeEach(() => {
    router = init_plugins()
    router.currentRoute.value.fullPath = '/clusters'
    mockGatewayAPI.clusters.mockReset()
  })

  test('display clusters list', async () => {
    expect(clusters.length).toBeGreaterThan(0)
    mockGatewayAPI.clusters.mockReturnValueOnce(Promise.resolve(clusters))
    const wrapper = shallowMount(ClustersView)
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Select a cluster')
    expect(wrapper.findAllComponents(ClusterListItem).length).toBe(clusters.length)
    expect(wrapper.findComponent(ErrorAlert).exists()).toBeFalsy()
    expect(wrapper.findComponent(InfoAlert).exists()).toBeFalsy()
  })

  test('show loading spinner before loaded', async () => {
    const wrapper = shallowMount(ClustersView)
    wrapper.getComponent(LoadingSpinner)
    expect(wrapper.text()).toContain('Loading clusters…')
  })

  test('authentication error', async () => {
    mockGatewayAPI.clusters.mockImplementationOnce(() => {
      throw new AuthenticationError('fake authentication error')
    })
    shallowMount(ClustersView)
    await flushPromises()
    expect(router.push).toHaveBeenCalledTimes(1)
    expect(router.push).toHaveBeenCalledWith({ name: 'signout' })
    expect(useAuthStore().returnUrl).toBe('/clusters')
  })

  test('show error alert on server error', async () => {
    mockGatewayAPI.clusters.mockImplementationOnce(() => {
      throw new APIServerError(500, 'fake error')
    })
    const wrapper = shallowMount(ClustersView)
    await flushPromises()
    expect(wrapper.findComponent(ErrorAlert).exists()).toBeTruthy()
  })

  test('show info alert when cluster list is empty', async () => {
    mockGatewayAPI.clusters.mockReturnValueOnce(Promise.resolve([]))
    const wrapper = shallowMount(ClustersView)
    await flushPromises()
    expect(wrapper.findComponent(InfoAlert).exists()).toBeTruthy()
  })

  test('auto redirect when a single cluster is available', async () => {
    const singleCluster: ClusterDescription = clusters[0]
    mockGatewayAPI.clusters.mockReturnValueOnce(Promise.resolve([singleCluster]))
    const wrapper = shallowMount(ClustersView)
    await flushPromises()
    const clusterItem = wrapper.findComponent(ClusterListItem)
    expect(clusterItem.exists()).toBe(true)
    clusterItem.vm.$emit('pinged', singleCluster)
    await flushPromises()
    expect(router.push).toHaveBeenCalledWith({
      name: 'dashboard',
      params: { cluster: singleCluster.name }
    })
  })

  test('no redirect when multiple clusters are available', async () => {
    expect(clusters.length).toBeGreaterThanOrEqual(2)
    mockGatewayAPI.clusters.mockReturnValueOnce(Promise.resolve(clusters))
    const wrapper = shallowMount(ClustersView)
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Select a cluster')
    expect(wrapper.findAllComponents(ClusterListItem).length).toBe(clusters.length)
    const clusterItems = wrapper.findAllComponents(ClusterListItem)
    clusterItems.forEach((item, index) => {
      item.vm.$emit('pinged', clusters[index])
    })
    await flushPromises()
    expect(router.push).not.toHaveBeenCalled()
  })

  test('show cluster list when the single cluster has errors', async () => {
    const singleCluster: ClusterDescription = { ...clusters[0] }
    mockGatewayAPI.clusters.mockReturnValueOnce(Promise.resolve([singleCluster]))
    const wrapper = shallowMount(ClustersView)
    await flushPromises()
    singleCluster.error = true
    wrapper.findComponent(ClusterListItem).vm.$emit('pinged', singleCluster)
    await flushPromises()
    expect(router.push).not.toHaveBeenCalled()
    expect(wrapper.findComponent(ClusterListItem).exists()).toBe(true)
  })
})
