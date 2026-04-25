import { describe, test, beforeEach, afterEach, expect } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useRuntimeStore } from '@/stores/runtime'

describe('Runtime Store', () => {
  beforeEach(() => {
    // creates a fresh pinia and makes it active
    // so it's automatically picked up by any useStore() call
    // without having to pass it to it: `useStore(pinia)`
    setActivePinia(createPinia())
  })
  afterEach(() => {
    localStorage.removeItem('availableClusters')
  })
  test('add and get cluster', () => {
    const runtime = useRuntimeStore()
    const clusterFoo = {
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    const clusterBar = {
      name: 'bar',
      infrastructure: 'bar',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    runtime.addCluster(clusterFoo)
    runtime.addCluster(clusterBar)
    expect(runtime.getCluster('foo')).toEqual(clusterFoo)
  })
  test('get cluster not found', () => {
    const runtime = useRuntimeStore()
    const clusterFoo = {
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    const clusterBar = {
      name: 'bar',
      infrastructure: 'bar',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    runtime.addCluster(clusterFoo)
    runtime.addCluster(clusterBar)
    expect(runtime.getCluster('baz')).toBeUndefined()
  })
  test('get available clusters', () => {
    const runtime = useRuntimeStore()
    const clusterFoo = {
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    const clusterBar = {
      name: 'bar',
      infrastructure: 'bar',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    runtime.addCluster(clusterFoo)
    runtime.addCluster(clusterBar)
    expect(runtime.availableClusters).toStrictEqual([clusterFoo, clusterBar])
  })
  test('get allowed clusters', () => {
    const runtime = useRuntimeStore()
    const clusterFoo = {
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    const clusterBar = {
      name: 'bar',
      infrastructure: 'bar',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: [] }
    }
    runtime.addCluster(clusterFoo)
    runtime.addCluster(clusterBar)
    expect(runtime.getAllowedClusters()).toStrictEqual([clusterFoo])
  })
  test('check cluster available', () => {
    const runtime = useRuntimeStore()
    const clusterFoo = {
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    const clusterBar = {
      name: 'bar',
      infrastructure: 'bar',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    runtime.addCluster(clusterFoo)
    runtime.addCluster(clusterBar)
    expect(runtime.checkClusterAvailable('foo')).toBeTruthy()
    expect(runtime.checkClusterAvailable('baz')).toBeFalsy()
  })
  test('has cluster permission', () => {
    const runtime = useRuntimeStore()
    const clusterFoo = {
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs', 'view-nodes'] }
    }
    const clusterBar = {
      name: 'bar',
      infrastructure: 'bar',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: { roles: ['user', 'admin'], actions: ['view-jobs'] }
    }
    runtime.addCluster(clusterFoo)
    runtime.addCluster(clusterBar)
    expect(runtime.hasClusterPermission('foo', 'view-nodes')).toBeTruthy()
    expect(runtime.hasClusterPermission('bar', 'view-nodes')).toBeFalsy()
  })

  test('has route permission respects jobs self scope', () => {
    const runtime = useRuntimeStore()
    runtime.addCluster({
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: {
        roles: [],
        actions: [],
        rules: ['jobs:view:self', 'jobs:edit:self', 'jobs:delete:self']
      }
    })

    expect(runtime.hasRoutePermission('foo', 'jobs', 'view', 'self')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'jobs', 'edit', 'self')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'jobs', 'delete', 'self')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'jobs', 'view')).toBe(false)
    expect(runtime.hasRoutePermission('foo', 'jobs', 'edit')).toBe(false)
    expect(runtime.hasRoutePermission('foo', 'jobs', 'delete')).toBe(false)
  })

  test('has route permission supports admin resources independently of legacy settings resources', () => {
    const runtime = useRuntimeStore()
    runtime.addCluster({
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: {
        roles: ['admin'],
        actions: [],
        rules: ['admin/system:view:*', 'admin/cache:edit:*', 'admin/access-control:delete:*']
      }
    })

    expect(runtime.hasRoutePermission('foo', 'admin/system', 'view')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'admin/cache', 'edit')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'admin/access-control', 'delete')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'settings/cache', 'view')).toBe(false)
    expect(runtime.hasRoutePermission('foo', 'settings/access-control', 'view')).toBe(false)
  })

  test('legacy actions normalize admin-manage and edit-own-jobs without granting cache delete access', () => {
    const runtime = useRuntimeStore()
    runtime.addCluster({
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: {
        roles: ['admin'],
        actions: ['admin-manage', 'edit-own-jobs'],
        rules: []
      }
    })

    expect(runtime.hasRoutePermission('foo', 'jobs', 'edit', 'self')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'admin/system', 'view')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'admin/system', 'edit')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'admin/system', 'delete')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'admin/cache', 'edit')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'admin/cache', 'delete')).toBe(false)
  })

  test('wildcard admin rules grant global view and edit without implying delete', () => {
    const runtime = useRuntimeStore()
    runtime.addCluster({
      name: 'foo',
      infrastructure: 'foo',
      racksdb: true,
      metrics: true,
      cache: true,
      permissions: {
        roles: ['admin'],
        actions: [],
        rules: ['*:view:*', '*:edit:*']
      }
    })

    expect(runtime.hasRoutePermission('foo', 'dashboard', 'view')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'resources', 'edit')).toBe(true)
    expect(runtime.hasRoutePermission('foo', 'resources', 'delete')).toBe(false)
  })
})
