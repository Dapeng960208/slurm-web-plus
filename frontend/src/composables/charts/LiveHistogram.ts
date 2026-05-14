/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { watch, onMounted } from 'vue'
import type { Ref } from 'vue'
import type { GatewayAnyClusterApiKey } from '@/composables/GatewayAPI'
import type { DashboardPartitionQuery } from '@/composables/GatewayAPI'
import { useClusterDataPoller } from '@/composables/DataPoller'
import type { ClusterDataPoller } from '@/composables/DataPoller'
import type { ClusterDataPollerParam } from '@/composables/DataPoller'
import type { MetricValue } from '@/composables/GatewayAPI'
import type { DashboardMetricsQuery } from '@/composables/GatewayAPI'
import { Chart } from 'chart.js/auto'
import type { ChartOptions, TimeScaleOptions, TimeUnit, Point } from 'chart.js'
import 'chartjs-adapter-luxon'
import { DateTime } from 'luxon'

type HistogramValueFormatter = (value: number) => string | undefined

export interface DashboardLiveChart<MetricKeyType extends string> {
  metrics: ClusterDataPoller<Record<MetricKeyType, MetricValue[]>>
  setCluster: (cluster: string) => void
  setRange: (range: string, query?: DashboardPartitionQuery | DashboardMetricsQuery) => void
  setCallback: (callback: GatewayAnyClusterApiKey) => void
  setLabels: (
    labels: Record<string, { group: MetricKeyType[]; color: string; invert?: boolean }>
  ) => void
  clear: () => void
}

export function useLiveHistogram<MetricKeyType extends string>(
  cluster: string,
  callback: GatewayAnyClusterApiKey,
  chartCanvas: Ref<HTMLCanvasElement | null>,
  originalLabels: Record<string, { group: MetricKeyType[]; color: string; invert?: boolean }>,
  originalRange: string,
  originalQuery?: DashboardPartitionQuery,
  valueFormatter?: HistogramValueFormatter
): DashboardLiveChart<MetricKeyType> {
  let range = originalRange
  let labels = originalLabels
  let filterQuery = originalQuery

  const metrics = useClusterDataPoller<Record<MetricKeyType, MetricValue[]>>(
    cluster,
    callback,
    60000,
    buildMetricsQuery(range, filterQuery)
  )
  let chart: Chart | null

  /* Detect dark mode to set darker grid and axis colors */
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    Chart.defaults.borderColor = '#333333'
  }

  function buildDatasets() {
    const metricData = metrics.data.value
    if (!metricData) return []
    return Object.entries(labels).flatMap(([label, properties]) => {
      if (!properties.group.some((metric) => metric in metricData)) {
        return []
      }
      const newData = metricData[properties.group[0]].map((value) => ({
        x: value[0],
        y: properties.invert ? -value[1] : value[1]
      }))
      if (properties.group.length > 1) {
        properties.group.forEach((metric, index) => {
          if (!index) return
          metricData[metric].forEach((value) => {
            const item = newData.find((_value) => _value.x == value[0])
            if (item) item.y += value[1]
          })
        })
      }
      return [
        {
          label: label,
          data: newData,
          barPercentage: 1,
          fill: 'stack' as const,
          backgroundColor: properties.color
        }
      ]
    })
  }

  function syncChart() {
    if (!chart) return
    if (!metrics.data.value) {
      chart.data.datasets = []
      chart.update()
      return
    }
    chart.data.datasets = buildDatasets()
    if (chart.options.scales && chart.options.scales.x) {
      chart.options.scales.x.suggestedMin = suggestedMin()
      ;(chart.options.scales.x as TimeScaleOptions).time.unit = timeframeUnit()
    }
    chart.update()
  }

  watch(
    () => metrics.data.value,
    () => {
      syncChart()
    }
  )

  /* Compute the suggested min of the x-axis depending on the current dashboard
   * range. */
  function suggestedMin() {
    const now = Date.now()
    let result = 0
    if (range == 'hour') {
      result = now - 60 * 60 * 1000
    }
    if (range == 'day') {
      result = now - 24 * 60 * 60 * 1000
    }
    if (range == 'week') {
      result = now - 7 * 24 * 60 * 60 * 1000
    }
    return result
  }

  /* Determine the timeframe unit of the x-axis depending on the current
   * dashboard range. */
  function timeframeUnit(): TimeUnit {
    if (range == 'hour') {
      return 'minute'
    }
    return 'hour'
  }

  /* Determine ticks labels on y-axis */
  function yTicksCallback(value: number | string) {
    if (typeof value !== 'number') return value
    const formattedValue = valueFormatter?.(value)
    if (formattedValue !== undefined) {
      return formattedValue
    }
    /* y-axis represent nodes, cores or jobs, select only integers values */
    if (value % 1 === 0) {
      return value
    }
  }

  /* Determine ticks labels on x-axis. */
  function xTicksCallback(value: number | string) {
    if (typeof value === 'number') {
      const dt = DateTime.fromMillis(value)
      // localized time simple every five minutes with hour range.
      if (range == 'hour' && value % (1000 * 60 * 5) === 0)
        return dt.toLocaleString(DateTime.TIME_SIMPLE)
      // localized time simple every hours with day range.
      if (range == 'day' && value % (1000 * 60 * 60) === 0)
        return dt.toLocaleString(DateTime.TIME_SIMPLE)
      // localized numeric day time at midnight and empty tick at noon.
      if (range == 'week') {
        if (value % (1000 * 60 * 60 * 24) === 0) {
          return dt.toLocaleString({ month: 'numeric', day: 'numeric' })
        }
        if (value % (1000 * 60 * 60 * 12) === 0) {
          return ''
        }
      }
    }
  }

  const genericOptions: ChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: valueFormatter
      ? {
          tooltip: {
            callbacks: {
              label: (context) => {
                const value = context.parsed.y
                const label = context.dataset.label ? `${context.dataset.label}: ` : ''
                if (typeof value !== 'number') {
                  return label.trim()
                }
                return `${label}${valueFormatter(value) ?? value}`
              }
            }
          }
        }
      : undefined,
    scales: {
      y: {
        stacked: true,
        beginAtZero: true,
        ticks: {
          callback: yTicksCallback
        }
      },
      x: {
        type: 'time',
        stacked: true,
        grid: {
          offset: false
        },
        ticks: {
          callback: xTicksCallback
        }
      }
    }
  }
  function clear() {
    if (chart) {
      chart.data.datasets = []
      chart.update()
    }
  }

  function buildMetricsQuery(
    metricsRange: string,
    query?: DashboardPartitionQuery | DashboardMetricsQuery
  ): ClusterDataPollerParam {
    if (query && 'start' in query && 'end' in query) {
      return {
        start: query.start,
        end: query.end,
        ...(query.partition ? { partition: query.partition } : {})
      }
    }
    if (!query?.partition) {
      return metricsRange
    }
    return {
      range: metricsRange,
      partition: query.partition
    }
  }

  function setCluster(newCluster: string) {
    clear()
    metrics.setCluster(newCluster)
  }

  /* Clear chart datasets and set new poller param when dashboard range is
   * modified. */
  function setRange(newRange: string, query?: DashboardPartitionQuery | DashboardMetricsQuery) {
    range = newRange
    filterQuery = query
    clear()
    metrics.setParam(buildMetricsQuery(range, filterQuery))
  }

  /* Clear chart datasets and set new metrics callback */
  function setCallback(callback: GatewayAnyClusterApiKey) {
    clear()
    metrics.setCallback(callback)
  }

  function setLabels(
    newLabels: Record<string, { group: MetricKeyType[]; color: string; invert?: boolean }>
  ) {
    labels = newLabels
    syncChart()
  }

  onMounted(() => {
    if (chartCanvas.value) {
      chart = new Chart(chartCanvas.value, {
        type: 'bar',
        data: { datasets: [] },
        options: genericOptions
      })
    }
  })

  return { metrics, setCluster, setRange, setCallback, setLabels, clear }
}
