<script setup lang="ts">
/**
 * 局部图渲染。
 *
 * 视觉参考 lineage-explorer 的图画布：点状网格底、胶囊节点、
 * 左侧图标方块 + 小字类型标签 + 等宽字体模型名。
 *
 * 交互：点节点 = 把它变成新的根（重新请求 + 重新布局 + 相机跟过去）。
 * 相机与节点位置都用 CSS transform 补间，所以整个过程是滑过去的。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

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
  (e: 'reroot', id: string): void
}>()

// 固定视口：换根时 bounds 变了也不会让画面"跳一下"
const VIEW_W = 1000
const VIEW_H = 620
const viewBox = `0 0 ${VIEW_W} ${VIEW_H}`

const scale = ref(1)
const offset = ref({ x: 0, y: 0 })
const dragging = ref<{ x: number; y: number } | null>(null)
const hovered = ref<string | null>(null)
const canvasEl = ref<HTMLDivElement | null>(null)

const transform = computed(
  () => `translate(${offset.value.x}px, ${offset.value.y}px) scale(${scale.value})`,
)

/** 整张图刚好放进视口时的缩放比 */
function fitScale(): number {
  const b = props.layout.bounds
  const kx = (VIEW_W - 80) / Math.max(b.width, 1)
  const ky = (VIEW_H - 80) / Math.max(b.height, 1)
  return Math.min(1.1, Math.max(0.35, Math.min(kx, ky)))
}

/** 把某个节点挪到视口中心 */
function centerOn(id: string, k = scale.value) {
  const node = props.layout.nodes.find((item) => item.id === id)
  if (!node) return
  scale.value = Number(k.toFixed(3))
  offset.value = { x: VIEW_W / 2 - k * node.x, y: VIEW_H / 2 - k * node.y }
}

function fit() {
  const b = props.layout.bounds
  const k = fitScale()
  scale.value = Number(k.toFixed(3))
  offset.value = {
    x: VIEW_W / 2 - k * (b.x + b.width / 2),
    y: VIEW_H / 2 - k * (b.y + b.height / 2),
  }
}

onMounted(() => nextTick(() => centerOn(props.root, fitScale())))

// 换根：新根居中；用户放大过就保持当前比例，否则回到适配比例
watch(
  () => props.root,
  (id) => {
    const k = Math.min(scale.value, fitScale())
    nextTick(() => centerOn(id, k))
  },
)

watch(
  () => props.layout,
  () => nextTick(() => centerOn(props.root, Math.min(scale.value, fitScale()))),
)

function handleNodeClick(id: string) {
  emit('select-node', id)
  if (id === props.root) {
    centerOn(id)
    return
  }
  emit('reroot', id)
}

function zoom(factor: number) {
  const next = Math.min(2.2, Math.max(0.35, scale.value * factor))
  centerOn(props.root, next)
}

function onWheel(event: WheelEvent) {
  event.preventDefault()
  zoom(event.deltaY > 0 ? 0.9 : 1.1)
}

/**
 * 拖拽平移。
 *
 * 注意：这里**不能**用 setPointerCapture —— 一旦把指针捕获到 SVG 根节点，
 * 后续的 click 会派发到 SVG 而不是被点的节点，节点点击就永远不触发了。
 * 所以改为在 window 上监听 move/up，并用 4px 阈值区分「点击」和「拖拽」。
 */
let dragStart: { x: number; y: number } | null = null

function onPointerDown(event: PointerEvent) {
  if (event.button !== 0) return
  dragStart = { x: event.clientX, y: event.clientY }
}

function onWindowPointerMove(event: PointerEvent) {
  if (!dragStart) return
  const dx = event.clientX - dragStart.x
  const dy = event.clientY - dragStart.y
  if (!dragging.value) {
    if (Math.hypot(dx, dy) < 4) return // 还没到拖拽阈值，当作点击
    dragging.value = { x: dragStart.x, y: dragStart.y }
  }
  const stepX = event.clientX - dragging.value.x
  const stepY = event.clientY - dragging.value.y
  dragging.value = { x: event.clientX, y: event.clientY }
  const rect = canvasEl.value?.getBoundingClientRect()
  const ratio = VIEW_W / Math.max(rect?.width ?? VIEW_W, 1)
  offset.value = { x: offset.value.x + stepX * ratio, y: offset.value.y + stepY * ratio }
}

function onWindowPointerUp() {
  dragStart = null
  dragging.value = null
}

onMounted(() => {
  window.addEventListener('pointermove', onWindowPointerMove)
  window.addEventListener('pointerup', onWindowPointerUp)
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onWindowPointerMove)
  window.removeEventListener('pointerup', onWindowPointerUp)
})

function shortId(id: string, max = 21): string {
  return id.length <= max ? id : `${id.slice(0, max - 1)}…`
}
</script>

<template>
  <div ref="canvasEl" class="canvas" @wheel="onWheel">
    <svg
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
      class="canvas-svg"
      :class="{ dragging: !!dragging, busy: props.busy }"
      @pointerdown="onPointerDown"
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
        </g>

        <!-- 节点 -->
        <g
          v-for="node in layout.nodes"
          :key="node.id"
          class="node"
          :style="{ transform: `translate(${node.x}px, ${node.y}px)` }"
          @click.stop="handleNodeClick(node.id)"
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
      <button class="tool" title="适配窗口" @click="fit">⤢</button>
    </div>

    <div class="canvas-hint">点节点：以它为中心重新展开 · 滚轮缩放 · 拖拽平移</div>
  </div>
</template>
