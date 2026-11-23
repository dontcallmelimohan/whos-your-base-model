<script setup lang="ts">
/**
 * 局部图渲染。
 *
 * 视觉参考 lineage-explorer 的图画布：点状网格底、胶囊节点、
 * 左侧图标方块 + 小字类型标签 + 等宽字体模型名。
 */
import { computed, ref } from 'vue'

import { NODE_H, NODE_W, type Layout } from './layout'

const props = defineProps<{
  layout: Layout
  root: string
  selectedId: string | null
  busy?: boolean
}>()

const emit = defineEmits<{
  (e: 'select-node', id: string): void
  (e: 'select-edge', id: string): void
  (e: 'focus-node', id: string): void
}>()

const scale = ref(1)
const offset = ref({ x: 0, y: 0 })
const dragging = ref<{ x: number; y: number } | null>(null)
const hovered = ref<string | null>(null)

const viewBox = computed(() => {
  const b = props.layout.bounds
  return `${b.x} ${b.y} ${Math.max(b.width, 320)} ${Math.max(b.height, 240)}`
})

const transform = computed(
  () => `translate(${offset.value.x} ${offset.value.y}) scale(${scale.value})`,
)

function zoom(factor: number) {
  const next = Math.min(2.2, Math.max(0.45, scale.value * factor))
  scale.value = Number(next.toFixed(2))
}

function reset() {
  scale.value = 1
  offset.value = { x: 0, y: 0 }
}

function onWheel(event: WheelEvent) {
  event.preventDefault()
  zoom(event.deltaY > 0 ? 0.9 : 1.1)
}

function onPointerDown(event: PointerEvent) {
  dragging.value = { x: event.clientX, y: event.clientY }
  ;(event.currentTarget as SVGElement).setPointerCapture?.(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  if (!dragging.value) return
  const dx = event.clientX - dragging.value.x
  const dy = event.clientY - dragging.value.y
  dragging.value = { x: event.clientX, y: event.clientY }
  // viewBox 单位与像素的比例，避免拖拽速度随缩放漂移
  const rect = (event.currentTarget as SVGElement).getBoundingClientRect()
  const ratio = Math.max(props.layout.bounds.width / Math.max(rect.width, 1), 0.2)
  offset.value = { x: offset.value.x + dx * ratio, y: offset.value.y + dy * ratio }
}

function onPointerUp() {
  dragging.value = null
}

function shortId(id: string, max = 21): string {
  return id.length <= max ? id : `${id.slice(0, max - 1)}…`
}
</script>

<template>
  <div class="canvas" @wheel="onWheel">
    <svg
      :viewBox="viewBox"
      class="canvas-svg"
      :class="{ dragging: !!dragging, busy: props.busy }"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointerleave="onPointerUp"
    >
      <g class="stage" :class="{ 'no-anim': !!dragging }" :style="{ transform }">
        <!-- 边 -->
        <g>
          <path
            v-for="edge in layout.edges"
            :key="edge.id"
            :d="edge.path"
            pathLength="1"
            class="edge"
            :class="{ active: selectedId === edge.id, hovered: hovered === edge.id }"
            @click.stop="emit('select-edge', edge.id)"
            @mouseenter="hovered = edge.id"
            @mouseleave="hovered = null"
          />
          <circle
            v-for="edge in layout.edges"
            :key="`dot-${edge.id}`"
            :cx="layout.nodes.find((n) => n.id === edge.target)?.x ?? 0"
            :cy="layout.nodes.find((n) => n.id === edge.target)?.y ?? 0"
            r="2.6"
            class="edge-dot"
          />
        </g>

        <!-- 节点 -->
        <g
          v-for="node in layout.nodes"
          :key="node.id"
          class="node"
          :style="{ transform: `translate(${node.x}px, ${node.y}px)` }"
          @click.stop="emit('select-node', node.id)"
          @dblclick.stop="emit('focus-node', node.id)"
        >
          <rect
            :x="-NODE_W / 2"
            :y="-NODE_H / 2"
            :width="NODE_W"
            :height="NODE_H"
            rx="14"
            class="node-box"
            :class="{
              root: node.id === root,
              ghost: node.ghost,
              selected: node.id === selectedId,
            }"
          />
          <g :transform="`translate(${-NODE_W / 2 + 10} -13)`">
            <rect width="26" height="26" rx="7" class="node-icon" />
            <circle cx="8.5" cy="8.5" r="2.1" class="glyph-dot" />
            <circle cx="17.5" cy="17.5" r="2.1" class="glyph-dot" />
            <path d="M10.2 10.2 L15.8 15.8" class="glyph-line" />
          </g>
          <text :x="-NODE_W / 2 + 46" y="-3" class="node-kind">
            {{ node.ghost ? 'UNKNOWN' : 'MODEL' }}
          </text>
          <text :x="-NODE_W / 2 + 46" y="13" class="node-label">{{ shortId(node.id) }}</text>
        </g>
      </g>
    </svg>

    <div class="canvas-tools">
      <button class="tool" title="放大" @click="zoom(1.15)">+</button>
      <button class="tool" title="缩小" @click="zoom(0.87)">−</button>
      <button class="tool" title="复位" @click="reset">⤢</button>
    </div>

    <div class="canvas-hint">点击节点查看属性 · 双击以该节点为根重新展开 · 滚轮缩放</div>
  </div>
</template>
