<script setup lang="ts">
/**
 * 右侧详情面板，版式参考 lineage-explorer 的 Model 面板：
 * 标题栏 + 分组（本体 / 关系）+ 键值行 + 徽标。
 */
import { computed } from 'vue'

import type { GraphEdge, GraphNode } from './api'

const props = defineProps<{
  node: GraphNode | null
  edge: GraphEdge | null
  nodes: GraphNode[]
  edges: GraphEdge[]
  root: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'focus', id: string): void
}>()

const title = computed(() => (props.edge ? '关系' : '模型'))

const related = computed(() => {
  if (!props.node) return []
  return props.edges
    .filter((item) => item.source === props.node!.id || item.target === props.node!.id)
    .map((item) => {
      const outgoing = item.source === props.node!.id
      return {
        edge: item,
        outgoing,
        other: outgoing ? item.target : item.source,
        otherNode: props.nodes.find((n) => n.id === (outgoing ? item.target : item.source)),
      }
    })
})

const edgeEnds = computed(() => {
  if (!props.edge) return null
  return {
    source: props.nodes.find((n) => n.id === props.edge!.source),
    target: props.nodes.find((n) => n.id === props.edge!.target),
  }
})

function copy(text: string) {
  navigator.clipboard?.writeText(text)
}

function num(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}
</script>

<template>
  <aside class="panel-side">
    <header class="panel-head">
      <span class="panel-icon">{{ edge ? '→' : '⚙' }}</span>
      <strong>{{ title }}</strong>
      <button class="panel-close" title="关闭" @click="emit('close')">✕</button>
    </header>

    <!-- 节点 -->
    <template v-if="node">
      <section class="panel-section">
        <h3>身份</h3>
        <dl class="kv">
          <dt>Model ID</dt>
          <dd>
            <code class="break">{{ node.id }}</code>
            <button class="copy" title="复制" @click="copy(node.id)">⧉</button>
          </dd>
          <dt>类型</dt>
          <dd>
            <span v-if="node.ghost" class="badge badge-warn">属性未收录</span>
            <span v-else class="badge">已收录</span>
            <span v-if="node.id === root" class="badge badge-accent" style="margin-left: 6px">当前根</span>
          </dd>
          <dt>作者</dt>
          <dd>{{ node.author ?? '—' }}</dd>
          <dt>家族</dt>
          <dd>{{ node.family ?? '—' }}</dd>
          <dt>任务</dt>
          <dd>{{ node.pipeline ?? '—' }}</dd>
          <dt>下载量</dt>
          <dd class="num-inline">{{ num(node.downloads) }}</dd>
        </dl>
      </section>

      <section class="panel-section">
        <h3>关系 · {{ related.length }}</h3>
        <div v-if="!related.length" class="muted small">当前视图里没有与它相连的关系。</div>
        <ul v-else class="rel-list">
          <li v-for="item in related" :key="item.edge.id" @click="emit('focus', item.other)">
            <span class="rel-type">{{ item.outgoing ? '下游' : '上游' }}</span>
            <span class="rel-arrow">{{ item.outgoing ? '→' : '←' }}</span>
            <code class="rel-target">{{ item.other }}</code>
            <span class="badge rel-badge">{{ item.edge.type }}</span>
          </li>
        </ul>
      </section>
    </template>

    <!-- 边 -->
    <template v-else-if="edge">
      <section class="panel-section">
        <h3>依赖</h3>
        <dl class="kv">
          <dt>上游</dt>
          <dd><code class="break">{{ edge.source }}</code></dd>
          <dt>下游</dt>
          <dd><code class="break">{{ edge.target }}</code></dd>
          <dt>类型</dt>
          <dd><span class="badge badge-accent">{{ edge.type }}</span></dd>
          <dt>来源字段</dt>
          <dd><code>{{ edge.source_field ?? '—' }}</code></dd>
          <dt>声明</dt>
          <dd>
            {{ edgeEnds?.source?.ghost ? '上游属性未收录' : '来自模型卡 base_model 标签' }}
          </dd>
        </dl>
      </section>
    </template>

    <div v-else class="panel-empty muted small">在左侧点一个节点或一条边</div>
  </aside>
</template>
