/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { createRouter, createWebHistory, type RouteLocation } from 'vue-router'
import { hasClusterAIAssistant, hasClusterAccessControl } from '@/composables/GatewayAPI'
import { resolveUserWorkspaceSections } from '@/composables/userWorkspace'
import { useAuthStore } from '@/stores/auth'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'

const DashboardView = () => import('@/views/DashboardView.vue')
const ClusterAnalysisView = () => import('@/views/ClusterAnalysisView.vue')
const LoginView = () => import('@/views/LoginView.vue')
const AnonymousView = () => import('@/views/AnonymousView.vue')
const SignoutView = () => import('@/views/SignoutView.vue')
const SettingsLayout = () => import('@/components/settings/SettingsLayout.vue')
const SettingsMainView = () => import('@/views/settings/SettingsMain.vue')
const SettingsErrorsView = () => import('@/views/settings/SettingsErrors.vue')
const SettingsAccountView = () => import('@/views/settings/SettingsAccount.vue')
const SettingsAIView = () => import('@/views/settings/SettingsAI.vue')
const SettingsAccessControlView = () => import('@/views/settings/SettingsAccessControl.vue')
const SettingsCacheView = () => import('@/views/settings/SettingsCache.vue')
const SettingsLdapCacheView = () => import('@/views/settings/SettingsLdapCache.vue')
const ClustersView = () => import('@/views/ClustersView.vue')
const JobsView = () => import('@/views/JobsView.vue')
const JobView = () => import('@/views/JobView.vue')
const JobsHistoryView = () => import('@/views/JobsHistoryView.vue')
const JobHistoryView = () => import('@/views/JobHistoryView.vue')
const ResourcesView = () => import('@/views/resources/ResourcesView.vue')
const ResourcesDiagramNodesView = () => import('@/views/resources/ResourcesDiagramNodesView.vue')
const ResourcesDiagramCoresView = () => import('@/views/resources/ResourcesDiagramCoresView.vue')
const NodeView = () => import('@/views/NodeView.vue')
const QosView = () => import('@/views/QosView.vue')
const ReservationsView = () => import('@/views/ReservationsView.vue')
const AccountsView = () => import('@/views/AccountsView.vue')
const AccountView = () => import('@/views/AccountView.vue')
const UserView = () => import('@/views/UserView.vue')
const AssistantView = () => import('@/views/AssistantView.vue')
const ForbiddenView = () => import('@/views/ForbiddenView.vue')
const JobsStatusBadges = () => import('@/views/tests/JobsStatusBadges.vue')
const NodesStatusBadges = () => import('@/views/tests/NodesStatusBadges.vue')
const NotFoundView = () => import('@/views/NotFoundView.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: {
        name: 'clusters'
      }
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/anonymous',
      name: 'anonymous',
      component: AnonymousView
    },
    {
      path: '/clusters',
      name: 'clusters',
      component: ClustersView
    },
    {
      path: '/signout',
      name: 'signout',
      component: SignoutView
    },
    {
      path: '/forbidden',
      name: 'forbidden',
      component: ForbiddenView
    },
    {
      path: '/settings',
      component: SettingsLayout,
      children: [
        {
          path: '',
          name: 'settings',
          component: SettingsMainView,
          meta: {
            settings: true
          }
        },
        {
          path: 'errors',
          name: 'settings-errors',
          component: SettingsErrorsView,
          meta: {
            settings: true
          }
        },
        {
          path: '/settings/account',
          name: 'settings-account',
          component: SettingsAccountView,
          meta: {
            settings: true
          }
        },
        {
          path: '/settings/ai',
          name: 'settings-ai',
          component: SettingsAIView,
          meta: {
            settings: true
          }
        },
        {
          path: '/settings/access-control',
          name: 'settings-access-control',
          component: SettingsAccessControlView,
          meta: {
            settings: true
          }
        },
        {
          path: '/settings/cache',
          name: 'settings-cache',
          component: SettingsCacheView,
          meta: {
            settings: true
          }
        },
        {
          path: '/settings/ldap-cache',
          name: 'settings-ldap-cache',
          component: SettingsLdapCacheView,
          meta: {
            settings: true
          }
        }
      ]
    },
    {
      path: '/:cluster',
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: DashboardView,
          props: true
        },
        {
          path: 'analysis',
          name: 'analysis',
          component: ClusterAnalysisView,
          props: true
        },
        {
          path: 'ai',
          name: 'ai',
          component: AssistantView,
          props: true
        },
        {
          path: 'assistant',
          redirect: (to: RouteLocation) => ({
            name: 'ai',
            params: { cluster: to.params.cluster }
          })
        },
        {
          path: 'jobs',
          name: 'jobs',
          component: JobsView,
          props: true
        },
        {
          path: 'jobs/history',
          name: 'jobs-history',
          component: JobsHistoryView,
          props: true
        },
        {
          path: 'jobs/history/:id',
          name: 'job-history',
          component: JobHistoryView,
          props: (route: RouteLocation) => ({
            cluster: route.params.cluster,
            id: parseInt(route.params.id as string)
          })
        },
        {
          path: 'job/:id',
          name: 'job',
          component: JobView,
          props: (route: RouteLocation) => ({
            cluster: route.params.cluster,
            id: parseInt(route.params.id as string)
          })
        },
        {
          path: 'resources',
          name: 'resources',
          component: ResourcesView,
          props: true
        },
        {
          path: 'resources/diagram/nodes',
          name: 'resources-diagram-nodes',
          component: ResourcesDiagramNodesView,
          props: true
        },
        {
          path: 'resources/diagram/cores',
          name: 'resources-diagram-cores',
          component: ResourcesDiagramCoresView,
          props: true
        },
        {
          path: 'node/:nodeName',
          name: 'node',
          component: NodeView,
          props: true
        },
        {
          path: 'qos',
          name: 'qos',
          component: QosView,
          props: true
        },
        {
          path: 'reservations',
          name: 'reservations',
          component: ReservationsView,
          props: true
        },
        {
          path: 'accounts',
          name: 'accounts',
          component: AccountsView,
          props: true
        },
        {
          path: 'accounts/:account',
          name: 'account',
          component: AccountView,
          props: true
        },
        {
          path: 'users/:user',
          name: 'user',
          component: UserView,
          props: true
        },
        {
          path: 'me',
          name: 'my-profile',
          component: UserView,
          props: (route: RouteLocation) => ({
            cluster: route.params.cluster,
            selfView: true
          })
        },
        {
          path: 'users/:user/analysis',
          name: 'user-analysis',
          redirect: (to: RouteLocation) => ({
            name: 'user',
            params: { cluster: to.params.cluster, user: to.params.user },
            query: {
              ...to.query,
              section: 'analysis'
            }
          })
        }
      ]
    },
    {
      path: '/tests/jobs-status-badges',
      name: 'tests-jobs-status-badges',
      component: JobsStatusBadges
    },
    {
      path: '/tests/nodes-status-badges',
      name: 'tests-nodes-status-badges',
      component: NodesStatusBadges
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundView
    }
  ]
})

function getSettingsCluster(runtime: ReturnType<typeof useRuntimeStore>) {
  if (runtime.currentCluster) return runtime.currentCluster
  const routeCluster = runtime.beforeSettingsRoute?.params?.cluster
  if (typeof routeCluster === 'string') {
    const cluster = runtime.getCluster(routeCluster)
    if (cluster) return cluster
  }
  return runtime.getAllowedClusters()[0]
}

function forbiddenRoute(
  cluster: string | null | undefined,
  permission: string
): { name: string; query: Record<string, string> } {
  return {
    name: 'forbidden',
    query: {
      ...(cluster ? { cluster } : {}),
      permission
    }
  }
}

function clusterRoutePermission(
  routeName: string | symbol | null | undefined
): { resource: string; operation: 'view' } | null {
  switch (routeName) {
    case 'dashboard':
      return { resource: 'dashboard', operation: 'view' }
    case 'analysis':
      return { resource: 'analysis', operation: 'view' }
    case 'ai':
      return { resource: 'ai', operation: 'view' }
    case 'jobs':
    case 'job':
      return { resource: 'jobs', operation: 'view' }
    case 'jobs-history':
    case 'job-history':
      return { resource: 'jobs-history', operation: 'view' }
    case 'resources':
    case 'resources-diagram-nodes':
    case 'resources-diagram-cores':
    case 'node':
      return { resource: 'resources', operation: 'view' }
    case 'qos':
      return { resource: 'qos', operation: 'view' }
    case 'reservations':
      return { resource: 'reservations', operation: 'view' }
    case 'accounts':
    case 'account':
      return { resource: 'accounts', operation: 'view' }
    default:
      return null
  }
}

router.beforeEach(async (to, from) => {
  /* redirect to login page if not logged in and trying to access a restricted page */
  const publicPages = [
    '/login',
    '/signout',
    '/anonymous',
    '/forbidden',
    '/tests/jobs-status-badges',
    '/tests/nodes-status-badges'
  ]
  const authRequired = !publicPages.includes(to.path) && to.name !== 'not-found'
  const auth = useAuthStore()
  const runtime = useRuntimeStore()
  const runtimeConfiguration = useRuntimeConfiguration()

  if (to.name == 'login' && !runtimeConfiguration.authentication) {
    return '/anonymous'
  }

  if (authRequired && !auth.token) {
    auth.returnUrl = to.fullPath
    if (runtimeConfiguration.authentication) {
      return '/login'
    } else {
      return '/anonymous'
    }
  }
  runtime.routePath = to.path as string

  if (to.params.cluster) {
    if (!runtime.currentCluster || to.params.cluster !== runtime.currentCluster.name) {
      runtime.currentCluster = runtime.getCluster(to.params.cluster as string)
      console.log(
        `New cluster ${runtime.currentCluster?.name} permissions: ${runtime.currentCluster?.permissions.rules}`
      )
    }
    const requiredPermission = clusterRoutePermission(to.name)
    if (
      requiredPermission &&
      !runtime.hasRoutePermission(
        to.params.cluster as string,
        requiredPermission.resource,
        requiredPermission.operation
      )
    ) {
      return forbiddenRoute(
        to.params.cluster as string,
        `${requiredPermission.resource}:${requiredPermission.operation}:*`
      )
    }
    // Guard feature-gated routes
    if (
      (to.name === 'jobs-history' || to.name === 'job-history') &&
      !runtime.currentCluster?.persistence
    ) {
      return { name: 'jobs', params: { cluster: to.params.cluster } }
    }
    if (
      (to.name === 'jobs-history' || to.name === 'job-history') &&
      !runtime.hasRoutePermission(to.params.cluster as string, 'jobs-history', 'view')
    ) {
      return forbiddenRoute(to.params.cluster as string, 'jobs-history:view:*')
    }
  } else {
    console.log(`Unsetting current cluster`)
    runtime.currentCluster = undefined
  }

  if (
    to.name === 'settings-access-control' &&
    !hasClusterAccessControl(getSettingsCluster(runtime))
  ) {
    return { name: 'settings-account' }
  }
  if (
    to.name === 'settings-access-control' &&
    !runtime.hasRoutePermission(
      getSettingsCluster(runtime)?.name ?? '',
      'settings/access-control',
      'view'
    )
  ) {
    return forbiddenRoute(getSettingsCluster(runtime)?.name, 'settings/access-control:view:*')
  }
  if (to.name === 'settings-ai') {
    const settingsCluster = getSettingsCluster(runtime)
    if (
      !hasClusterAIAssistant(settingsCluster) ||
      !settingsCluster
    ) {
      return { name: 'settings' }
    }
    if (!runtime.hasRoutePermission(settingsCluster.name, 'settings/ai', 'view')) {
      return forbiddenRoute(settingsCluster.name, 'settings/ai:view:*')
    }
  }
  if (to.name === 'ai' && !hasClusterAIAssistant(runtime.currentCluster)) {
    return { name: 'dashboard', params: { cluster: to.params.cluster } }
  }
  if (
    to.name === 'ai' &&
    !runtime.hasRoutePermission(to.params.cluster as string, 'ai', 'view')
  ) {
    return forbiddenRoute(to.params.cluster as string, 'ai:view:*')
  }

  if (to.name === 'user' || to.name === 'my-profile') {
    const clusterName = to.params.cluster as string
    const cluster = runtime.getCluster(clusterName)
    const viewedUser =
      to.name === 'my-profile' ? auth.username : (to.params.user as string | undefined)
    const sections = resolveUserWorkspaceSections(
      runtime,
      cluster,
      clusterName,
      viewedUser,
      auth.username
    )
    if (!sections.any) {
      return forbiddenRoute(clusterName, 'user/profile:view:* or user/analysis:view:*')
    }
  }

  /* If entering settings page, save previous route to get it back */
  if (
    from.name !== undefined &&
    runtime.beforeSettingsRoute === undefined &&
    'settings' in to.meta
  ) {
    runtime.beforeSettingsRoute = from
  }
})

export default router
