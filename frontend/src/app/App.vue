<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import { api } from '@/shared/api'
import { theme, toggleTheme } from '@/shared/theme'
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
        <span class="brand-sub">model-supply-chain</span>
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

        <button
          class="icon-btn"
          :title="theme === 'dark' ? '切换到亮色' : '切换到暗色'"
          :aria-label="theme === 'dark' ? '切换到亮色' : '切换到暗色'"
          @click="toggleTheme"
        >
          <svg v-if="theme === 'dark'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
            <circle cx="12" cy="12" r="4.2" />
            <path d="M12 2.5v2.2M12 19.3v2.2M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6" stroke-linecap="round" />
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
            <path d="M20.5 14.6A8.6 8.6 0 1 1 9.4 3.5a6.9 6.9 0 0 0 11.1 11.1Z" stroke-linejoin="round" />
          </svg>
        </button>
      </div>
    </header>

    <main class="content">
      <RouterView />
      <p class="footnote">
        数据来源 hub-stats（Apache-2.0）· 字段口径与界面参考
        <a href="https://github.com/h9-tec/model-family-tree" target="_blank" rel="noreferrer">model-family-tree</a>
        （MIT）与
        <a href="https://huggingface.co/spaces/EQTYLab/lineage-explorer" target="_blank" rel="noreferrer">lineage-explorer</a>
        （Apache-2.0）· 课程作业
      </p>
    </main>
  </div>
</template>
