<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { RouterView } from 'vue-router'
import NotificationsPanel from './components/notifications/NotificationsPanel.vue'
</script>

<template>
  <RouterView />
  <NotificationsPanel />
</template>
