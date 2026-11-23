<script setup lang="ts">
/**
 * 任务 2：谱系图。
 *
 * 交互参考 EQTY Lab 的 Lineage Explorer（Apache-2.0）：左侧画布 + 右侧详情面板，
 * 但数据源不是它的 .eqtylab manifest，而是本项目 SQLite 里的 base_model 边。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { errorText } from '@/shared/api'
import { fetchMeta } from '@/shared/meta'
import type { ModelSummary } from '@/shared/types'

import DetailPanel from './DetailPanel.vue'
import GraphCanvas from './GraphCanvas.vue'
import { fetchGraph, searchModels, type Direction, type GraphEdge, type GraphNode, type GraphResponse } from './api'
import { layoutGraph } from './layout'

const route = useRoute()
const root = ref('')
const graph = ref<GraphResponse | null>(null)
const loading = ref(false)
const error = ref('')

const direction = ref<Direction>('both')
const depth = ref(1)
const relationType = ref('')
const view = ref<'declared' | 'completed'>('declared')

const selectedNodeId = ref<string | null>(null)
const selectedEdgeId = ref<string | null>(null)

const query = ref('')
const suggestions = ref<ModelSummary[]>([])
const showSuggestions = ref(false)
const typing = ref(false)
const relationTypes = ref<string[]>([])
const showAll = ref(false)

const layout = computed(() =>
  graph.value ? layoutGraph(graph.value, showAll.value ? 24 : 8) : null,
)
const selectedNode = computed<GraphNode | null>(
  () => graph.value?.nodes.find((node) => node.id === selectedNodeId.value) ?? null,
)
const selectedEdge = computed<GraphEdge | null>(
  () => graph.value?.edges.find((edge) => edge.id === selectedEdgeId.value) ?? null,
)

async function load(modelId = root.value) {
  if (!modelId) return
  loading.value = true
  error.value = ''
  showSuggestions.value = false
  try {
    root.value = modelId
    query.value = modelId
    graph.value = await fetchGraph({
      model_id: modelId,
      direction: direction.value,
      depth: depth.value,
      relation_type: relationType.value || undefined,
      limit: 100,
      view: view.value,
    })
    selectedNodeId.value = modelId
    selectedEdgeId.value = null
  } catch (err) {
    error.value = errorText(err)
    graph.value = null
  } finally {
    loading.value = false
  }
}

let timer: number | undefined
watch(query, (value) => {
  window.clearTimeout(timer)
  if (!value.trim()) {
    suggestions.value = []
    return
  }
  timer = window.setTimeout(async () => {
    try {
      suggestions.value = (await searchModels(value.trim())).items
      showSuggestions.value = typing.value
    } catch {
      suggestions.value = []
    }
  }, 250)
})

function pick(model: ModelSummary) {
  typing.value = false
  showSuggestions.value = false
  query.value = model.model_id
  load(model.model_id)
}

function onSelectNode(id: string) {
  selectedNodeId.value = id
  selectedEdgeId.value = null
}

function onSelectEdge(id: string) {
  selectedEdgeId.value = id
  selectedNodeId.value = null
}

async function bootstrap() {
  try {
    const meta = await fetchMeta()
    relationTypes.value = meta.relation_types
  } catch {
    relationTypes.value = ['finetune', 'adapter', 'quantized', 'merge', 'unknown']
  }
  if (route.query.view === 'completed') view.value = 'completed'
  const requested = typeof route.query.model === 'string' ? route.query.model : ''
  if (requested) {
    await load(requested)
    typing.value = false
    showSuggestions.value = false
    return
  }
  try {
    const first = await searchModels('qwen2.5')
    if (first.items.length) {
      query.value = first.items[0].model_id
      await load(first.items[0].model_id)
      typing.value = false
      showSuggestions.value = false
    }
  } catch (err) {
    error.value = errorText(err)
  }
}

onMounted(bootstrap)

defineExpose({ load })
</script>

<template>
  <section>
    <div class="page-head" style="margin-bottom: 20px">
      <div>
        <h1>供应链小图</h1>
        <p class="lede">
          围绕一个模型展开它的上游与下游。默认一层、最多两层，节点上限 100，截断时会提示。
        </p>
      </div>
      <div class="search-wrap">
        <input
          v-model="query"
          type="search"
          placeholder="搜索模型，回车打开"
          style="width: 280px"
          @input="typing = true"
          @focus="showSuggestions = typing && suggestions.length > 0"
          @blur="((typing = false), (showSuggestions = false))"
          @keydown.enter="load(query.trim() || root)"
        />
        <ul v-if="showSuggestions && suggestions.length" class="suggest">
          <li v-for="item in suggestions" :key="item.model_id" @mousedown.prevent="pick(item)">
            <code>{{ item.model_id }}</code>
            <span class="muted small">{{ item.downloads?.toLocaleString() ?? '—' }} 下载</span>
          </li>
        </ul>
      </div>
    </div>

    <div class="toolbar">
      <div class="row">
        <select v-model="direction" @change="load()">
          <option value="both">双向</option>
          <option value="upstream">只看上游</option>
          <option value="downstream">只看下游</option>
        </select>
        <select v-model.number="depth" @change="load()">
          <option :value="1">深度 1</option>
          <option :value="2">深度 2</option>
        </select>
        <select v-model="view" @change="load()">
          <option value="declared">声明图</option>
          <option value="completed">补全图</option>
        </select>
        <select v-model="relationType" @change="load()">
          <option value="">全部关系</option>
          <option v-for="type in relationTypes" :key="type" :value="type">{{ type }}</option>
        </select>
        <button class="ghost" :disabled="loading" @click="load()">
          {{ loading ? '加载中…' : '重新展开' }}
        </button>
      </div>
      <div class="row">
        <span v-if="graph" class="badge">{{ graph.node_count }} 节点 / {{ graph.edge_count }} 边</span>
        <span v-if="graph?.truncated" class="badge badge-warn">已截断至 {{ graph.node_limit }} 个节点</span>
        <button
          v-if="layout?.hidden"
          class="badge badge-warn"
          style="cursor: pointer"
          @click="showAll = !showAll"
        >
          {{ showAll ? '收起' : `另有 ${layout.hidden} 个节点未绘制 · 展开` }}
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <div class="split">
      <div v-if="!layout" class="canvas canvas-empty muted small">
        {{ loading ? '正在展开…' : '还没有图。搜索一个模型或点上方按钮。' }}
      </div>
      <GraphCanvas
        v-else
        :layout="layout"
        :root="root"
        :busy="loading"
        :selected-id="selectedEdgeId ?? selectedNodeId"
        @select-node="onSelectNode"
        @select-edge="onSelectEdge"
        @reroot="load($event)"
      />

      <DetailPanel
        :node="selectedNode"
        :edge="selectedEdge"
        :nodes="graph?.nodes ?? []"
        :edges="graph?.edges ?? []"
        :root="root"
        :busy="loading"
        @close="((selectedNodeId = null), (selectedEdgeId = null))"
        @focus="load($event)"
      />
    </div>

    <p class="footnote" style="margin-top: 20px">
      关系来自模型卡声明的 <code>base_model</code> 标签，方向为「上游 → 下游」。
      <span v-if="graph?.snapshot_id">当前数据版本：<code>{{ graph.snapshot_id }}</code></span>
      <span v-if="view === 'completed'">· 补全图包含已核验通过的关系</span>
    </p>
  </section>
</template>
