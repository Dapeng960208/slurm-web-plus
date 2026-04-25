/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Ref } from 'vue'
import type { RouteLocation } from 'vue-router'
import type { ClusterDescription } from '@/composables/GatewayAPI'
import { useDashboardRuntimeStore } from './runtime/dashboard'
import { useJobsHistoryRuntimeStore } from './runtime/jobsHistory'
import { useJobsRuntimeStore } from './runtime/jobs'
import { useResourcesRuntimeStore } from './runtime/resources'

/*
 * Shared settings
 */

type NotificationType = 'INFO' | 'ERROR'

export class Notification {
  id: number
  type: NotificationType
  message: string
  timeout: number
  constructor(type: NotificationType, message: string, timeout: number) {
    this.id = Date.now()
    this.type = type
    this.message = message
    this.timeout = timeout
  }
}

class RuntimeError {
  timestamp: Date
  route: string
  message: string
  constructor(route: string, message: string) {
    this.timestamp = new Date()
    this.route = route
    this.message = message
  }
}

export interface RuntimeStore {
  reportError: CallableFunction
}

type PermissionOperation = 'view' | 'edit' | 'delete' | '*'
type PermissionScope = '*' | 'self'

const LEGACY_PERMISSION_RULES: Record<string, string[]> = {
  'view-stats': ['dashboard:view:*', 'analysis:view:*'],
  'view-jobs': ['jobs:view:*', 'jobs:view:self', 'user/analysis:view:self'],
  'view-history-jobs': ['jobs-history:view:*'],
  'view-nodes': ['resources:view:*'],
  'view-qos': ['qos:view:*', 'jobs/filter-qos:view:*'],
  'view-reservations': ['reservations:view:*'],
  'associations-view': ['accounts:view:*', 'user/profile:view:*'],
  'view-accounts': ['jobs/filter-accounts:view:*'],
  'view-partitions': ['jobs/filter-partitions:view:*', 'resources/filter-partitions:view:*'],
  'cache-view': [
    'settings/cache:view:*',
    'settings/ldap-cache:view:*',
    'admin/cache:view:*',
    'admin/ldap-cache:view:*'
  ],
  'cache-reset': ['settings/cache:edit:*', 'admin/cache:edit:*'],
  'roles-view': ['settings/access-control:view:*', 'admin/access-control:view:*'],
  'roles-manage': [
    'settings/access-control:edit:*',
    'settings/access-control:delete:*',
    'admin/access-control:edit:*',
    'admin/access-control:delete:*'
  ],
  'view-ai': ['ai:view:*', 'settings/ai:view:*', 'admin/ai:view:*'],
  'manage-ai': ['settings/ai:edit:*', 'admin/ai:edit:*']
}

function operationAllows(granted: PermissionOperation, requested: PermissionOperation): boolean {
  if (granted === '*') return true
  if (requested === 'view') return ['view', 'edit', 'delete'].includes(granted)
  return granted === requested
}

function resourceAllows(granted: string, requested: string): boolean {
  if (granted === '*') return true
  if (granted === requested) return true
  return granted.endsWith('/*') && requested.startsWith(granted.slice(0, -1))
}

function ruleAllows(
  rule: string,
  resource: string,
  operation: PermissionOperation,
  scope: PermissionScope
): boolean {
  const [grantedResource, grantedOperation, grantedScope] = rule.split(':')
  if (!grantedResource || !grantedOperation || !grantedScope) return false
  return (
    resourceAllows(grantedResource, resource) &&
    operationAllows(grantedOperation as PermissionOperation, operation) &&
    (grantedScope === '*' || grantedScope === scope)
  )
}

export const useRuntimeStore = defineStore('runtime', () => {
  const routePath: Ref<string> = ref('/')
  const beforeSettingsRoute: Ref<RouteLocation | undefined> = ref(undefined)

  const dashboard = useDashboardRuntimeStore()
  const jobsHistory = useJobsHistoryRuntimeStore()
  const jobs = useJobsRuntimeStore()
  const resources = useResourcesRuntimeStore()

  const errors: Ref<Array<RuntimeError>> = ref([])
  const notifications: Ref<Array<Notification>> = ref([])

  const availableClusters: Ref<Array<ClusterDescription>> = ref(
    JSON.parse(localStorage.getItem('availableClusters') || '[]') as ClusterDescription[]
  )
  const currentCluster: Ref<ClusterDescription | undefined> = ref()

  function addCluster(cluster: ClusterDescription) {
    availableClusters.value.push(cluster)
    localStorage.setItem('availableClusters', JSON.stringify(availableClusters.value))
  }

  function getCluster(name: string): ClusterDescription {
    return availableClusters.value.filter((cluster) => cluster.name === name)[0]
  }

  function getAllowedClusters() {
    return availableClusters.value.filter(
      (cluster) =>
        (cluster.permissions.actions?.length ?? 0) > 0 ||
        (cluster.permissions.rules?.length ?? 0) > 0
    )
  }

  function checkClusterAvailable(name: string): boolean {
    return availableClusters.value.filter((cluster) => cluster.name === name).length > 0
  }

  function hasPermission(permission: string): boolean {
    return (
      currentCluster.value === undefined ||
      (currentCluster.value.permissions.actions ?? []).includes(permission)
    )
  }

  function hasClusterPermission(clusterName: string, permission: string): boolean {
    const cluster = getCluster(clusterName)
    if (!cluster) return false
    return (cluster.permissions.actions ?? []).includes(permission)
  }

  function hasRoutePermission(
    clusterName: string,
    resource: string,
    operation: PermissionOperation = 'view',
    scope: PermissionScope = '*'
  ): boolean {
    const cluster = getCluster(clusterName)
    if (!cluster) return false
    const rules = new Set(cluster.permissions.sources?.merged?.rules ?? cluster.permissions.rules ?? [])
    if (rules.size === 0) {
      for (const action of cluster.permissions.actions ?? []) {
        for (const rule of LEGACY_PERMISSION_RULES[action] ?? []) {
          rules.add(rule)
        }
      }
    }
    return [...rules].some((rule) => ruleAllows(rule, resource, operation, scope))
  }

  function hasRoutePermissionAnyScope(
    clusterName: string,
    resource: string,
    operation: PermissionOperation = 'view',
    scopes: PermissionScope[] = ['*', 'self']
  ): boolean {
    return scopes.some((scope) => hasRoutePermission(clusterName, resource, operation, scope))
  }

  function addNotification(notification: Notification) {
    notifications.value.push(notification)
    setTimeout(removeNotification, notification.timeout * 1000, notification)
  }

  function removeNotification(searched: Notification) {
    console.log(`notification ${searched.id} is removed`)
    notifications.value = notifications.value.filter(
      (notification) => notification.id != searched.id
    )
  }

  function reportError(message: string) {
    errors.value.push(new RuntimeError(routePath.value, message))
    // Do not store more than 100 errors
    if (errors.value.length > 100) {
      errors.value = errors.value.slice(errors.value.length - 100)
    }
    addNotification(new Notification('ERROR', message, 5))
  }
  function reportInfo(message: string) {
    addNotification(new Notification('INFO', message, 5))
  }
  return {
    routePath,
    beforeSettingsRoute,
    dashboard,
    jobsHistory,
    jobs,
    resources,
    errors,
    notifications,
    availableClusters,
    currentCluster,
    addCluster,
    getCluster,
    getAllowedClusters,
    checkClusterAvailable,
    hasPermission,
    hasClusterPermission,
    hasRoutePermission,
    hasRoutePermissionAnyScope,
    addNotification,
    removeNotification,
    reportError,
    reportInfo
  }
})
