<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { errorText } from '@/shared/api'
import type { DatasetUsage, Health, ImportRecord, Snapshot, SnapshotStats } from '@/shared/types'

import { fetchDatasets, fetchHealth, fetchImports, fetchSnapshots, fetchStats, postImport, syncHubStats } from './api'

const emit = defineEmits<{ 'data-updated': [] }>()
const health = ref<Health | null>(null)
const snapshots = ref<Snapshot[]>([])
const selected = ref<string>('')
const stats = ref<SnapshotStats | null>(null)
const datasets = ref<DatasetUsage[]>([])
const imports = ref<ImportRecord[]>([])

const loading = ref(false)
const detailLoading = ref(false)
const importing = ref(false)
const error = ref('')
const notice = ref('')
const snapshotPicker = ref<HTMLSelectElement | null>(null)

const source = ref('hubstats-online')
const limit = ref<number | string>(20000)
let detailRequest = 0

const current = computed(() => snapshots.value.find((item) => item.id === selected.value) ?? null)

const revision = computed(() => current.value?.source.match(/^hubstats:([0-9a-f]{40})$/)?.[1])
const otherSources: Record<string, string> = {
  hubstats: '本地 Parquet', modeltree: 'Model Family Tree', fixtures: '开发样例',
}
const sourceLabel = computed(() => {
  const value = current.value?.source ?? ''
  if (revision.value) return 'Hugging Face · hub-stats'
  if (value.startsWith('hubstats:')) return 'hub-stats · 本地文件'
  if (value.startsWith('modeltree')) return otherSources.modeltree
  if (value.startsWith('fixtures')) return otherSources.fixtures
  return value
})
const isActive = computed(() => selected.value !== '' && health.value?.snapshot_id === selected.value)
const kpis = computed(() => stats.value ? [
  { label: '模型节点', value: stats.value.model_count },
  { label: '声明关系', value: stats.value.relation_count },
  { label: '占位上游', value: stats.value.ghost_count },
  { label: '数据集关联', value: stats.value.dataset_link_count },
] : [])
const relationLabels: Record<string, string> = {
  finetune: '微调', adapter: '适配器', quantized: '量化', merge: '合并', unknown: '未知',
}
const typeRows = computed(() => {
  if (!stats.value) return []
  const total = stats.value.type_distribution.reduce((sum, item) => sum + item.count, 0) || 1
  return stats.value.type_distribution.map((item) => ({
    ...item,
    percent: (item.count / total) * 100,
  }))
})

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

const importDate = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
})

function formatDate(value: string): string {
  const iso = value.replace(' ', 'T')
  const date = new Date(/(?:Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : iso + 'Z')
  return Number.isNaN(date.valueOf()) ? value : importDate.format(date)
}

function datasetUrl(id: string): string | undefined {
  if (!/^[\w.-]+(?:\/[\w.-]+)?$/.test(id)) return undefined
  return 'https://huggingface.co/datasets/' + id.split('/').map(encodeURIComponent).join('/')
}

function inspectHistory(snapshotId: string) {
  selected.value = snapshotId
  void onSelect()
  snapshotPicker.value?.focus({ preventScroll: true })
  snapshotPicker.value?.scrollIntoView({ block: 'center' })
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [nextHealth, list, history] = await Promise.all([fetchHealth(), fetchSnapshots(), fetchImports(10)])
    health.value = nextHealth
    snapshots.value = list.items
    if (!selected.value || !snapshots.value.some((item) => item.id === selected.value)) {
      selected.value = list.items[0]?.id ?? ''
    }
    imports.value = history.items
    await loadSnapshotDetail()
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function loadSnapshotDetail() {
  const snapshotId = selected.value
  const request = ++detailRequest
  stats.value = null
  datasets.value = []
  detailLoading.value = Boolean(snapshotId)
  if (!snapshotId) return
  try {
    const [nextStats, nextDatasets] = await Promise.all([
      fetchStats(snapshotId), fetchDatasets(snapshotId, 10),
    ])
    if (request === detailRequest) {
      stats.value = nextStats
      datasets.value = nextDatasets.items
    }
  } catch (err) {
    if (request === detailRequest) throw err
  } finally {
    if (request === detailRequest) detailLoading.value = false
  }
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
    const requested = limit.value === '' ? 20000 : Number(limit.value)
    const online = source.value === 'hubstats-online'
    const result = online
      ? await syncHubStats(requested)
      : await postImport(source.value, source.value === 'fixtures' ? null : requested)
    notice.value = 'updated' in result && result.updated === false
      ? '本地已有最新版本，已切换到该快照。'
      : `导入完成，收录 ${formatNumber(result.model_count)} 个模型节点和 ${formatNumber(result.relation_count)} 条声明关系。`
    selected.value = result.snapshot_id
    emit('data-updated')
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
  <section class="data-workspace">
    <header class="workspace-heading">
      <div>
        <h1>数据管理</h1>
        <p>同步 Hugging Face 模型数据，按快照检查来源和覆盖范围。</p>
      </div>
      <button class="ghost refresh-button" :disabled="loading || importing" @click="loadAll">
        {{ loading ? '刷新中…' : '刷新记录' }}
      </button>
    </header>

    <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>
    <p v-if="notice" class="alert alert-info" role="status">{{ notice }}</p>

    <div class="overview-grid">
      <section class="surface snapshot" aria-labelledby="snapshot-heading">
        <header class="section-heading">
          <h2 id="snapshot-heading">快照概览</h2>
          <span v-if="current" class="snapshot-status" :class="{ active: isActive }">
            {{ isActive ? '当前默认版本' : '历史版本' }}
          </span>
        </header>

        <template v-if="current">
          <div class="snapshot-summary">
            <div>
              <time :datetime="current.snapshot_date">{{ current.snapshot_date }}</time>
              <p class="snapshot-source">{{ sourceLabel }}</p>
            </div>
            <label class="field snapshot-picker">
              <span>查看版本</span>
              <select ref="snapshotPicker" v-model="selected" aria-label="数据版本" @change="onSelect">
                <option v-for="item in snapshots" :key="item.id" :value="item.id">{{ item.id }}</option>
              </select>
            </label>
          </div>

          <dl v-if="kpis.length" class="snapshot-kpis" aria-label="快照覆盖情况">
            <div v-for="kpi in kpis" :key="kpi.label"><dt>{{ kpi.label }}</dt><dd>{{ formatNumber(kpi.value) }}</dd></div>
          </dl>
          <p v-else-if="detailLoading" class="kpi-placeholder" role="status">正在读取快照统计…</p>
          <details class="provenance">
            <summary>来源与校验</summary>
            <p v-if="current.scope_note" class="note">{{ current.scope_note }}</p>
            <dl class="snapshot-meta">
              <div><dt>导入规则</dt><dd><code>{{ current.rule_version }}</code></dd></div>
              <div v-if="revision">
                <dt>上游提交</dt><dd>
                  <a :href="'https://huggingface.co/datasets/cfahlgren1/hub-stats/blob/' + revision + '/models.parquet'"
                    target="_blank" rel="noopener noreferrer" :title="revision">{{ revision.slice(0, 12) }} ↗</a>
                </dd>
              </div>
              <div v-if="current.input_hash"><dt>文件 SHA-256</dt><dd><code>{{ current.input_hash }}</code></dd></div>
            </dl>
          </details>
        </template>
        <p v-else class="note">{{ loading ? '正在读取版本…' : '还没有快照，可以先同步或导入样例。' }}</p>
      </section>

      <section class="surface sync" aria-labelledby="sync-heading">
        <header class="section-heading"><h2 id="sync-heading">同步与导入</h2></header>
        <form class="sync-form" @submit.prevent="runImport">
          <label class="field">
            <span>数据来源</span>
            <select v-model="source" :disabled="importing">
              <option value="hubstats-online">Hugging Face · hub-stats</option>
              <option value="hubstats">本地 · models.parquet</option>
              <option value="fixtures">本地 · 开发样例</option>
              <option value="modeltree">本地 · Model Family Tree</option>
            </select>
          </label>
          <label v-if="source !== 'fixtures'" class="field">
            <span>{{ source === 'modeltree' ? '上游模型上限' : '模型上限' }}</span>
            <input v-model.number="limit" :disabled="importing" type="number" :min="source === 'modeltree' ? 1 : 0"
              step="1" placeholder="20,000" />
          </label>
          <p v-if="source.startsWith('hubstats')" class="note sync-note">
            按下载量选取模型，并收录直接上游。输入 0 导入全量。
            <template v-if="source === 'hubstats-online'">首次下载或版本更新时约 1.8 GB。</template>
          </p>
          <button class="sync-button" type="submit" :disabled="importing || loading">
            {{ importing ? '处理中…' : source === 'hubstats-online' ? '同步最新快照' : '开始导入' }}
          </button>
        </form>
        <p v-if="importing" class="note sync-progress" role="status">正在导入，完成后会刷新快照和记录。</p>
      </section>
    </div>

    <div class="coverage-grid" :aria-busy="detailLoading">
      <section class="surface" aria-labelledby="relation-heading">
        <header class="section-heading">
          <h2 id="relation-heading">声明关系构成</h2>
          <span v-if="stats" class="section-total">{{ formatNumber(stats.relation_count) }} 条</span>
        </header>
        <template v-if="typeRows.length">
          <div class="relation-stack" aria-hidden="true">
            <span v-for="row in typeRows" :key="row.type" :class="'relation-' + row.type" :style="{ width: row.percent + '%' }"></span>
          </div>
          <ul class="relation-legend">
            <li v-for="row in typeRows" :key="row.type">
              <span class="swatch" :class="'relation-' + row.type"></span>
              <span>{{ relationLabels[row.type] ?? row.type }}</span>
              <span class="figure">{{ formatNumber(row.count) }}</span>
              <span class="figure share">{{ row.percent.toFixed(1) }}%</span>
            </li>
          </ul>
        </template>
        <p v-else class="note">{{ detailLoading ? '正在读取…' : '暂无声明关系。' }}</p>
      </section>

      <section class="surface" aria-labelledby="dataset-heading">
        <header class="section-heading">
          <h2 id="dataset-heading">关联最多的数据集</h2>
          <span v-if="datasets.length" class="section-total">前 {{ datasets.length }} 项</span>
        </header>
        <p v-if="!datasets.length" class="note">{{ detailLoading ? '正在读取…' : '当前快照暂无模型卡数据集声明。' }}</p>
        <table v-else class="dataset-table">
          <thead><tr><th scope="col">数据集</th><th scope="col" class="num">关联模型数</th></tr></thead>
          <tbody>
            <tr v-for="item in datasets" :key="item.dataset_id">
              <td>
                <a v-if="datasetUrl(item.dataset_id)" :href="datasetUrl(item.dataset_id)" target="_blank" rel="noopener noreferrer">{{ item.dataset_id }} <span aria-hidden="true">↗</span></a>
                <span v-else>{{ item.dataset_id }}</span>
              </td>
              <td class="num">{{ formatNumber(item.model_count) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <section class="surface history" aria-labelledby="history-heading">
      <header class="section-heading"><h2 id="history-heading">导入记录</h2></header>
      <p v-if="!imports.length" class="note">{{ loading ? '正在读取记录…' : '还没有导入记录。' }}</p>
      <div v-else class="history-scroll" tabindex="0" role="region" aria-label="导入记录表">
        <table>
          <thead>
            <tr>
              <th scope="col">导入时间（北京时间）</th><th scope="col">数据版本</th><th scope="col">来源</th>
              <th scope="col" class="num">模型</th><th scope="col" class="num">关系</th>
              <th scope="col" class="num">数据集关联</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in imports" :key="item.id" :class="{ 'selected-version': selected === item.snapshot_id }">
              <td class="import-time">{{ formatDate(item.created_at) }}</td>
              <td><button type="button" class="version-link" @click="inspectHistory(item.snapshot_id)">{{ item.snapshot_id }}</button></td>
              <td>{{ item.source === 'hubstats' ? 'hub-stats' : (otherSources[item.source] ?? item.source) }}</td>
              <td class="num">{{ formatNumber(item.model_count) }}</td>
              <td class="num">{{ formatNumber(item.relation_count) }}</td>
              <td class="num">{{ formatNumber(item.dataset_link_count) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<style scoped>
.data-workspace { --surface-padding: clamp(14px, 2vw, 24px); display: grid; gap: 16px; }
.workspace-heading, .section-heading { display: flex; align-items: center; justify-content: space-between; gap: .65rem; }
.workspace-heading { align-items: end; padding: .35rem 0 .5rem; }
.workspace-heading h1 { margin: 0; font-size: clamp(1.8rem, 4vw, 2.6rem); letter-spacing: -.045em; }
.workspace-heading p { color: var(--muted); margin: .4rem 0 0; }
.refresh-button { flex: none; }
.overview-grid, .coverage-grid { display: grid; gap: 16px; align-items: start; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
.overview-grid { align-items: stretch; grid-template-columns: minmax(0, 1.75fr) minmax(0, 1fr); }
.surface {
  min-width: 0; border: 1px solid var(--line); border-radius: 12px; background: var(--bg);
  padding: var(--surface-padding);
}
.section-heading { margin: 0 0 .85rem; }
.section-heading h2 { color: var(--fg); font-size: 1rem; letter-spacing: -.015em; margin: 0; }
.snapshot { background: var(--card); }
.snapshot-status { border: 1px solid var(--line); border-radius: 999px; padding: .16rem .55rem; color: var(--muted); font-size: .75rem; white-space: nowrap; }
.snapshot-status.active { border-color: var(--ok-line); background: var(--ok-bg); color: var(--ok); }
.snapshot-summary { display: flex; align-items: flex-end; gap: 1rem; justify-content: space-between; flex-wrap: wrap; }
.snapshot-summary time { font: 650 clamp(1.55rem, 3.2vw, 2.35rem)/1.15 var(--mono); letter-spacing: -.055em; }
.snapshot-source { color: var(--muted); font-size: .82rem; margin: .38rem 0 0; }
.field { display: grid; gap: .28rem; min-width: 0; }
.field > span, .snapshot-meta dt { color: var(--muted); font-size: .78rem; }
.field input, .field select { width: 100%; min-width: 0; }
.snapshot-picker { flex: 1 1 170px; max-width: 305px; }
.snapshot-picker select { font-family: var(--mono); font-size: .79rem; }
.snapshot-kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 1rem 0 .8rem; border-block: 1px solid var(--line); }
.snapshot-kpis > div { padding: .68rem .62rem; }
.snapshot-kpis > div:first-child { padding-inline-start: 0; }
.snapshot-kpis > div + div { border-inline-start: 1px solid var(--line); }
.snapshot-kpis dt, .section-total { color: var(--muted); font-size: .79rem; }
.snapshot-kpis dd { font-size: clamp(1rem, 2vw, 1.5rem); font-weight: 680; margin: .12rem 0 0; font-variant-numeric: tabular-nums; }
.kpi-placeholder { color: var(--muted); min-height: 40px; margin: .8rem 0; }
.note { color: var(--muted); line-height: 1.55; font-size: .81rem; margin: .52rem 0 0; }
.provenance summary { color: var(--accent-ink); cursor: pointer; font-size: .82rem; }
.snapshot-meta { display: flex; flex-wrap: wrap; gap: .5rem 1rem; margin: .7rem 0 0; }
.snapshot-meta dd { margin: .1rem 0 0; font-size: .8rem; overflow-wrap: anywhere; }
.sync { border-top: 2px solid var(--accent); }
.sync-form { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 7rem); gap: .7rem; align-items: end; }
.sync-form .field:only-of-type { grid-column: 1 / -1; }
.sync-note { grid-column: 1 / -1; margin: 0; }
.sync-button {
  grid-column: 1 / -1; border-color: var(--accent-ink); background: var(--accent-ink); color: var(--bg);
  min-height: 38px; font-weight: 650;
}
.sync-progress { margin-top: .7rem; }
.relation-stack { display: flex; height: .65rem; overflow: hidden; background: var(--card); border-radius: 4px; margin: 1.05rem 0 .5rem; }
.relation-stack span + span { border-left: 1px solid var(--bg); }
.relation-legend { list-style: none; margin: 0; padding: 0; }
.relation-legend li { display: grid; grid-template-columns: 9px minmax(0, 1fr) auto 4rem; align-items: center; gap: .65rem; padding: .54rem 0; font-size: .83rem; }
.relation-legend li + li { border-top: 1px solid var(--line-soft); }
.swatch { width: 9px; height: 9px; border-radius: 2px; }
.figure { text-align: right; font-variant-numeric: tabular-nums; }
.share { color: var(--muted); }
.relation-finetune { background: #4c78a8; }
.relation-adapter { background: #f58518; }
.relation-quantized { background: #54a24b; }
.relation-merge { background: #e45756; }
.relation-unknown { background: #9a9aa2; }
.dataset-table { table-layout: fixed; }
.dataset-table th:last-child { width: 6.5rem; }
.dataset-table td:first-child { font-family: var(--mono); font-size: .79rem; overflow-wrap: anywhere; }
.dataset-table td, .history td { padding-block: .49rem; }
.dataset-table tbody tr:last-child td, .history tbody tr:last-child td { border-bottom: 0; }
.history-scroll { overflow-x: auto; }
.history table { min-width: 650px; }
.history .selected-version { background: color-mix(in srgb, var(--accent) 7%, var(--bg)); }
.import-time { color: var(--muted); white-space: nowrap; font-variant-numeric: tabular-nums; }
.version-link { border: 0; padding: 0; background: transparent; color: var(--accent-ink); font: .79rem var(--mono); text-align: left; overflow-wrap: anywhere; }
.version-link:hover { text-decoration: underline; }
@media (max-width: 870px) {
  .overview-grid, .coverage-grid { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 470px) {
  .workspace-heading { align-items: start; }
  .workspace-heading p { font-size: .84rem; }
  .snapshot-picker { max-width: 100%; }
  .snapshot-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .snapshot-kpis > div:nth-child(3) { border-inline-start: 0; padding-inline-start: 0; }
  .snapshot-kpis > div:nth-child(n+3) { border-top: 1px solid var(--line); }
}
</style>
