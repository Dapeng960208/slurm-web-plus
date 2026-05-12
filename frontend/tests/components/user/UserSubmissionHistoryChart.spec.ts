import { describe, test, expect } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Chart } from 'chart.js/auto'
import UserSubmissionHistoryChart from '@/components/user/UserSubmissionHistoryChart.vue'
import { init_plugins } from '../../lib/common'

describe('UserSubmissionHistoryChart.vue', () => {
  test('renders submissions and completions datasets from history values', async () => {
    init_plugins()
    const wrapper = mount(UserSubmissionHistoryChart, {
      props: {
        history: {
          submissions: [
            [1748004750000, 3],
            [1748004810000, 5]
          ],
          completions: [
            [1748004750000, 1],
            [1748004810000, 4]
          ]
        }
      }
    })

    await flushPromises()

    const canvas = wrapper.get({ ref: 'chartCanvas' }).element as HTMLCanvasElement
    const chart = Chart.getChart(canvas)

    expect(chart).toBeDefined()
    expect(chart?.data.datasets).toHaveLength(6)
    expect(chart?.data.datasets[0].label).toBe('Submissions')
    expect(chart?.data.datasets[0].data).toEqual([
      { x: 1748004750000, y: 3 },
      { x: 1748004810000, y: 5 }
    ])
    expect(chart?.data.datasets[1].label).toBe('Completions')
    expect(chart?.data.datasets[1].data).toEqual([
      { x: 1748004750000, y: 1 },
      { x: 1748004810000, y: 4 }
    ])
    expect(chart?.data.datasets.map((dataset) => dataset.label)).toEqual([
      'Submissions',
      'Completions',
      'Running',
      'Pending',
      'Failed',
      'Cancelled'
    ])
    expect(chart?.data.datasets[2].data).toEqual([])
    expect(chart?.data.datasets[3].data).toEqual([])
    expect(chart?.data.datasets[4].data).toEqual([])
    expect(chart?.data.datasets[5].data).toEqual([])
  })

  test('clears datasets when history becomes null', async () => {
    init_plugins()
    const wrapper = mount(UserSubmissionHistoryChart, {
      props: {
        history: {
          submissions: [[1748004750000, 3]],
          completions: [[1748004750000, 1]]
        }
      }
    })

    await flushPromises()
    await wrapper.setProps({ history: null })
    await flushPromises()

    const canvas = wrapper.get({ ref: 'chartCanvas' }).element as HTMLCanvasElement
    const chart = Chart.getChart(canvas)

    expect(chart).toBeDefined()
    expect(chart?.data.datasets).toEqual([])
  })
})
