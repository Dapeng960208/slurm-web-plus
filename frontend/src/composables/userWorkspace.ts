import type { ClusterDescription } from '@/composables/GatewayAPI'
type RuntimePermissionStore = {
  hasClusterPermission: (clusterName: string, permission: string) => boolean
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

export function canViewUserProfile(
  runtimeStore: RuntimePermissionStore,
  clusterName: string
): boolean {
  return runtimeStore.hasClusterPermission(clusterName, 'associations-view')
}

export function canViewUserAnalytics(
  runtimeStore: RuntimePermissionStore,
  cluster: ClusterDescription | undefined,
  clusterName: string
): boolean {
  return Boolean(cluster?.user_metrics) && runtimeStore.hasClusterPermission(clusterName, 'view-jobs')
}

export function resolveUserWorkspaceSections(
  runtimeStore: RuntimePermissionStore,
  cluster: ClusterDescription | undefined,
  clusterName: string,
  viewedUser: string | null | undefined,
  currentUser: string | null | undefined
): UserWorkspaceSections {
  const self = isCurrentUser(viewedUser, currentUser)
  const profile = canViewUserProfile(runtimeStore, clusterName)
  const analytics = canViewUserAnalytics(runtimeStore, cluster, clusterName)
  return {
    self,
    profile,
    analytics,
    any: self || profile || analytics
  }
}
