<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import { api, errorText } from '@/shared/api'
import type { Health } from '@/shared/types'

const health = ref<Health | null>(null)
const offline = ref(false)

async function refresh() {
  try {
    health.value = await api<Health>('/api/health')
    offline.value = false
  } catch {
    offline.value = true
  }
}

onMounted(refresh)
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <span class="brand-title">AI 模型供应链平台</span>
        <span class="brand-sub">Model Supply Chain</span>
      </div>

      <nav class="nav">
        <RouterLink to="/data">数据管理</RouterLink>
        <RouterLink to="/catalog">模型目录</RouterLink>
        <RouterLink to="/lineage">供应链小图</RouterLink>
        <RouterLink to="/galaxy">大图 Galaxy</RouterLink>
        <RouterLink to="/analysis">生态分析</RouterLink>
      </nav>

      <div class="status">
        <span v-if="offline" class="badge badge-danger">后端未连接</span>
        <span v-else-if="health?.data_ready" class="badge badge-ok">
          {{ health.snapshot_id }} · {{ health.model_count.toLocaleString() }} 模型
        </span>
        <span v-else class="badge badge-warn">无数据</span>
      </div>
    </header>

    <main class="content">
      <RouterView />
      <p class="footnote">
        数据来源：hub-stats dump（Apache-2.0）· 字段口径与布局参考
        <a href="https://github.com/h9-tec/model-family-tree" target="_blank" rel="noreferrer">model-family-tree</a>
        （MIT）· 课程作业，非生产系统。
      </p>
    </main>
  </div>
</template>
