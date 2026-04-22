<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import ResourcesDiagramGeneric from '@/components/resources/ResourcesDiagramGeneric.vue'

const { cluster } = defineProps<{ cluster: string }>()
</script>

<template>
  <ResourcesDiagramGeneric :cluster="cluster" mode="nodes" />
</template>
