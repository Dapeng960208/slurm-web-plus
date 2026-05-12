/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DateTimeWindowQuery, MetricRange } from '@/composables/GatewayAPI'
import { isMetricRange } from '@/composables/GatewayAPI'
import type { LocationQuery } from 'vue-router'

/*
 * Dashboard view settings
 */

const chartResourcesTypes = ['nodes', 'cores', 'memory', 'gpus'] as const
export type ChartResourcesType = (typeof chartResourcesTypes)[number]

export function isChartResourcesType(value: unknown): value is ChartResourcesType {
  return typeof value === 'string' && (chartResourcesTypes as readonly string[]).indexOf(value) >= 0
}

export interface DashboardQueryParameters {
  range?: string
  resources?: ChartResourcesType
  partition?: string
  start?: string
  end?: string
}

export const useDashboardRuntimeStore = defineStore('dashboardRuntime', () => {
  const range = ref<MetricRange>('hour')
  const chartResourcesType = ref<ChartResourcesType>('nodes')
  const partition = ref('')
  const start = ref('')
  const end = ref('')

  function reset() {
    range.value = 'hour'
    chartResourcesType.value = 'nodes'
    partition.value = ''
    start.value = ''
    end.value = ''
  }

  function restoreQuery(query: LocationQuery) {
    range.value = query.range && isMetricRange(query.range) ? query.range : 'hour'
    chartResourcesType.value =
      query.resources && isChartResourcesType(query.resources) ? query.resources : 'nodes'
    partition.value = typeof query.partition === 'string' ? query.partition : ''
    start.value = typeof query.start === 'string' ? query.start : ''
    end.value = typeof query.end === 'string' ? query.end : ''
  }

  function query() {
    const result: DashboardQueryParameters = {}
    if (!start.value || !end.value) {
      if (range.value != 'hour') {
        result.range = range.value
      }
    } else {
      result.start = start.value
      result.end = end.value
    }
    if (chartResourcesType.value != 'nodes') {
      result.resources = chartResourcesType.value
    }
    if (partition.value) {
      result.partition = partition.value
    }
    return result
  }

  function clearWindow() {
    start.value = ''
    end.value = ''
  }

  function setWindow(window: DateTimeWindowQuery) {
    start.value = window.start
    end.value = window.end
  }

  function metricsQuery() {
    if (start.value && end.value) {
      return {
        start: start.value,
        end: end.value,
        ...(partition.value ? { partition: partition.value } : {})
      }
    }
    return {
      range: range.value,
      ...(partition.value ? { partition: partition.value } : {})
    }
  }
  return {
    range,
    chartResourcesType,
    partition,
    start,
    end,
    reset,
    restoreQuery,
    query,
    clearWindow,
    setWindow,
    metricsQuery
  }
})
