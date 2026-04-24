<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import type {
  AccessControlUserAssignment,
  AccessControlUserRow,
  ClusterDescription,
  CustomRole,
  CustomRolePayload
} from '@/composables/GatewayAPI'
import { hasClusterAccessControl, useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const ACTION_OPTIONS = [
  'view-stats',
  'view-jobs',
  'view-history-jobs',
  'view-nodes',
  'view-partitions',
  'view-qos',
  'view-accounts',
  'associations-view',
  'view-reservations',
  'cache-view',
  'cache-reset',
  'roles-view',
  'roles-manage'
] as const

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()

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
  actions: string[]
}>({
  id: null,
  name: '',
  description: '',
  actions: []
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
    runtimeStore.hasClusterPermission(settingsCluster.value.name, 'roles-view')
)
const canManage = computed(
  () =>
    !!settingsCluster.value &&
    runtimeStore.hasClusterPermission(settingsCluster.value.name, 'roles-manage')
)
const currentClusterName = computed(() => settingsCluster.value?.name ?? '')
const selectedRoleNames = computed(() =>
  roles.value.filter((role) => assignedRoleIds.value.includes(role.id)).map((role) => role.name)
)
const totalUserPages = computed(() => Math.max(Math.ceil(usersTotal.value / usersPageSize), 1))

function resetRoleForm() {
  roleForm.id = null
  roleForm.name = ''
  roleForm.description = ''
  roleForm.actions = []
  rolesFormError.value = null
}

function rolePayload(): CustomRolePayload {
  return {
    name: roleForm.name.trim(),
    description: roleForm.description.trim() || null,
    actions: [...roleForm.actions].sort()
  }
}

function editRole(role: CustomRole) {
  roleForm.id = role.id
  roleForm.name = role.name
  roleForm.description = role.description ?? ''
  roleForm.actions = [...role.actions]
  rolesFormError.value = null
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
  await Promise.all([loadRoles(), loadUsers()])
  await loadSelectedUser()
}

async function submitRole() {
  if (!currentClusterName.value) return
  const payload = rolePayload()
  if (!payload.name) {
    rolesFormError.value = 'Role name is required.'
    return
  }
  if (!payload.actions.length) {
    rolesFormError.value = 'Select at least one action.'
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
    <SettingsTabs entry="Access Control" />
    <div class="ui-panel ui-section">
      <SettingsHeader
        title="Access Control"
        description="Manage database-backed custom roles and assign them to cached users for the current cluster."
      />
      <div
        v-if="settingsCluster"
        class="mt-6 flex flex-wrap items-center gap-3 rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)] px-5 py-4"
      >
        <span class="ui-page-kicker !mb-0">Active Cluster</span>
        <span class="ui-chip">{{ settingsCluster.name }}</span>
      </div>
    </div>

    <InfoAlert v-if="!settingsCluster">
      No cluster context is available for access control management.
    </InfoAlert>
    <InfoAlert v-else-if="!accessControlAvailable">
      Access control is not enabled for the current cluster.
    </InfoAlert>
    <InfoAlert v-else-if="!canView">
      No permission to view access control data on this cluster.
    </InfoAlert>

    <template v-else>
      <div class="grid gap-4 xl:grid-cols-[1.15fr_1fr]">
        <section class="ui-panel ui-section">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="ui-page-kicker">Custom Roles</p>
              <h2 class="ui-panel-title">Role Definitions</h2>
              <p class="ui-panel-description mt-2">
                Define reusable action bundles stored in the local database.
              </p>
            </div>
            <button type="button" class="ui-button-secondary" @click="loadRoles">
              Refresh
            </button>
          </div>

          <ErrorAlert v-if="rolesError" class="mt-5">
            {{ rolesError }}
          </ErrorAlert>
          <ErrorAlert v-if="rolesFormError" class="mt-5">
            {{ rolesFormError }}
          </ErrorAlert>

          <div v-if="rolesLoading" class="mt-6 text-[var(--color-brand-muted)]">
            <LoadingSpinner :size="5" />
            Loading custom roles...
          </div>
          <InfoAlert v-else-if="roles.length === 0" class="mt-6">
            No custom roles have been created yet.
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
                    {{ role.description || 'No description provided.' }}
                  </p>
                </div>
                <div v-if="canManage" class="flex gap-2">
                  <button type="button" class="ui-button-secondary" @click="editRole(role)">
                    Edit
                  </button>
                  <button type="button" class="ui-button-secondary" @click="removeRole(role)">
                    Delete
                  </button>
                </div>
              </div>
              <div class="mt-4 flex flex-wrap gap-2">
                <span v-for="action in [...role.actions].sort()" :key="`${role.id}-${action}`" class="ui-chip">
                  {{ action }}
                </span>
              </div>
            </article>
          </div>

          <div
            class="mt-6 rounded-[28px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)] px-5 py-5"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="ui-page-kicker">{{ roleForm.id === null ? 'Create Role' : 'Edit Role' }}</p>
                <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                  {{ roleForm.id === null ? 'New Custom Role' : `Editing ${roleForm.name}` }}
                </h3>
              </div>
              <button
                v-if="roleForm.id !== null"
                type="button"
                class="ui-button-secondary"
                @click="resetRoleForm"
              >
                Clear
              </button>
            </div>

            <InfoAlert v-if="!canManage" class="mt-4">
              You can inspect roles on this cluster, but editing requires the `roles-manage` action.
            </InfoAlert>

            <form class="mt-5 space-y-4" @submit.prevent="submitRole">
              <div>
                <label class="mb-2 block text-sm font-semibold text-[var(--color-brand-ink-strong)]">
                  Role Name
                </label>
                <input
                  v-model="roleForm.name"
                  :disabled="!canManage || rolesSubmitting"
                  type="text"
                  class="block w-full rounded-[18px] border border-[rgba(80,105,127,0.16)] bg-white px-4 py-3 text-sm text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                  placeholder="bio-admin"
                />
              </div>

              <div>
                <label class="mb-2 block text-sm font-semibold text-[var(--color-brand-ink-strong)]">
                  Description
                </label>
                <textarea
                  v-model="roleForm.description"
                  :disabled="!canManage || rolesSubmitting"
                  rows="3"
                  class="block w-full rounded-[18px] border border-[rgba(80,105,127,0.16)] bg-white px-4 py-3 text-sm text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                  placeholder="Describe when this role should be assigned."
                />
              </div>

              <div>
                <p class="mb-3 text-sm font-semibold text-[var(--color-brand-ink-strong)]">Allowed Actions</p>
                <div class="grid gap-3 sm:grid-cols-2">
                  <label
                    v-for="action in ACTION_OPTIONS"
                    :key="action"
                    class="flex items-center gap-3 rounded-[18px] border border-[rgba(80,105,127,0.12)] bg-white px-4 py-3 text-sm text-[var(--color-brand-ink-strong)]"
                  >
                    <input
                      v-model="roleForm.actions"
                      :disabled="!canManage || rolesSubmitting"
                      :value="action"
                      type="checkbox"
                      class="h-4 w-4 rounded border-[rgba(80,105,127,0.24)] text-[var(--color-brand-deep)]"
                    />
                    <span>{{ action }}</span>
                  </label>
                </div>
              </div>

              <div class="flex flex-wrap gap-3">
                <button
                  type="submit"
                  class="ui-button-primary"
                  :disabled="!canManage || rolesSubmitting"
                >
                  {{ roleForm.id === null ? 'Create Role' : 'Save Role' }}
                </button>
                <button
                  type="button"
                  class="ui-button-secondary"
                  :disabled="rolesSubmitting"
                  @click="resetRoleForm"
                >
                  Reset
                </button>
              </div>
            </form>
          </div>
        </section>

        <section class="ui-panel ui-section">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="ui-page-kicker">User Assignment</p>
              <h2 class="ui-panel-title">User Role Bindings</h2>
              <p class="ui-panel-description mt-2">
                Assign local custom roles to cached users for this cluster.
              </p>
            </div>
            <button type="button" class="ui-button-secondary" @click="loadUsers">
              Refresh
            </button>
          </div>

          <ErrorAlert v-if="usersError" class="mt-5">
            {{ usersError }}
          </ErrorAlert>
          <ErrorAlert v-if="userAssignmentError" class="mt-5">
            {{ userAssignmentError }}
          </ErrorAlert>

          <div class="mt-5 flex flex-col gap-3 sm:flex-row">
            <input
              v-model="userSearch"
              type="text"
              class="block w-full rounded-[18px] border border-[rgba(80,105,127,0.16)] bg-white px-4 py-3 text-sm text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
              placeholder="Search username..."
              @keyup.enter="searchUsers"
            />
            <button type="button" class="ui-button-primary" @click="searchUsers">
              Search
            </button>
            <button type="button" class="ui-button-secondary" @click="resetUsersSearch">
              Reset
            </button>
          </div>

          <div v-if="usersLoading" class="mt-6 text-[var(--color-brand-muted)]">
            <LoadingSpinner :size="5" />
            Loading users...
          </div>
          <InfoAlert v-else-if="users.length === 0" class="mt-6">
            No cached users match the current search.
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
                    {{ user.fullname || 'No full name cached.' }}
                  </p>
                </div>
                <span class="ui-chip">
                  {{ user.custom_roles.length }} custom role{{ user.custom_roles.length === 1 ? '' : 's' }}
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
              Previous
            </button>
            <span class="text-[var(--color-brand-muted)]">
              Page {{ usersPage }} / {{ totalUserPages }}
            </span>
            <button
              type="button"
              class="ui-button-secondary"
              :disabled="usersPage >= totalUserPages"
              @click="changePage(1)"
            >
              Next
            </button>
          </div>

          <div
            class="mt-6 rounded-[28px] border border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)] px-5 py-5"
          >
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="ui-page-kicker">Assignment Details</p>
                <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                  {{ selectedUsername || 'Select a user' }}
                </h3>
                <p class="mt-2 text-sm text-[var(--color-brand-muted)]">
                  Override this user's effective permissions by attaching local custom roles.
                </p>
              </div>
              <button
                v-if="selectedUsername"
                type="button"
                class="ui-button-secondary"
                @click="loadSelectedUser"
              >
                Refresh
              </button>
            </div>

            <div v-if="userAssignmentLoading" class="mt-5 text-[var(--color-brand-muted)]">
              <LoadingSpinner :size="5" />
              Loading user assignment...
            </div>
            <InfoAlert v-else-if="!selectedUsername" class="mt-5">
              Select a user to inspect and modify role bindings.
            </InfoAlert>
            <template v-else-if="selectedUserDetails">
              <div class="mt-5 grid gap-4 lg:grid-cols-3">
                <section class="rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-white px-4 py-4">
                  <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">Policy Roles</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <span
                      v-for="role in [...selectedUserDetails.policy_roles].sort()"
                      :key="`policy-role-${role}`"
                      class="ui-chip"
                    >
                      {{ role }}
                    </span>
                    <span v-if="selectedUserDetails.policy_roles.length === 0" class="text-sm text-[var(--color-brand-muted)]">
                      None
                    </span>
                  </div>
                </section>
                <section class="rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-white px-4 py-4">
                  <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">Custom Roles</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <span
                      v-for="roleName in [...selectedRoleNames].sort()"
                      :key="`custom-role-${roleName}`"
                      class="ui-chip"
                    >
                      {{ roleName }}
                    </span>
                    <span v-if="selectedRoleNames.length === 0" class="text-sm text-[var(--color-brand-muted)]">
                      None
                    </span>
                  </div>
                </section>
                <section class="rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-white px-4 py-4">
                  <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">Merged Actions</p>
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
                      None
                    </span>
                  </div>
                </section>
              </div>

              <div class="mt-5">
                <p class="mb-3 text-sm font-semibold text-[var(--color-brand-ink-strong)]">Assigned Custom Roles</p>
                <div v-if="roles.length === 0" class="text-sm text-[var(--color-brand-muted)]">
                  Create at least one role before assigning users.
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
                        {{ role.description || 'No description provided.' }}
                      </p>
                      <div class="mt-2 flex flex-wrap gap-2">
                        <span
                          v-for="action in [...role.actions].sort()"
                          :key="`assign-${role.id}-${action}`"
                          class="ui-chip"
                        >
                          {{ action }}
                        </span>
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              <div class="mt-5 flex flex-wrap gap-3">
                <button
                  type="button"
                  class="ui-button-primary"
                  :disabled="!canManage || userAssignmentSaving"
                  @click="saveUserRoles"
                >
                  Save Assignments
                </button>
                <button
                  type="button"
                  class="ui-button-secondary"
                  :disabled="userAssignmentSaving"
                  @click="loadSelectedUser"
                >
                  Reset Selection
                </button>
              </div>
            </template>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
