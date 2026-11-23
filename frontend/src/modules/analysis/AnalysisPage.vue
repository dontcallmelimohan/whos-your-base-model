<script setup lang="ts">
/**
 * 任务 1：生态分析（核验汇总、补全前后差分、CSV）。
 *
 * 版式参考 Open Model Evolution（Dash + Mantine，未声明许可，仅借结构）：
 *   顶部数据说明 → 居中标题与导语 → 左侧口径切换（每项带说明）→ 右侧榜单 → 底部口径定义
 *
 * 这一页回答「整体长什么样」：规模、集中度、关系构成、谁在中心。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { errorText } from '@/shared/api'
import type { AnalysisResponse, DiffResponse, Snapshot } from '@/shared/types'

import { exportCsvUrl, fetchAnalysis, fetchDiff, fetchSnapshots } from './api'

type Tab = 'upstream' | 'family'
type Metric = 'direct' | 'total'

const router = useRouter()
const data = ref<AnalysisResponse | null>(null)
const diff = ref<DiffResponse | null>(null)
const view = ref<'declared' | 'completed'>('declared')
const snapshotId = ref('')
const snapshots = ref<Snapshot[]>([])
const loading = ref(false)
const error = ref('')

const tab = ref<Tab>('upstream')
const metric = ref<Metric>('direct')
const topN = ref(10)

const typeRows = computed(() => {
  if (!data.value) return []
  const total = data.value.metrics.edge_count || 1
  return data.value.type_distribution.map((item) => ({
    ...item,
    percent: Math.round((item.count / total) * 100),
  }))
})

const upstreamRows = computed(() => {
  if (!data.value) return []
  const key = metric.value
  return [...data.value.top_upstream]
    .sort((a, b) => (b[key] as number) - (a[key] as number) || a.model_id.localeCompare(b.model_id))
    .slice(0, topN.value)
})

const familyRows = computed(() => {
  if (!data.value) return []
  const total = data.value.metrics.model_count || 1
  return [...data.value.family_distribution]
    .slice(0, topN.value)
    .map((item) => ({ ...item, share: item.models / total }))
})

const maxUpstream = computed(() =>
  Math.max(...upstreamRows.value.map((row) => row[metric.value] as number), 1),
)
const maxFamily = computed(() => Math.max(...familyRows.value.map((row) => row.models), 1))

const share = (value: number, total: number) => (total ? value / total : 0)

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function num(value: number | undefined | null): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

function openInLineage(modelId: string) {
  router.push({ path: '/lineage', query: { model: modelId } })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchAnalysis(snapshotId.value || undefined)
    diff.value = await fetchDiff(snapshotId.value || undefined)
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    snapshots.value = (await fetchSnapshots()).items
    snapshotId.value = snapshots.value[0]?.id ?? ''
  } catch {
    /* 忽略，用默认快照 */
  }
  await load()
})
</script>

<template>
  <section>
    <!-- 数据说明 -->
    <div v-if="data" class="note">
      <span class="note-icon">i</span>
      <span>
        指标基于公开的 Hugging Face 模型元数据（hub-stats，Apache-2.0）计算，关系来自模型卡声明的
        <code>base_model</code> 标签。当前快照 <code>{{ data.snapshot_id }}</code>，处理规则
        <code>{{ data.rule_version }}</code>。
      </span>
    </div>

    <!-- 标题与导语 -->
    <header class="analysis-head">
      <h1>生态分析</h1>
      <p class="lede">
        把小图里的结构汇总成可比较的数字：规模、集中度、关系构成与上游排名。
        回答四个问题——生态多大、是否集中、大家在做什么、谁在中心。
      </p>
    </header>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="!data && loading" class="panel muted small">正在计算…</div>

    <template v-if="data">
      <div class="row" style="justify-content: flex-end; gap: 10px; margin-bottom: 14px">
        <span class="muted small">数据版本</span>
        <select v-if="snapshots.length" v-model="snapshotId" @change="load">
          <option v-for="item in snapshots" :key="item.id" :value="item.id">{{ item.id }}</option>
        </select>
        <span v-else class="badge">{{ data.snapshot_id }}</span>
      </div>

      <div class="analysis-body">
        <!-- 左：筛选与口径 -->
        <aside class="filter-panel">
          <div class="filter-block">
            <div class="filter-label">
              排名口径
              <span class="tip" title="直接下游只数一跳；可达后代沿关系递归，含间接继承">ⓘ</span>
            </div>
            <div class="segmented">
              <button :class="{ active: metric === 'direct' }" @click="metric = 'direct'">
                直接下游
              </button>
              <button :class="{ active: metric === 'total' }" @click="metric = 'total'">
                可达后代
              </button>
            </div>
            <p class="filter-desc">
              {{
                metric === 'direct'
                  ? '统计与某个上游直接相连的模型数，反映「被直接微调或量化」的次数。'
                  : '统计沿关系递归能到达的全部模型，反映「间接继承」的总体规模。'
              }}
            </p>
          </div>

          <div class="filter-block">
            <div class="filter-label">显示条数</div>
            <div class="segmented">
              <button :class="{ active: topN === 10 }" @click="topN = 10">Top 10</button>
              <button :class="{ active: topN === 20 }" @click="topN = 20">Top 20</button>
            </div>
          </div>

          <div class="filter-block">
            <div class="filter-label">口径常量</div>
            <dl class="mini-kv">
              <dt>关系总数</dt>
              <dd>{{ num(data.metrics.edge_count) }}</dd>
              <dt>上游总数</dt>
              <dd>{{ num(data.metrics.parent_count) }}</dd>
              <dt>唯一上下游对</dt>
              <dd>{{ num(data.metrics.unique_pair_count) }}</dd>
              <dt>模型总数</dt>
              <dd>{{ num(data.metrics.model_count) }}</dd>
            </dl>
          </div>
        </aside>

        <!-- 右：指标与榜单 -->
        <div>
          <h2>集中度</h2>
          <div class="grid grid-4" style="margin-bottom: 8px">
            <div class="stat">
              <div class="stat-label">
                HHI（×10000）
                <span class="tip" title="Σ(上游直接下游数 ÷ 关系总数)²，再乘 10000">ⓘ</span>
              </div>
              <div class="stat-value">{{ data.concentration.hhi_scaled.toFixed(1) }}</div>
              <div class="faint small">越低越分散，10000 = 完全垄断</div>
            </div>
            <div class="stat">
              <div class="stat-label">
                Top-10 份额
                <span class="tip" title="前 10 上游的直接下游数之和 ÷ 关系总数">ⓘ</span>
              </div>
              <div class="stat-value">{{ pct(data.concentration.top10_share) }}</div>
              <div class="faint small">头部上游的集中程度</div>
            </div>
            <div class="stat">
              <div class="stat-label">
                断链率
                <span class="tip" title="有下游、但自身属性未收录的上游占全部上游的比例">ⓘ</span>
              </div>
              <div class="stat-value">{{ pct(data.data_quality.ghost_ratio) }}</div>
              <div class="faint small">
                {{ num(data.data_quality.ghost_parent_count) }} 个上游属性未收录
              </div>
            </div>
            <div class="stat">
              <div class="stat-label">家族</div>
              <div class="stat-value">{{ num(data.metrics.family_count) }}</div>
              <div class="faint small">按派生数据的 family 字段</div>
            </div>
          </div>

          <p
            v-if="data.data_quality.ghost_ratio > 0.3"
            class="alert alert-info small"
            style="margin: 8px 0 24px"
          >
            断链率偏高是导入范围造成的：当前快照只收了下载量靠前的一部分模型，它们的上游大多不在集合内，
            因此以「属性未收录」的占位节点出现。这是范围问题，不是生态缺失。
          </p>

          <!-- 榜单 -->
          <div class="panel">
            <div class="tabs">
              <button :class="{ active: tab === 'upstream' }" @click="tab = 'upstream'">上游</button>
              <button :class="{ active: tab === 'family' }" @click="tab = 'family'">家族</button>
            </div>

            <table v-if="tab === 'upstream'" class="rank-table">
              <thead>
                <tr>
                  <th style="width: 40px">#</th>
                  <th>模型</th>
                  <th style="width: 110px">家族</th>
                  <th class="num" style="width: 96px">
                    {{ metric === 'direct' ? '直接下游' : '可达后代' }}
                  </th>
                  <th class="num" style="width: 72px">占比</th>
                  <th style="width: 150px"></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, index) in upstreamRows"
                  :key="row.model_id"
                  class="row-click"
                  @click="openInLineage(row.model_id)"
                >
                  <td class="faint">{{ index + 1 }}</td>
                  <td><code :title="row.model_id">{{ row.model_id }}</code></td>
                  <td class="muted" :title="row.family ?? ''">{{ row.family ?? '—' }}</td>
                  <td class="num">{{ (row[metric] as number).toLocaleString() }}</td>
                  <td class="num muted">{{ pct(share(row[metric] as number, data.metrics.edge_count)) }}</td>
                  <td>
                    <span class="bar">
                      <span
                        :style="{ width: ((row[metric] as number) / maxUpstream) * 100 + '%' }"
                      ></span>
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>

            <table v-else class="rank-table">
              <thead>
                <tr>
                  <th style="width: 40px">#</th>
                  <th>家族</th>
                  <th class="num" style="width: 96px">模型数</th>
                  <th class="num" style="width: 72px">占比</th>
                  <th style="width: 150px"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in familyRows" :key="row.family">
                  <td class="faint">{{ index + 1 }}</td>
                  <td :title="row.family">{{ row.family }}</td>
                  <td class="num">{{ row.models.toLocaleString() }}</td>
                  <td class="num muted">{{ pct(row.share) }}</td>
                  <td>
                    <span class="bar">
                      <span :style="{ width: (row.models / maxFamily) * 100 + '%' }"></span>
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>

            <p class="faint small" style="margin: 14px 0 0">
              <template v-if="tab === 'upstream'">
                点任意一行可在小图中以它为根展开。「直接下游」只数一跳邻居；「可达后代」沿关系递归，
                含间接继承，两者不可混用。
              </template>
              <template v-else>
                家族按派生数据的 family 字段分组；占比分母为当前快照的模型总数
                {{ num(data.metrics.model_count) }}。
              </template>
            </p>
          </div>

          <!-- 关系构成 -->
          <div class="panel">
            <h2>关系类型构成</h2>
            <div v-for="row in typeRows" :key="row.type" class="bar-row">
              <span class="label">{{ row.type }}</span>
              <span class="bar"><span :style="{ width: row.percent + '%' }"></span></span>
              <span class="num">{{ row.count.toLocaleString() }}</span>
            </div>
            <p class="faint small" style="margin: 14px 0 0">
              按带类型的关系条数计，与上方的「唯一上下游对」是两个口径。
            </p>
          </div>

          <!-- 补全前后对比 -->
          <div v-if="diff" class="panel">
            <div class="row" style="justify-content: space-between; margin-bottom: 14px">
              <h2 style="margin: 0">补全前后对比</h2>
              <div class="row">
                <a class="chip" :href="exportCsvUrl('declared')" download>导出 CSV · 声明图</a>
                <a class="chip" :href="exportCsvUrl('completed')" download>导出 CSV · 补全图</a>
              </div>
            </div>

            <div class="diff-grid">
              <div v-for="(metric, name) in diff.metrics" :key="name" class="diff-cell">
                <div class="label">{{ name }}</div>
                <div class="values">
                  {{ metric.declared }} → {{ metric.completed }}
                  <span :class="metric.delta ? 'delta-up' : 'delta-flat'">
                    ({{ metric.delta > 0 ? '+' : '' }}{{ metric.delta }})
                  </span>
                </div>
              </div>
            </div>

            <p v-if="!diff.added_edges.length" class="muted small" style="margin: 0">
              还没有核验通过的关系。去「核验」页确认一条候选，这里会出现新增的边。
            </p>
            <table v-else class="rank-table">
              <thead>
                <tr>
                  <th>新增边</th>
                  <th style="width: 96px">类型</th>
                  <th style="width: 80px">状态</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="edge in diff.added_edges"
                  :key="edge.relation_id"
                  class="row-click"
                  @click="openInLineage(edge.child_id)"
                >
                  <td>
                    <code class="model-id">{{ edge.parent_id }} → {{ edge.child_id }}</code>
                  </td>
                  <td class="muted">{{ edge.relation_type }}</td>
                  <td><span class="badge badge-ok">{{ edge.status }}</span></td>
                </tr>
              </tbody>
            </table>

            <p class="faint small" style="margin: 14px 0 0">
              声明图 = 模型卡字段里写的关系；补全图 = 声明 + 核验通过。待核验
              {{ diff.pending_count }} 条。
            </p>
          </div>

          <!-- 指标定义 -->
          <div class="panel">
            <h2>指标定义</h2>
            <table class="def-table">
              <tbody>
                <tr>
                  <td><code>HHI</code></td>
                  <td>Σ (某上游直接下游数 ÷ 关系总数)² × 10000，产业组织学常用集中度</td>
                </tr>
                <tr>
                  <td><code>top10_share</code></td>
                  <td>前 10 上游的直接下游数之和 ÷ 关系总数</td>
                </tr>
                <tr>
                  <td><code>direct</code></td>
                  <td>直接下游数：只统计一跳邻居</td>
                </tr>
                <tr>
                  <td><code>total</code></td>
                  <td>可达后代数：沿关系递归统计，含间接继承</td>
                </tr>
                <tr>
                  <td><code>ghost_ratio</code></td>
                  <td>有下游但属性未收录的上游数 ÷ 全部上游数</td>
                </tr>
              </tbody>
            </table>
            <p class="faint small" style="margin: 14px 0 0">
              方法参考 HuggingGraph（关系类型与深度）、model-family-tree（direct / total 口径）、
              Open Model Evolution（集中度视角）。接口定义见 <code>docs/CONTRACTS.md</code>。
            </p>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
