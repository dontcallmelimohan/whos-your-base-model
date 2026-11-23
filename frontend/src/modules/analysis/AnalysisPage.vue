<script setup lang="ts">
/**
 * 工作包 D：生态分析。
 *
 * 这一页回答的是「整体长什么样」，不是「某个模型的邻居是谁」：
 *   规模 → 集中度 → 关系构成 → 谁在中心 → 谁在垄断
 * 每个数字旁边都标口径，避免被问住。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { errorText } from '@/shared/api'
import type { AnalysisResponse } from '@/shared/types'

import { fetchAnalysis } from './api'

const router = useRouter()
const data = ref<AnalysisResponse | null>(null)
const loading = ref(false)
const error = ref('')

const typeRows = computed(() => {
  if (!data.value) return []
  const total = data.value.metrics.edge_count || 1
  return data.value.type_distribution.map((item) => ({
    ...item,
    percent: Math.round((item.count / total) * 100),
  }))
})

const familyRows = computed(() => {
  if (!data.value) return []
  const max = Math.max(...data.value.family_distribution.map((f) => f.models), 1)
  return data.value.family_distribution.map((item) => ({
    ...item,
    percent: Math.round((item.models / max) * 100),
  }))
})

const maxDirect = computed(() =>
  Math.max(...(data.value?.top_upstream.map((u) => u.direct) ?? [1]), 1),
)

function num(value: number | undefined | null): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function openInLineage(modelId: string) {
  router.push({ path: '/lineage', query: { model: modelId } })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchAnalysis()
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <div class="page-head">
      <div>
        <h1>生态分析</h1>
        <p class="lede">
          把小图里的结构汇总成可比较的数字：规模、集中度、关系构成与上游排名。
          每个指标旁边标注口径，便于复算。
        </p>
      </div>
      <div class="row">
        <span v-if="data" class="badge">{{ data.snapshot_id }}</span>
        <span v-if="data" class="badge">规则 {{ data.rule_version }}</span>
        <button class="ghost" :disabled="loading" @click="load">
          {{ loading ? '刷新中…' : '刷新' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="!data && loading" class="panel muted small">正在计算…</div>

    <template v-if="data">
      <!-- 规模 -->
      <h2>规模</h2>
      <div class="grid grid-4" style="margin-bottom: 24px">
        <div class="stat">
          <div class="stat-label">模型</div>
          <div class="stat-value">{{ num(data.metrics.model_count) }}</div>
        </div>
        <div class="stat">
          <div class="stat-label">关系</div>
          <div class="stat-value">{{ num(data.metrics.edge_count) }}</div>
        </div>
        <div class="stat">
          <div class="stat-label">有下游的上游</div>
          <div class="stat-value">{{ num(data.metrics.parent_count) }}</div>
        </div>
        <div class="stat">
          <div class="stat-label">根模型（无上游）</div>
          <div class="stat-value">{{ num(data.metrics.root_count) }}</div>
        </div>
      </div>

      <!-- 集中度 -->
      <h2>集中度</h2>
      <div class="grid grid-4" style="margin-bottom: 10px">
        <div class="stat">
          <div class="stat-label">HHI（×10000）</div>
          <div class="stat-value">{{ data.concentration.hhi_scaled.toFixed(1) }}</div>
          <div class="faint small">越低越分散，10000 = 完全垄断</div>
        </div>
        <div class="stat">
          <div class="stat-label">Top-10 份额</div>
          <div class="stat-value">{{ pct(data.concentration.top10_share) }}</div>
          <div class="faint small">前 10 上游占全部关系的比例</div>
        </div>
        <div class="stat">
          <div class="stat-label">断链率</div>
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
      <p class="faint small" style="margin-bottom: 8px">
        口径：HHI = Σ (上游直接下游数 ÷ 关系总数)² × 10000；份额分母为关系总数
        {{ num(data.metrics.edge_count) }}。关系方向统一为「上游 → 下游」。
      </p>
      <p v-if="data.data_quality.ghost_ratio > 0.3" class="alert alert-info small" style="margin-bottom: 24px">
        断链率偏高是导入范围造成的：当前快照只收了下载量靠前的一部分模型，
        它们的上游大多不在集合内，因此以「属性未收录」的占位节点出现。
        这不是生态本身的数据缺失，换全量快照后会显著下降。
      </p>

      <div class="grid grid-2">
        <!-- 类型构成 -->
        <div class="panel">
          <h2>关系类型构成</h2>
          <div v-for="row in typeRows" :key="row.type" class="bar-row">
            <span class="label">{{ row.type }}</span>
            <span class="bar"><span :style="{ width: row.percent + '%' }"></span></span>
            <span class="num">{{ row.count.toLocaleString() }}</span>
          </div>
          <p class="faint small" style="margin: 14px 0 0">
            按带类型的关系条数计，与「唯一上下游对」是两个口径。
          </p>
        </div>

        <!-- 家族 -->
        <div class="panel">
          <h2>家族规模 Top {{ familyRows.length }}</h2>
          <div v-for="row in familyRows" :key="row.family" class="bar-row">
            <span class="label">{{ row.family }}</span>
            <span class="bar"><span :style="{ width: row.percent + '%' }"></span></span>
            <span class="num">{{ row.models.toLocaleString() }}</span>
          </div>
          <p v-if="!familyRows.length" class="muted small">当前快照没有家族字段。</p>
        </div>
      </div>

      <!-- 上游榜 -->
      <div class="panel">
        <h2>上游 Top 10 · 按直接下游数</h2>
        <table>
          <thead>
            <tr>
              <th style="width: 36px">#</th>
              <th>模型</th>
              <th>家族</th>
              <th class="num" style="width: 110px">直接下游</th>
              <th class="num" style="width: 110px">可达后代</th>
              <th style="width: 140px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in data.top_upstream" :key="row.model_id">
              <td class="faint">{{ index + 1 }}</td>
              <td><code>{{ row.model_id }}</code></td>
              <td class="muted">{{ row.family ?? '—' }}</td>
              <td class="num">{{ row.direct.toLocaleString() }}</td>
              <td class="num">{{ row.total.toLocaleString() }}</td>
              <td>
                <span class="bar" style="height: 4px">
                  <span :style="{ width: (row.direct / maxDirect) * 100 + '%' }"></span>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <p class="faint small" style="margin: 14px 0 0">
          「直接下游」只数一跳邻居；「可达后代」沿关系递归，含间接继承。两者不可混用。
        </p>
      </div>

      <!-- 案例 -->
      <div v-if="data.cases.length" class="panel">
        <h2>案例</h2>
        <div class="case-list">
          <button
            v-for="item in data.cases"
            :key="item.model_id"
            class="case-card"
            @click="openInLineage(item.model_id)"
          >
            <strong>{{ item.title }}</strong>
            <code class="small">{{ item.model_id }}</code>
            <span class="muted small">{{ item.note }}</span>
          </button>
        </div>
      </div>

      <p class="footnote">
        方法参考 HuggingGraph（关系类型与深度）、model-family-tree（direct / total
        后代口径）、Open Model Evolution（集中度视角）。指标定义见
        <code>docs/CONTRACTS.md</code>。
      </p>
    </template>
  </section>
</template>
