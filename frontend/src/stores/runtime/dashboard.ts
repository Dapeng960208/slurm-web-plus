/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MetricRange } from '@/composables/GatewayAPI'
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
}

export const useDashboardRuntimeStore = defineStore('dashboardRuntime', () => {
  const range = ref<MetricRange>('hour')
  const chartResourcesType = ref<ChartResourcesType>('nodes')
  const partition = ref('')

  function reset() {
    range.value = 'hour'
    chartResourcesType.value = 'nodes'
    partition.value = ''
  }

  function restoreQuery(query: LocationQuery) {
    range.value = query.range && isMetricRange(query.range) ? query.range : 'hour'
    chartResourcesType.value =
      query.resources && isChartResourcesType(query.resources) ? query.resources : 'nodes'
    partition.value = typeof query.partition === 'string' ? query.partition : ''
  }

  function query() {
    const result: DashboardQueryParameters = {}
    if (range.value != 'hour') {
      result.range = range.value
    }
    if (chartResourcesType.value != 'nodes') {
      result.resources = chartResourcesType.value
    }
    if (partition.value) {
      result.partition = partition.value
    }
    return result
  }
  return {
    range,
    chartResourcesType,
    partition,
    reset,
    restoreQuery,
    query
  }
})
