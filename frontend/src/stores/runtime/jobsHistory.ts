/*
 * Copyright (c) 2026 Rackslab
 *
 * This file is part of Slurm-web.
 *
 * SPDX-License-Identifier: MIT
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { LocationQuery } from 'vue-router'
import type {
  JobHistoryFilters,
  JobHistorySortCriterion,
  JobHistorySortOrder
} from '@/composables/GatewayAPI'

const JobHistorySortCriteria = [
  'submit_time',
  'id',
  'user',
  'state',
  'priority',
  'resources'
] as const
const JobHistorySortOrders = ['asc', 'desc'] as const

function defaultFilters(): JobHistoryFilters {
  return {
    keyword: '',
    user: '',
    account: '',
    partition: '',
    qos: '',
    state: '',
    job_id: undefined,
    start: '',
    end: ''
  }
}

export interface JobsHistoryQueryParameters {
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
  sort?: JobHistorySortCriterion
  order?: JobHistorySortOrder
}

export const useJobsHistoryRuntimeStore = defineStore('jobsHistoryRuntime', () => {
  const sort = ref<JobHistorySortCriterion>('submit_time')
  const order = ref<JobHistorySortOrder>('desc')
  const page = ref(1)
  const filters = ref<JobHistoryFilters>(defaultFilters())

  function resetFilters() {
    filters.value = defaultFilters()
  }

  function isValidSortOrder(candidate: unknown): candidate is JobHistorySortOrder {
    return (
      typeof candidate === 'string' &&
      JobHistorySortOrders.includes(candidate as JobHistorySortOrder)
    )
  }

  function isValidSortCriterion(candidate: unknown): candidate is JobHistorySortCriterion {
    return (
      typeof candidate === 'string' &&
      JobHistorySortCriteria.includes(candidate as JobHistorySortCriterion)
    )
  }

  function hydrate(query: LocationQuery) {
    resetFilters()
    sort.value = 'submit_time'
    order.value = 'desc'
    page.value = 1

    if (isValidSortCriterion(query.sort)) {
      sort.value = query.sort
    }
    if (isValidSortOrder(query.order)) {
      order.value = query.order
    }

    if (typeof query.page === 'string') {
      const parsed = parseInt(query.page, 10)
      page.value = Number.isNaN(parsed) ? 1 : Math.max(parsed, 1)
    }

    const stringKeys: Array<
      'keyword' | 'start' | 'end' | 'user' | 'account' | 'partition' | 'qos' | 'state'
    > = [
      'keyword',
      'start',
      'end',
      'user',
      'account',
      'partition',
      'qos',
      'state'
    ]
    for (const key of stringKeys) {
      const value = query[key]
      filters.value[key] = typeof value === 'string' ? value : ''
    }

    if (typeof query.job_id === 'string') {
      const parsed = parseInt(query.job_id, 10)
      filters.value.job_id = Number.isNaN(parsed) ? undefined : parsed
    }
  }

  function query(): JobsHistoryQueryParameters {
    const result: JobsHistoryQueryParameters = {}
    if (filters.value.keyword) result.keyword = filters.value.keyword
    if (filters.value.start) result.start = filters.value.start
    if (filters.value.end) result.end = filters.value.end
    if (filters.value.user) result.user = filters.value.user
    if (filters.value.account) result.account = filters.value.account
    if (filters.value.partition) result.partition = filters.value.partition
    if (filters.value.qos) result.qos = filters.value.qos
    if (filters.value.state) result.state = filters.value.state
    if (filters.value.job_id !== undefined) result.job_id = filters.value.job_id
    if (page.value !== 1) result.page = page.value
    if (sort.value !== 'submit_time') result.sort = sort.value
    if (order.value !== 'desc') result.order = order.value
    return result
  }

  return {
    sort,
    order,
    page,
    filters,
    resetFilters,
    hydrate,
    query,
    isValidSortOrder,
    isValidSortCriterion
  }
})
