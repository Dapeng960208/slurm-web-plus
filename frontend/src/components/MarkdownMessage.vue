<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import type { RenderRule } from 'markdown-it/lib/renderer.mjs'

const props = defineProps<{
  content: string
  role: 'user' | 'assistant' | 'system'
}>()

const markdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true
})

const defaultLinkOpenRenderer: RenderRule | undefined = markdownRenderer.renderer.rules.link_open

markdownRenderer.renderer.rules.link_open = (tokens, index, options, env, self) => {
  const token = tokens[index]
  const targetIndex = token.attrIndex('target')
  const relIndex = token.attrIndex('rel')

  if (targetIndex < 0) {
    token.attrPush(['target', '_blank'])
  } else {
    token.attrs![targetIndex][1] = '_blank'
  }

  if (relIndex < 0) {
    token.attrPush(['rel', 'noopener noreferrer'])
  } else {
    token.attrs![relIndex][1] = 'noopener noreferrer'
  }

  if (defaultLinkOpenRenderer) {
    return defaultLinkOpenRenderer(tokens, index, options, env, self)
  }

  return self.renderToken(tokens, index, options)
}

const markdownClasses = computed(() => [
  'ui-markdown',
  props.role === 'user' ? 'ui-markdown-user' : 'ui-markdown-assistant'
])

const renderedHtml = computed(() =>
  DOMPurify.sanitize(markdownRenderer.render(props.content || ''), {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel']
  })
)
</script>

<template>
  <div :class="markdownClasses" v-html="renderedHtml" />
</template>
