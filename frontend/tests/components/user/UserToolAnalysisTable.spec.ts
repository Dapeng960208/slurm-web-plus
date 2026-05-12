import { describe, test, expect } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UserToolAnalysisTable from '@/components/user/UserToolAnalysisTable.vue'
import { init_plugins } from '../../lib/common'

describe('UserToolAnalysisTable.vue', () => {
  test('renders detailed completed job tool metrics in a table', async () => {
    init_plugins()
    const wrapper = mount(UserToolAnalysisTable, {
      props: {
        totalCompletedJobs: 12,
        tools: [
          {
            tool: 'bwa',
            jobs: 8,
            avg_memory_gb: 8,
            max_memory_gb: 12,
            median_memory_gb: 7.5,
            avg_cpu_cores: 7.5,
            avg_runtime_seconds: 5400
          },
          {
            tool: 'samtools',
            jobs: 4,
            avg_memory_gb: 3.25,
            max_memory_gb: 4,
            median_memory_gb: 3,
            avg_cpu_cores: 2,
            avg_runtime_seconds: 1800
          }
        ]
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Avg Memory')
    expect(wrapper.text()).toContain('Max Memory')
    expect(wrapper.text()).toContain('Median Memory')
    expect(wrapper.text()).toContain('Avg Runtime')
    expect(wrapper.text()).toContain('Avg CPU')
    expect(wrapper.text()).not.toContain('Completed Job Tool Table')

    const bwaRow = wrapper.get('[data-testid="tool-analysis-row-bwa"]')
    expect(bwaRow.text()).toContain('bwa')
    expect(bwaRow.text()).toContain('67%')
    expect(bwaRow.text()).toContain('8.00 GB')
    expect(bwaRow.text()).toContain('12.0 GB')
    expect(bwaRow.text()).toContain('7.50 GB')
    expect(bwaRow.text()).toContain('1h 30m')
    expect(bwaRow.text()).toContain('7.5 cores')
    expect(bwaRow.text()).not.toContain('avg 8.00 GB')
    expect(bwaRow.text()).not.toContain('peak 12.0 GB')

    const samtoolsRow = wrapper.get('[data-testid="tool-analysis-row-samtools"]')
    expect(samtoolsRow.text()).toContain('samtools')
    expect(samtoolsRow.text()).toContain('33%')
    expect(samtoolsRow.text()).toContain('3.25 GB')
    expect(samtoolsRow.text()).toContain('4.00 GB')
    expect(samtoolsRow.text()).toContain('30 min')
    expect(samtoolsRow.text()).toContain('2.0 cores')
  })

  test('renders fallback markers when optional metrics are missing', async () => {
    init_plugins()
    const wrapper = mount(UserToolAnalysisTable, {
      props: {
        tools: [
          {
            tool: 'unknown',
            jobs: 1,
            avg_memory_gb: null,
            max_memory_gb: null,
            median_memory_gb: null,
            avg_cpu_cores: null,
            avg_runtime_seconds: null
          }
        ]
      }
    })

    await flushPromises()

    const row = wrapper.get('[data-testid="tool-analysis-row-unknown"]')
    expect(row.text()).toContain('unknown')
    expect(row.text()).toContain('100%')
    expect(row.text()).toContain('--')
  })
})
