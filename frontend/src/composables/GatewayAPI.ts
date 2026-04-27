/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { useRESTAPI } from '@/composables/RESTAPI'
import type { AxiosResponse } from 'axios'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { useRuntimeConfiguration } from '@/plugins/runtimeConfiguration'
import { AuthenticationError, APIServerError } from '@/composables/HTTPErrors'
import type { JobSortCriterion, JobSortOrder } from '@/stores/runtime/jobs'
import { useAuthStore } from '@/stores/auth'

interface loginIdents {
  user: string
  password: string
}

export interface ClusterDescription {
  name: string
  racksdb: boolean
  infrastructure: string
  metrics: boolean
  cache: boolean
  database?: boolean
  access_control?: boolean
  ai?: ClusterAICapability
  permissions: ClusterPermissions
  capabilities?: ClusterCapabilities
  versions?: ClusterVersions
  stats?: ClusterStats
  error?: boolean
  persistence?: boolean
  node_metrics?: boolean
  user_metrics?: boolean
}

export type PermissionRule = string

const LEGACY_PERMISSION_RULES: Record<string, PermissionRule[]> = {
  'view-stats': ['dashboard:view:*', 'analysis:view:*'],
  'view-jobs': ['jobs:view:*'],
  'view-history-jobs': ['jobs-history:view:*'],
  'view-nodes': ['resources:view:*'],
  'view-qos': ['qos:view:*', 'jobs/filter-qos:view:*'],
  'view-reservations': ['reservations:view:*'],
  'associations-view': ['accounts:view:*', 'user/profile:view:*'],
  'view-accounts': ['jobs/filter-accounts:view:*'],
  'view-partitions': ['jobs/filter-partitions:view:*', 'resources/filter-partitions:view:*'],
  'cache-view': ['admin/cache:view:*', 'admin/ldap-cache:view:*'],
  'cache-reset': ['admin/cache:edit:*'],
  'admin-manage': ['*:*:*']
}

export interface ClusterPermissionAssignment {
  roles: string[]
  actions: string[]
  rules: PermissionRule[]
}

export interface ClusterPermissionsSources {
  policy?: ClusterPermissionAssignment
  custom?: ClusterPermissionAssignment
  merged?: ClusterPermissionAssignment
}

export interface ClusterPermissions extends ClusterPermissionAssignment {
  sources?: ClusterPermissionsSources
}

export interface ClusterCapabilities {
  access_control?: boolean
  ai?: ClusterAICapability
  job_history?: boolean
  ldap_cache?: boolean
  node_metrics?: boolean
  user_metrics?: boolean | Record<string, unknown>
  user_analytics?: Record<string, unknown>
  [key: string]: unknown
}

export type AccessControlSourceName = keyof ClusterPermissionsSources

export interface AIProviderOption {
  key: string
  label: string
}

export interface ClusterAICapability {
  enabled?: boolean
  configurable?: boolean
  streaming?: boolean
  persistence?: boolean
  available_models_count?: number
  default_model_id?: number | null
  providers?: AIProviderOption[]
  tool_mode?: string | null
  [key: string]: unknown
}

function normalizeClusterPermissionAssignment(
  assignment?: ClusterPermissionAssignment
): ClusterPermissionAssignment {
  const rules = new Set<PermissionRule>(assignment?.rules ?? [])
  for (const action of assignment?.actions ?? []) {
    for (const rule of LEGACY_PERMISSION_RULES[action] ?? []) {
      rules.add(rule)
    }
  }
  return {
    roles: [...(assignment?.roles ?? [])],
    actions: [...(assignment?.actions ?? [])],
    rules: [...rules].sort()
  }
}

export function normalizeClusterPermissions(permissions?: ClusterPermissions): ClusterPermissions {
  const merged = normalizeClusterPermissionAssignment({
    roles: permissions?.sources?.merged?.roles ?? permissions?.roles ?? [],
    actions: permissions?.sources?.merged?.actions ?? permissions?.actions ?? [],
    rules: permissions?.sources?.merged?.rules ?? permissions?.rules ?? []
  })

  return {
    roles: merged.roles,
    actions: merged.actions,
    rules: merged.rules,
    sources: {
      policy: normalizeClusterPermissionAssignment(permissions?.sources?.policy),
      custom: normalizeClusterPermissionAssignment(permissions?.sources?.custom),
      merged
    }
  }
}

type ClusterPermissionsResponse = ClusterPermissions

type ClusterPermissionsLegacyResponse = ClusterPermissionAssignment

function clusterSupportsAccessControl(cluster?: ClusterDescription): boolean {
  return cluster?.access_control === true || cluster?.capabilities?.access_control === true
}

export function hasClusterAccessControl(cluster?: ClusterDescription): boolean {
  return clusterSupportsAccessControl(cluster)
}

function clusterSupportsAIAssistant(cluster?: ClusterDescription): boolean {
  return cluster?.ai?.enabled === true || cluster?.capabilities?.ai?.enabled === true
}

export function hasClusterAIAssistant(cluster?: ClusterDescription): boolean {
  return clusterSupportsAIAssistant(cluster)
}

function normalizeClusterAICapability(capability?: ClusterAICapability): ClusterAICapability {
  return {
    enabled: capability?.enabled ?? false,
    configurable: capability?.configurable ?? false,
    streaming: capability?.streaming ?? false,
    persistence: capability?.persistence ?? false,
    available_models_count: capability?.available_models_count ?? 0,
    default_model_id: capability?.default_model_id ?? null,
    providers: [...(capability?.providers ?? [])],
    tool_mode: capability?.tool_mode ?? null
  }
}

export interface AIModelConfig {
  id: number
  cluster?: string
  name: string
  provider: string
  provider_label?: string | null
  model: string
  display_name: string
  enabled: boolean
  is_default: boolean
  sort_order: number
  base_url: string | null
  deployment: string | null
  api_version: string | null
  request_timeout: number | null
  temperature: number | null
  system_prompt: string | null
  extra_options: Record<string, unknown>
  secret_configured: boolean
  secret_mask: string | null
  last_validated_at: string | null
  last_validation_error: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface AIModelConfigPayload {
  name: string
  provider: string
  model: string
  display_name: string
  enabled: boolean
  is_default: boolean
  sort_order: number
  base_url?: string | null
  deployment?: string | null
  api_version?: string | null
  request_timeout?: number | null
  temperature?: number | null
  system_prompt?: string | null
  extra_options?: Record<string, unknown>
  api_key?: string
  clear_secret?: boolean
}

export interface AIConversationSummary {
  id: number
  title: string
  created_at: string | null
  updated_at: string | null
  last_message: string | null
  model_config_id: number | null
}

export interface AIConversationMessage {
  id: number | string
  role: 'system' | 'user' | 'assistant'
  content: string
  created_at: string | null
  model_config_id?: number | null
  metadata?: Record<string, unknown>
}

export interface AIToolCallRecord {
  id: number
  message_id?: number | null
  tool_name: string
  permission?: string | null
  interface_key?: string | null
  status_code?: number | null
  input_payload?: Record<string, unknown>
  result_summary?: string | null
  status: 'ok' | 'error' | string
  error?: string | null
  duration_ms?: number | null
  created_at?: string | null
}

export interface AIConversation extends AIConversationSummary {
  messages: AIConversationMessage[]
  tool_calls: AIToolCallRecord[]
}

export interface AIConversationListResponse {
  items: AIConversationSummary[]
}

export interface AIModelConfigListResponse {
  items: AIModelConfig[]
}

export interface AIChatRequest {
  message: string
  conversation_id?: number | null
  model_config_id?: number | null
}

export interface AIChatConversationEvent {
  conversation_id: number
  message_id?: number
  model_config_id?: number
}

export interface AIChatToolEvent {
  tool_name: string
  interface_key?: string | null
  arguments?: Record<string, unknown>
  duration_ms?: number
  status_code?: number
  result_summary?: string
  error?: string | null
}

export interface AIChatCompleteEvent {
  conversation_id: number
  message_id: number
  model_config_id?: number
}

export interface AIChatStreamHandlers {
  onConversation?: (event: AIChatConversationEvent) => void
  onContent?: (delta: string) => void
  onToolStart?: (event: AIChatToolEvent) => void
  onToolEnd?: (event: AIChatToolEvent) => void
  onComplete?: (event: AIChatCompleteEvent) => void
  onError?: (message: string) => void
  onDone?: (event: AIChatConversationEvent) => void
}

export interface AIConfigValidationResult {
  result: string
  provider: string
  model: string
  sample: string
  last_validated_at: string | null
}

export interface AIChatStreamSession {
  controller: AbortController
  finished: Promise<void>
}

function normalizeAIModelConfig(config?: Partial<AIModelConfig>): AIModelConfig {
  return {
    id: config?.id ?? 0,
    cluster: config?.cluster,
    name: config?.name ?? '',
    provider: config?.provider ?? 'openai-compatible',
    provider_label: config?.provider_label ?? null,
    model: config?.model ?? '',
    display_name: config?.display_name ?? '',
    enabled: config?.enabled ?? false,
    is_default: config?.is_default ?? false,
    sort_order: config?.sort_order ?? 0,
    base_url: config?.base_url ?? null,
    deployment: config?.deployment ?? null,
    api_version: config?.api_version ?? null,
    request_timeout: config?.request_timeout ?? null,
    temperature: config?.temperature ?? null,
    system_prompt: config?.system_prompt ?? null,
    extra_options: { ...(config?.extra_options ?? {}) },
    secret_configured: config?.secret_configured ?? false,
    secret_mask: config?.secret_mask ?? null,
    last_validated_at: config?.last_validated_at ?? null,
    last_validation_error: config?.last_validation_error ?? null,
    created_at: config?.created_at ?? null,
    updated_at: config?.updated_at ?? null
  }
}

function normalizeAIConversationSummary(summary?: Partial<AIConversationSummary>): AIConversationSummary {
  return {
    id: summary?.id ?? 0,
    title: summary?.title ?? 'Untitled conversation',
    created_at: summary?.created_at ?? null,
    updated_at: summary?.updated_at ?? null,
    last_message: summary?.last_message ?? null,
    model_config_id: summary?.model_config_id ?? null
  }
}

function normalizeAIConversationMessage(message?: Partial<AIConversationMessage>): AIConversationMessage {
  return {
    id: message?.id ?? '',
    role: message?.role ?? 'assistant',
    content: message?.content ?? '',
    created_at: message?.created_at ?? null,
    model_config_id: message?.model_config_id ?? null,
    metadata: { ...(message?.metadata ?? {}) }
  }
}

function normalizeAIToolCallRecord(toolCall?: Partial<AIToolCallRecord>): AIToolCallRecord {
  return {
    id: toolCall?.id ?? 0,
    message_id: toolCall?.message_id ?? null,
    tool_name: toolCall?.tool_name ?? '',
    permission: toolCall?.permission ?? null,
    interface_key: toolCall?.interface_key ?? null,
    status_code: toolCall?.status_code ?? null,
    input_payload: { ...(toolCall?.input_payload ?? {}) },
    result_summary: toolCall?.result_summary ?? null,
    status: toolCall?.status ?? 'ok',
    error: toolCall?.error ?? null,
    duration_ms: toolCall?.duration_ms ?? null,
    created_at: toolCall?.created_at ?? null
  }
}

function normalizeAIConversation(conversation?: Partial<AIConversation>): AIConversation {
  return {
    ...normalizeAIConversationSummary(conversation),
    messages: (conversation?.messages ?? []).map((message) => normalizeAIConversationMessage(message)),
    tool_calls: (conversation?.tool_calls ?? []).map((toolCall) => normalizeAIToolCallRecord(toolCall))
  }
}

function isAIConversationListResponse(
  response: AIConversationListResponse | AIConversationSummary[]
): response is AIConversationListResponse {
  return typeof response === 'object' && response !== null && 'items' in response
}

export interface CustomRole {
  id: number
  name: string
  description: string | null
  actions: string[]
  permissions: PermissionRule[]
  created_at?: string | null
  updated_at?: string | null
}

export interface CustomRolePayload {
  name: string
  description?: string | null
  actions: string[]
  permissions: PermissionRule[]
}

export interface AccessControlRolesResponse {
  items: CustomRole[]
}

export interface AccessControlUserRole {
  id: number
  name: string
  description?: string | null
  actions?: string[]
  permissions?: PermissionRule[]
}

export interface AccessControlUserRow {
  username: string
  fullname: string | null
  policy_roles: string[]
  policy_actions: string[]
  custom_roles: AccessControlUserRole[]
  custom_actions: string[]
}

export interface AccessControlUsersResponse {
  items: AccessControlUserRow[]
  total: number
  page: number
  page_size: number
}

export type AccessControlUserAssignment = AccessControlUserRow

export interface AccessControlUsersFilters {
  username?: string
  page?: number
  page_size?: number
}

export interface AccessControlCatalogResource {
  resource: string
  label: string
  operations: string[]
  scopes: string[]
  owner_aware?: boolean
}

export interface AccessControlCatalogGroup {
  group: string
  label: string
  resources: AccessControlCatalogResource[]
}

export interface AccessControlCatalog {
  operations: string[]
  scopes: string[]
  groups: AccessControlCatalogGroup[]
  legacy_map: Record<string, PermissionRule[]>
}

export interface UserDescription {
  login: string
  fullname: string
}

export interface AccountDescription {
  name: string
}

interface GatewayLoginResponse extends UserDescription {
  token: string
  groups: string[]
}

interface GatewayAnonymousLoginResponse {
  token: string
}

export interface ClusterVersions {
  slurm: string
  api: string
}

interface ClusterPingResponse {
  versions: ClusterVersions
}

interface ClusterStatsResponse {
  resources: {
    nodes: number
    cores: number
    memory: number
    memory_allocated: number
    memory_available: number
    gpus: number
  }
  jobs: {
    running: number
    total: number
  }
}

export interface ClusterStats {
  resources: {
    nodes: number
    cores: number
    memory: number
    memory_allocated: number
    memory_available: number
    gpus: number
  }
  jobs: {
    running: number
    total: number
  }
}

export interface ClusterJob {
  account: string
  cpus: ClusterOptionalNumber
  gres_detail: string[]
  job_id: number
  job_state: string[]
  node_count: ClusterOptionalNumber
  nodes: string
  partition: string
  priority: ClusterOptionalNumber
  qos: string
  sockets_per_node: ClusterOptionalNumber
  state_reason: string
  tasks: ClusterOptionalNumber
  tres_per_job: string
  tres_per_node: string
  tres_per_socket: string
  tres_per_task: string
  user_name: string
}

export interface ClusterTRES {
  count: number
  id: number
  name: string
  type: string
}

export interface ClusterOptionalNumber {
  infinite: boolean
  number: number
  set: boolean
}

/* Compare two ClusterOptionalNumber a and b.
 * Return 0 if a and b are equal. On ascending order, return 1 if a is over b
 * else -1. Values are inverted in descending order. */
function compareClusterOptionalNumberOrder(
  a: ClusterOptionalNumber,
  b: ClusterOptionalNumber,
  order: JobSortOrder
): number {
  /* Check both values are set */
  if (!a.set) {
    if (b.set) {
      return order == 'asc' ? -1 : 1
    }
    return 0
  }
  if (!b.set) {
    return order == 'asc' ? 1 : -1
  }
  /* Check infinite values */
  if (a.infinite) {
    if (!b.infinite) {
      return order == 'asc' ? 1 : -1
    }
    return 0
  }
  /* Check number values */
  if (a.number > b.number) {
    return order == 'asc' ? 1 : -1
  }
  if (a.number < b.number) {
    return order == 'asc' ? -1 : 1
  }
  /* Both values are equal */
  return 0
}

export interface ClusterPreciseTime {
  seconds: number
  microseconds: number
}

export interface ClusterJobTime {
  elapsed: number
  eligible: number
  end: number
  limit: ClusterOptionalNumber
  planned: ClusterOptionalNumber
  start: number
  submission: number
  suspended: number
  system: ClusterPreciseTime
  total: ClusterPreciseTime
  user: ClusterPreciseTime
}

interface ClusterAccountedResources {
  average: ClusterTRES[]
  max: ClusterTRES[]
  min: ClusterTRES[]
  total: ClusterTRES[]
}

export interface ClusterJobStep {
  CPU: {
    governor: string
    requested_frequency: { max: ClusterOptionalNumber; min: ClusterOptionalNumber }
  }
  exit_code: ClusterJobExitCode
  kill_request_user: string
  nodes: { count: number; list: string[]; range: string }
  pid: string
  state: string[]
  statistics: { CPU: { actual_frequency: number }; energy: { consumed: ClusterOptionalNumber } }
  step: { id: string; name: string }
  task: { distribution: string }
  tasks: { count: number }
  time: {
    elapsed: number
    end: ClusterOptionalNumber
    start: ClusterOptionalNumber
    suspended: number
    system: ClusterPreciseTime
    total: ClusterPreciseTime
    user: ClusterPreciseTime
  }
  tres: {
    allocated: ClusterTRES[]
    consumed: ClusterAccountedResources
    requested: ClusterAccountedResources
  }
}

export interface ClusterJobComment {
  administrator: string
  job: string
  system: string
}

export interface ClusterJobExitCode {
  return_code: ClusterOptionalNumber
  signal: { id: ClusterOptionalNumber; name: string }
  status: string[]
}

function getOptionalNumberValue(value: ClusterOptionalNumber | null | undefined): number | null {
  if (!value || !value.set || value.infinite) {
    return null
  }
  return value.number
}

export interface ClusterIndividualJob {
  accrue_time?: ClusterOptionalNumber
  association: { account: string; cluster: string; id: number; partition: string; user: string }
  batch_flag?: boolean
  command?: string
  comment: ClusterJobComment
  cpus?: ClusterOptionalNumber
  current_working_directory?: string
  derived_exit_code: ClusterJobExitCode
  shared?: string[]
  exit_code: ClusterJobExitCode
  gres_detail?: string[]
  group: string
  last_sched_evaluation?: ClusterOptionalNumber
  name: string
  node_count?: ClusterOptionalNumber
  nodes: string
  partition: string
  priority: ClusterOptionalNumber
  qos: string
  script: string
  sockets_per_node?: ClusterOptionalNumber
  stderr_expanded?: string
  stdin_expanded?: string
  stdout_expanded?: string
  state: { current: string[]; reason: string }
  steps: ClusterJobStep[]
  submit_line: string
  tasks?: ClusterOptionalNumber
  time: ClusterJobTime
  tres: { allocated: ClusterTRES[]; requested: ClusterTRES[] }
  tres_per_job?: string
  tres_per_node?: string
  tres_per_socket?: string
  tres_per_task?: string
  tres_req_str?: string
  used_gres: string
  user: string
  wckey: { flags: string[]; wckey: string }
  working_directory: string
}

/* Compare two ClusterJob a and b on JobSortCriterion.
 * Return 0 if a and b are equal. On ascending order, return 1 if a is over b
 * else -1. Values are inverted in descending order. */
export function compareClusterJobSortOrder(
  a: ClusterJob,
  b: ClusterJob,
  sort: JobSortCriterion,
  order: JobSortOrder
): number {
  if (sort == 'user') {
    if (a.user_name > b.user_name) {
      return order == 'asc' ? 1 : -1
    }
    if (a.user_name < b.user_name) {
      return order == 'asc' ? -1 : 1
    }
    return 0
  } else if (sort == 'state') {
    if (a.job_state > b.job_state) {
      return order == 'asc' ? 1 : -1
    }
    if (a.job_state < b.job_state) {
      return order == 'asc' ? -1 : 1
    }
    return 0
  } else if (sort == 'priority') {
    return compareClusterOptionalNumberOrder(a.priority, b.priority, order)
  } else if (sort == 'resources') {
    const cmp = compareClusterOptionalNumberOrder(a.node_count, b.node_count, order)
    // if node count is different, return the value of the comparison
    if (cmp) return cmp
    // else return the comparison of cpus count
    return compareClusterOptionalNumberOrder(a.cpus, b.cpus, order)
  } else {
    // by default, sort by id
    if (a.job_id > b.job_id) {
      return order == 'asc' ? 1 : -1
    }
    if (a.job_id < b.job_id) {
      return order == 'asc' ? -1 : 1
    }
    return 0
  }
}

export function jobResourcesTRES(tres: ClusterTRES[]): {
  node: number
  cpu: number
  memory: number
} {
  const node_tres = tres.find((_tres) => _tres.type == 'node')
  let node
  if (node_tres) node = node_tres.count
  else node = -1
  const cpu_tres = tres.find((_tres) => _tres.type == 'cpu')
  let cpu
  if (cpu_tres) cpu = cpu_tres.count
  else cpu = -1
  const memory_tres = tres.find((_tres) => _tres.type == 'mem')
  let memory
  if (memory_tres) memory = memory_tres.count
  else memory = -1
  return { node: node, cpu: cpu, memory: memory }
}

/*
 * Return the number of GPUs from a GRES string, eg:
 *
 * "gpu:4" -> 4
 * "gres/gpu:tesla:2" -> 2
 * "gpu:h100:2(IDX:0-1),gpu:h200:4(IDX:2-5)" -> 6
 */
function countGPUTRESRequest(tresRequest: string): number {
  let total = 0
  for (const _tres of tresRequest.split(',')) {
    // remove optional index between parenthesis
    let tres = _tres.split('(')[0]
    // replace equal sign encountered on tres_per_task in Slurm 24.11
    tres = tres.replace('=', ':')
    const items = tres.split(':')
    if (!['gpu', 'gres/gpu'].includes(items[0])) continue
    if (items.length == 2) total += parseInt(items[1])
    // tres has gpu type
    else total += parseInt(items[2])
  }
  return total
}

/*
 * Return number of GPU allocated to a job.
 *
 * For running jobs, allocated GPUs can be retrieved from gres_detail attribute
 * provided by slurmctld. This attribute is an empty string for pending and
 * completed jobs. The attribute does not even exist on archived jobs with
 * attributes from slurmdbd only. When the value is not available, return -1.
 */
export function jobAllocatedGPU(job: ClusterJob | ClusterIndividualJob): number {
  if (job.gres_detail && job.gres_detail.length)
    /* parse strings in job.gres_detail array */
    return job.gres_detail.reduce((gpu, currentGres) => gpu + countGPUTRESRequest(currentGres), 0)
  return -1
}

/*
 * Return an object with the number of GPU requested by a job and a boolean to
 * indicate reliability of the value.
 *
 * Requested GPUs can be retrieved from tres_per_* attributes provided by
 * slurmctld. Number of GPUs can be requested by job, node, task or socket.
 *
 * There is no reliable method to determine the number of sockets that will be
 * allocated to a job. A bold estimate is computed based on the number of nodes
 * and requested sockets per node. The reliable boolean is set to false in this
 * case.
 *
 * For archived jobs, with attributes from slurmdbd only, there is no way to
 * determine requested GPU. In this case, 0 is returned…
 */
export function jobRequestedGPU(job: ClusterJob | ClusterIndividualJob): {
  count: number
  reliable: boolean
} {
  if (job.tres_per_job && job.tres_per_job.length) {
    return { count: countGPUTRESRequest(job.tres_per_job), reliable: true }
  }
  if (job.tres_per_node && job.tres_per_node.length && job.node_count && job.node_count.set) {
    return { count: countGPUTRESRequest(job.tres_per_node) * job.node_count.number, reliable: true }
  }
  if (
    job.tres_per_socket &&
    job.tres_per_socket.length &&
    job.node_count &&
    job.node_count.set &&
    job.sockets_per_node &&
    job.sockets_per_node.set
  ) {
    return {
      count:
        countGPUTRESRequest(job.tres_per_socket) *
        job.node_count.number *
        job.sockets_per_node.number,
      reliable: false
    }
  }
  if (job.tres_per_task && job.tres_per_task.length && job.tasks && job.tasks.set) {
    return { count: countGPUTRESRequest(job.tres_per_task) * job.tasks.number, reliable: true }
  }
  return { count: 0, reliable: true }
}

/*
 * Return an object with the number of GPU allocated, or requested, by a job and
 * a boolean to indicate reliability of the value.
 */
export function jobResourcesGPU(job: ClusterJob | ClusterIndividualJob): {
  count: number
  reliable: boolean
} {
  const result = jobAllocatedGPU(job)
  if (result != -1) return { count: result, reliable: true }
  return jobRequestedGPU(job)
}

/* Convert a number of megabytes into a string with simplified unit (eg. GB, TB)
 * when possible. Round value with up to 2 decimals. */
export function getMBHumanUnit(megabytes: number): string {
  if (!megabytes) return '0'
  let value = megabytes
  let divides = 0
  const units = ['MB', 'GB', 'TB']
  while (value > 1024) {
    value /= 1024
    divides += 1
  }
  return `${Math.round(value * 100) / 100}${units[divides]}`
}

export type ClusterNodeMainState =
  | 'down'
  | 'error'
  | 'drain'
  | 'draining'
  | 'fail'
  | 'failing'
  | 'future'
  | 'up'

export type ClusterNodeAllocatedState = 'allocated' | 'mixed' | 'unavailable' | 'planned' | 'idle'

export function getNodeMainState(status: string[]): ClusterNodeMainState {
  if (status.includes('DOWN')) {
    return 'down'
  } else if (status.includes('ERROR')) {
    return 'error'
  } else if (status.includes('FUTURE')) {
    return 'future'
  } else if (status.includes('DRAIN')) {
    if (status.includes('ALLOCATED') || status.includes('MIXED') || status.includes('COMPLETING'))
      return 'draining'
    else return 'drain'
  } else if (status.includes('FAIL')) {
    if (status.includes('ALLOCATED') || status.includes('MIXED') || status.includes('COMPLETING'))
      return 'failing'
    else return 'fail'
  } else {
    return 'up'
  }
}

export function getNodeAllocationState(status: string[]): ClusterNodeAllocatedState {
  if (status.includes('ALLOCATED')) {
    return 'allocated'
  } else if (status.includes('MIXED')) {
    return 'mixed'
  } else if (status.includes('DOWN') || status.includes('ERROR') || status.includes('FUTURE')) {
    return 'unavailable'
  } else if (status.includes('PLANNED')) {
    return 'planned'
  } else {
    return 'idle'
  }
}

interface NodeGPU {
  model: string
  count: number
}

const gresMatcher = new RegExp(',(?![^()]*\\))')
const gpumatcher = new RegExp('^gpu(?::([^:]*))?(?::([^:]*))$')

export function getNodeGPUFromGres(fullGres: string): NodeGPU[] {
  if (!fullGres.length) return []
  const results: NodeGPU[] = []
  fullGres.split(gresMatcher).forEach((gres) => {
    const matched = gpumatcher.exec(gres.replace(/\([^)]*\)$/g, ''))
    if (matched === null) return
    const [, model, end] = matched
    let count = -1
    if (end.includes('(')) count = parseInt(end.split('(')[0])
    else count = parseInt(end)
    results.push({ model: model || 'unknown', count: count })
  })
  return results
}

export function getNodeGPU(fullGres: string): string[] {
  const results: string[] = []
  getNodeGPUFromGres(fullGres).forEach((gpu) => {
    results.push(`${gpu.count} x ${gpu.model}`)
  })
  return results
}

export interface ClusterNode {
  alloc_cpus: number
  alloc_idle_cpus: number
  cores: number
  cpus: number
  gres: string
  gres_used: string
  name: string
  partitions: Array<string>
  real_memory: number
  sockets: number
  state: Array<string>
  reason: string
}

export interface ClusterIndividualNode extends ClusterNode {
  architecture: string
  operating_system: string
  boot_time: ClusterOptionalNumber
  last_busy: ClusterOptionalNumber
  threads: number
  alloc_memory: number
}

export interface ClusterPartition {
  name: string
  node_sets: string
}

export interface ClusterQos {
  description: string
  flags: string[]
  limits: {
    factor: ClusterOptionalNumber
    grace_time: number
    max: {
      accruing: {
        per: {
          account: ClusterOptionalNumber // MaxJobsAccruePerAccount
          user: ClusterOptionalNumber // MaxJobsAccruePerUser
        }
      }
      active_jobs: {
        accruing: ClusterOptionalNumber // GrpJobsAccrue
        count: ClusterOptionalNumber // GrpJobs
      }
      jobs: {
        active_jobs: {
          per: {
            account: ClusterOptionalNumber // MaxJobsPerAccount
            user: ClusterOptionalNumber // MaxJobsPerUser
          }
        }
        count: ClusterOptionalNumber // GrpSubmit
        per: {
          account: ClusterOptionalNumber // MaxJobsSubmitPerAccount
          user: ClusterOptionalNumber // MaxJobsSubmitPerUser
        }
      }
      tres: {
        minutes: {
          per: {
            account: ClusterTRES[] // MaxTRESRunMinsPerAccount
            job: ClusterTRES[] // MaxTRESMins(PerJob)
            qos: ClusterTRES[] // GrpTRESRunMins
            user: ClusterTRES[] // MaxTRESRunMinsPerUser
          }
          total: ClusterTRES[] // GrpTRESMins
        }
        per: {
          account: ClusterTRES[] // MaxTRESPA
          job: ClusterTRES[] // MaxTRES
          node: ClusterTRES[] // MaxTRESPerNode
          user: ClusterTRES[] // MaxTRESPerUser
        }
        total: ClusterTRES[] // GrpTRES
      }
      wall_clock: {
        per: {
          job: ClusterOptionalNumber // MaxWall, in minutes
          qos: ClusterOptionalNumber // GrpWall
        }
      }
    }
    min: {
      priority_threshold: ClusterOptionalNumber // MinPrioThreshold
      tres: {
        per: {
          job: ClusterTRES[] // MinTRES
        }
      }
    }
  }
  name: string
  priority: ClusterOptionalNumber
}

export interface ClusterAssociation {
  account: string
  max: {
    jobs: {
      accruing: ClusterOptionalNumber // MaxJobsAccrue
      active: ClusterOptionalNumber // MaxJobs
      per: {
        accruing: ClusterOptionalNumber // GrpJobsAccrue
        count: ClusterOptionalNumber // GrpJobs
        submitted: ClusterOptionalNumber // GrpSubmit
        wall_clock: ClusterOptionalNumber // MaxWall in minutes
      }
      total: ClusterOptionalNumber // MaxSubmit
    }
    per: {
      account: {
        wall_clock: ClusterOptionalNumber // GrpWall in minutes
      }
    }
    tres: {
      group: {
        active: ClusterTRES[] // GrpTRESRunMins
        minutes: ClusterTRES[] // GrpTRESMins
      }
      minutes: {
        per: {
          job: ClusterTRES[] // MaxTRESMins
        }
        total: ClusterTRES[] // ?
      }
      per: {
        job: ClusterTRES[] // MaxTRES
        node: ClusterTRES[] // MaxTRESPerNode
      }
      total: ClusterTRES[] // GrpTRES
    }
  }
  parent_account: string
  qos: string[]
  user: string
}

export interface ClusterAccountTreeNode {
  children: ClusterAccountTreeNode[]
  level: number
  account: string
  max: ClusterAssociation['max']
  parent_account: string
  qos: string[]
  users: string[]
}

export interface ClusterReservation {
  accounts: string
  end_time: ClusterOptionalNumber
  flags: string[]
  name: string
  node_count: number
  node_list: string
  start_time: ClusterOptionalNumber
  users: string
}

export interface JobHistoryRecord {
  id: number
  snapshot_time: string
  job_id: number
  job_name: string | null
  job_state: string | null
  state_reason: string | null
  user_id: number | null
  user_name: string | null
  account: string | null
  group: string | null
  partition: string | null
  qos: string | null
  nodes: string | null
  node_count: number | null
  cpus: number | null
  priority: number | null
  tres_req_str: string | null
  tres_per_job: string | null
  tres_per_node: string | null
  gres_detail: string | null
  submit_time: string | null
  eligible_time: string | null
  start_time: string | null
  end_time: string | null
  last_sched_evaluation_time: string | null
  time_limit_minutes: number | null
  tres_requested: ClusterTRES[] | null
  tres_allocated: ClusterTRES[] | null
  used_memory_gb: number | null
  usage_stats: Record<string, unknown> | null
  used_cpu_cores_avg: number | null
  exit_code: JobHistoryExitCode
  working_directory: string | null
  command: string | null
}

export type JobHistoryExitCode = string | ClusterJobExitCode | null

export type JobHistorySortCriterion =
  | 'submit_time'
  | 'id'
  | 'user'
  | 'state'
  | 'priority'
  | 'resources'
export type JobHistorySortOrder = 'asc' | 'desc'

export interface CachedLdapUser {
  username: string
  fullname: string | null
}

export interface CachedLdapUsersResponse {
  items: CachedLdapUser[]
  total: number
  page: number
  page_size: number
}

export interface CachedLdapUsersFilters {
  username?: string
  page?: number
  page_size?: number
}

export interface ClusterOperationResult {
  supported?: boolean
  operation: string
  target?: string | null
  api_version?: string | null
  warnings?: unknown[]
  errors?: unknown[]
  result?: unknown
}

export interface JobSubmitPayload extends Record<string, unknown> {
  name?: string
  script?: string
  partition?: string
  account?: string
  qos?: string
}

export interface JobUpdatePayload extends Record<string, unknown> {
  partition?: string
  qos?: string
  priority?: number | null
  time_limit?: string | null
  comment?: string | null
}

export interface NodeUpdatePayload extends Record<string, unknown> {
  state?: string
  reason?: string
  features?: string[]
  active_features?: string[]
}

export interface ReservationPayload extends Record<string, unknown> {
  name?: string
  partition?: string
  users?: string[]
  accounts?: string[]
}

export interface SlurmdbObjectPayload extends Record<string, unknown> {
  name?: string
  description?: string | null
}

type CachedLdapUsersAPIResponse = CachedLdapUser[] | CachedLdapUsersResponse

function isCachedLdapUsersResponse(
  response: CachedLdapUsersAPIResponse
): response is CachedLdapUsersResponse {
  return !Array.isArray(response)
}

export function splitJobHistoryState(jobState: string | null | undefined): string[] {
  if (!jobState) return ['UNKNOWN']

  const states = jobState
    .split(',')
    .map((state) => state.trim())
    .filter((state) => state.length > 0)

  return states.length ? states : ['UNKNOWN']
}

export function isClusterJobExitCode(value: unknown): value is ClusterJobExitCode {
  if (typeof value !== 'object' || value === null || !('return_code' in value)) {
    return false
  }
  const returnCode = value.return_code
  return typeof returnCode === 'object' && returnCode !== null && 'number' in returnCode
}

export function formatJobExitCode(
  exitCode: JobHistoryExitCode | ClusterJobExitCode | null
): string {
  if (exitCode == null) return '-'

  if (typeof exitCode === 'string') {
    const trimmed = exitCode.trim()
    if (!trimmed.length) return '-'

    try {
      return formatJobExitCode(JSON.parse(trimmed))
    } catch {
      const match = /^(-?\d+)(?::(-?\d+))?$/.exec(trimmed)
      if (!match) return trimmed

      const returnCode = parseInt(match[1], 10)
      const signalId = parseInt(match[2] ?? '0', 10)
      if (signalId > 0) {
        return returnCode === 0
          ? `SIGNALED (${signalId})`
          : `SIGNALED (rc=${returnCode}, sig=${signalId})`
      }
      return `${returnCode === 0 ? 'SUCCESS' : 'FAILED'} (${returnCode})`
    }
  }

  if (!isClusterJobExitCode(exitCode)) {
    return '-'
  }

  const status =
    exitCode.status.find((candidate) => typeof candidate === 'string' && candidate.length > 0) ??
    null
  const returnCode = getOptionalNumberValue(exitCode.return_code)
  const signalId = getOptionalNumberValue(exitCode.signal.id)
  const signalName =
    exitCode.signal.name && exitCode.signal.name !== 'NONE' ? exitCode.signal.name : null
  const signalLabel =
    signalId && signalId > 0 ? (signalName ? `${signalName}/${signalId}` : String(signalId)) : null
  const effectiveStatus =
    status ??
    (signalLabel ? 'SIGNALED' : returnCode === 0 ? 'SUCCESS' : returnCode != null ? 'FAILED' : null)

  if (signalLabel && returnCode != null) {
    return `${effectiveStatus ?? 'UNKNOWN'} (rc=${returnCode}, sig=${signalLabel})`
  }
  if (signalLabel) {
    return `${effectiveStatus ?? 'SIGNALED'} (${signalLabel})`
  }
  if (returnCode != null) {
    return `${effectiveStatus ?? 'UNKNOWN'} (${returnCode})`
  }
  if (effectiveStatus) {
    return effectiveStatus
  }

  return '-'
}

export function formatMemoryGB(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return '-'
  }
  return `${value.toFixed(2)} GB`
}

export interface JobHistoryResponse {
  total: number
  page: number
  page_size: number
  jobs: JobHistoryRecord[]
}

export interface JobHistoryFilters {
  keyword?: string
  start?: string
  end?: string
  user?: string
  account?: string
  partition?: string
  qos?: string
  state?: string
  job_id?: number
  page?: number
  page_size?: number
  sort?: JobHistorySortCriterion
  order?: JobHistorySortOrder
}

export interface NodeInstantMetrics {
  cpu_usage: number | null
  memory_usage: number | null
  disk_usage: number | null
}

export interface NodeMetricsHistory {
  cpu_usage: MetricValue[]
  memory_usage: MetricValue[]
  disk_usage: MetricValue[]
}

export interface UserMetricsHistory {
  submissions: MetricValue[]
  completions: MetricValue[]
}

export interface UserToolActivityRecord {
  tool: string
  jobs: number
  avg_max_memory_mb: number | null
  avg_cpu_cores: number | null
  avg_runtime_seconds: number | null
}

export interface UserActivityProfile {
  fullname: string | null
  groups: string[] | null
  ldap_synced_at: string | null
  ldap_found: boolean
}

export interface UserActivitySummary {
  username: string
  profile?: UserActivityProfile | null
  generated_at: string | null
  totals: {
    submitted_jobs_today: number
    completed_jobs_today: number
    active_tools: number
    latest_submissions_per_minute: number | null
    avg_max_memory_mb: number | null
    avg_cpu_cores: number | null
    avg_runtime_seconds: number | null
    busiest_tool: string | null
    busiest_tool_jobs: number
  }
  tool_breakdown: UserToolActivityRecord[]
}

export interface CacheStatistics {
  hit: {
    keys: Record<string, number>
    total: number
  }
  miss: {
    keys: Record<string, number>
    total: number
  }
}

export type MetricValue = [number, number]
const MetricRanges = ['week', 'day', 'hour'] as const
export type MetricRange = (typeof MetricRanges)[number]
export type MetricResourceState =
  | 'idle'
  | 'mixed'
  | 'allocated'
  | 'drain'
  | 'down'
  | 'error'
  | 'fail'
  | 'unknown'
export type MetricMemoryState = 'idle' | 'allocated'
export type MetricJobState =
  | 'running'
  | 'pending'
  | 'completing'
  | 'completed'
  | 'cancelled'
  | 'suspended'
  | 'preempted'
  | 'failed'
  | 'timeout'
  | 'node_fail'
  | 'boot_fail'
  | 'deadline'
  | 'out_of_memory'
  | 'unknown'
export type MetricCacheResult = 'hit' | 'miss'

export function isMetricRange(range: unknown): range is MetricRange {
  return typeof range === 'string' && MetricRanges.includes(range as MetricRange)
}

export function renderClusterOptionalNumber(optionalNumber: ClusterOptionalNumber): string {
  if (!optionalNumber.set) {
    return '-'
  }
  if (optionalNumber.infinite) {
    return '∞'
  }
  return optionalNumber.number.toString()
}

function sortClusterTRES(tres_a: ClusterTRES, tres_b: ClusterTRES) {
  const allTRES = ['node', 'cpu', 'mem']
  return allTRES.indexOf(tres_a.type) - allTRES.indexOf(tres_b.type)
}

export function renderClusterTRES(tres: ClusterTRES[]): string {
  if (tres.length == 0) {
    return '-'
  }
  return tres
    .sort((a, b) => sortClusterTRES(a, b))
    .map((_tres) => _tres.type + '=' + _tres.count)
    .join()
}

export function renderClusterTRESHuman(tres: ClusterTRES[]): string {
  if (tres.length == 0) {
    return '-'
  }

  function renderClusterTRESComponent(type: string, count: number): string {
    switch (type) {
      case 'node':
        return `${count} ${type}${count > 1 ? 's' : ''}`
      case 'cpu':
        return `${count} CPU${count > 1 ? 's' : ''}`
      case 'mem':
        return `${count} MB of memory`
      default:
        return `${count} ${type}${count > 1 ? 's' : ''}`
    }
  }

  return tres
    .sort((a, b) => sortClusterTRES(a, b))
    .map((_tres) => renderClusterTRESComponent(_tres.type, _tres.count))
    .join(', ')
    .replace(/, ([^,]*)$/, ' and $1')
}

export function renderQosFlag(flag: string): string {
  switch (flag) {
    case 'OVERRIDE_PARTITION_QOS':
      return 'OverPartQos'
    default:
      return flag
  }
}

export function renderQosLabel(list?: string[]): string {
  if (!list || list.length === 0) {
    return '∅'
  }
  return list.join(', ')
}

export function renderWalltime(value: ClusterOptionalNumber): string {
  if (!value.set) {
    return '-'
  }
  if (value.infinite) {
    return '∞'
  }
  let minutes = value.number
  let result = ''
  if (minutes > 60 * 24) {
    const nb_days = Math.floor(minutes / (60 * 24))
    result += nb_days.toString() + ' days '
    minutes -= nb_days * (60 * 24)
  }
  if (minutes > 60) {
    const nb_hours = Math.floor(minutes / 60)
    result += nb_hours.toString() + ' hours '
    minutes -= nb_hours * 60
  }
  if (minutes > 0) {
    result += minutes.toString() + ' mins'
  }
  return result
}

export type RacksDBAPIImage = ImageBitmapSource
export type RacksDBAPIResult = RacksDBAPIImage
export type RacksDBInfrastructureCoordinates = Record<string, [number, number, number, number]>
const GatewayGenericAPIKeys = ['clusters', 'users', 'message_login'] as const
export type GatewayGenericAPIKey = (typeof GatewayGenericAPIKeys)[number]
const GatewayClusterAPIKeys = [
  'stats',
  'nodes',
  'partitions',
  'qos',
  'reservations',
  'accounts',
  'associations',
  'cache_stats',
  'ai_configs',
  'ai_conversations'
] as const
export type GatewayClusterAPIKey = (typeof GatewayClusterAPIKeys)[number]
const GatewayClusterWithNumberAPIKeys = ['job', 'ai_conversation'] as const
export type GatewayClusterWithNumberAPIKey = (typeof GatewayClusterWithNumberAPIKeys)[number]
const GatewayClusterWithStringAPIKeys = [
  'node',
  'jobs',
  'metrics_nodes',
  'metrics_cores',
  'metrics_memory',
  'metrics_gpus',
  'metrics_jobs',
  'metrics_cache',
  'user_metrics_history'
] as const
export type GatewayClusterWithStringAPIKey = (typeof GatewayClusterWithStringAPIKeys)[number]
export type GatewayAnyClusterApiKey =
  | GatewayClusterAPIKey
  | GatewayClusterWithNumberAPIKey
  | GatewayClusterWithStringAPIKey

export function useGatewayAPI() {
  const restAPI = useRESTAPI()
  const runtimeConfiguration = useRuntimeConfiguration()
  const authStore = useAuthStore()

  function gatewayURL(path: string): string {
    return `${runtimeConfiguration.api_server}/api${path.startsWith('/') ? path : `/${path}`}`
  }

  async function login(idents: loginIdents): Promise<GatewayLoginResponse> {
    try {
      return (await restAPI.post('/login', idents, false)) as GatewayLoginResponse
    } catch (error) {
      /* Translate 401 APIServerError into AuthenticationError */
      if (error instanceof APIServerError && error.status == 401) {
        throw new AuthenticationError(error.message)
      }
      throw error
    }
  }

  async function anonymousLogin(): Promise<GatewayAnonymousLoginResponse> {
    try {
      return (await restAPI.get('/anonymous', false)) as GatewayAnonymousLoginResponse
    } catch (error) {
      /* Translate 401 APIServerError into AuthenticationError */
      if (error instanceof APIServerError && error.status == 401) {
        throw new AuthenticationError(error.message)
      }
      throw error
    }
  }

  async function message_login(): Promise<string> {
    return await restAPI.get<string>('/messages/login', false)
  }

  async function clusters(): Promise<Array<ClusterDescription>> {
    const result = await restAPI.get<ClusterDescription[]>(`/clusters`)
    console.log('[GatewayAPI] clusters loaded')
    return result.map((cluster) => {
      console.log(
        `[GatewayAPI]   cluster "${cluster.name}": persistence=${
          cluster.persistence ?? false
        }, node_metrics=${cluster.node_metrics ?? false}`
      )
      return {
        ...cluster,
        access_control: cluster.access_control ?? cluster.capabilities?.access_control === true,
        ai: normalizeClusterAICapability(cluster.ai ?? cluster.capabilities?.ai),
        permissions: normalizeClusterPermissions(cluster.permissions)
      }
    })
  }

  async function users(): Promise<Array<UserDescription>> {
    return await restAPI.get<UserDescription[]>(`/users`)
  }

  async function ping(cluster: string): Promise<ClusterPingResponse> {
    return await restAPI.get<ClusterPingResponse>(`/agents/${cluster}/ping`)
  }

  async function analysis_ping(cluster: string): Promise<unknown> {
    return await restAPI.get<unknown>(`/agents/${cluster}/analysis/ping`)
  }

  async function analysis_diag(cluster: string): Promise<unknown> {
    return await restAPI.get<unknown>(`/agents/${cluster}/analysis/diag`)
  }

  async function stats(cluster: string): Promise<ClusterStats> {
    const result = await restAPI.get<ClusterStatsResponse>(`/agents/${cluster}/stats`)
    return {
      resources: {
        nodes: result.resources.nodes,
        cores: result.resources.cores,
        memory: result.resources.memory,
        memory_allocated: result.resources.memory_allocated,
        memory_available: result.resources.memory_available,
        gpus: result.resources.gpus
      },
      jobs: result.jobs
    }
  }

  async function jobs(cluster: string, node?: string): Promise<ClusterJob[]> {
    if (node) return await restAPI.get<ClusterJob[]>(`/agents/${cluster}/jobs?node=${node}`)
    return await restAPI.get<ClusterJob[]>(`/agents/${cluster}/jobs`)
  }

  async function job(cluster: string, job: number): Promise<ClusterIndividualJob> {
    return await restAPI.get<ClusterIndividualJob>(`/agents/${cluster}/job/${job}`)
  }

  async function nodes(cluster: string): Promise<ClusterNode[]> {
    return await restAPI.get<ClusterNode[]>(`/agents/${cluster}/nodes`)
  }

  async function node(cluster: string, nodeName: string): Promise<ClusterIndividualNode> {
    return await restAPI.get<ClusterIndividualNode>(`/agents/${cluster}/node/${nodeName}`)
  }

  async function partitions(cluster: string): Promise<ClusterPartition[]> {
    return await restAPI.get<ClusterPartition[]>(`/agents/${cluster}/partitions`)
  }

  async function qos(cluster: string): Promise<ClusterQos[]> {
    return await restAPI.get<ClusterQos[]>(`/agents/${cluster}/qos`)
  }

  async function reservations(cluster: string): Promise<ClusterQos[]> {
    return await restAPI.get<ClusterQos[]>(`/agents/${cluster}/reservations`)
  }

  async function submit_job(
    cluster: string,
    payload: JobSubmitPayload
  ): Promise<ClusterOperationResult> {
    return await restAPI.post<ClusterOperationResult>(`/agents/${cluster}/jobs/submit`, payload)
  }

  async function update_job(
    cluster: string,
    jobId: number,
    payload: JobUpdatePayload
  ): Promise<ClusterOperationResult> {
    return await restAPI.post<ClusterOperationResult>(
      `/agents/${cluster}/job/${jobId}/update`,
      payload
    )
  }

  async function cancel_job(
    cluster: string,
    jobId: number,
    payload: Record<string, unknown> = {}
  ): Promise<ClusterOperationResult> {
    return await restAPI.delete<ClusterOperationResult>(
      `/agents/${cluster}/job/${jobId}/cancel`,
      payload
    )
  }

  async function update_node(
    cluster: string,
    nodeName: string,
    payload: NodeUpdatePayload
  ): Promise<ClusterOperationResult> {
    const encodedNodeName = encodeURIComponent(nodeName)
    return await restAPI.post<ClusterOperationResult>(
      `/agents/${cluster}/node/${encodedNodeName}/update`,
      payload
    )
  }

  async function delete_node(cluster: string, nodeName: string): Promise<ClusterOperationResult> {
    const encodedNodeName = encodeURIComponent(nodeName)
    return await restAPI.delete<ClusterOperationResult>(
      `/agents/${cluster}/node/${encodedNodeName}/delete`
    )
  }

  async function save_reservation(
    cluster: string,
    payload: ReservationPayload
  ): Promise<ClusterOperationResult> {
    return await restAPI.post<ClusterOperationResult>(`/agents/${cluster}/reservation`, payload)
  }

  async function update_reservation(
    cluster: string,
    reservationName: string,
    payload: ReservationPayload
  ): Promise<ClusterOperationResult> {
    const encodedReservation = encodeURIComponent(reservationName)
    return await restAPI.post<ClusterOperationResult>(
      `/agents/${cluster}/reservation/${encodedReservation}/update`,
      payload
    )
  }

  async function delete_reservation(
    cluster: string,
    reservationName: string
  ): Promise<ClusterOperationResult> {
    const encodedReservation = encodeURIComponent(reservationName)
    return await restAPI.delete<ClusterOperationResult>(
      `/agents/${cluster}/reservation/${encodedReservation}/delete`
    )
  }

  async function save_account(
    cluster: string,
    payload: SlurmdbObjectPayload
  ): Promise<ClusterOperationResult> {
    return await restAPI.post<ClusterOperationResult>(`/agents/${cluster}/accounts`, payload)
  }

  async function delete_account(
    cluster: string,
    accountName: string
  ): Promise<ClusterOperationResult> {
    return await restAPI.delete<ClusterOperationResult>(
      `/agents/${cluster}/account/${encodeURIComponent(accountName)}/delete`
    )
  }

  async function save_user(
    cluster: string,
    payload: SlurmdbObjectPayload
  ): Promise<ClusterOperationResult> {
    return await restAPI.post<ClusterOperationResult>(`/agents/${cluster}/users`, payload)
  }

  async function delete_user(cluster: string, username: string): Promise<ClusterOperationResult> {
    return await restAPI.delete<ClusterOperationResult>(
      `/agents/${cluster}/user/${encodeURIComponent(username)}/delete`
    )
  }

  async function save_association(
    cluster: string,
    payload: Record<string, unknown>
  ): Promise<ClusterOperationResult> {
    return await restAPI.post<ClusterOperationResult>(`/agents/${cluster}/associations`, payload)
  }

  async function save_qos(
    cluster: string,
    payload: SlurmdbObjectPayload
  ): Promise<ClusterOperationResult> {
    return await restAPI.post<ClusterOperationResult>(`/agents/${cluster}/qos`, payload)
  }

  async function delete_qos(cluster: string, qosName: string): Promise<ClusterOperationResult> {
    return await restAPI.delete<ClusterOperationResult>(
      `/agents/${cluster}/qos/${encodeURIComponent(qosName)}/delete`
    )
  }

  async function accounts(cluster: string): Promise<Array<AccountDescription>> {
    return await restAPI.get<AccountDescription[]>(`/agents/${cluster}/accounts`)
  }

  async function associations(cluster: string): Promise<Array<ClusterAssociation>> {
    return await restAPI.get<ClusterAssociation[]>(`/agents/${cluster}/associations`)
  }

  async function permissions(cluster: string): Promise<ClusterPermissions> {
    const result = await restAPI.get<ClusterPermissionsResponse | ClusterPermissionsLegacyResponse>(
      `/agents/${cluster}/permissions`
    )
    return normalizeClusterPermissions(result)
  }

  async function access_roles(cluster: string): Promise<CustomRole[]> {
    const result = await restAPI.get<AccessControlRolesResponse>(`/agents/${cluster}/access/roles`)
    return result.items.map((role) => ({
      ...role,
      permissions: [...(role.permissions ?? [])].sort()
    }))
  }

  async function create_access_role(
    cluster: string,
    payload: CustomRolePayload
  ): Promise<CustomRole> {
    return await restAPI.post<CustomRole>(`/agents/${cluster}/access/roles`, payload)
  }

  async function update_access_role(
    cluster: string,
    roleId: number,
    payload: CustomRolePayload
  ): Promise<CustomRole> {
    return await restAPI.patch<CustomRole>(`/agents/${cluster}/access/roles/${roleId}`, payload)
  }

  async function delete_access_role(cluster: string, roleId: number): Promise<{ result: string }> {
    return await restAPI.delete<{ result: string }>(`/agents/${cluster}/access/roles/${roleId}`)
  }

  async function access_users(
    cluster: string,
    filters: AccessControlUsersFilters = {}
  ): Promise<AccessControlUsersResponse> {
    const params = new URLSearchParams()
    if (filters.username) params.append('username', filters.username)
    if (filters.page) params.append('page', filters.page.toString())
    if (filters.page_size) params.append('page_size', filters.page_size.toString())
    const query = params.toString()
    return await restAPI.get<AccessControlUsersResponse>(
      `/agents/${cluster}/access/users${query ? '?' + query : ''}`
    )
  }

  async function access_user_roles(
    cluster: string,
    username: string
  ): Promise<AccessControlUserAssignment> {
    const encodedUsername = encodeURIComponent(username)
    const result = await restAPI.get<AccessControlUserAssignment>(
      `/agents/${cluster}/access/users/${encodedUsername}/roles`
    )
    return {
      ...result,
      custom_roles: (result.custom_roles ?? []).map((role) => ({
        ...role,
        permissions: [...(role.permissions ?? [])].sort()
      }))
    }
  }

  async function access_catalog(cluster: string): Promise<AccessControlCatalog> {
    return await restAPI.get<AccessControlCatalog>(`/agents/${cluster}/access/catalog`)
  }

  async function update_access_user_roles(
    cluster: string,
    username: string,
    roleIds: number[]
  ): Promise<AccessControlUserAssignment> {
    const encodedUsername = encodeURIComponent(username)
    return await restAPI.put<AccessControlUserAssignment>(
      `/agents/${cluster}/access/users/${encodedUsername}/roles`,
      { role_ids: roleIds }
    )
  }

  async function cache_stats(cluster: string): Promise<CacheStatistics> {
    return await restAPI.get<CacheStatistics>(`/agents/${cluster}/cache/stats`)
  }

  async function ldap_cache_users(
    cluster: string,
    filters: CachedLdapUsersFilters = {}
  ): Promise<CachedLdapUsersResponse> {
    const params = new URLSearchParams()
    if (filters.username) params.append('username', filters.username)
    if (filters.page) params.append('page', filters.page.toString())
    if (filters.page_size) params.append('page_size', filters.page_size.toString())
    const query = params.toString()
    const url = `/agents/${cluster}/users/cache${query ? '?' + query : ''}`
    const response = await restAPI.get<CachedLdapUsersAPIResponse>(url)
    if (isCachedLdapUsersResponse(response)) {
      return response
    }
    return {
      items: response,
      total: response.length,
      page: filters.page ?? 1,
      page_size: filters.page_size ?? response.length
    }
  }

  async function cache_reset(cluster: string): Promise<CacheStatistics> {
    return await restAPI.post<CacheStatistics>(`/agents/${cluster}/cache/reset`, {})
  }

  async function admin_licenses(cluster: string): Promise<unknown> {
    return await restAPI.get<unknown>(`/agents/${cluster}/admin/system/licenses`)
  }

  async function admin_shares(cluster: string): Promise<unknown> {
    return await restAPI.get<unknown>(`/agents/${cluster}/admin/system/shares`)
  }

  async function admin_reconfigure(cluster: string): Promise<ClusterOperationResult> {
    return await restAPI.post<ClusterOperationResult>(`/agents/${cluster}/admin/system/reconfigure`, {})
  }

  async function admin_slurmdb_diag(cluster: string): Promise<unknown> {
    return await restAPI.get<unknown>(`/agents/${cluster}/admin/system/slurmdb/diag`)
  }

  async function admin_slurmdb_config(cluster: string): Promise<unknown> {
    return await restAPI.get<unknown>(`/agents/${cluster}/admin/system/slurmdb/config`)
  }

  async function admin_slurmdb_instances(cluster: string): Promise<unknown> {
    return await restAPI.get<unknown>(`/agents/${cluster}/admin/system/slurmdb/instances`)
  }

  async function admin_slurmdb_tres(cluster: string): Promise<unknown> {
    return await restAPI.get<unknown>(`/agents/${cluster}/admin/system/slurmdb/tres`)
  }

  async function ai_configs(cluster: string): Promise<AIModelConfig[]> {
    const result = await restAPI.get<AIModelConfigListResponse>(`/agents/${cluster}/ai/configs`)
    return (result.items ?? []).map((config) => normalizeAIModelConfig(config))
  }

  async function create_ai_config(
    cluster: string,
    payload: AIModelConfigPayload
  ): Promise<AIModelConfig> {
    const result = await restAPI.post<Partial<AIModelConfig>>(`/agents/${cluster}/ai/configs`, payload)
    return normalizeAIModelConfig(result)
  }

  async function update_ai_config(
    cluster: string,
    configId: number,
    payload: Partial<AIModelConfigPayload>
  ): Promise<AIModelConfig> {
    const result = await restAPI.patch<Partial<AIModelConfig>>(
      `/agents/${cluster}/ai/configs/${configId}`,
      payload
    )
    return normalizeAIModelConfig(result)
  }

  async function delete_ai_config(cluster: string, configId: number): Promise<{ result: string }> {
    return await restAPI.delete<{ result: string }>(`/agents/${cluster}/ai/configs/${configId}`)
  }

  async function validate_ai_config(
    cluster: string,
    configId: number
  ): Promise<AIConfigValidationResult> {
    return await restAPI.post<AIConfigValidationResult>(
      `/agents/${cluster}/ai/configs/${configId}/validate`,
      {}
    )
  }

  async function ai_conversations(cluster: string): Promise<AIConversationSummary[]> {
    const result = await restAPI.get<AIConversationListResponse | AIConversationSummary[]>(
      `/agents/${cluster}/ai/conversations`
    )
    const items = isAIConversationListResponse(result) ? result.items : result
    return items.map((conversation) => normalizeAIConversationSummary(conversation))
  }

  async function ai_conversation(cluster: string, conversationId: number): Promise<AIConversation> {
    const result = await restAPI.get<Partial<AIConversation>>(
      `/agents/${cluster}/ai/conversations/${conversationId}`
    )
    return normalizeAIConversation(result)
  }

  function stream_ai_chat(
    cluster: string,
    payload: AIChatRequest,
    handlers: AIChatStreamHandlers = {}
  ): AIChatStreamSession {
    const controller = new AbortController()
    const url = gatewayURL(`/agents/${cluster}/ai/chat/stream`)

    const finished = fetchEventSource(url, {
      method: 'POST',
      signal: controller.signal,
      openWhenHidden: true,
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.token ?? ''}`
      },
      body: JSON.stringify(payload),
      async onopen(response) {
        if (response.ok) {
          return
        }
        let message = `AI chat request failed with status ${response.status}`
        try {
          const data = (await response.json()) as { description?: string }
          if (data?.description) {
            message = data.description
          }
        } catch {
          /* Keep fallback message */
        }
        if (response.status === 401) {
          throw new AuthenticationError(message)
        }
        throw new APIServerError(response.status, message)
      },
      onmessage(event) {
        let data: Record<string, unknown> = {}
        try {
          data = event.data ? (JSON.parse(event.data) as Record<string, unknown>) : {}
        } catch {
          handlers.onError?.(`Unable to parse AI stream event: ${event.event}`)
          return
        }
        if (event.event === 'conversation') {
          handlers.onConversation?.(data as unknown as AIChatConversationEvent)
        } else if (event.event === 'content') {
          handlers.onContent?.(String(data.delta ?? ''))
        } else if (event.event === 'tool_start') {
          handlers.onToolStart?.(data as unknown as AIChatToolEvent)
        } else if (event.event === 'tool_end') {
          handlers.onToolEnd?.(data as unknown as AIChatToolEvent)
        } else if (event.event === 'complete') {
          handlers.onComplete?.(data as unknown as AIChatCompleteEvent)
        } else if (event.event === 'error') {
          handlers.onError?.(String(data.message ?? 'Unknown AI stream error'))
        } else if (event.event === 'done') {
          handlers.onDone?.(data as unknown as AIChatConversationEvent)
        }
      },
      onerror(error) {
        throw error
      }
    })

    return { controller, finished }
  }

  async function metrics_nodes(
    cluster: string,
    last: string
  ): Promise<Record<MetricResourceState, MetricValue[]>> {
    return await restAPI.get<Record<MetricResourceState, MetricValue[]>>(
      `/agents/${cluster}/metrics/nodes?range=${last}`
    )
  }

  async function metrics_cores(
    cluster: string,
    last: string
  ): Promise<Record<MetricResourceState, MetricValue[]>> {
    return await restAPI.get<Record<MetricResourceState, MetricValue[]>>(
      `/agents/${cluster}/metrics/cores?range=${last}`
    )
  }

  async function metrics_gpus(
    cluster: string,
    last: string
  ): Promise<Record<MetricResourceState, MetricValue[]>> {
    return await restAPI.get<Record<MetricResourceState, MetricValue[]>>(
      `/agents/${cluster}/metrics/gpus?range=${last}`
    )
  }

  async function metrics_memory(
    cluster: string,
    last: string
  ): Promise<Record<MetricMemoryState, MetricValue[]>> {
    return await restAPI.get<Record<MetricMemoryState, MetricValue[]>>(
      `/agents/${cluster}/metrics/memory?range=${last}`
    )
  }

  async function metrics_jobs(
    cluster: string,
    last: string
  ): Promise<Record<MetricJobState, MetricValue[]>> {
    return await restAPI.get<Record<MetricJobState, MetricValue[]>>(
      `/agents/${cluster}/metrics/jobs?range=${last}`
    )
  }

  async function metrics_cache(
    cluster: string,
    last: string
  ): Promise<Record<MetricCacheResult, MetricValue[]>> {
    return await restAPI.get<Record<MetricCacheResult, MetricValue[]>>(
      `/agents/${cluster}/metrics/cache?range=${last}`
    )
  }

  async function job_history_detail(cluster: string, id: number): Promise<JobHistoryRecord> {
    return await restAPI.get<JobHistoryRecord>(`/agents/${cluster}/jobs/history/${id}`)
  }

  async function jobs_history(
    cluster: string,
    filters: JobHistoryFilters
  ): Promise<JobHistoryResponse> {
    const params = new URLSearchParams()
    if (filters.keyword) params.append('keyword', filters.keyword)
    if (filters.start) params.append('start', filters.start)
    if (filters.end) params.append('end', filters.end)
    if (filters.user) params.append('user', filters.user)
    if (filters.account) params.append('account', filters.account)
    if (filters.partition) params.append('partition', filters.partition)
    if (filters.qos) params.append('qos', filters.qos)
    if (filters.state) params.append('state', filters.state)
    if (filters.job_id) params.append('job_id', filters.job_id.toString())
    if (filters.page) params.append('page', filters.page.toString())
    if (filters.page_size) params.append('page_size', filters.page_size.toString())
    if (filters.sort) params.append('sort', filters.sort)
    if (filters.order) params.append('order', filters.order)
    const query = params.toString()
    const url = `/agents/${cluster}/jobs/history${query ? '?' + query : ''}`
    console.log('[GatewayAPI] jobs_history request URL:', url)
    const result = await restAPI.get<JobHistoryResponse>(url)
    console.log(
      '[GatewayAPI] jobs_history response: total=',
      result.total,
      'jobs=',
      result.jobs.length
    )
    return result
  }

  async function node_metrics(cluster: string, nodeName: string): Promise<NodeInstantMetrics> {
    const url = `/agents/${cluster}/node/${nodeName}/metrics`
    console.log('[GatewayAPI] node_metrics request URL:', url)
    const result = await restAPI.get<NodeInstantMetrics>(url)
    console.log('[GatewayAPI] node_metrics response:', result)
    return result
  }

  async function node_metrics_history(
    cluster: string,
    nodeName: string,
    range: MetricRange
  ): Promise<NodeMetricsHistory> {
    const url = `/agents/${cluster}/node/${nodeName}/metrics/history?range=${range}`
    console.log('[GatewayAPI] node_metrics_history request URL:', url)
    const result = await restAPI.get<NodeMetricsHistory>(url)
    console.log('[GatewayAPI] node_metrics_history response:', result)
    return result
  }

  async function user_metrics_history(
    cluster: string,
    username: string,
    range: MetricRange = 'hour'
  ): Promise<UserMetricsHistory> {
    const encodedUsername = encodeURIComponent(username)
    const url = `/agents/${cluster}/user/${encodedUsername}/metrics/history?range=${range}`
    console.log('[GatewayAPI] user_metrics_history request URL:', url)
    const result = await restAPI.get<UserMetricsHistory>(url)
    console.log('[GatewayAPI] user_metrics_history response:', result)
    return result
  }

  async function user_activity_summary(
    cluster: string,
    username: string
  ): Promise<UserActivitySummary> {
    const encodedUsername = encodeURIComponent(username)
    const url = `/agents/${cluster}/user/${encodedUsername}/activity/summary`
    console.log('[GatewayAPI] user_activity_summary request URL:', url)
    const result = await restAPI.get<UserActivitySummary>(url)
    console.log('[GatewayAPI] user_activity_summary response:', result)
    return result
  }

  async function infrastructureImagePng(
    cluster: string,
    infrastructure: string,
    width: number,
    height: number
  ): Promise<[RacksDBAPIImage, RacksDBInfrastructureCoordinates]> {
    /* Detect dark mode to set lighter racks colors */
    let rack_colors
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      rack_colors = { frame: '#555555', pane: '#505050' }
    } else {
      rack_colors = {}
    }
    const response = await restAPI.postRaw<AxiosResponse>(
      `/agents/${cluster}/racksdb/draw/infrastructure/${infrastructure}.png?coordinates`,
      {
        general: { pixel_perfect: true },
        dimensions: { width: width, height: height },
        infrastructure: { equipment_labels: false, ghost_unselected: true },
        row: { labels: runtimeConfiguration.racksdb_rows_labels },
        rack: { labels: runtimeConfiguration.racksdb_racks_labels },
        colors: { racks: [rack_colors] }
      },
      true,
      'arraybuffer'
    )
    // parse multipart response with Response.formData()
    const multipart = await new Response(response.data, {
      headers: response.headers as HeadersInit
    }).formData()
    const image = multipart.get('image') as File
    const coordinates = JSON.parse(await (multipart.get('coordinates') as File)?.text())
    return [
      new Blob([image], { type: image.type }) as RacksDBAPIImage,
      coordinates as RacksDBInfrastructureCoordinates
    ]
  }

  function abort() {
    /* Abort all pending requests */
    console.log('Aborting requests')
    restAPI.abortController()
  }

  /*
   * Custom type guards for Gateway API keys
   */

  function isValidGatewayGenericAPIKey(key: string): key is GatewayGenericAPIKey {
    return typeof key === 'string' && GatewayGenericAPIKeys.includes(key as GatewayGenericAPIKey)
  }
  function isValidGatewayClusterAPIKey(key: string): key is GatewayClusterAPIKey {
    return typeof key === 'string' && GatewayClusterAPIKeys.includes(key as GatewayClusterAPIKey)
  }
  function isValidGatewayClusterWithStringAPIKey(
    key: string
  ): key is GatewayClusterWithStringAPIKey {
    return (
      typeof key === 'string' &&
      GatewayClusterWithStringAPIKeys.includes(key as GatewayClusterWithStringAPIKey)
    )
  }
  function isValidGatewayClusterWithNumberAPIKey(
    key: string
  ): key is GatewayClusterWithNumberAPIKey {
    return (
      typeof key === 'string' &&
      GatewayClusterWithNumberAPIKeys.includes(key as GatewayClusterWithNumberAPIKey)
    )
  }

  return {
    login,
    anonymousLogin,
    message_login,
    clusters,
    users,
    ping,
    analysis_ping,
    analysis_diag,
    stats,
    jobs,
    job,
    nodes,
    node,
    partitions,
    qos,
    reservations,
    submit_job,
    update_job,
    cancel_job,
    update_node,
    delete_node,
    save_reservation,
    update_reservation,
    delete_reservation,
    accounts,
    save_account,
    delete_account,
    associations,
    save_association,
    save_user,
    delete_user,
    save_qos,
    delete_qos,
    permissions,
    access_roles,
    access_catalog,
    create_access_role,
    update_access_role,
    delete_access_role,
    access_users,
    access_user_roles,
    update_access_user_roles,
    cache_stats,
    ldap_cache_users,
    cache_reset,
    admin_licenses,
    admin_shares,
    admin_reconfigure,
    admin_slurmdb_diag,
    admin_slurmdb_config,
    admin_slurmdb_instances,
    admin_slurmdb_tres,
    ai_configs,
    create_ai_config,
    update_ai_config,
    delete_ai_config,
    validate_ai_config,
    ai_conversations,
    ai_conversation,
    stream_ai_chat,
    metrics_nodes,
    metrics_cores,
    metrics_memory,
    metrics_gpus,
    metrics_jobs,
    metrics_cache,
    jobs_history,
    job_history_detail,
    node_metrics,
    node_metrics_history,
    user_metrics_history,
    user_activity_summary,
    infrastructureImagePng,
    abort,
    isValidGatewayGenericAPIKey,
    isValidGatewayClusterAPIKey,
    isValidGatewayClusterWithStringAPIKey,
    isValidGatewayClusterWithNumberAPIKey
  }
}
