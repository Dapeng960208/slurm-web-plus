import { describe, expect, test, beforeEach, afterEach, vi } from 'vitest'
import {
  compareClusterJobSortOrder,
  hasClusterAIAssistant,
  jobResourcesTRES,
  jobAllocatedGPU,
  jobRequestedGPU,
  jobResourcesGPU,
  getMBHumanUnit,
  getNodeMainState,
  getNodeAllocationState,
  getNodeGPUFromGres,
  getNodeGPU,
  useGatewayAPI
} from '@/composables/GatewayAPI'
import jobs from '../assets/jobs.json'
import { createPinia, setActivePinia } from 'pinia'
import jobPending from '../assets/job-pending.json'
import jobGpuArchived from '../assets/job-gpus-archived.json'
import jobGpuCompleted from '../assets/job-gpus-completed.json'
import jobGpuPending from '../assets/job-gpus-pending.json'
import jobGpuRunning from '../assets/job-gpus-running.json'
import jobGpuGres from '../assets/job-gpus-gres.json'
import jobGpuMultiNodes from '../assets/job-gpus-multi-nodes.json'
import jobGpuType from '../assets/job-gpus-type.json'
import jobGpuMultiTypes from '../assets/job-gpus-multi-types.json'
import jobGpuPerNode from '../assets/job-gpus-per-node.json'
import jobGpuPerSocket from '../assets/job-gpus-per-socket.json'
import jobGpuPerTask from '../assets/job-gpus-per-task.json'
import nodeDown from '../assets/node-down.json'
import nodeAllocated from '../assets/node-allocated.json'
import nodeIdle from '../assets/node-idle.json'
import nodeMixed from '../assets/node-mixed.json'
import nodeWithGpusAllocated from '../assets/node-with-gpus-allocated.json'
import nodeWithGpusIdle from '../assets/node-with-gpus-idle.json'
import nodeWithGpusMixed from '../assets/node-with-gpus-mixed.json'
import nodeWithGpusModelAllocated from '../assets/node-with-gpus-model-allocated.json'
import nodeWithGpusModelIdle from '../assets/node-with-gpus-model-idle.json'
import nodeWithGpusModelMixed from '../assets/node-with-gpus-model-mixed.json'

import nodeWithoutGpu from '../assets/node-without-gpu.json'

// Stub REST API for infrastructureImagePng and request builder tests.
const mockRestAPI = {
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  postRaw: vi.fn()
}

vi.mock('@/composables/RESTAPI', () => ({
  useRESTAPI: () => mockRestAPI
}))

// Provide minimal runtime configuration for GatewayAPI initialization.
vi.mock('@/plugins/runtimeConfiguration', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/plugins/runtimeConfiguration')>()
  return {
    ...actual,
    useRuntimeConfiguration: () => ({
      api_server: 'http://localhost',
      authentication: true,
      racksdb_rows_labels: true,
      racksdb_racks_labels: true,
      version: 'test'
    })
  }
})

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('infrastructureImagePng', () => {
  const originalResponse = globalThis.Response
  const coordinates = { node1: [0, 0, 10, 10] }
  const imageBytes = new Uint8Array([0x89, 0x50, 0x4e, 0x47])

  beforeEach(() => {
    // The response body is not used by our fake Response, but keep a realistic
    // shape so GatewayAPI continues to call Response.formData().
    mockRestAPI.postRaw.mockResolvedValue({
      headers: { 'content-type': 'multipart/form-data; boundary=mock' },
      data: new Uint8Array([0x00])
    })

    // Build a minimal FormData-like object with the parts GatewayAPI expects.
    // This avoids undici multipart parsing in tests while still exercising
    // the extraction and JSON parsing logic.
    const image = new Blob([imageBytes], { type: 'image/png' })
    const coordinatesFile = new Blob([JSON.stringify(coordinates)], {
      type: 'application/json'
    })
    const formData = {
      get: (key: string) => {
        if (key === 'image') return image
        if (key === 'coordinates') return coordinatesFile
        return null
      }
    }

    // Fake Response.formData() to return our synthetic parts.
    globalThis.Response = class {
      constructor() {}
      async formData() {
        return formData
      }
    } as typeof Response
  })

  afterEach(() => {
    globalThis.Response = originalResponse
    vi.clearAllMocks()
  })

  test('parses image and coordinates from multipart response', async () => {
    const gateway = useGatewayAPI()
    const [image, parsedCoordinates] = await gateway.infrastructureImagePng(
      'cluster',
      'infra',
      100,
      100
    )

    expect(image).toBeInstanceOf(Blob)
    expect((image as Blob).type).toBe('image/png')
    expect(parsedCoordinates).toStrictEqual(coordinates)
  })
})

describe('user metrics requests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('requests user metrics history with range query', async () => {
    mockRestAPI.get.mockResolvedValueOnce({ submissions: [] })

    const gateway = useGatewayAPI()
    await gateway.user_metrics_history('cluster-a', 'alice', 'day')

    expect(mockRestAPI.get).toHaveBeenCalledWith(
      '/agents/cluster-a/user/alice/metrics/history?range=day'
    )
  })

  test('requests user activity summary', async () => {
    mockRestAPI.get.mockResolvedValueOnce({
      username: 'alice',
      profile: {
        fullname: 'Alice Doe',
        groups: ['users'],
        ldap_synced_at: '2026-04-24T07:55:00Z',
        ldap_found: true
      },
      generated_at: null,
      totals: {
        submitted_jobs_today: 0,
        completed_jobs_today: 0,
        active_tools: 0,
        latest_submissions_per_minute: null,
        avg_max_memory_mb: null,
        avg_cpu_cores: null,
        avg_runtime_seconds: null,
        busiest_tool: null,
        busiest_tool_jobs: 0
      },
      tool_breakdown: []
    })

    const gateway = useGatewayAPI()
    await gateway.user_activity_summary('cluster-a', 'alice')

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster-a/user/alice/activity/summary')
  })

  test('encodes usernames in user metrics requests', async () => {
    mockRestAPI.get.mockResolvedValueOnce({ submissions: [] })

    const gateway = useGatewayAPI()
    await gateway.user_metrics_history('cluster-a', 'alice doe', 'week')

    expect(mockRestAPI.get).toHaveBeenCalledWith(
      '/agents/cluster-a/user/alice%20doe/metrics/history?range=week'
    )
  })

  test('encodes usernames in user activity summary requests', async () => {
    mockRestAPI.get.mockResolvedValueOnce({
      username: 'alice doe',
      profile: null,
      generated_at: null,
      totals: {
        submitted_jobs_today: 0,
        completed_jobs_today: 0,
        active_tools: 0,
        latest_submissions_per_minute: null,
        avg_max_memory_mb: null,
        avg_cpu_cores: null,
        avg_runtime_seconds: null,
        busiest_tool: null,
        busiest_tool_jobs: 0
      },
      tool_breakdown: []
    })

    const gateway = useGatewayAPI()
    await gateway.user_activity_summary('cluster-a', 'alice doe')

    expect(mockRestAPI.get).toHaveBeenCalledWith(
      '/agents/cluster-a/user/alice%20doe/activity/summary'
    )
  })
})

describe('user activity gateway methods', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('requests user submission history with the provided range', async () => {
    mockRestAPI.get.mockResolvedValue({
      submissions: [[1748004750000, 3]]
    })

    const gateway = useGatewayAPI()
    const result = await gateway.user_metrics_history('cluster', 'alice', 'day')

    expect(mockRestAPI.get).toHaveBeenCalledWith(
      '/agents/cluster/user/alice/metrics/history?range=day'
    )
    expect(result).toStrictEqual({
      submissions: [[1748004750000, 3]]
    })
  })

  test('defaults user submission history requests to the hour range', async () => {
    mockRestAPI.get.mockResolvedValue({
      submissions: [[1748004750000, 1]]
    })

    const gateway = useGatewayAPI()
    await gateway.user_metrics_history('cluster', 'alice')

    expect(mockRestAPI.get).toHaveBeenCalledWith(
      '/agents/cluster/user/alice/metrics/history?range=hour'
    )
  })

  test('requests user activity summary', async () => {
    mockRestAPI.get.mockResolvedValue({
      username: 'alice',
      profile: {
        fullname: 'Alice Doe',
        groups: ['users', 'bio'],
        ldap_synced_at: '2026-04-24T07:55:00Z',
        ldap_found: true
      },
      generated_at: '2026-04-24T08:00:00Z',
      totals: {
        submitted_jobs_today: 5,
        completed_jobs_today: 4,
        active_tools: 2,
        latest_submissions_per_minute: 1,
        avg_max_memory_mb: 2048,
        avg_cpu_cores: 8,
        avg_runtime_seconds: 600,
        busiest_tool: 'blastn',
        busiest_tool_jobs: 3
      },
      tool_breakdown: []
    })

    const gateway = useGatewayAPI()
    const result = await gateway.user_activity_summary('cluster', 'alice')

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/user/alice/activity/summary')
    expect(result.username).toBe('alice')
    expect(result.profile?.fullname).toBe('Alice Doe')
    expect(result.totals.busiest_tool).toBe('blastn')
  })
})

describe('gateway data APIs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('uses the corrected write routes for jobs and nodes', async () => {
    mockRestAPI.post.mockResolvedValue({ result: 'ok' })
    mockRestAPI.delete.mockResolvedValue({ result: 'ok' })

    const gateway = useGatewayAPI()
    await gateway.update_job('cluster', 12, { qos: 'debug' })
    await gateway.cancel_job('cluster', 12, { signal: 'TERM' })
    await gateway.update_node('cluster', 'cn-01', { state: 'DRAIN' })
    await gateway.delete_node('cluster', 'cn-01')

    expect(mockRestAPI.post).toHaveBeenNthCalledWith(
      1,
      '/agents/cluster/job/12/update',
      { qos: 'debug' }
    )
    expect(mockRestAPI.delete).toHaveBeenNthCalledWith(
      1,
      '/agents/cluster/job/12/cancel',
      { signal: 'TERM' }
    )
    expect(mockRestAPI.post).toHaveBeenNthCalledWith(
      2,
      '/agents/cluster/node/cn-01/update',
      { state: 'DRAIN' }
    )
    expect(mockRestAPI.delete).toHaveBeenNthCalledWith(
      2,
      '/agents/cluster/node/cn-01/delete'
    )
  })

  test('uses delete endpoints with explicit /delete suffixes for SlurmDB resources', async () => {
    mockRestAPI.post.mockResolvedValue({ result: 'ok' })
    mockRestAPI.delete.mockResolvedValue({ result: 'ok' })

    const gateway = useGatewayAPI()
    await gateway.update_reservation('cluster', 'maint', { users: ['alice'] })
    await gateway.delete_reservation('cluster', 'maint')
    await gateway.delete_account('cluster', 'science')
    await gateway.delete_user('cluster', 'alice')
    await gateway.delete_qos('cluster', 'debug')

    expect(mockRestAPI.post).toHaveBeenCalledWith('/agents/cluster/reservation/maint/update', {
      users: ['alice']
    })
    expect(mockRestAPI.delete).toHaveBeenNthCalledWith(
      1,
      '/agents/cluster/reservation/maint/delete'
    )
    expect(mockRestAPI.delete).toHaveBeenNthCalledWith(
      2,
      '/agents/cluster/account/science/delete'
    )
    expect(mockRestAPI.delete).toHaveBeenNthCalledWith(
      3,
      '/agents/cluster/user/alice/delete'
    )
    expect(mockRestAPI.delete).toHaveBeenNthCalledWith(
      4,
      '/agents/cluster/qos/debug/delete'
    )
  })

  test('detects AI capability from discovery payloads', () => {
    expect(
      hasClusterAIAssistant({
        name: 'cluster-a',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'cluster-a',
        metrics: true,
        cache: true,
        capabilities: {
          ai: {
            enabled: true,
            streaming: true
          }
        }
      })
    ).toBe(true)

    expect(
      hasClusterAIAssistant({
        name: 'cluster-b',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'cluster-b',
        metrics: true,
        cache: true,
        capabilities: {
          ai: false
        }
      })
    ).toBe(false)
  })

  test('requests AI model configs', async () => {
    mockRestAPI.get.mockResolvedValue({
      items: [
        {
          id: 7,
          name: 'cluster-qwen',
          provider: 'qwen',
          model: 'qwen3-coder',
          display_name: 'Qwen',
          enabled: true,
          is_default: true,
          sort_order: 10,
          secret_configured: true,
          secret_mask: '***1234'
        }
      ]
    })

    const gateway = useGatewayAPI()
    const result = await gateway.ai_configs('cluster')

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/ai/configs')
    expect(result[0].provider).toBe('qwen')
    expect(result[0].secret_mask).toBe('***1234')
  })

  test('requests AI conversations from wrapped list responses', async () => {
    mockRestAPI.get.mockResolvedValue({
      items: [
        {
          id: 1,
          title: 'Queue pressure',
          created_at: '2026-04-24T09:00:00Z',
          updated_at: '2026-04-24T09:05:00Z',
          last_message: 'GPU partition is saturated.',
          model_config_id: 7
        }
      ]
    })

    const gateway = useGatewayAPI()
    const result = await gateway.ai_conversations('cluster')

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/ai/conversations')
    expect(result).toStrictEqual([
      {
        id: 1,
        title: 'Queue pressure',
        created_at: '2026-04-24T09:00:00Z',
        updated_at: '2026-04-24T09:05:00Z',
        last_message: 'GPU partition is saturated.',
        model_config_id: 7
      }
    ])
  })

  test('creates and updates AI model configs', async () => {
    mockRestAPI.post.mockResolvedValue({
      id: 2,
      name: 'deepseek-prod',
      provider: 'deepseek',
      model: 'deepseek-chat',
      display_name: 'DeepSeek Prod',
      enabled: true,
      is_default: false,
      sort_order: 20,
      secret_configured: true,
      secret_mask: '***5678'
    })
    mockRestAPI.patch.mockResolvedValue({
      id: 2,
      name: 'deepseek-prod',
      provider: 'deepseek',
      model: 'deepseek-chat',
      display_name: 'DeepSeek Prod',
      enabled: true,
      is_default: true,
      sort_order: 20,
      secret_configured: true,
      secret_mask: '***5678'
    })

    const gateway = useGatewayAPI()
    const created = await gateway.create_ai_config('cluster', {
      name: 'deepseek-prod',
      provider: 'deepseek',
      model: 'deepseek-chat',
      display_name: 'DeepSeek Prod',
      enabled: true,
      is_default: false,
      sort_order: 20,
      api_key: 'sk-secret'
    })
    const updated = await gateway.update_ai_config('cluster', 2, { is_default: true })

    expect(mockRestAPI.post).toHaveBeenCalledWith('/agents/cluster/ai/configs', {
      name: 'deepseek-prod',
      provider: 'deepseek',
      model: 'deepseek-chat',
      display_name: 'DeepSeek Prod',
      enabled: true,
      is_default: false,
      sort_order: 20,
      api_key: 'sk-secret'
    })
    expect(mockRestAPI.patch).toHaveBeenCalledWith('/agents/cluster/ai/configs/2', {
      is_default: true
    })
    expect(created.name).toBe('deepseek-prod')
    expect(updated.is_default).toBe(true)
  })

  test('validates AI configs', async () => {
    mockRestAPI.post.mockResolvedValue({
      result: 'ok',
      provider: 'qwen',
      model: 'qwen3-coder',
      sample: 'PONG',
      last_validated_at: '2026-04-24T10:15:00Z'
    })

    const gateway = useGatewayAPI()
    const result = await gateway.validate_ai_config('cluster', 7)

    expect(mockRestAPI.post).toHaveBeenCalledWith('/agents/cluster/ai/configs/7/validate', {})
    expect(result.result).toBe('ok')
  })

  test('requests AI conversation detail', async () => {
    mockRestAPI.post.mockResolvedValue({
      id: 2,
      title: 'New conversation',
      created_at: '2026-04-24T10:00:00Z',
      updated_at: '2026-04-24T10:00:05Z',
      messages: [
        {
          id: 10,
          role: 'user',
          content: 'Summarize the queue.',
          created_at: '2026-04-24T10:00:00Z'
        },
        {
          id: 11,
          role: 'assistant',
          content: 'Current queue is balanced.',
          created_at: '2026-04-24T10:00:05Z'
        }
      ]
    })
    mockRestAPI.get.mockResolvedValue({
      id: 2,
      title: 'New conversation',
      created_at: '2026-04-24T10:00:00Z',
      updated_at: '2026-04-24T10:00:05Z',
      messages: [
        {
          id: 10,
          role: 'user',
          content: 'Summarize the queue.',
          created_at: '2026-04-24T10:00:00Z'
        }
      ]
    })

    const gateway = useGatewayAPI()
    const result = await gateway.ai_conversation('cluster', 2)

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/ai/conversations/2')
    expect(result.id).toBe(2)
    expect(result.messages).toHaveLength(1)
  })

  test('normalizes permissions sources from merged payload', async () => {
    mockRestAPI.get.mockResolvedValue({
      roles: ['ignored-role'],
      actions: ['ignored-action'],
      sources: {
        policy: { roles: ['user'], actions: ['view-jobs'], rules: ['jobs:view:*'] },
        custom: {
          roles: ['db-admin'],
          actions: [],
          rules: ['admin/access-control:delete:*', 'admin/access-control:edit:*']
        },
        merged: {
          roles: ['user', 'db-admin'],
          actions: ['view-jobs'],
          rules: ['jobs:view:*', 'admin/access-control:delete:*', 'admin/access-control:edit:*']
        }
      }
    })

    const gateway = useGatewayAPI()
    const result = await gateway.permissions('cluster')

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/permissions')
    expect(result.roles).toStrictEqual(['user', 'db-admin'])
    expect(result.actions).toStrictEqual(['view-jobs'])
    expect(result.rules).toEqual(
      expect.arrayContaining([
        'jobs:view:*',
        'admin/access-control:delete:*',
        'admin/access-control:edit:*'
      ])
    )
    expect(result.sources?.policy.rules).toEqual(expect.arrayContaining(['jobs:view:*']))
    expect(result.sources?.custom.rules).toEqual(
      expect.arrayContaining(['admin/access-control:delete:*', 'admin/access-control:edit:*'])
    )
    expect(result.sources?.merged.rules).toEqual(
      expect.arrayContaining([
        'jobs:view:*',
        'admin/access-control:delete:*',
        'admin/access-control:edit:*'
      ])
    )
  })

  test('normalizes legacy permissions payloads without sources', async () => {
    mockRestAPI.get.mockResolvedValue({
      roles: ['user'],
      actions: ['view-jobs']
    })

    const gateway = useGatewayAPI()
    const result = await gateway.permissions('cluster')

    expect(result.roles).toStrictEqual(['user'])
    expect(result.actions).toStrictEqual(['view-jobs'])
    expect(result.rules).toEqual(expect.arrayContaining(['jobs:view:*']))
    expect(result.sources?.policy.rules).toStrictEqual([])
    expect(result.sources?.custom.rules).toStrictEqual([])
    expect(result.sources?.merged.rules).toEqual(expect.arrayContaining(['jobs:view:*']))
  })

  test('requests access control roles list', async () => {
    mockRestAPI.get.mockResolvedValue({
      items: [{ id: 1, name: 'db-admin', description: null, actions: ['admin-manage'] }]
    })

    const gateway = useGatewayAPI()
    const result = await gateway.access_roles('cluster')

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/access/roles')
    expect(result).toStrictEqual([
      {
        id: 1,
        name: 'db-admin',
        description: null,
        actions: ['admin-manage'],
        permissions: []
      }
    ])
  })

  test('creates access control roles', async () => {
    mockRestAPI.post.mockResolvedValue({
      id: 2,
      name: 'ops-viewer',
      description: 'Operations read-only',
      actions: ['view-jobs']
    })

    const gateway = useGatewayAPI()
    const result = await gateway.create_access_role('cluster', {
      name: 'ops-viewer',
      description: 'Operations read-only',
      actions: ['view-jobs']
    })

    expect(mockRestAPI.post).toHaveBeenCalledWith('/agents/cluster/access/roles', {
      name: 'ops-viewer',
      description: 'Operations read-only',
      actions: ['view-jobs']
    })
    expect(result.id).toBe(2)
  })

  test('normalizes remaining admin legacy actions and super-admin alias', async () => {
    mockRestAPI.get.mockResolvedValue({
      roles: ['admin'],
      actions: ['cache-view', 'cache-reset', 'admin-manage']
    })

    const gateway = useGatewayAPI()
    const result = await gateway.permissions('cluster')

    expect(result.rules).toEqual(
      expect.arrayContaining([
        'admin/cache:edit:*',
        'admin/cache:view:*',
        'admin/ldap-cache:view:*',
        '*:*:*'
      ])
    )
    expect(result.rules).toEqual(expect.arrayContaining(['*:*:*']))
  })

  test('lists access control users with filters', async () => {
    mockRestAPI.get.mockResolvedValue({
      items: [
        { username: 'alice', fullname: 'Alice Doe', role_ids: [1], role_names: ['db-admin'] }
      ],
      total: 1,
      page: 2,
      page_size: 20
    })

    const gateway = useGatewayAPI()
    const result = await gateway.access_users('cluster', {
      username: 'ali',
      page: 2,
      page_size: 20
    })

    expect(mockRestAPI.get).toHaveBeenCalledWith(
      '/agents/cluster/access/users?username=ali&page=2&page_size=20'
    )
    expect(result.total).toBe(1)
  })

  test('encodes usernames for access control user role queries', async () => {
    mockRestAPI.get.mockResolvedValue({
      username: 'alice doe',
      fullname: 'Alice Doe',
      policy_roles: ['user'],
      policy_actions: ['view-jobs'],
      custom_roles: [],
      custom_actions: [],
      role_ids: []
    })

    const gateway = useGatewayAPI()
    await gateway.access_user_roles('cluster', 'alice doe')

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/access/users/alice%20doe/roles')
  })

  test('updates access control user roles', async () => {
    mockRestAPI.put.mockResolvedValue({
      username: 'alice',
      fullname: 'Alice Doe',
      policy_roles: ['user'],
      policy_actions: ['view-jobs'],
      custom_roles: ['db-admin'],
      custom_actions: ['admin-manage'],
      role_ids: [1]
    })

    const gateway = useGatewayAPI()
    const result = await gateway.update_access_user_roles('cluster', 'alice', [1])

    expect(mockRestAPI.put).toHaveBeenCalledWith('/agents/cluster/access/users/alice/roles', {
      role_ids: [1]
    })
    expect(result.custom_roles).toStrictEqual(['db-admin'])
  })

  test('requests LDAP cache users with filters', async () => {
    mockRestAPI.get.mockResolvedValue({
      items: [{ username: 'alice', fullname: 'Alice Doe' }],
      total: 1,
      page: 2,
      page_size: 20
    })

    const gateway = useGatewayAPI()
    const result = await gateway.ldap_cache_users('cluster', {
      username: 'ali',
      page: 2,
      page_size: 20
    })

    expect(mockRestAPI.get).toHaveBeenCalledWith(
      '/agents/cluster/users/cache?username=ali&page=2&page_size=20'
    )
    expect(result).toStrictEqual({
      items: [{ username: 'alice', fullname: 'Alice Doe' }],
      total: 1,
      page: 2,
      page_size: 20
    })
  })

  test('normalizes legacy LDAP cache array responses', async () => {
    mockRestAPI.get.mockResolvedValue([
      { username: 'alice', fullname: 'Alice Doe' },
      { username: 'bob', fullname: null }
    ])

    const gateway = useGatewayAPI()
    const result = await gateway.ldap_cache_users('cluster', {
      page: 3,
      page_size: 10
    })

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/users/cache?page=3&page_size=10')
    expect(result).toStrictEqual({
      items: [
        { username: 'alice', fullname: 'Alice Doe' },
        { username: 'bob', fullname: null }
      ],
      total: 2,
      page: 3,
      page_size: 10
    })
  })

  test('requests jobs history with all supported filters', async () => {
    mockRestAPI.get.mockResolvedValue({
      total: 1,
      page: 2,
      page_size: 50,
      jobs: []
    })

    const gateway = useGatewayAPI()
    await gateway.jobs_history('cluster', {
      keyword: 'blast',
      start: '2026-04-01',
      end: '2026-04-24',
      user: 'alice',
      account: 'bio',
      partition: 'gpu',
      qos: 'normal',
      state: 'COMPLETED',
      job_id: 42,
      page: 2,
      page_size: 50,
      sort: 'resources',
      order: 'desc'
    })

    expect(mockRestAPI.get).toHaveBeenCalledWith(
      '/agents/cluster/jobs/history?keyword=blast&start=2026-04-01&end=2026-04-24&user=alice&account=bio&partition=gpu&qos=normal&state=COMPLETED&job_id=42&page=2&page_size=50&sort=resources&order=desc'
    )
  })

  test('requests job history detail by record id', async () => {
    mockRestAPI.get.mockResolvedValue({
      id: 12,
      job_id: 1234,
      exit_code: null
    })

    const gateway = useGatewayAPI()
    const result = await gateway.job_history_detail('cluster', 12)

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/jobs/history/12')
    expect(result.id).toBe(12)
  })

  test('requests node instant metrics', async () => {
    mockRestAPI.get.mockResolvedValue({
      cpu_usage: 0.2,
      memory_usage: 0.3,
      disk_usage: 0.4
    })

    const gateway = useGatewayAPI()
    const result = await gateway.node_metrics('cluster', 'cn1')

    expect(mockRestAPI.get).toHaveBeenCalledWith('/agents/cluster/node/cn1/metrics')
    expect(result).toStrictEqual({
      cpu_usage: 0.2,
      memory_usage: 0.3,
      disk_usage: 0.4
    })
  })

  test('requests node metrics history with range', async () => {
    mockRestAPI.get.mockResolvedValue({
      cpu_usage: [[1748004750000, 0.2]],
      memory_usage: [],
      disk_usage: []
    })

    const gateway = useGatewayAPI()
    const result = await gateway.node_metrics_history('cluster', 'cn1', 'day')

    expect(mockRestAPI.get).toHaveBeenCalledWith(
      '/agents/cluster/node/cn1/metrics/history?range=day'
    )
    expect(result.cpu_usage).toStrictEqual([[1748004750000, 0.2]])
  })
})

describe('compareClusterJobSorter', () => {
  test('compare same jobs', () => {
    const jobA = jobs[1]
    const jobB = jobs[1]
    // A == B
    expect(compareClusterJobSortOrder(jobA, jobB, 'id', 'asc')).toBe(0)
    expect(compareClusterJobSortOrder(jobA, jobB, 'id', 'desc')).toBe(0)
  })
  test('compare sort by id', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobB.job_id = jobB.job_id + 1
    // A < B
    expect(compareClusterJobSortOrder(jobA, jobB, 'id', 'asc')).toBe(-1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'id', 'desc')).toBe(1)
  })
  test('compare sort by user', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.user_name = 'john'
    jobB.user_name = 'mary'
    // A < B
    expect(compareClusterJobSortOrder(jobA, jobB, 'user', 'asc')).toBe(-1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'user', 'desc')).toBe(1)
  })
  test('compare sort by state', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.job_state = ['RUNNING']
    jobB.job_state = ['TERMINATED']
    // A < B
    expect(compareClusterJobSortOrder(jobA, jobB, 'state', 'asc')).toBe(-1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'state', 'desc')).toBe(1)
  })
  test('compare sort by priority number', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.priority = { set: true, infinite: false, number: 1 }
    jobB.priority = { set: true, infinite: false, number: 2 }
    // A < B
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'asc')).toBe(-1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'desc')).toBe(1)
  })
  test('compare sort by priority unset', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.priority = { set: true, infinite: false, number: 1 }
    jobB.priority = { set: false, infinite: false, number: 2 }
    // A > B
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'asc')).toBe(1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'desc')).toBe(-1)
  })
  test('compare sort by priority unset both', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.priority = { set: false, infinite: false, number: 1 }
    jobB.priority = { set: false, infinite: false, number: 2 }
    // A == B
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'asc')).toBe(0)
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'desc')).toBe(0)
  })
  test('compare sort by priority infinite', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.priority = { set: true, infinite: true, number: 0 }
    jobB.priority = { set: true, infinite: false, number: 2 }
    // A > B
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'asc')).toBe(1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'desc')).toBe(-1)
  })
  test('compare sort by priority infinite both', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.priority = { set: true, infinite: true, number: 0 }
    jobB.priority = { set: true, infinite: true, number: 2 }
    // A == B
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'asc')).toBe(0)
    expect(compareClusterJobSortOrder(jobA, jobB, 'priority', 'desc')).toBe(0)
  })
  test('compare sort by resources nodes number', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: false, number: 1 }
    jobA.cpus = { set: true, infinite: false, number: 4 }
    jobB.node_count = { set: true, infinite: false, number: 2 }
    jobB.cpus = { set: true, infinite: false, number: 3 }
    // A < B (cpus ignored)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(-1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(1)
  })
  test('compare sort by resources nodes unset', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: false, number: 1 }
    jobA.cpus = { set: true, infinite: false, number: 4 }
    jobB.node_count = { set: false, infinite: false, number: 2 }
    jobB.cpus = { set: true, infinite: false, number: 3 }
    // A > B (cpus ignored)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(-1)
  })
  test('compare sort by resources nodes unset both', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: false, infinite: false, number: 2 }
    jobA.cpus = { set: true, infinite: false, number: 3 }
    jobB.node_count = { set: false, infinite: false, number: 1 }
    jobB.cpus = { set: true, infinite: false, number: 4 }
    // A < B (cpus considered)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(-1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(1)
  })
  test('compare sort by resources nodes infinite', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: true, number: 1 }
    jobA.cpus = { set: true, infinite: false, number: 4 }
    jobB.node_count = { set: true, infinite: false, number: 2 }
    jobB.cpus = { set: true, infinite: false, number: 3 }
    // A > B (cpus ignored)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(-1)
  })
  test('compare sort by resources nodes infinite both', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: true, number: 0 }
    jobA.cpus = { set: true, infinite: false, number: 3 }
    jobB.node_count = { set: true, infinite: true, number: 1 }
    jobB.cpus = { set: true, infinite: false, number: 4 }
    // A < B (cpus considered)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(-1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(1)
  })
  test('compare sort by resources cpus number', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: false, number: 1 }
    jobA.cpus = { set: true, infinite: false, number: 3 }
    jobB.node_count = { set: true, infinite: false, number: 1 }
    jobB.cpus = { set: true, infinite: false, number: 4 }
    // A < B
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(-1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(1)
  })
  test('compare sort by resources cpus number equal', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: false, number: 1 }
    jobA.cpus = { set: true, infinite: false, number: 4 }
    jobB.node_count = { set: true, infinite: false, number: 1 }
    jobB.cpus = { set: true, infinite: false, number: 4 }
    // A == B
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(0)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(0)
  })
  test('compare sort by resources cpus unset', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: false, number: 1 }
    jobA.cpus = { set: true, infinite: false, number: 4 }
    jobB.node_count = { set: true, infinite: false, number: 1 }
    jobB.cpus = { set: false, infinite: false, number: 3 }
    // A > B
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(-1)
  })
  test('compare sort by resources cpus unset both', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: false, number: 1 }
    jobA.cpus = { set: false, infinite: false, number: 4 }
    jobB.node_count = { set: true, infinite: false, number: 1 }
    jobB.cpus = { set: false, infinite: false, number: 3 }
    // A == B
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(0)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(0)
  })
  test('compare sort by resources cpus infinite', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: false, number: 1 }
    jobA.cpus = { set: true, infinite: true, number: 3 }
    jobB.node_count = { set: true, infinite: false, number: 1 }
    jobB.cpus = { set: true, infinite: false, number: 4 }
    // A > B
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(1)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(-1)
  })
  test('compare sort by resources cpus infinite both', () => {
    const jobA = { ...jobs[1] }
    const jobB = { ...jobs[1] }
    jobA.node_count = { set: true, infinite: false, number: 1 }
    jobA.cpus = { set: true, infinite: true, number: 3 }
    jobB.node_count = { set: true, infinite: false, number: 1 }
    jobB.cpus = { set: true, infinite: true, number: 4 }
    // A == B
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'asc')).toBe(0)
    expect(compareClusterJobSortOrder(jobA, jobB, 'resources', 'desc')).toBe(0)
  })
})

describe('jobResourcesTRES', () => {
  test('basic TRES', () => {
    const job = jobPending
    job.tres.requested = [
      {
        count: 128,
        id: 1,
        name: '',
        type: 'cpu'
      },
      {
        count: 65536,
        id: 2,
        name: '',
        type: 'mem'
      },
      {
        count: 1,
        id: 4,
        name: '',
        type: 'node'
      },
      {
        count: 128,
        id: 5,
        name: '',
        type: 'billing'
      }
    ]
    expect(jobResourcesTRES(job.tres.requested)).toStrictEqual({ node: 1, cpu: 128, memory: 65536 })
  })
  test('empty TRES', () => {
    const job = jobPending
    job.tres.requested = []
    expect(jobResourcesTRES(job.tres.requested)).toStrictEqual({ node: -1, cpu: -1, memory: -1 })
  })
})

describe('jobAllocatedGPU', () => {
  // test specific values
  test('empty GRES', () => {
    const job = { ...jobs[0] }
    job.gres_detail = []
    expect(jobAllocatedGPU(job)).toBe(-1)
  })
  test('simple GRES', () => {
    const job = { ...jobs[0] }
    job.gres_detail = ['gpu:4']
    expect(jobAllocatedGPU(job)).toBe(4)
  })
  test('mixed GRES', () => {
    const job = { ...jobs[0] }
    job.gres_detail = ['license:1,gpu:2']
    expect(jobAllocatedGPU(job)).toBe(2)
  })
  test('GRES with prefix', () => {
    const job = { ...jobs[0] }
    job.gres_detail = ['gres/gpu:4']
    expect(jobAllocatedGPU(job)).toBe(4)
  })
  test('GRES with model', () => {
    const job = { ...jobs[0] }
    job.gres_detail = ['gpu:h200:8']
    expect(jobAllocatedGPU(job)).toBe(8)
  })
  test('GRES with model and prefix', () => {
    const job = { ...jobs[0] }
    job.gres_detail = ['gres/gpu:h200:6']
    expect(jobAllocatedGPU(job)).toBe(6)
  })
  test('GRES with index', () => {
    const job = { ...jobs[0] }
    job.gres_detail = ['gpu:2(IDX:0-1)']
    expect(jobAllocatedGPU(job)).toBe(2)
  })
  test('GRES with model and index', () => {
    const job = { ...jobs[0] }
    job.gres_detail = ['gpu:h100:2(IDX:2-3)']
    expect(jobAllocatedGPU(job)).toBe(2)
  })
  test('multiple GRES with model and index', () => {
    const job = { ...jobs[0] }
    job.gres_detail = ['gpu:h100:2(IDX:2-3)', 'gpu:h100:4(IDX:0-3)']
    expect(jobAllocatedGPU(job)).toBe(6)
  })
  // test with assets
  test('archived job', () => {
    const job = { ...jobGpuArchived }
    expect(jobAllocatedGPU(job)).toBe(-1)
  })
  test('completed job', () => {
    const job = { ...jobGpuCompleted }
    expect(jobAllocatedGPU(job)).toBe(-1)
  })
  test('pending job', () => {
    const job = { ...jobGpuPending }
    expect(jobAllocatedGPU(job)).toBe(-1)
  })
  test('running job', () => {
    const job = { ...jobGpuRunning }
    expect(jobAllocatedGPU(job)).toBeGreaterThan(0)
  })
  test('running gres', () => {
    const job = { ...jobGpuGres }
    expect(jobAllocatedGPU(job)).toBeGreaterThan(0)
  })
  test('running multi nodes', () => {
    const job = { ...jobGpuMultiNodes }
    expect(jobAllocatedGPU(job)).toBeGreaterThan(0)
  })
  test('running type', () => {
    const job = { ...jobGpuType }
    expect(jobAllocatedGPU(job)).toBeGreaterThan(0)
  })
  test('running multi types', () => {
    const job = { ...jobGpuMultiTypes }
    expect(jobAllocatedGPU(job)).toBeGreaterThan(0)
  })
  test('running gpu per node', () => {
    const job = { ...jobGpuPerNode }
    expect(jobAllocatedGPU(job)).toBeGreaterThan(0)
  })
  test('running gpu per socket', () => {
    const job = { ...jobGpuPerSocket }
    expect(jobAllocatedGPU(job)).toBeGreaterThan(0)
  })
  test('running gpu per task', () => {
    const job = { ...jobGpuPerTask }
    expect(jobAllocatedGPU(job)).toBeGreaterThan(0)
  })
})

describe('jobRequestedGPU', () => {
  // tests with specific values
  test('empty requested GRES', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = ''
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 0, reliable: true })
  })
  test('simple GRES requested per job', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = 'gres/gpu:2'
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 2, reliable: true })
  })
  test('simple GRES requested per job with equal sign', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = 'gres/gpu=2'
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 2, reliable: true })
  })
  test('multiple GRES requested per job', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = 'gres/license:1,gres/gpu:4'
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 4, reliable: true })
  })
  test('multiple GRES with gpu type with equal sign', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = 'gres/gpu:h100=6'
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 6, reliable: true })
  })
  test('multiple GRES with gpu type per job', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = 'gres/license:1,gres/gpu:h100:6'
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 6, reliable: true })
  })
  test('multiple GRES with multiple type per job', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = 'gres/license:1,gres/gpu:h100:2,gres/gpu:h200:6'
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 8, reliable: true })
  })
  test('simple GRES requested per node', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = ''
    job.tres_per_node = 'gres/gpu:2'
    job.tres_per_socket = ''
    job.tres_per_task = ''
    job.node_count.number = 4
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 8, reliable: true })
  })
  test('simple GRES requested per socket', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = ''
    job.tres_per_node = ''
    job.tres_per_socket = 'gres/gpu:2'
    job.tres_per_task = ''
    job.node_count.number = 4
    job.sockets_per_node.set = true
    job.sockets_per_node.number = 2
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 16, reliable: false })
  })
  test('simple GRES requested per task', () => {
    const job = { ...jobs[0] }
    job.tres_per_job = ''
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = 'gres/gpu:2'
    job.tasks.number = 4
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 8, reliable: true })
  })
  // tests with assets
  test('archived job', () => {
    const job = { ...jobGpuArchived }
    expect(jobRequestedGPU(job)).toStrictEqual({ count: 0, reliable: true })
  })
  test('completed job', () => {
    const job = { ...jobGpuCompleted }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeTruthy()
  })
  test('pending job', () => {
    const job = { ...jobGpuPending }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeTruthy()
  })
  test('running job', () => {
    const job = { ...jobGpuPending }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeTruthy()
  })
  test('running gres', () => {
    const job = { ...jobGpuGres }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeTruthy()
  })
  test('running multi nodes', () => {
    const job = { ...jobGpuMultiNodes }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeTruthy()
  })
  test('running type', () => {
    const job = { ...jobGpuType }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeTruthy()
  })
  test('running multi types', () => {
    const job = { ...jobGpuMultiTypes }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeTruthy()
  })
  test('running GPU per node', () => {
    const job = { ...jobGpuPerNode }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeTruthy()
  })
  test('running GPU per socket', () => {
    const job = { ...jobGpuPerSocket }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeFalsy()
  })
  test('running GPU per task', () => {
    const job = { ...jobGpuPerTask }
    const gpu = jobRequestedGPU(job)
    expect(gpu.count).toBeGreaterThan(0)
    expect(gpu.reliable).toBeTruthy()
  })
})

describe('jobResourcesGPU', () => {
  test('empty GRES', () => {
    const job = { ...jobs[0] }
    job.gres_detail = []
    job.tres_per_job = ''
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobResourcesGPU(job)).toStrictEqual({ count: 0, reliable: true })
  })
  test('with requested GRES', () => {
    const job = { ...jobs[0] }
    job.gres_detail = []
    job.tres_per_job = 'gres/gpu:4'
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobResourcesGPU(job)).toStrictEqual({ count: 4, reliable: true })
  })
  test('with allocated GRES', () => {
    const job = { ...jobs[0] }
    job.gres_detail = ['gpu:2']
    job.tres_per_job = 'gres/gpu:4'
    job.tres_per_node = ''
    job.tres_per_socket = ''
    job.tres_per_task = ''
    expect(jobResourcesGPU(job)).toStrictEqual({ count: 2, reliable: true })
  })
})

describe('getMBHumanUnit', () => {
  test('MB', () => {
    expect(getMBHumanUnit(128)).toStrictEqual('128MB')
  })
  test('MB rounded', () => {
    expect(getMBHumanUnit(128.5)).toStrictEqual('128.5MB')
    expect(getMBHumanUnit(128.32)).toStrictEqual('128.32MB')
    expect(getMBHumanUnit(128.128)).toStrictEqual('128.13MB')
  })
  test('GB', () => {
    expect(getMBHumanUnit(64 * 1024)).toStrictEqual('64GB')
  })
  test('GB rounded', () => {
    expect(getMBHumanUnit(64.4 * 1024)).toStrictEqual('64.4GB')
    expect(getMBHumanUnit(64.46 * 1024)).toStrictEqual('64.46GB')
    expect(getMBHumanUnit(64.462 * 1024)).toStrictEqual('64.46GB')
  })
  test('TB', () => {
    expect(getMBHumanUnit(4 * 1024 ** 2)).toStrictEqual('4TB')
  })
  test('TB rounded', () => {
    expect(getMBHumanUnit(4.3004 * 1024 ** 2)).toStrictEqual('4.3TB')
    expect(getMBHumanUnit(4.01 * 1024 ** 2)).toStrictEqual('4.01TB')
    expect(getMBHumanUnit(4.016 * 1024 ** 2)).toStrictEqual('4.02TB')
  })
})

describe('getNodeGPUFromGres', () => {
  // test with specific values
  test('empty', () => {
    expect(getNodeGPUFromGres('')).toStrictEqual([])
  })
  test('simple', () => {
    expect(getNodeGPUFromGres('gpu:2')).toStrictEqual([{ model: 'unknown', count: 2 }])
  })
  test('with model', () => {
    expect(getNodeGPUFromGres('gpu:h100:4')).toStrictEqual([{ model: 'h100', count: 4 }])
  })
  test('with index', () => {
    expect(getNodeGPUFromGres('gpu:2(IDX:0-1)')).toStrictEqual([{ model: 'unknown', count: 2 }])
  })
  test('with model and index', () => {
    expect(getNodeGPUFromGres('gpu:h100:2(IDX:0-1)')).toStrictEqual([{ model: 'h100', count: 2 }])
  })
  test('with model and socket', () => {
    expect(getNodeGPUFromGres('gpu:h100:8(S:1,3,5,7)')).toStrictEqual([{ model: 'h100', count: 8 }])
  })
  test('multiple types', () => {
    expect(getNodeGPUFromGres('gpu:1,gpu:h100:2,gpu:h200:4')).toStrictEqual([
      { model: 'unknown', count: 1 },
      { model: 'h100', count: 2 },
      { model: 'h200', count: 4 }
    ])
  })
  test('multiple types with index', () => {
    expect(getNodeGPUFromGres('gpu:1(IDX:0),gpu:h100:1(IDX:1),gpu:h200:0(IDX:N/A)')).toStrictEqual([
      { model: 'unknown', count: 1 },
      { model: 'h100', count: 1 },
      { model: 'h200', count: 0 }
    ])
  })
  // test with assets
  test('node with gpu allocated', () => {
    const node = { ...nodeWithGpusAllocated }
    expect(
      getNodeGPUFromGres(node.gres).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
    expect(
      getNodeGPUFromGres(node.gres_used).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
  })
  test('node with gpu model allocated', () => {
    const node = { ...nodeWithGpusModelAllocated }
    expect(
      getNodeGPUFromGres(node.gres).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
    expect(
      getNodeGPUFromGres(node.gres_used).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
  })
  test('node with gpu mixed', () => {
    const node = { ...nodeWithGpusMixed }
    expect(
      getNodeGPUFromGres(node.gres).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
    expect(
      getNodeGPUFromGres(node.gres_used).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
  })
  test('node with gpu momdel mixed', () => {
    const node = { ...nodeWithGpusModelMixed }
    expect(
      getNodeGPUFromGres(node.gres).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
    expect(
      getNodeGPUFromGres(node.gres_used).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
  })
  test('node with gpu idle', () => {
    const node = { ...nodeWithGpusIdle }
    expect(
      getNodeGPUFromGres(node.gres).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
    expect(
      getNodeGPUFromGres(node.gres_used).reduce((total, current) => total + current.count, 0)
    ).toBe(0)
  })
  test('node with gpu model idle', () => {
    const node = { ...nodeWithGpusModelIdle }
    expect(
      getNodeGPUFromGres(node.gres).reduce((total, current) => total + current.count, 0)
    ).toBeGreaterThan(0)
    expect(
      getNodeGPUFromGres(node.gres_used).reduce((total, current) => total + current.count, 0)
    ).toBe(0)
  })
  test('node without gpu', () => {
    const node = { ...nodeWithoutGpu }
    expect(getNodeGPUFromGres(node.gres).reduce((total, current) => total + current.count, 0)).toBe(
      0
    )
    expect(
      getNodeGPUFromGres(node.gres_used).reduce((total, current) => total + current.count, 0)
    ).toBe(0)
  })
})

describe('getNodeMainState', () => {
  // tests with specific values
  test('node down', () => {
    expect(getNodeMainState(['DOWN'])).toStrictEqual('down')
  })
  test('node error', () => {
    expect(getNodeMainState(['ERROR'])).toStrictEqual('error')
  })
  test('node future', () => {
    expect(getNodeMainState(['FUTURE'])).toStrictEqual('future')
  })
  test('node drain', () => {
    expect(getNodeMainState(['IDLE', 'DRAIN'])).toStrictEqual('drain')
  })
  test('node draining', () => {
    expect(getNodeMainState(['ALLOCATED', 'DRAIN'])).toStrictEqual('draining')
    expect(getNodeMainState(['MIXED', 'DRAIN'])).toStrictEqual('draining')
    expect(getNodeMainState(['IDLE', 'COMPLETING', 'DRAIN'])).toStrictEqual('draining')
  })
  test('node fail', () => {
    expect(getNodeMainState(['IDLE', 'FAIL'])).toStrictEqual('fail')
  })
  test('node failing', () => {
    expect(getNodeMainState(['ALLOCATED', 'FAIL'])).toStrictEqual('failing')
    expect(getNodeMainState(['MIXED', 'FAIL'])).toStrictEqual('failing')
    expect(getNodeMainState(['IDLE', 'COMPLETING', 'FAIL'])).toStrictEqual('failing')
  })
  test('node idle', () => {
    expect(getNodeMainState(['IDLE'])).toStrictEqual('up')
  })
  // tests with assets
  test('asset node down', () => {
    const node = { ...nodeDown }
    expect(getNodeMainState(node.state)).toStrictEqual('down')
  })
  test('asset node allocated', () => {
    const node = { ...nodeAllocated }
    expect(getNodeMainState(node.state)).toStrictEqual('up')
  })
  test('asset node mixed', () => {
    const node = { ...nodeMixed }
    expect(getNodeMainState(node.state)).toStrictEqual('up')
  })
  test('asset node idle', () => {
    const node = { ...nodeIdle }
    expect(getNodeMainState(node.state)).toStrictEqual('up')
  })
})

describe('getNodeAllocationState', () => {
  // tests with specific values
  test('node allocated', () => {
    expect(getNodeAllocationState(['ALLOCATED'])).toStrictEqual('allocated')
  })
  test('node mixed', () => {
    expect(getNodeAllocationState(['MIXED'])).toStrictEqual('mixed')
  })
  test('node down', () => {
    expect(getNodeAllocationState(['DOWN'])).toStrictEqual('unavailable')
  })
  test('node error', () => {
    expect(getNodeAllocationState(['ERROR'])).toStrictEqual('unavailable')
  })
  test('node future', () => {
    expect(getNodeAllocationState(['FUTURE'])).toStrictEqual('unavailable')
  })
  test('node planned', () => {
    expect(getNodeAllocationState(['IDLE', 'PLANNED'])).toStrictEqual('planned')
  })
  test('node idle', () => {
    expect(getNodeAllocationState(['IDLE'])).toStrictEqual('idle')
  })
  // tests with assets
  test('asset node down', () => {
    const node = { ...nodeDown }
    expect(getNodeAllocationState(node.state)).toStrictEqual('unavailable')
  })
  test('asset node allocated', () => {
    const node = { ...nodeAllocated }
    expect(getNodeAllocationState(node.state)).toStrictEqual('allocated')
  })
  test('asset node idle', () => {
    const node = { ...nodeIdle }
    expect(getNodeAllocationState(node.state)).toSatisfy((value) =>
      ['idle', 'planned'].includes(value)
    )
  })
  test('asset node mixed', () => {
    const node = { ...nodeMixed }
    expect(getNodeAllocationState(node.state)).toStrictEqual('mixed')
  })
})

describe('getNodeGPU', () => {
  // test with specific values
  test('empty', () => {
    expect(getNodeGPU('')).toStrictEqual([])
  })
  test('simple', () => {
    expect(getNodeGPU('gpu:2')).toStrictEqual(['2 x unknown'])
  })
  test('with model', () => {
    expect(getNodeGPU('gpu:h100:4')).toStrictEqual(['4 x h100'])
  })
  test('with index', () => {
    expect(getNodeGPU('gpu:2(IDX:0-1)')).toStrictEqual(['2 x unknown'])
  })
  test('with model and index', () => {
    expect(getNodeGPU('gpu:h100:2(IDX:0-1)')).toStrictEqual(['2 x h100'])
  })
  test('with model and multiple indexes', () => {
    expect(getNodeGPU('gpu:h100:5(IDX:0-2,4-5)')).toStrictEqual(['5 x h100'])
  })
  test('multiple types', () => {
    expect(getNodeGPU('gpu:1,gpu:h100:2,gpu:h200:4')).toStrictEqual([
      '1 x unknown',
      '2 x h100',
      '4 x h200'
    ])
  })
  test('multiple types with index', () => {
    expect(getNodeGPU('gpu:1(IDX:0),gpu:h100:1(IDX:1),gpu:h200:0(IDX:N/A)')).toStrictEqual([
      '1 x unknown',
      '1 x h100',
      '0 x h200'
    ])
  })
  // test with assets
  test('node with gpu allocated', () => {
    const node = { ...nodeWithGpusAllocated }
    expect(getNodeGPU(node.gres).length).toBeGreaterThan(0)
    expect(getNodeGPU(node.gres_used).length).toBeGreaterThan(0)
  })
  test('node with gpu model allocated', () => {
    const node = { ...nodeWithGpusModelAllocated }
    expect(getNodeGPU(node.gres).length).toBeGreaterThan(0)
    expect(getNodeGPU(node.gres_used).length).toBeGreaterThan(0)
  })
  test('node with gpu mixed', () => {
    const node = { ...nodeWithGpusMixed }
    expect(getNodeGPU(node.gres).length).toBeGreaterThan(0)
    expect(getNodeGPU(node.gres_used).length).toBeGreaterThan(0)
  })
  test('node with gpu model mixed', () => {
    const node = { ...nodeWithGpusModelMixed }
    expect(getNodeGPU(node.gres).length).toBeGreaterThan(0)
    expect(getNodeGPU(node.gres_used).length).toBeGreaterThan(0)
  })
  test('node with gpu idle', () => {
    const node = { ...nodeWithGpusIdle }
    expect(getNodeGPU(node.gres).length).toBeGreaterThan(0)
    expect(getNodeGPU(node.gres_used).length).toBeGreaterThan(0)
    getNodeGPU(node.gres_used).forEach((gpu) => {
      expect(gpu[0]).toBe('0')
    })
  })
  test('node with gpu model idle', () => {
    const node = { ...nodeWithGpusModelIdle }
    expect(getNodeGPU(node.gres).length).toBeGreaterThan(0)
    expect(getNodeGPU(node.gres_used).length).toBeGreaterThan(0)
    getNodeGPU(node.gres_used).forEach((gpu) => {
      expect(gpu[0]).toBe('0')
    })
  })
  test('node without gpu', () => {
    const node = { ...nodeWithoutGpu }
    expect(getNodeGPU(node.gres).length).toBe(0)
    expect(getNodeGPU(node.gres_used).length).toBe(0)
  })
})
