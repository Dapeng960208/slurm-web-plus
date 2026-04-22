import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import BrandLogo from '@/components/BrandLogo.vue'

describe('BrandLogo.vue', () => {
  test('uses framed style by default', () => {
    const wrapper = mount(BrandLogo)

    expect(wrapper.classes()).toContain('brand-logo-frame')
  })

  test('can render without the frame', () => {
    const wrapper = mount(BrandLogo, {
      props: {
        framed: false
      }
    })

    expect(wrapper.classes()).not.toContain('brand-logo-frame')
  })
})
