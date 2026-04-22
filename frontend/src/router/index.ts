/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { createRouter, createWebHistory, type RouteLocation } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useRuntimeStore } from '@/stores/runtime'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'

const DashboardView = () => import('@/views/DashboardView.vue')
const LoginView = () => import('@/views/LoginView.vue')
const AnonymousView = () => import('@/views/AnonymousView.vue')
const SignoutView = () => import('@/views/SignoutView.vue')
const SettingsLayout = () => import('@/components/settings/SettingsLayout.vue')
const SettingsMainView = () => import('@/views/settings/SettingsMain.vue')
const SettingsErrorsView = () => import('@/views/settings/SettingsErrors.vue')
const SettingsAccountView = () => import('@/views/settings/SettingsAccount.vue')
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

router.beforeEach(async (to, from) => {
  /* redirect to login page if not logged in and trying to access a restricted page */
  const publicPages = [
    '/login',
    '/signout',
    '/anonymous',
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
        `New cluster ${runtime.currentCluster?.name} permissions: ${runtime.currentCluster?.permissions.actions}`
      )
    }
    // Guard feature-gated routes
    if (to.name === 'jobs-history' && !runtime.currentCluster?.persistence) {
      return { name: 'jobs', params: { cluster: to.params.cluster } }
    }
  } else {
    console.log(`Unsetting current cluster`)
    runtime.currentCluster = undefined
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
