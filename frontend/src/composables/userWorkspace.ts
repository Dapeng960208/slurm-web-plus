import type { ClusterDescription } from '@/composables/GatewayAPI'
type RuntimePermissionStore = {
  hasRoutePermission?: (
    clusterName: string,
    resource: string,
    operation?: 'view' | 'edit' | 'delete' | '*',
    scope?: '*' | 'self'
  ) => boolean
  hasClusterPermission?: (clusterName: string, permission: string) => boolean
}

export type UserWorkspaceSections = {
  self: boolean
  profile: boolean
  analytics: boolean
  any: boolean
}

export function isCurrentUser(targetUser: string | null | undefined, currentUser: string | null | undefined): boolean {
  if (!targetUser || !currentUser) return false
  return targetUser === currentUser
}

function hasUserWorkspacePermission(
  runtimeStore: RuntimePermissionStore,
  clusterName: string,
  resource: 'user/profile' | 'user/analysis' | 'accounts' | 'jobs',
  self: boolean
): boolean {
  if (runtimeStore.hasRoutePermission) {
    return runtimeStore.hasRoutePermission(clusterName, resource, 'view', self ? 'self' : '*')
  }
  if (!runtimeStore.hasClusterPermission) return false
  if (resource === 'user/profile' || resource === 'accounts') {
    return runtimeStore.hasClusterPermission(clusterName, 'associations-view')
  }
  return runtimeStore.hasClusterPermission(clusterName, 'view-jobs')
}

export function canViewUserProfile(
  runtimeStore: RuntimePermissionStore,
  clusterName: string,
  self: boolean
): boolean {
  return (
    hasUserWorkspacePermission(runtimeStore, clusterName, 'user/profile', self) ||
    hasUserWorkspacePermission(runtimeStore, clusterName, 'accounts', false)
  )
}

export function canViewUserAnalytics(
  runtimeStore: RuntimePermissionStore,
  cluster: ClusterDescription | undefined,
  clusterName: string,
  self: boolean
): boolean {
  return (
    Boolean(cluster?.user_metrics) &&
    (
      hasUserWorkspacePermission(runtimeStore, clusterName, 'user/analysis', self) ||
      hasUserWorkspacePermission(runtimeStore, clusterName, 'jobs', false)
    )
  )
}

export function resolveUserWorkspaceSections(
  runtimeStore: RuntimePermissionStore,
  cluster: ClusterDescription | undefined,
  clusterName: string,
  viewedUser: string | null | undefined,
  currentUser: string | null | undefined
): UserWorkspaceSections {
  const self = isCurrentUser(viewedUser, currentUser)
  const profile = canViewUserProfile(runtimeStore, clusterName, self)
  const analytics = canViewUserAnalytics(runtimeStore, cluster, clusterName, self)
  return {
    self,
    profile,
    analytics,
    any: self || profile || analytics
  }
}
