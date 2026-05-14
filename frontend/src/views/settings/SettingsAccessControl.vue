<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type {
  AccessControlCatalog,
  AccessControlUserAssignment,
  AccessControlUserRow,
  ClusterDescription,
  CustomRole,
  CustomRolePayload,
  PermissionRule
} from '@/composables/GatewayAPI'
import { hasClusterAccessControl, useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import AdminTabs from '@/components/admin/AdminTabs.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

type PermissionOperation = 'view' | 'edit' | 'delete' | '*'
type PermissionScope = '*' | 'self'

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const route = useRoute()
const { t } = useI18n()

const isAdminRoute = computed(() => String(route.name ?? '').startsWith('admin-'))
const tabsComponent = computed(() => (isAdminRoute.value ? AdminTabs : SettingsTabs))
const headerComponent = computed(() => (isAdminRoute.value ? AdminHeader : SettingsHeader))
const catalog = ref<AccessControlCatalog | null>(null)
const catalogLoading = ref(false)
const catalogError = ref<string | null>(null)

const roles = ref<CustomRole[]>([])
const rolesLoading = ref(false)
const rolesError = ref<string | null>(null)
const rolesFormError = ref<string | null>(null)
const rolesSubmitting = ref(false)

const users = ref<AccessControlUserRow[]>([])
const usersLoading = ref(false)
const usersError = ref<string | null>(null)
const userAssignmentLoading = ref(false)
const userAssignmentError = ref<string | null>(null)
const userAssignmentSaving = ref(false)
const selectedUsername = ref<string | null>(null)
const selectedUserDetails = ref<AccessControlUserAssignment | null>(null)
const usersPage = ref(1)
const usersPageSize = 20
const usersTotal = ref(0)
const userSearch = ref('')

const roleForm = reactive<{
  id: number | null
  name: string
  description: string
  permissions: PermissionRule[]
}>({
  id: null,
  name: '',
  description: '',
  permissions: []
})

const assignedRoleIds = ref<number[]>([])

const settingsCluster = computed<ClusterDescription | undefined>(() => {
  if (runtimeStore.currentCluster) return runtimeStore.currentCluster
  const routeCluster = runtimeStore.beforeSettingsRoute?.params?.cluster
  if (typeof routeCluster === 'string') {
    const cluster = runtimeStore.getCluster(routeCluster)
    if (cluster) return cluster
  }
  return runtimeStore.getAllowedClusters()[0]
})

const accessControlAvailable = computed(() => hasClusterAccessControl(settingsCluster.value))
const canView = computed(
  () =>
    !!settingsCluster.value &&
    runtimeStore.hasRoutePermission(
      settingsCluster.value.name,
      isAdminRoute.value ? 'admin/access-control' : 'settings/access-control',
      'view'
    )
)
const canManage = computed(
  () =>
    !!settingsCluster.value &&
    runtimeStore.hasRoutePermission(
      settingsCluster.value.name,
      isAdminRoute.value ? 'admin/access-control' : 'settings/access-control',
      'edit'
    )
)
const canDelete = computed(
  () =>
    !!settingsCluster.value &&
    runtimeStore.hasRoutePermission(
      settingsCluster.value.name,
      isAdminRoute.value ? 'admin/access-control' : 'settings/access-control',
      'delete'
    )
)
const currentClusterName = computed(() => settingsCluster.value?.name ?? '')
const selectedRoleNames = computed(() =>
  roles.value.filter((role) => assignedRoleIds.value.includes(role.id)).map((role) => role.name)
)
const totalUserPages = computed(() => Math.max(Math.ceil(usersTotal.value / usersPageSize), 1))
const sortedCatalogGroups = computed(() => catalog.value?.groups ?? [])
const totalCatalogResources = computed(() =>
  sortedCatalogGroups.value.reduce((count, group) => count + group.resources.length, 0)
)

function sortRules(rules: PermissionRule[]): PermissionRule[] {
  return [...new Set(rules)].sort()
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

function permissionRuleAllows(
  rule: PermissionRule,
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

function ruleKey(resource: string, operation: string, scope: string): PermissionRule {
  return `${resource}:${operation}:${scope}`
}

function permissionsToActions(permissions: PermissionRule[]): string[] {
  const rules = sortRules(permissions)
  const legacyMap = catalog.value?.legacy_map ?? {}
  return Object.entries(legacyMap)
    .filter(([, requiredRules]) =>
      requiredRules.every((requiredRule) => {
        const [resource, operation, scope] = requiredRule.split(':')
        return permissionRuleAllows(
          rules.find((rule) =>
            permissionRuleAllows(rule, resource, operation as PermissionOperation, scope as PermissionScope)
          ) ?? '',
          resource,
          operation as PermissionOperation,
          scope as PermissionScope
        )
      })
    )
    .map(([action]) => action)
    .sort()
}

function roleActions(role: CustomRole): string[] {
  return role.actions.length > 0 ? [...role.actions].sort() : permissionsToActions(role.permissions)
}

function resetRoleForm() {
  roleForm.id = null
  roleForm.name = ''
  roleForm.description = ''
  roleForm.permissions = []
  rolesFormError.value = null
}

function rolePayload(): CustomRolePayload {
  const permissions = sortRules(roleForm.permissions)
  return {
    name: roleForm.name.trim(),
    description: roleForm.description.trim() || null,
    actions: permissionsToActions(permissions),
    permissions
  }
}

function editRole(role: CustomRole) {
  roleForm.id = role.id
  roleForm.name = role.name
  roleForm.description = role.description ?? ''
  roleForm.permissions = [...role.permissions]
  rolesFormError.value = null
}

function hasSelectedRule(resource: string, operation: string, scope: string): boolean {
  return roleForm.permissions.includes(ruleKey(resource, operation, scope))
}

function togglePermission(resource: string, operation: string, scope: string) {
  if (!canManage.value || rolesSubmitting.value) return
  const targetRule = ruleKey(resource, operation, scope)
  if (roleForm.permissions.includes(targetRule)) {
    roleForm.permissions = roleForm.permissions.filter((rule) => rule !== targetRule)
    return
  }
  roleForm.permissions = sortRules([...roleForm.permissions, targetRule])
}

async function loadCatalog() {
  if (!currentClusterName.value || !accessControlAvailable.value || !canView.value) return
  catalogLoading.value = true
  catalogError.value = null
  try {
    catalog.value = await gateway.access_catalog(currentClusterName.value)
  } catch (error: unknown) {
    catalogError.value = error instanceof Error ? error.message : String(error)
  } finally {
    catalogLoading.value = false
  }
}

async function loadRoles() {
  if (!currentClusterName.value || !accessControlAvailable.value || !canView.value) return
  rolesLoading.value = true
  rolesError.value = null
  try {
    roles.value = await gateway.access_roles(currentClusterName.value)
    if (
      selectedUserDetails.value &&
      selectedUserDetails.value.username === selectedUsername.value
    ) {
      assignedRoleIds.value = selectedUserDetails.value.custom_roles.map((role) => role.id)
    }
  } catch (error: unknown) {
    rolesError.value = error instanceof Error ? error.message : String(error)
  } finally {
    rolesLoading.value = false
  }
}

async function loadUsers() {
  if (!currentClusterName.value || !accessControlAvailable.value || !canView.value) return
  usersLoading.value = true
  usersError.value = null
  try {
    const result = await gateway.access_users(currentClusterName.value, {
      username: userSearch.value || undefined,
      page: usersPage.value,
      page_size: usersPageSize
    })
    users.value = result.items
    usersTotal.value = result.total
    usersPage.value = result.page
    if (
      selectedUsername.value &&
      !result.items.some((user) => user.username === selectedUsername.value)
    ) {
      selectedUsername.value = result.items[0]?.username ?? null
    } else if (!selectedUsername.value) {
      selectedUsername.value = result.items[0]?.username ?? null
    }
  } catch (error: unknown) {
    usersError.value = error instanceof Error ? error.message : String(error)
  } finally {
    usersLoading.value = false
  }
}

async function loadSelectedUser() {
  if (!currentClusterName.value || !selectedUsername.value || !canView.value) {
    selectedUserDetails.value = null
    assignedRoleIds.value = []
    return
  }
  userAssignmentLoading.value = true
  userAssignmentError.value = null
  try {
    selectedUserDetails.value = await gateway.access_user_roles(
      currentClusterName.value,
      selectedUsername.value
    )
    assignedRoleIds.value = selectedUserDetails.value.custom_roles.map((role) => role.id)
  } catch (error: unknown) {
    selectedUserDetails.value = null
    assignedRoleIds.value = []
    userAssignmentError.value = error instanceof Error ? error.message : String(error)
  } finally {
    userAssignmentLoading.value = false
  }
}

async function reloadAll() {
  resetRoleForm()
  selectedUserDetails.value = null
  assignedRoleIds.value = []
  await Promise.all([loadCatalog(), loadRoles(), loadUsers()])
  await loadSelectedUser()
}

async function submitRole() {
  if (!currentClusterName.value) return
  const payload = rolePayload()
  if (!payload.name) {
    rolesFormError.value = t('settings.accessControl.roles.errors.roleNameRequired')
    return
  }
  if (!payload.permissions.length) {
    rolesFormError.value = t('settings.accessControl.roles.errors.permissionRequired')
    return
  }
  rolesSubmitting.value = true
  rolesFormError.value = null
  try {
    if (roleForm.id === null) {
      await gateway.create_access_role(currentClusterName.value, payload)
    } else {
      await gateway.update_access_role(currentClusterName.value, roleForm.id, payload)
    }
    resetRoleForm()
    await loadRoles()
    await loadSelectedUser()
  } catch (error: unknown) {
    rolesFormError.value = error instanceof Error ? error.message : String(error)
  } finally {
    rolesSubmitting.value = false
  }
}

async function removeRole(role: CustomRole) {
  if (!currentClusterName.value) return
  rolesFormError.value = null
  rolesSubmitting.value = true
  try {
    await gateway.delete_access_role(currentClusterName.value, role.id)
    if (roleForm.id === role.id) resetRoleForm()
    await loadRoles()
    await loadUsers()
    await loadSelectedUser()
  } catch (error: unknown) {
    rolesFormError.value = error instanceof Error ? error.message : String(error)
  } finally {
    rolesSubmitting.value = false
  }
}

function toggleAssignedRole(roleId: number) {
  if (!canManage.value) return
  if (assignedRoleIds.value.includes(roleId)) {
    assignedRoleIds.value = assignedRoleIds.value.filter((id) => id !== roleId)
  } else {
    assignedRoleIds.value = [...assignedRoleIds.value, roleId].sort((left, right) => left - right)
  }
}

async function saveUserRoles() {
  if (!currentClusterName.value || !selectedUsername.value) return
  userAssignmentSaving.value = true
  userAssignmentError.value = null
  try {
    selectedUserDetails.value = await gateway.update_access_user_roles(
      currentClusterName.value,
      selectedUsername.value,
      assignedRoleIds.value
    )
    assignedRoleIds.value = selectedUserDetails.value.custom_roles.map((role) => role.id)
    await loadUsers()
  } catch (error: unknown) {
    userAssignmentError.value = error instanceof Error ? error.message : String(error)
  } finally {
    userAssignmentSaving.value = false
  }
}

function searchUsers() {
  usersPage.value = 1
  void loadUsers().then(loadSelectedUser)
}

function resetUsersSearch() {
  userSearch.value = ''
  usersPage.value = 1
  void loadUsers().then(loadSelectedUser)
}

function changePage(offset: number) {
  const nextPage = usersPage.value + offset
  if (nextPage < 1 || nextPage > totalUserPages.value || nextPage === usersPage.value) return
  usersPage.value = nextPage
  void loadUsers().then(loadSelectedUser)
}

watch(
  () => settingsCluster.value?.name,
  () => {
    usersPage.value = 1
    userSearch.value = ''
    selectedUsername.value = null
    void reloadAll()
  }
)

watch(selectedUsername, () => {
  void loadSelectedUser()
})

onMounted(async () => {
  await reloadAll()
})
</script>

<template>
  <div class="ui-section-stack">
    <component :is="tabsComponent" entry="access-control" :cluster="currentClusterName" />
    <div class="ui-panel ui-section">
      <component
        :is="headerComponent"
        title="settings.accessControl.title"
        description="settings.accessControl.description"
      />
      <div
        v-if="settingsCluster"
        class="mt-6 flex flex-wrap items-center gap-3 rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)] px-5 py-4"
      >
        <span class="ui-page-kicker !mb-0">{{ t('settings.accessControl.activeCluster') }}</span>
        <span class="ui-chip">{{ settingsCluster.name }}</span>
        <span v-if="catalog" class="ui-chip">{{ t('settings.accessControl.resourcesCount', { count: totalCatalogResources }) }}</span>
      </div>
    </div>

    <InfoAlert v-if="!settingsCluster">
      {{ t('settings.accessControl.alerts.noClusterContext') }}
    </InfoAlert>
    <InfoAlert v-else-if="!accessControlAvailable">
      {{ t('settings.accessControl.alerts.unavailable') }}
    </InfoAlert>
    <InfoAlert v-else-if="!canView">
      {{ t('settings.accessControl.alerts.noPermission') }}
    </InfoAlert>
    <InfoAlert v-else-if="!canManage">
      {{ t('settings.accessControl.alerts.readOnly', { permission: 'admin/access-control:edit:*' }) }}
    </InfoAlert>

    <template v-else>
      <ErrorAlert v-if="catalogError">
        {{ catalogError }}
      </ErrorAlert>

      <div class="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <section class="ui-panel ui-section">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="ui-page-kicker">{{ t('settings.accessControl.roles.kicker') }}</p>
              <h2 class="ui-panel-title">{{ t('settings.accessControl.roles.title') }}</h2>
              <p class="ui-panel-description mt-2">
                {{ t('settings.accessControl.roles.description') }}
              </p>
            </div>
            <button type="button" class="ui-button-secondary" @click="reloadAll">
              {{ t('common.buttons.refresh') }}
            </button>
          </div>

          <ErrorAlert v-if="rolesError" class="mt-5">
            {{ rolesError }}
          </ErrorAlert>
          <ErrorAlert v-if="rolesFormError" class="mt-5">
            {{ rolesFormError }}
          </ErrorAlert>

          <div v-if="rolesLoading || catalogLoading" class="mt-6 text-[var(--color-brand-muted)]">
            <LoadingSpinner :size="5" />
            {{ t('settings.accessControl.roles.loading') }}
          </div>
          <InfoAlert v-else-if="roles.length === 0" class="mt-6">
            {{ t('settings.accessControl.roles.empty') }}
          </InfoAlert>
          <div v-else class="mt-6 space-y-3">
            <article
              v-for="role in roles"
              :key="role.id"
              class="rounded-[24px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)] px-5 py-4"
            >
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ role.name }}
                  </h3>
                  <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
                    {{ role.description || t('settings.accessControl.roles.noDescription') }}
                  </p>
                </div>
                <div class="flex gap-2">
                  <button
                    v-if="canManage"
                    type="button"
                    class="ui-button-warning"
                    @click="editRole(role)"
                  >
                    {{ t('common.buttons.edit') }}
                  </button>
                  <button
                    v-if="canDelete"
                    type="button"
                    class="ui-button-danger"
                    @click="removeRole(role)"
                  >
                    {{ t('common.buttons.delete') }}
                  </button>
                </div>
              </div>

              <div class="mt-4">
                <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.accessControl.roles.permissions') }}</p>
                <div class="mt-2 flex flex-wrap gap-2">
                  <span
                    v-for="permission in role.permissions"
                    :key="`${role.id}-${permission}`"
                    class="ui-chip"
                  >
                    {{ permission }}
                  </span>
                </div>
              </div>

              <div class="mt-4">
                <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.accessControl.roles.compatibilityActions') }}</p>
                <div class="mt-2 flex flex-wrap gap-2">
                  <span
                    v-for="action in roleActions(role)"
                    :key="`${role.id}-action-${action}`"
                    class="ui-chip"
                  >
                    {{ action }}
                  </span>
                  <span v-if="roleActions(role).length === 0" class="text-sm text-[var(--color-brand-muted)]">
                    {{ t('settings.accessControl.roles.noLegacyActions') }}
                  </span>
                </div>
              </div>
            </article>
          </div>

          <div
            class="mt-6 rounded-[28px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)] px-5 py-5"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="ui-page-kicker">
                  {{ roleForm.id === null ? t('settings.accessControl.roles.createKicker') : t('settings.accessControl.roles.editKicker') }}
                </p>
                <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                  {{
                    roleForm.id === null
                      ? t('settings.accessControl.roles.createTitle')
                      : t('settings.accessControl.roles.editTitle', { name: roleForm.name })
                  }}
                </h3>
              </div>
              <button
                v-if="roleForm.id !== null"
                type="button"
                class="ui-button-secondary"
                @click="resetRoleForm"
              >
                {{ t('settings.accessControl.roles.clear') }}
              </button>
            </div>

            <InfoAlert v-if="!canManage" class="mt-4">
              {{ t('settings.accessControl.alerts.readOnly', {
                permission: isAdminRoute ? 'admin/access-control:edit:*' : 'settings/access-control:edit:*'
              }) }}
            </InfoAlert>

            <form class="mt-5 space-y-5" @submit.prevent="submitRole">
              <div class="grid gap-4 lg:grid-cols-2">
                <div>
                  <label class="mb-2 block text-sm font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ t('settings.accessControl.roles.roleName') }}
                  </label>
                  <input
                    v-model="roleForm.name"
                    :disabled="!canManage || rolesSubmitting"
                    type="text"
                    class="block w-full rounded-[18px] border border-[rgba(80,105,127,0.16)] bg-white px-4 py-3 text-sm text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                    :placeholder="t('settings.accessControl.roles.roleNamePlaceholder')"
                  />
                </div>

                <div>
                  <label class="mb-2 block text-sm font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ t('settings.accessControl.roles.roleDescription') }}
                  </label>
                  <input
                    v-model="roleForm.description"
                    :disabled="!canManage || rolesSubmitting"
                    type="text"
                    class="block w-full rounded-[18px] border border-[rgba(80,105,127,0.16)] bg-white px-4 py-3 text-sm text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                    :placeholder="t('settings.accessControl.roles.roleDescriptionPlaceholder')"
                  />
                </div>
              </div>

              <div>
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.accessControl.roles.resourceMatrix') }}</p>
                    <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
                      {{ t('settings.accessControl.roles.resourceMatrixDescription') }}
                    </p>
                  </div>
                  <span class="ui-chip">{{ t('settings.accessControl.roles.selectedCount', { count: roleForm.permissions.length }) }}</span>
                </div>

                <div class="mt-4 space-y-4">
                  <section
                    v-for="group in sortedCatalogGroups"
                    :key="group.group"
                    class="rounded-[24px] border border-[rgba(80,105,127,0.1)] bg-white px-4 py-4"
                  >
                    <div class="mb-4">
                      <p class="ui-page-kicker">{{ group.label }}</p>
                      <h4 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                        {{ group.label }}
                      </h4>
                    </div>

                    <div class="space-y-3">
                      <div
                        v-for="resource in group.resources"
                        :key="resource.resource"
                        class="rounded-[20px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.72)] px-4 py-4"
                      >
                        <div class="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p class="font-semibold text-[var(--color-brand-ink-strong)]">
                              {{ resource.label }}
                            </p>
                            <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
                              <code>{{ resource.resource }}</code>
                            </p>
                          </div>
                          <div class="flex flex-wrap gap-2">
                            <label
                              v-for="scope in resource.scopes"
                              :key="`${resource.resource}-scope-${scope}`"
                              class="ui-chip"
                            >
                              {{ scope === 'self' ? t('settings.accessControl.roles.ownerAware') : t('settings.accessControl.roles.clusterWide') }}
                            </label>
                          </div>
                        </div>

                        <div class="mt-4 flex flex-wrap gap-2">
                          <label
                            v-for="operation in resource.operations"
                            :key="`${resource.resource}-${operation}`"
                            class="flex flex-wrap gap-2"
                          >
                            <span
                              v-for="scope in resource.scopes"
                              :key="`${resource.resource}-${operation}-${scope}`"
                              class="inline-flex items-center gap-2 rounded-full border border-[rgba(80,105,127,0.12)] bg-white px-3 py-2 text-sm text-[var(--color-brand-ink-strong)]"
                            >
                              <input
                                :checked="hasSelectedRule(resource.resource, operation, scope)"
                                :disabled="!canManage || rolesSubmitting"
                                type="checkbox"
                                class="h-4 w-4 rounded border-[rgba(80,105,127,0.24)] text-[var(--color-brand-deep)]"
                                @change="togglePermission(resource.resource, operation, scope)"
                              />
                              <span>
                                {{
                                  t('settings.accessControl.roles.ruleLabel', {
                                    operation,
                                    scope:
                                      scope === 'self'
                                        ? t('settings.accessControl.roles.ownerAware')
                                        : t('settings.accessControl.roles.clusterWide')
                                  })
                                }}
                              </span>
                            </span>
                          </label>
                        </div>
                      </div>
                    </div>
                  </section>
                </div>
              </div>

              <div class="rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-white px-4 py-4">
                <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.accessControl.roles.selectedRules') }}</p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <span
                    v-for="permission in sortRules(roleForm.permissions)"
                    :key="`selected-${permission}`"
                    class="ui-chip"
                  >
                    {{ permission }}
                  </span>
                  <span v-if="roleForm.permissions.length === 0" class="text-sm text-[var(--color-brand-muted)]">
                    {{ t('settings.accessControl.roles.noRulesSelected') }}
                  </span>
                </div>
                <p class="mt-4 text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.accessControl.roles.derivedActions') }}</p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <span
                    v-for="action in permissionsToActions(roleForm.permissions)"
                    :key="`derived-action-${action}`"
                    class="ui-chip"
                  >
                    {{ action }}
                  </span>
                  <span
                    v-if="permissionsToActions(roleForm.permissions).length === 0"
                    class="text-sm text-[var(--color-brand-muted)]"
                  >
                    {{ t('settings.accessControl.roles.noDerivedActions') }}
                  </span>
                </div>
              </div>

              <div class="flex flex-wrap gap-3">
                <button
                  type="submit"
                  :class="roleForm.id === null ? 'ui-button-primary' : 'ui-button-warning'"
                  :disabled="!canManage || rolesSubmitting"
                >
                  {{ roleForm.id === null ? t('settings.accessControl.roles.createSubmit') : t('settings.accessControl.roles.saveSubmit') }}
                </button>
                <button
                  type="button"
                  class="ui-button-secondary"
                  :disabled="rolesSubmitting"
                  @click="resetRoleForm"
                >
                  {{ t('settings.accessControl.roles.reset') }}
                </button>
              </div>
            </form>
          </div>
        </section>

        <section class="ui-panel ui-section">
          <div class="ui-page-tools">
            <div>
              <p class="ui-page-kicker">{{ t('settings.accessControl.users.kicker') }}</p>
              <h2 class="ui-panel-title">{{ t('settings.accessControl.users.title') }}</h2>
              <p class="ui-panel-description mt-2">
                {{ t('settings.accessControl.users.description') }}
              </p>
            </div>
          </div>

          <ErrorAlert v-if="usersError" class="mt-5">
            {{ usersError }}
          </ErrorAlert>
          <ErrorAlert v-if="userAssignmentError" class="mt-5">
            {{ userAssignmentError }}
          </ErrorAlert>

          <div class="mt-5 ui-admin-search-bar">
            <div class="ui-admin-search-fields">
              <input
                v-model="userSearch"
                type="search"
                class="ui-input-field ui-admin-search-field"
                :placeholder="t('settings.accessControl.users.searchPlaceholder')"
                @keyup.enter="searchUsers"
              />
            </div>
            <div class="ui-admin-search-actions">
              <button type="button" class="ui-button-primary" @click="searchUsers">
                {{ t('common.buttons.search') }}
              </button>
              <button type="button" class="ui-button-secondary" @click="resetUsersSearch">
                {{ t('common.buttons.reset') }}
              </button>
              <button type="button" class="ui-button-secondary" @click="loadUsers">
                {{ t('common.buttons.refresh') }}
              </button>
            </div>
          </div>

          <div v-if="usersLoading" class="mt-6 text-[var(--color-brand-muted)]">
            <LoadingSpinner :size="5" />
            {{ t('settings.accessControl.users.loading') }}
          </div>
          <InfoAlert v-else-if="users.length === 0" class="mt-6">
            {{ t('settings.accessControl.users.empty') }}
          </InfoAlert>
          <div v-else class="mt-6 grid gap-3">
            <button
              v-for="user in users"
              :key="user.username"
              type="button"
              class="rounded-[22px] border px-4 py-4 text-left transition"
              :class="
                selectedUsername === user.username
                  ? 'border-[rgba(182,232,44,0.55)] bg-[rgba(182,232,44,0.12)]'
                  : 'border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)]'
              "
              @click="selectedUsername = user.username"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ user.username }}
                  </p>
                  <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
                    {{ user.fullname || t('settings.accessControl.users.noFullNameCached') }}
                  </p>
                </div>
                <span class="ui-chip">
                  {{
                    user.custom_roles.length === 1
                      ? t('settings.accessControl.users.roleCount', { count: user.custom_roles.length })
                      : t('settings.accessControl.users.roleCountPlural', { count: user.custom_roles.length })
                  }}
                </span>
              </div>
            </button>
          </div>

          <div v-if="users.length > 0" class="mt-5 flex items-center justify-between gap-3 text-sm">
            <button
              type="button"
              class="ui-button-secondary"
              :disabled="usersPage <= 1"
              @click="changePage(-1)"
            >
              {{ t('common.buttons.previous') }}
            </button>
            <span class="text-[var(--color-brand-muted)]">
              {{ t('settings.accessControl.users.page', { page: usersPage, total: totalUserPages }) }}
            </span>
            <button
              type="button"
              class="ui-button-secondary"
              :disabled="usersPage >= totalUserPages"
              @click="changePage(1)"
            >
              {{ t('common.buttons.next') }}
            </button>
          </div>

          <div
            class="mt-6 rounded-[28px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)] px-5 py-5"
          >
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="ui-page-kicker">{{ t('settings.accessControl.users.assignmentKicker') }}</p>
                <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                  {{
                    selectedUsername
                      ? t('settings.accessControl.users.assignmentTitle', { user: selectedUsername })
                      : t('settings.accessControl.users.assignmentEmptyTitle')
                  }}
                </h3>
                <p class="mt-2 text-sm text-[var(--color-brand-muted)]">
                  {{ t('settings.accessControl.users.assignmentDescription') }}
                </p>
              </div>
              <button
                v-if="selectedUsername"
                type="button"
                class="ui-button-secondary"
                @click="loadSelectedUser"
              >
                {{ t('common.buttons.refresh') }}
              </button>
            </div>

            <div v-if="userAssignmentLoading" class="mt-5 text-[var(--color-brand-muted)]">
              <LoadingSpinner :size="5" />
              {{ t('settings.accessControl.users.loadingAssignment') }}
            </div>
            <InfoAlert v-else-if="!selectedUsername" class="mt-5">
              {{ t('settings.accessControl.users.selectUserNotice') }}
            </InfoAlert>
            <template v-else-if="selectedUserDetails">
              <div class="mt-5 grid gap-4 lg:grid-cols-3">
                <section class="rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-white px-4 py-4">
                  <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.accessControl.users.policyRoles') }}</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <span
                      v-for="role in [...selectedUserDetails.policy_roles].sort()"
                      :key="`policy-role-${role}`"
                      class="ui-chip"
                    >
                      {{ role }}
                    </span>
                    <span v-if="selectedUserDetails.policy_roles.length === 0" class="text-sm text-[var(--color-brand-muted)]">
                      {{ t('settings.accessControl.users.none') }}
                    </span>
                  </div>
                </section>
                <section class="rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-white px-4 py-4">
                  <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.accessControl.users.customRoles') }}</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <span
                      v-for="roleName in [...selectedRoleNames].sort()"
                      :key="`custom-role-${roleName}`"
                      class="ui-chip"
                    >
                      {{ roleName }}
                    </span>
                    <span v-if="selectedRoleNames.length === 0" class="text-sm text-[var(--color-brand-muted)]">
                      {{ t('settings.accessControl.users.none') }}
                    </span>
                  </div>
                </section>
                <section class="rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-white px-4 py-4">
                  <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.accessControl.users.mergedActions') }}</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <span
                      v-for="action in [...new Set([...selectedUserDetails.policy_actions, ...selectedUserDetails.custom_actions])].sort()"
                      :key="`merged-action-${action}`"
                      class="ui-chip"
                    >
                      {{ action }}
                    </span>
                    <span
                      v-if="
                        [...new Set([...selectedUserDetails.policy_actions, ...selectedUserDetails.custom_actions])]
                          .length === 0
                      "
                      class="text-sm text-[var(--color-brand-muted)]"
                    >
                      {{ t('settings.accessControl.users.none') }}
                    </span>
                  </div>
                </section>
              </div>

              <div class="mt-5">
                <p class="mb-3 text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.accessControl.users.assignedRoles') }}</p>
                <div v-if="roles.length === 0" class="text-sm text-[var(--color-brand-muted)]">
                  {{ t('settings.accessControl.users.createRoleFirst') }}
                </div>
                <div v-else class="grid gap-3">
                  <label
                    v-for="role in roles"
                    :key="`assign-${selectedUsername}-${role.id}`"
                    class="flex items-start gap-3 rounded-[18px] border border-[rgba(80,105,127,0.12)] bg-white px-4 py-3"
                  >
                    <input
                      :checked="assignedRoleIds.includes(role.id)"
                      :disabled="!canManage || userAssignmentSaving"
                      type="checkbox"
                      class="mt-1 h-4 w-4 rounded border-[rgba(80,105,127,0.24)] text-[var(--color-brand-deep)]"
                      @change="toggleAssignedRole(role.id)"
                    />
                    <div>
                      <p class="font-semibold text-[var(--color-brand-ink-strong)]">{{ role.name }}</p>
                      <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
                        {{ role.description || t('settings.accessControl.users.noDescription') }}
                      </p>
                      <div class="mt-2 flex flex-wrap gap-2">
                        <span
                          v-for="permission in role.permissions"
                          :key="`assign-${role.id}-${permission}`"
                          class="ui-chip"
                        >
                          {{ permission }}
                        </span>
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              <div class="mt-5 flex flex-wrap gap-3">
                <button
                  type="button"
                  class="ui-button-warning"
                  :disabled="!canManage || userAssignmentSaving"
                  @click="saveUserRoles"
                >
                  {{ t('settings.accessControl.users.saveAssignments') }}
                </button>
                <button
                  type="button"
                  class="ui-button-secondary"
                  :disabled="userAssignmentSaving"
                  @click="loadSelectedUser"
                >
                  {{ t('settings.accessControl.users.resetSelection') }}
                </button>
              </div>
            </template>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
