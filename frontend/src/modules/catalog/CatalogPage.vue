<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorText } from '@/shared/api'
import type { ModelSummary, Snapshot } from '@/shared/types'

import { fetchBoard, fetchModel, fetchModels, fetchSnapshots, type BoardMetric, type BoardRow, type CatalogDetail, type CatalogMetric } from './api'

import SnapshotTrends from './SnapshotTrends.vue'

// Ranking presets, sortable columns and relative score bars adapted from
// model-family-tree/site/app.js, Copyright (c) 2026 Hesham Haroon, MIT.
type View = 'board' | 'catalog' | 'trends'
const columns: { key: Exclude<BoardMetric, 'model_id'>; label: string }[] = [
  { key: 'total', label: '全部后代' }, { key: 'direct', label: '直接下游' },
  { key: 'recent', label: '近 90 天' }, { key: 'finetune', label: '微调' },
  { key: 'adapter', label: '适配器' }, { key: 'quantized', label: '量化' },
  { key: 'merge', label: '合并' },
]
const presets = [{ key: 'total', label: '全部时间' }, { key: 'recent', label: '近 90 天' },
  { key: 'finetune', label: '按微调' }] as const
const boardSortOptions = [
  { key: 'model_id', label: '模型名称' },
  ...columns,
]
const catalogSortOptions: { key: CatalogMetric; label: string }[] = [
  { key: 'downloads', label: '下载量' }, { key: 'downloads_all', label: '累计下载' },
  { key: 'likes', label: '点赞数' }, { key: 'created', label: '创建时间' },
  { key: 'model_id', label: '模型名称' },
]
const route = useRoute()
const view = ref<View>(route.query.view === 'trends' ? 'trends' : route.query.view === 'catalog' ? 'catalog' : 'board')
const catalogMetric = ref<CatalogMetric>('downloads')
const catalogAscending = ref(false)
const metric = ref<BoardMetric>('total')
const ascending = ref(false)
const showGhost = ref(true)
const board = ref<BoardRow[]>([])
const families = ref<string[]>([])
const modeLabel = computed(() => view.value === 'board' ? '有下游的模型' : '模型')
const activeColumn = computed(() => columns.find((column) => column.key === metric.value)?.key)
const maxScore = computed(() => {
  const key = activeColumn.value
  return key ? Math.max(1, ...board.value.map((row) => row[key])) : 1
})

const router = useRouter()

const query = ref('')
const family = ref('')
const page = ref(1)
const pageSize = 25

const items = ref<ModelSummary[]>([])
const total = ref(0)
const snapshots = ref<Snapshot[]>([])
const snapshotId = ref('')
const detail = ref<CatalogDetail | null>(null)
let searchRequest = 0
let detailRequest = 0

const loading = ref(false)
const error = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

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

onBeforeUnmount(() => window.clearTimeout(timer))

watch([view, family, showGhost, metric, ascending, catalogMetric, catalogAscending], () => {
  page.value = 1
  load()
})

function selectView(next: View) {
  if (view.value === next) return
  family.value = ''
  closeDetail()
  view.value = next
  void router.replace({ query: { ...route.query, view: next === 'board' ? undefined : next } })
}

function selectSort(key: BoardMetric, toggle = false) {
  if (toggle && metric.value === key) ascending.value = !ascending.value
  else {
    metric.value = key
    ascending.value = key === 'model_id'
  }
}

function sortState(key: BoardMetric) {
  return metric.value !== key ? 'none' : ascending.value ? 'ascending' : 'descending'
}

function changeSnapshot() {
  page.value = 1
  closeDetail()
  board.value = []
  items.value = []
  if (family.value) family.value = ''
  else load()
}

async function load() {
  const request = ++searchRequest
  if (view.value === 'trends') {
    loading.value = false
    error.value = ''
    return
  }
  loading.value = true
  error.value = ''
  try {
    const params = {
      snapshot_id: snapshotId.value || undefined,
      q: query.value.trim() || undefined,
      family: family.value || undefined,
      page: page.value,
      page_size: pageSize,
      include_ghost: showGhost.value,
    }
    if (view.value === 'board') {
      const result = await fetchBoard({ ...params, sort: metric.value, ascending: ascending.value })
      if (request !== searchRequest) return
      board.value = result.items
      families.value = result.families
      total.value = result.total
    } else {
      const result = await fetchModels({ ...params, sort: catalogMetric.value, ascending: catalogAscending.value })
      if (request !== searchRequest) return
      items.value = result.items
      total.value = result.total
    }
  } catch (err) {
    if (request === searchRequest) error.value = errorText(err)
  } finally {
    if (request === searchRequest) loading.value = false
  }
}

async function openDetail(modelId: string) {
  const request = ++detailRequest
  try {
    const result = await fetchModel(modelId, snapshotId.value || undefined)
    if (request === detailRequest) detail.value = result
  } catch (err) {
    if (request === detailRequest) error.value = errorText(err)
  }
}

function closeDetail() {
  ++detailRequest
  detail.value = null
}

function hubModelUrl(modelId: string) {
  return 'https://huggingface.co/' + modelId.split('/').map(encodeURIComponent).join('/')
}

function gotoPage(next: number) {
  page.value = Math.min(Math.max(1, next), totalPages.value)
  load()
}

function openInLineage(modelId: string) {
  router.push({ path: '/lineage', query: { model: modelId } })
}

function fmt(value: number | null | undefined): string {
  return value == null ? '—' : Number(value).toLocaleString('en-US')
}

onMounted(async () => {
  try {
    snapshots.value = (await fetchSnapshots()).items
    snapshotId.value = snapshots.value[0]?.id ?? ''
  } catch {
    /* 快照取不到不影响主流程 */
  }
  await load()
})
</script>

<template>
  <section class="catalog-workspace" @keydown.esc="closeDetail">
    <header class="registry-header">
      <div>
        <h1>模型目录</h1>
        <p>查询 Hugging Face 模型及其已声明的衍生关系。</p>
      </div>
      <label class="snapshot-control" v-if="snapshots.length">
        <span>数据快照</span>
        <select v-model="snapshotId" aria-label="目录快照" @change="changeSnapshot">
          <option v-for="item in snapshots" :key="item.id" :value="item.id">
            {{ item.snapshot_date }} · {{ item.id }}
          </option>
        </select>
      </label>
    </header>

    <div v-if="view !== 'trends'" class="catalog-search registry-search">
      <span class="search-icon" aria-hidden="true">⌕</span>
      <input v-model="query" type="search" aria-label="搜索模型"
        placeholder="搜索模型或组织，例如 Qwen/Qwen2.5" spellcheck="false" />
    </div>

    <nav class="registry-tabs" aria-label="目录视图">
      <button type="button" :aria-pressed="view === 'board'" @click="selectView('board')">衍生排行</button>
      <button type="button" :aria-pressed="view === 'catalog'" @click="selectView('catalog')">全部模型</button>
      <button type="button" :aria-pressed="view === 'trends'" @click="selectView('trends')">快照趋势</button>
    </nav>

    <SnapshotTrends v-if="view === 'trends'" :snapshot-id="snapshotId" />
    <template v-else>
    <div class="registry-toolbar">
      <div v-if="view === 'board'" class="board-presets" aria-label="排行方式">
        <button v-for="preset in presets" :key="preset.key" type="button"
          :aria-pressed="metric === preset.key && !ascending" @click="selectSort(preset.key)">
          {{ preset.label }}
        </button>
      </div>
      <label v-if="view === 'board'" class="family-control">
        <span>家族</span>
        <select v-model="family" aria-label="筛选家族">
          <option value="">全部家族</option>
          <option v-for="item in families" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button v-else-if="family" type="button" class="ghost" @click="family = ''">清除家族 {{ family }}</button>
      <label class="family-control">
        <span>排序</span>
        <select v-if="view === 'board'" :value="metric" aria-label="排序字段"
          @change="selectSort(($event.target as HTMLSelectElement).value as BoardMetric)">
          <option v-for="option in boardSortOptions" :key="option.key" :value="option.key">{{ option.label }}</option>
        </select>
        <select v-else v-model="catalogMetric" aria-label="排序字段">
          <option v-for="option in catalogSortOptions" :key="option.key" :value="option.key">{{ option.label }}</option>
        </select>
      </label>
      <button v-if="view === 'board'" type="button" class="ghost" aria-label="切换排序方向"
        @click="ascending = !ascending">{{ ascending ? '↑ 升序' : '↓ 降序' }}</button>
      <button v-else type="button" class="ghost" aria-label="切换排序方向"
        @click="catalogAscending = !catalogAscending">{{ catalogAscending ? '↑ 升序' : '↓ 降序' }}</button>
      <label class="ghost-control"><input v-model="showGhost" type="checkbox" /> 包含占位上游</label>
      <span class="result-count" role="status">{{ loading ? '查询中…' : fmt(total) + ' 个' + modeLabel }}</span>
    </div>

    <div v-if="error" class="alert alert-error" role="alert">{{ error }}</div>
    <div class="registry-table" tabindex="0" role="region" aria-label="模型查询结果">
      <table v-if="view === 'board'" class="board-table">
        <thead>
          <tr>
            <th scope="col" class="index-cell">#</th>
            <th scope="col" :aria-sort="sortState('model_id')">
              <button type="button" @click="selectSort('model_id', true)">模型 <span v-if="metric === 'model_id'">{{ ascending ? '↑' : '↓' }}</span></button>
            </th>
            <th scope="col">家族</th>
            <th v-for="column in columns" :key="column.key" scope="col" class="num"
              :aria-sort="sortState(column.key)">
              <button type="button" @click="selectSort(column.key, true)">
                {{ column.label }} <span v-if="metric === column.key">{{ ascending ? '↑' : '↓' }}</span>
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading || !board.length"><td colspan="10" class="table-empty">
            {{ loading ? '正在读取快照…' : '当前条件下没有匹配的模型。' }}
          </td></tr>
          <tr v-for="(row, index) in loading ? [] : board" :key="row.model_id">
            <td class="index-cell">{{ (page - 1) * pageSize + index + 1 }}</td>
            <td>
              <button type="button" class="registry-link" @click="openDetail(row.model_id)">{{ row.model_id }}</button>
              <span v-if="row.ghost" class="ghost-mark" title="快照内只有上游 ID">†</span>
              <a class="out-link" :href="hubModelUrl(row.model_id)" target="_blank" rel="noopener noreferrer"
                :aria-label="'在 Hugging Face 打开 ' + row.model_id">↗</a>
            </td>
            <td><button v-if="row.family" type="button" class="family-link" @click="family = row.family">{{ row.family }}</button><span v-else>—</span></td>
            <td v-for="column in columns" :key="column.key" class="num" :class="{ 'score-cell': activeColumn === column.key }">
              <span v-if="activeColumn === column.key" class="score-bar" aria-hidden="true"
                :style="{ width: row[column.key] / maxScore * 100 + '%' }"></span>
              <span>{{ fmt(row[column.key]) }}</span>
            </td>
          </tr>
        </tbody>
      </table>

      <table v-else class="catalog-table">
        <thead><tr>
          <th scope="col" class="index-cell">#</th><th scope="col">模型</th><th scope="col">家族</th>
          <th scope="col">任务</th><th scope="col" class="num">下载量</th><th scope="col" class="num">累计下载</th>
          <th scope="col" class="num">点赞</th><th scope="col">创建日期</th>
        </tr></thead>
        <tbody>
          <tr v-if="loading || !items.length"><td colspan="8" class="table-empty">
            {{ loading ? '正在读取快照…' : '当前条件下没有匹配的模型。' }}
          </td></tr>
          <tr v-for="(row, index) in loading ? [] : items" :key="row.model_id">
            <td class="index-cell">{{ (page - 1) * pageSize + index + 1 }}</td>
            <td><button type="button" class="registry-link" @click="openDetail(row.model_id)">{{ row.model_id }}</button>
              <span v-if="row.ghost" class="ghost-mark" title="快照内只有上游 ID">†</span></td>
            <td><button v-if="row.family" type="button" class="family-link" @click="family = row.family">{{ row.family }}</button><span v-else>—</span></td>
            <td>{{ row.pipeline ?? '—' }}</td>
            <td class="num">{{ fmt(row.downloads) }}</td>
            <td class="num">{{ fmt(row.downloads_all) }}</td>
            <td class="num">{{ fmt(row.likes) }}</td>
            <td>{{ row.created?.slice(0, 10) ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="registry-footer">
      <div>
        <span>{{ rangeText }}</span>
        <p v-if="view === 'board'">后代跨层去重。近 90 天按快照日期计算。微调、适配器、量化和合并按直接关系计数。</p>
      </div>
      <div class="registry-pagination">
        <button type="button" class="ghost" :disabled="page <= 1 || loading" @click="gotoPage(page - 1)">上一页</button>
        <span>{{ page }} / {{ fmt(totalPages) }}</span>
        <button type="button" class="ghost" :disabled="page >= totalPages || loading" @click="gotoPage(page + 1)">下一页</button>
      </div>
    </footer>

    </template>

    <!-- 详情 -->
    <div v-if="detail" class="drawer">
      <header class="drawer-head">
        <span class="badge badge-accent">模型</span>
        <strong>详情</strong>
        <button class="panel-close" aria-label="关闭详情" @click="closeDetail">✕</button>
      </header>

      <section class="drawer-section">
        <dl class="kv">
          <dt>Model ID</dt>
          <dd><a :href="hubModelUrl(detail.model_id)" target="_blank" rel="noopener noreferrer">
            <code class="break">{{ detail.model_id }}</code>
          </a></dd>
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
        <h3>声明的直接上游 · {{ detail.declared_parents.length }}</h3>
        <p v-if="!detail.declared_parents.length" class="faint small">当前快照没有收录上游声明。</p>
        <ul v-else class="rel-list">
          <li v-for="parent in detail.declared_parents" :key="parent.model_id + ':' + parent.relation_type">
            <button class="ghost" @click="openDetail(parent.model_id)">{{ parent.model_id }}</button>
            <span class="badge">{{ parent.relation_type }}</span>
            <small>{{ parent.source_field }}</small>
          </li>
        </ul>
      </section>

      <section class="drawer-section">
        <h3>许可证声明</h3>
        <p v-if="!detail.license_declaration" class="faint small">当前快照没有收录许可证声明。</p>
        <dl v-else class="kv">
          <dt>许可证</dt>
          <dd>{{ detail.license_declaration.license ?? '—' }}</dd>
          <dt v-if="detail.license_declaration.license_name">名称</dt>
          <dd v-if="detail.license_declaration.license_name">{{ detail.license_declaration.license_name }}</dd>
          <dt v-if="detail.license_declaration.license_link">声明链接</dt>
          <dd v-if="detail.license_declaration.license_link" class="break">{{ detail.license_declaration.license_link }}</dd>
          <dt>来源</dt>
          <dd>{{ detail.license_declaration.source_field }}</dd>
        </dl>
      </section>

      <section class="drawer-section">
        <h3>关联数据集 · {{ detail.datasets.length }}</h3>
        <p v-if="!detail.datasets.length" class="faint small" style="margin: 0">
          当前快照没有收录模型卡中的数据集声明。
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
        <button v-if="snapshotId === snapshots[0]?.id" @click="openInLineage(detail.model_id)">在供应链小图中打开</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.catalog-workspace {
  --registry-accent: var(--accent-ink);
  --registry-tint: color-mix(in srgb, var(--accent) 9%, var(--card));
}
.registry-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 0 1.15rem;
}
.registry-header h1 { font-size: clamp(1.8rem, 4vw, 2.6rem); letter-spacing: -.045em; line-height: 1.12; }
.registry-header p { margin: .55rem 0 0; color: var(--muted); }
.snapshot-control { display: grid; gap: .35rem; max-width: min(100%, 360px); }
.snapshot-control span { font-size: .75rem; font-weight: 650; color: var(--muted); }
.snapshot-control select { width: 100%; min-width: 0; font-family: var(--mono); font-size: .78rem; }
.registry-search { margin-bottom: 1rem; }
.registry-search input {
  min-height: 50px;
  border-radius: 8px;
  box-shadow: inset 0 1px 1px #00000008;
}
.registry-tabs {
  display: flex;
  gap: 1.2rem;
  border-bottom: 1px solid var(--line);
  margin-bottom: .85rem;
}
.registry-tabs button {
  color: var(--muted); background: transparent; border: 0; border-bottom: 2px solid transparent;
  border-radius: 0; margin-bottom: -1px; padding: .65rem .15rem; font-weight: 650;
}
.registry-tabs button[aria-pressed='true'] { color: var(--registry-accent); border-bottom-color: var(--accent); }
.registry-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: .65rem 1rem; margin-bottom: .8rem; }
.board-presets {
  display: flex; flex-wrap: wrap; background: var(--card); border: 1px solid var(--line);
  border-radius: 8px; padding: 3px; gap: 2px;
}
.board-presets button {
  padding: .35rem .65rem; background: transparent; color: var(--muted); border: 1px solid transparent;
  font-size: .82rem;
}
.board-presets button[aria-pressed='true'] {
  background: var(--registry-tint); border-color: color-mix(in srgb, var(--accent) 25%, var(--line));
  color: var(--registry-accent);
}
.family-control, .ghost-control { display: flex; align-items: center; gap: .4rem; font-size: .82rem; color: var(--muted); }
.family-control select { max-width: 165px; font-size: inherit; }
.ghost-control input { accent-color: var(--accent-ink); }
.result-count { margin-left: auto; font-size: .8rem; color: var(--muted); }
.registry-table { overflow: auto; border: 1px solid var(--line); border-radius: 9px; }
.registry-table table { margin: 0; font-size: .84rem; }
.board-table { min-width: 920px; }
.catalog-table { min-width: 810px; }
.registry-table th, .registry-table td { padding: .72rem .65rem; white-space: nowrap; }
.registry-table th { background: var(--card); color: var(--muted); font-size: .77rem; }
.registry-table tbody tr:nth-child(even) { background: color-mix(in srgb, var(--card) 55%, var(--bg)); }
.registry-table tbody tr:hover { background: var(--registry-tint); }
.registry-table th button, .registry-link, .family-link {
  border: 0; padding: 0; border-radius: 2px; background: transparent; color: inherit;
  font-size: inherit; text-align: inherit; line-height: inherit;
}
.registry-table th button:hover, .registry-link:hover, .family-link:hover { text-decoration: underline; }
.registry-table th[aria-sort='ascending'], .registry-table th[aria-sort='descending'] { color: var(--registry-accent); }
.registry-link { font-family: var(--mono); color: var(--registry-accent); font-weight: 550; }
.family-link { color: var(--muted); }
.out-link, .ghost-mark { margin-inline-start: .35rem; color: var(--muted); }
.index-cell { text-align: right; color: var(--muted); width: 38px; font-variant-numeric: tabular-nums; }
.score-cell { position: relative; isolation: isolate; }
.score-bar {
  position: absolute; z-index: -1; inset: auto 0 4px auto; height: 3px;
  background: var(--accent); opacity: .55; border-radius: 2px;
}
.registry-table .table-empty { padding: 2rem 1rem; text-align: center; color: var(--muted); }
.registry-footer { display: flex; align-items: start; justify-content: space-between; gap: 1rem; padding-top: .8rem; color: var(--muted); font-size: .8rem; }
.registry-footer p { margin: .35rem 0 0; }
.registry-pagination { display: flex; align-items: center; gap: .6rem; flex-shrink: 0; }
@media (max-width: 660px) {
  .registry-header, .registry-footer { flex-direction: column; align-items: stretch; }
  .registry-pagination { align-self: center; }
  .result-count { margin-left: 0; }
}
</style>
