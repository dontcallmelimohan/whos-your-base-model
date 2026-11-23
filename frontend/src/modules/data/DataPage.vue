<script setup lang="ts">
/**
 * 工作包 A：数据管理页。
 *
 * 职责：导入数据、查看数据版本与范围、检查快照统计、看数据集关联与导入记录。
 * 其他三个工作包的页面不依赖这个页面，只依赖 /api/* 契约。
 */
import { computed, onMounted, ref } from 'vue'

import { errorText } from '@/shared/api'
import type { DatasetUsage, Health, ImportRecord, Snapshot, SnapshotStats } from '@/shared/types'

import { fetchDatasets, fetchHealth, fetchImports, fetchSnapshots, fetchStats, postImport } from './api'

const health = ref<Health | null>(null)
const snapshots = ref<Snapshot[]>([])
const selected = ref<string>('')
const stats = ref<SnapshotStats | null>(null)
const datasets = ref<DatasetUsage[]>([])
const imports = ref<ImportRecord[]>([])

const loading = ref(false)
const importing = ref(false)
const error = ref('')
const notice = ref('')

const source = ref('fixtures')
const limit = ref<number | null>(20000)

const current = computed(() => snapshots.value.find((item) => item.id === selected.value) ?? null)

const typeRows = computed(() => {
  if (!stats.value) return []
  const total = stats.value.type_distribution.reduce((sum, item) => sum + item.count, 0) || 1
  return stats.value.type_distribution.map((item) => ({
    ...item,
    percent: Math.round((item.count / total) * 100),
  }))
})

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

function formatDate(value: string | null | undefined): string {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    health.value = await fetchHealth()
    const list = await fetchSnapshots()
    snapshots.value = list.items
    if (!selected.value || !snapshots.value.some((item) => item.id === selected.value)) {
      selected.value = list.items[0]?.id ?? ''
    }
    await loadSnapshotDetail()
    imports.value = (await fetchImports(10)).items
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function loadSnapshotDetail() {
  if (!selected.value) {
    stats.value = null
    datasets.value = []
    return
  }
  stats.value = await fetchStats(selected.value)
  datasets.value = (await fetchDatasets(selected.value, 10)).items
}

async function onSelect() {
  error.value = ''
  try {
    await loadSnapshotDetail()
  } catch (err) {
    error.value = errorText(err)
  }
}

async function runImport() {
  importing.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await postImport(source.value, limit.value)
    notice.value =
      `导入完成：${result.snapshot_id} · 模型 ${result.model_count.toLocaleString()} · ` +
      `关系 ${result.relation_count.toLocaleString()}`
    selected.value = result.snapshot_id
    await loadAll()
  } catch (err) {
    error.value = errorText(err)
  } finally {
    importing.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <section>
    <div class="row" style="justify-content: space-between; margin-bottom: 16px">
      <div>
        <h1>数据管理</h1>
        <p class="muted small" style="margin: 0">
          导入快照、查看数据范围、核对统计口径。工作包 A 负责本页与
          <code>/api/imports</code>、<code>/api/snapshots</code>、<code>/api/datasets</code>。
        </p>
      </div>
      <button class="ghost" :disabled="loading" @click="loadAll">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="notice" class="alert alert-info">{{ notice }}</div>
    <div v-if="!loading && health && !health.data_ready" class="alert alert-info">
      数据库还没有数据。先在下面导入一次样例（fixtures），或运行
      <code>python -m scripts.seed</code>。
    </div>

    <!-- 导入 -->
    <div class="panel">
      <h2>导入数据</h2>
      <div class="row">
        <select v-model="source">
          <option value="fixtures">fixtures · 12 条边的样例（秒级）</option>
          <option value="hubstats">hubstats · 仓库根 models.parquet（真实数据）</option>
          <option value="modeltree">modeltree · model-family-tree 派生数据</option>
        </select>
        <input
          v-model.number="limit"
          type="number"
          min="1"
          style="width: 120px"
          placeholder="模型上限"
        />
        <button :disabled="importing" @click="runImport">
          {{ importing ? '导入中…' : '开始导入' }}
        </button>
        <span class="muted small">重复导入同一数据源不会产生重复记录。</span>
      </div>
    </div>

    <!-- 快照 -->
    <div class="panel">
      <h2>数据版本</h2>
      <div v-if="!snapshots.length" class="muted small">还没有任何数据版本。</div>
      <div v-else class="row" style="margin-bottom: 12px">
        <select v-model="selected" @change="onSelect">
          <option v-for="item in snapshots" :key="item.id" :value="item.id">
            {{ item.id }} · {{ item.source }}
          </option>
        </select>
        <span v-if="current" class="badge badge-muted">规则 {{ current.rule_version }}</span>
        <span v-if="current" class="badge badge-muted">快照日期 {{ current.snapshot_date }}</span>
      </div>
      <p v-if="current?.scope_note" class="muted small" style="margin: 0">
        范围说明：{{ current.scope_note }}
      </p>
      <p v-if="current?.input_hash" class="muted small" style="margin: 4px 0 0">
        输入哈希：<code>{{ current.input_hash.slice(0, 16) }}…</code>
      </p>
    </div>

    <!-- 统计 -->
    <div v-if="stats" class="grid grid-4" style="margin-bottom: 16px">
      <div class="stat">
        <div class="stat-label">模型</div>
        <div class="stat-value">{{ formatNumber(stats.model_count) }}</div>
      </div>
      <div class="stat">
        <div class="stat-label">关系</div>
        <div class="stat-value">{{ formatNumber(stats.relation_count) }}</div>
      </div>
      <div class="stat">
        <div class="stat-label">占位上游</div>
        <div class="stat-value">{{ formatNumber(stats.ghost_count) }}</div>
      </div>
      <div class="stat">
        <div class="stat-label">家族</div>
        <div class="stat-value">{{ formatNumber(stats.family_count) }}</div>
      </div>
    </div>

    <div class="grid grid-2">
      <div class="panel">
        <h2>关系类型分布</h2>
        <div v-if="!typeRows.length" class="muted small">无数据</div>
        <div v-for="row in typeRows" :key="row.type" class="bar-row">
          <span>{{ row.type }}</span>
          <span class="bar"><span :style="{ width: row.percent + '%' }"></span></span>
          <span class="num">{{ row.count.toLocaleString() }}</span>
        </div>
      </div>

      <div class="panel">
        <h2>数据集关联 Top 10</h2>
        <div v-if="!datasets.length" class="muted small">
          当前快照没有模型—数据集关联（hubstats 源不含该字段，可用 modelbiome 源补）。
        </div>
        <table v-else>
          <thead>
            <tr>
              <th>数据集</th>
              <th class="num">关联模型</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in datasets" :key="item.dataset_id">
              <td><code>{{ item.dataset_id }}</code></td>
              <td class="num">{{ item.model_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 导入记录 -->
    <div class="panel">
      <h2>导入记录</h2>
      <div v-if="!imports.length" class="muted small">还没有导入记录。</div>
      <table v-else>
        <thead>
          <tr>
            <th>#</th>
            <th>数据版本</th>
            <th>来源</th>
            <th class="num">模型</th>
            <th class="num">关系</th>
            <th class="num">数据集关联</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in imports" :key="item.id">
            <td>{{ item.id }}</td>
            <td><code>{{ item.snapshot_id }}</code></td>
            <td>{{ item.source }}</td>
            <td class="num">{{ item.model_count.toLocaleString() }}</td>
            <td class="num">{{ item.relation_count.toLocaleString() }}</td>
            <td class="num">{{ item.dataset_link_count.toLocaleString() }}</td>
            <td class="muted">{{ formatDate(item.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
