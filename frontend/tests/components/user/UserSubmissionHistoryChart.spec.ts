import { describe, test, expect } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Chart } from 'chart.js/auto'
import UserSubmissionHistoryChart from '@/components/user/UserSubmissionHistoryChart.vue'

describe('UserSubmissionHistoryChart.vue', () => {
  test('renders submissions dataset from history values', async () => {
    const wrapper = mount(UserSubmissionHistoryChart, {
      props: {
        history: {
          submissions: [
            [1748004750000, 3],
            [1748004810000, 5]
          ]
        }
      }
    })

    await flushPromises()

    const canvas = wrapper.get({ ref: 'chartCanvas' }).element as HTMLCanvasElement
    const chart = Chart.getChart(canvas)

    expect(chart).toBeDefined()
    expect(chart?.data.datasets).toHaveLength(1)
    expect(chart?.data.datasets[0].label).toBe('Submissions')
    expect(chart?.data.datasets[0].data).toEqual([
      { x: 1748004750000, y: 3 },
      { x: 1748004810000, y: 5 }
    ])
  })

  test('clears datasets when history becomes null', async () => {
    const wrapper = mount(UserSubmissionHistoryChart, {
      props: {
        history: {
          submissions: [[1748004750000, 3]]
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
