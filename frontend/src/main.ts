/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import './style.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { initRuntimeConfiguration, runtimeConfiguration } from '@/plugins/runtimeConfiguration'
import { httpPlugin } from '@/plugins/http'

const runtimeConfigurationOptions = await initRuntimeConfiguration()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(runtimeConfiguration, runtimeConfigurationOptions)
app.use(httpPlugin)
app.mount('#app')
