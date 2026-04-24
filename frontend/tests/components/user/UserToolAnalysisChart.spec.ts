import { describe, test, expect } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Chart } from 'chart.js/auto'
import UserToolAnalysisChart from '@/components/user/UserToolAnalysisChart.vue'

describe('UserToolAnalysisChart.vue', () => {
  test('maps tool labels and job counts into the chart dataset', async () => {
    const wrapper = mount(UserToolAnalysisChart, {
      props: {
        tools: [
          {
            tool: 'bwa',
            jobs: 8,
            avg_max_memory_mb: 9216,
            avg_cpu_cores: 8,
            avg_runtime_seconds: 7200
          },
          {
            tool: 'samtools',
            jobs: 3,
            avg_max_memory_mb: 4096,
            avg_cpu_cores: 4,
            avg_runtime_seconds: 1800
          }
        ]
      }
    })

    await flushPromises()

    const canvas = wrapper.get({ ref: 'chartCanvas' }).element as HTMLCanvasElement
    const chart = Chart.getChart(canvas)

    expect(chart).toBeDefined()
    expect(chart?.data.labels).toEqual(['bwa', 'samtools'])
    expect(chart?.data.datasets[0].data).toEqual([8, 3])
  })

  test('formats tooltip details for missing values', async () => {
    const wrapper = mount(UserToolAnalysisChart, {
      props: {
        tools: [
          {
            tool: 'unknown',
            jobs: 1,
            avg_max_memory_mb: null,
            avg_cpu_cores: null,
            avg_runtime_seconds: null
          }
        ]
      }
    })

    await flushPromises()

    const canvas = wrapper.get({ ref: 'chartCanvas' }).element as HTMLCanvasElement
    const chart = Chart.getChart(canvas)
    const afterBody = chart?.options.plugins?.tooltip?.callbacks?.afterBody as
      | ((items: Array<{ dataIndex: number }>) => string[])
      | undefined

    expect(afterBody?.([{ dataIndex: 0 }])).toEqual([
      'Avg memory: N/A',
      'Avg CPU: N/A',
      'Avg runtime: N/A'
    ])
  })
})
