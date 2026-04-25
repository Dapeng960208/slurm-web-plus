import { describe, expect, test } from 'vitest'
import type { ClusterDescription } from '@/composables/GatewayAPI'
import {
  canViewUserAnalytics,
  canViewUserProfile,
  isCurrentUser,
  resolveUserWorkspaceSections
} from '@/composables/userWorkspace'

function buildRuntimeStore(permissions: string[]) {
  return {
    hasClusterPermission: (_clusterName: string, permission: string) => permissions.includes(permission)
  }
}

function buildCluster(userMetrics: boolean): ClusterDescription {
  return {
    name: 'foo',
    permissions: { roles: [], actions: [] },
    racksdb: true,
    infrastructure: 'foo',
    metrics: true,
    cache: true,
    user_metrics: userMetrics
  }
}

describe('userWorkspace', () => {
  test('detects the current user correctly', () => {
    expect(isCurrentUser('alice', 'alice')).toBe(true)
    expect(isCurrentUser('alice', 'bob')).toBe(false)
    expect(isCurrentUser(null, 'alice')).toBe(false)
  })

  test('resolves self workspace even without profile or analytics permissions', () => {
    const sections = resolveUserWorkspaceSections(
      buildRuntimeStore([]),
      buildCluster(false),
      'foo',
      'alice',
      'alice'
    )

    expect(sections).toEqual({
      self: true,
      profile: false,
      analytics: false,
      any: true
    })
  })

  test('resolves partial access for other users', () => {
    const runtimeStore = buildRuntimeStore(['associations-view'])
    const cluster = buildCluster(true)

    expect(canViewUserProfile(runtimeStore, 'foo')).toBe(true)
    expect(canViewUserAnalytics(runtimeStore, cluster, 'foo')).toBe(false)
    expect(resolveUserWorkspaceSections(runtimeStore, cluster, 'foo', 'bob', 'alice')).toEqual({
      self: false,
      profile: true,
      analytics: false,
      any: true
    })
  })

  test('requires permissions or self access for other users', () => {
    const sections = resolveUserWorkspaceSections(
      buildRuntimeStore([]),
      buildCluster(false),
      'foo',
      'bob',
      'alice'
    )

    expect(sections.any).toBe(false)
  })

  test('enables analytics only when capability and permission are both present', () => {
    const runtimeStore = buildRuntimeStore(['view-jobs'])

    expect(canViewUserAnalytics(runtimeStore, buildCluster(true), 'foo')).toBe(true)
    expect(canViewUserAnalytics(runtimeStore, buildCluster(false), 'foo')).toBe(false)
  })
})
