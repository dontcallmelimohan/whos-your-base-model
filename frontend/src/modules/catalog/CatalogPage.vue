<script setup lang="ts">
/**
 * 任务 1：模型目录。
 *
 * 版式参考 model-family-tree 的 leaderboard 页：
 *   标题 + 一行统计副标题 → 全局搜索框 → 筛选 chips → 密集表格（含条形）→ 详情
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { errorText } from '@/shared/api'
import type { ModelDetail, ModelSummary, Snapshot } from '@/shared/types'

import { fetchModel, fetchModels, fetchSnapshots } from './api'

type Filter = 'all' | 'no-ghost'

const router = useRouter()

const query = ref('')
const filter = ref<Filter>('all')
const page = ref(1)
const pageSize = 25

const items = ref<ModelSummary[]>([])
const total = ref(0)
const snapshot = ref<Snapshot | null>(null)
const detail = ref<ModelDetail | null>(null)

const loading = ref(false)
const error = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const maxDownloads = computed(() => Math.max(...items.value.map((m) => m.downloads ?? 0), 1))

const rangeText = computed(() => {
  if (!total.value) return '0'
  const from = (page.value - 1) * pageSize + 1
  const to = Math.min(page.value * pageSize, total.value)
  return `${from}–${to} / ${total.value.toLocaleString()}`
})

let timer: number | undefined
watch(query, () => {
  window.clearTimeout(timer)
  timer = window.setTimeout(() => {
    page.value = 1
    load()
  }, 250)
})

watch(filter, () => {
  page.value = 1
  load()
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await fetchModels({
      q: query.value.trim() || undefined,
      page: page.value,
      page_size: pageSize,
      include_ghost: filter.value !== 'no-ghost',
    })
    items.value = result.items
    total.value = result.total
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function openDetail(modelId: string) {
  try {
    detail.value = await fetchModel(modelId)
  } catch (err) {
    error.value = errorText(err)
  }
}

function gotoPage(next: number) {
  page.value = Math.min(Math.max(1, next), totalPages.value)
  load()
}

function openInLineage(modelId: string) {
  router.push({ path: '/lineage', query: { model: modelId } })
}

function fmt(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`
  return String(value)
}

onMounted(async () => {
  try {
    const snapshots = await fetchSnapshots()
    snapshot.value = snapshots.items[0] ?? null
  } catch {
    /* 快照取不到不影响主流程 */
  }
  await load()
})
</script>

<template>
  <section>
    <!-- 标题 + 统计副标题 -->
    <header class="catalog-head">
      <div>
        <h1>模型目录</h1>
        <p class="muted small" style="margin: 4px 0 0">
          按名称搜索 Hugging Face 模型
          <template v-if="snapshot">
            · 快照 {{ snapshot.id }}
            · 更新于 {{ snapshot.snapshot_date }}
          </template>
        </p>
      </div>
      <div class="row">
        <span class="badge">{{ total.toLocaleString() }} 条结果</span>
      </div>
    </header>

    <!-- 搜索 -->
    <div class="catalog-search">
      <span class="search-icon">⌕</span>
      <input
        v-model="query"
        type="search"
        placeholder="搜索任意模型，例如 unsloth/Llama-3.1-8B-Instruct"
        spellcheck="false"
      />
    </div>

    <!-- 筛选 chips -->
    <div class="chips">
      <button class="chip" :class="{ active: filter === 'all' }" @click="filter = 'all'">全部</button>
      <button class="chip" :class="{ active: filter === 'no-ghost' }" @click="filter = 'no-ghost'">
        排除属性未收录
      </button>
      <span class="chips-hint muted small">
        共 {{ total.toLocaleString() }} 个模型 · {{ rangeText }}
      </span>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <!-- 表格 -->
    <div class="panel" style="padding: 0">
      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 48px">#</th>
            <th>模型</th>
            <th style="width: 120px">家族</th>
            <th style="width: 130px">任务</th>
            <th style="width: 190px">下载量</th>
            <th style="width: 110px">创建</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="6" class="muted small" style="padding: 24px">加载中…</td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="6" class="muted small" style="padding: 24px">
              没有匹配的模型。试试更短的关键词，或去掉筛选条件。
            </td>
          </tr>
          <template v-else>
            <tr
              v-for="(row, index) in items"
              :key="row.model_id"
              class="row-click"
              @click="openDetail(row.model_id)"
            >
            <td class="faint">{{ (page - 1) * pageSize + index + 1 }}</td>
            <td>
              <code class="model-id" :title="row.model_id">{{ row.model_id }}</code>
              <span v-if="row.ghost" class="badge badge-warn" style="margin-left: 8px">未收录</span>
            </td>
            <td class="muted">{{ row.family ?? '—' }}</td>
            <td class="muted">{{ row.pipeline ?? '—' }}</td>
            <td>
              <div class="metric-cell">
                <span class="num">{{ fmt(row.downloads) }}</span>
                <span class="bar">
                  <span
                    :style="{ width: Math.min(100, ((row.downloads ?? 0) / maxDownloads) * 100) + '%' }"
                  ></span>
                </span>
              </div>
            </td>
              <td class="faint small">{{ (row.created ?? '—').slice(0, 10) }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pager">
      <button class="ghost" :disabled="page <= 1 || loading" @click="gotoPage(page - 1)">上一页</button>
      <span class="muted small">{{ page }} / {{ totalPages }}</span>
      <button class="ghost" :disabled="page >= totalPages || loading" @click="gotoPage(page + 1)">
        下一页
      </button>
    </div>

    <!-- 详情 -->
    <div v-if="detail" class="drawer">
      <header class="drawer-head">
        <span class="badge badge-accent">模型</span>
        <strong>详情</strong>
        <button class="panel-close" @click="detail = null">✕</button>
      </header>

      <section class="drawer-section">
        <dl class="kv">
          <dt>Model ID</dt>
          <dd><code class="break">{{ detail.model_id }}</code></dd>
          <dt>作者</dt>
          <dd>{{ detail.author ?? '—' }}</dd>
          <dt>家族</dt>
          <dd>{{ detail.family ?? '—' }}</dd>
          <dt>任务</dt>
          <dd>{{ detail.pipeline ?? '—' }}</dd>
          <dt>库</dt>
          <dd>{{ detail.library ?? '—' }}</dd>
          <dt>下载量</dt>
          <dd class="num-inline">{{ fmt(detail.downloads) }}</dd>
          <dt>创建</dt>
          <dd>{{ (detail.created ?? '—').slice(0, 10) }}</dd>
        </dl>
      </section>

      <section class="drawer-section">
        <h3>关联数据集 · {{ detail.datasets.length }}</h3>
        <p v-if="!detail.datasets.length" class="faint small" style="margin: 0">
          当前快照没有模型—数据集关联（hubstats 源不含该字段）。
        </p>
        <ul v-else class="rel-list">
          <li v-for="link in detail.datasets" :key="link.dataset_id">
            <code>{{ link.dataset_id }}</code>
            <span class="badge">{{ link.source_field ?? 'datasets' }}</span>
          </li>
        </ul>
        <p class="faint small" style="margin: 10px 0 0">
          只展示记录中的关联，不推断训练用途。
        </p>
      </section>

      <div class="drawer-actions">
        <button @click="openInLineage(detail.model_id)">在供应链小图中打开</button>
      </div>
    </div>
  </section>
</template>
