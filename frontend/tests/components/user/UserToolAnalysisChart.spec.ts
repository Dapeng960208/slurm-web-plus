import { describe, test, expect } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UserToolAnalysisChart from '@/components/user/UserToolAnalysisChart.vue'

describe('UserToolAnalysisChart.vue', () => {
  test('renders tool rows with labels, metrics, and proportional bars', async () => {
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

    const rows = wrapper.findAll('[data-testid^="tool-chart-"]')
    expect(rows).toHaveLength(2)

    expect(wrapper.get('[data-testid="tool-chart-bwa"]').text()).toContain('8 completed job(s)')
    expect(wrapper.get('[data-testid="tool-chart-bwa"]').text()).toContain('9GB')
    expect(wrapper.get('[data-testid="tool-chart-bwa"]').text()).toContain('CPU: 8.0 cores')
    expect(wrapper.get('[data-testid="tool-chart-bwa"]').text()).toContain('Runtime: 2h')

    expect(wrapper.get('[data-testid="tool-chart-samtools"]').text()).toContain('3 completed job(s)')
    expect(wrapper.get('[data-testid="tool-chart-samtools"]').text()).toContain('4GB')
    expect(wrapper.get('[data-testid="tool-chart-samtools"]').text()).toContain('Runtime: 30m')

    const fills = wrapper.findAll('.ui-tool-chart-fill')
    expect(fills).toHaveLength(4)
    expect(fills[0].attributes('style')).toContain('width: 100%')
    expect(fills[1].attributes('style')).toContain('width: 100%')
    expect(fills[2].attributes('style')).toContain('width: 44.44444444444444%')
    expect(fills[3].attributes('style')).toContain('width: 37.5%')
  })

  test('renders fallback values when tool metrics are missing', async () => {
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

    const row = wrapper.get('[data-testid="tool-chart-unknown"]')
    expect(row.text()).toContain('1 completed job(s)')
    expect(row.text()).toContain('N/A')
    expect(row.text()).toContain('CPU: N/A')
    expect(row.text()).toContain('Runtime: N/A')
    expect(row.text()).toContain('Peak reference: N/A')
    expect(wrapper.find('.ui-tool-chart-fill-memory').attributes('style')).toContain('width: 0%')
    expect(wrapper.find('.ui-tool-chart-fill-jobs').attributes('style')).toContain('width: 100%')
  })
})
