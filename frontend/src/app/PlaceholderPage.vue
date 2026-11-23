<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => String(route.meta.title ?? '未命名'))
const owner = computed(() => String(route.meta.owner ?? '?'))
const desc = computed(() => String(route.meta.desc ?? ''))
</script>

<template>
  <section class="placeholder">
    <div class="badge badge-accent">任务 {{ owner }}</div>
    <h1>{{ title }}</h1>
    <p>{{ desc }}</p>

    <h2 style="margin-top: 8px">接入方式</h2>
    <ol>
      <li>后端：在 <code>backend/modules/</code> 下建自己的包，在 <code>app.py</code> 加一行 <code>include_router</code>；证据模块按 <code>retrieval/</code> 与 <code>verification/</code> 分开。</li>
      <li>前端：把 <code>src/app/router.ts</code> 里的 <code>PlaceholderPage</code> 换成自己的页面组件。</li>
      <li>测试：在仓库根 <code>tests/</code> 下建同名目录（证据按 <code>retrieval/</code>、<code>verification/</code> 分），只测自己的接口。</li>
      <li>只 import <code>@/shared</code> 与 <code>shared/</code>，不跨人引用。</li>
    </ol>

    <p class="faint small" style="margin-top: 28px; margin-bottom: 0">
      本页为占位，等待认领者实现。
    </p>
  </section>
</template>
