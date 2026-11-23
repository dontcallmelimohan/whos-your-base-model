<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { errorText } from '@/shared/api'

import { fetchTrends, type SnapshotTrends } from './api'

const props = defineProps<{ snapshotId: string }>()
const data = ref<SnapshotTrends>()
const error = ref('')
const loading = ref(false)
const mode = ref<'cumulative' | 'monthly'>('cumulative')
const hidden = ref(new Set<string>())
const monthIndex = ref(0)

watch(() => props.snapshotId, async (snapshotId, _, onCleanup) => {
  let active = true
  onCleanup(() => { active = false })
  data.value = undefined
  error.value = ''
  if (!snapshotId) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    const result = await fetchTrends(snapshotId)
    if (active) {
      data.value = result
      monthIndex.value = result.months.length - 1
      hidden.value = new Set()
    }
  } catch (err) {
    if (active) error.value = errorText(err)
  } finally {
    if (active) loading.value = false
  }
}, { immediate: true })

const colors = ['#267cbf', '#d37528', '#3a957d', '#a978c1', '#c85070', '#8a801c']
const dashes = ['', '8 4', '', '2 4', '10 4 2 4', '5 4']
const series = computed(() => (data.value?.series ?? []).map((item, index) => {
  let running = item.before_window
  return {
    ...item,
    color: colors[index],
    dash: dashes[index],
    values: mode.value === 'monthly' ? item.monthly : item.monthly.map((count) => (running += count)),
  }
}))
const visible = computed(() => series.value.filter((item) => !hidden.value.has(item.family)))
const months = computed(() => data.value?.months ?? [])
const plot = { left: 62, right: 916, top: 24, bottom: 299 }
const step = computed(() => {
  const peak = Math.max(1, ...visible.value.flatMap((item) => item.values))
  const target = peak / 5
  const unit = 10 ** Math.floor(Math.log10(target))
  const size = [1, 2, 2.5, 5, 10].find((candidate) => candidate * unit >= target) ?? 10
  return Math.max(1, size * unit)
})
const ceiling = computed(() => Math.ceil(Math.max(1, ...visible.value.flatMap((item) => item.values)) / step.value) * step.value)
const ticks = computed(() => Array.from({ length: Math.round(ceiling.value / step.value) + 1 }, (_, i) => i * step.value))
const x = (index: number) => plot.left + index * (plot.right - plot.left) / Math.max(1, months.value.length - 1)
const y = (value: number) => plot.bottom - value * (plot.bottom - plot.top) / ceiling.value
const activeMonth = computed(() => months.value[monthIndex.value])
const format = (value: number) => value.toLocaleString('zh-CN')

function toggle(family: string) {
  if (hidden.value.has(family)) hidden.value.delete(family)
  else hidden.value.add(family)
}
</script>

<template>
  <section class="trend-panel" aria-labelledby="trend-heading">
    <header class="trend-header">
      <div>
        <h2 id="trend-heading">模型家族直接下游趋势</h2>
        <p>按下游模型的创建月份统计，展示当前快照中有日期的直接下游最多的 6 个家族。</p>
      </div>
      <div class="trend-modes" aria-label="趋势统计方式">
        <button type="button" :aria-pressed="mode === 'cumulative'" @click="mode = 'cumulative'">累计</button>
        <button type="button" :aria-pressed="mode === 'monthly'" @click="mode = 'monthly'">月度新增</button>
      </div>
    </header>

    <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>
    <p v-else-if="loading" role="status">正在读取快照趋势…</p>
    <p v-else-if="!series.length" class="muted">当前快照没有可绘制的家族及创建日期记录。</p>
    <template v-else>
      <div class="figure-layout">
        <div class="plot-frame">
          <svg viewBox="0 0 950 340" role="img" aria-labelledby="trend-figure-title">
            <title id="trend-figure-title">{{ mode === 'cumulative' ? '累计' : '月度新增' }}直接下游模型数，按家族比较</title>
            <text :x="plot.left" y="12" class="axis-label">下游模型数</text>
            <g v-for="tick in ticks" :key="tick">
              <line :x1="plot.left" :x2="plot.right" :y1="y(tick)" :y2="y(tick)" class="grid-line" />
              <text :x="plot.left - 9" :y="y(tick) + 4" text-anchor="end">{{ format(tick) }}</text>
            </g>
            <template v-for="(month, index) in months" :key="month">
              <text v-if="index % 4 === 0 || index === months.length - 1" :class="{ 'secondary-tick': index % 8 === 4 }" :x="x(index)" y="323" text-anchor="middle">{{ month }}</text>
            </template>
            <line :x1="x(monthIndex)" :x2="x(monthIndex)" :y1="plot.top" :y2="plot.bottom" class="month-line" />
            <g v-for="item in visible" :key="item.family">
              <polyline :points="item.values.map((value, index) => x(index) + ',' + y(value)).join(' ')"
                :stroke="item.color" :stroke-dasharray="item.dash || undefined" fill="none" stroke-width="2.5"
                vector-effect="non-scaling-stroke" stroke-linejoin="round" />
              <circle :cx="x(monthIndex)" :cy="y(item.values[monthIndex])" r="4" :fill="item.color" class="month-point" />
            </g>
            <rect v-for="(month, index) in months" :key="'hit-' + month"
              :x="x(index) - 14" :y="plot.top" width="29" :height="plot.bottom - plot.top"
              fill="transparent" @pointerenter="monthIndex = index" @click="monthIndex = index" />
          </svg>
        </div>

        <aside class="trend-legend" aria-label="家族图例">
          <label class="month-control">
            <span>查看月份</span>
            <select v-model.number="monthIndex">
              <option v-for="(month, index) in months" :key="month" :value="index">{{ month }}</option>
            </select>
          </label>
          <button v-for="item in series" :key="item.family" type="button"
            :aria-pressed="!hidden.has(item.family)" @click="toggle(item.family)">
            <span class="legend-swatch" :style="{ backgroundColor: item.color }"></span>
            <span>{{ item.family }}</span>
            <strong>{{ hidden.has(item.family) ? '—' : format(item.values[monthIndex]) }}</strong>
          </button>
          <p v-if="!visible.length" class="muted small">选择一个家族显示曲线。</p>
        </aside>
      </div>
      <p class="trend-note">
        快照 {{ data?.snapshot_date }}。家族内按下游模型 ID 去重，同一模型可归入不同上游家族。
        缺少创建日期的记录不进入曲线。累计口径包含图示窗口之前已创建的模型。
      </p>
      <details>
        <summary>查看 {{ activeMonth }} 的数值和缺失记录</summary>
        <table>
          <thead><tr><th scope="col">家族</th><th scope="col" class="num">{{ mode === 'cumulative' ? '累计' : '月度新增' }}</th><th scope="col" class="num">缺少创建日期</th></tr></thead>
          <tbody>
            <tr v-for="item in series" :key="item.family">
              <td>{{ item.family }}</td><td class="num">{{ format(item.values[monthIndex]) }}</td><td class="num">{{ format(item.undated) }}</td>
            </tr>
          </tbody>
        </table>
      </details>
    </template>
  </section>
</template>

<style scoped>
.trend-panel { padding: 20px clamp(12px, 2.4vw, 28px); border: 1px solid var(--line); border-radius: 9px; background: var(--card); }
.trend-header { display: flex; align-items: start; justify-content: space-between; flex-wrap: wrap; gap: .75rem; margin-bottom: 1.25rem; }
.trend-header h2 { font-size: 1.25rem; color: var(--fg); letter-spacing: -.015em; margin: 0 0 .4rem; }
.trend-header p, .trend-note { font-size: .84rem; color: var(--muted); margin: 0; }
.trend-modes { display: flex; gap: 3px; padding: 3px; border: 1px solid var(--line); border-radius: 7px; background: var(--bg); }
.trend-modes button { color: var(--muted); background: transparent; border-color: transparent; padding: .35rem .6rem; font-size: .8rem; }
.trend-modes button[aria-pressed='true'] { border-color: var(--line); background: var(--card); color: var(--accent-ink); }
.figure-layout { display: grid; grid-template-columns: minmax(0, 1fr) 190px; align-items: start; gap: .8rem; }
.plot-frame { overflow-x: auto; }
svg { display: block; width: 100%; color: var(--muted); }
svg text { fill: currentColor; font: 12px var(--mono); }
svg .axis-label { font: 12px var(--font); }
.grid-line { stroke: var(--line); }
.month-line { stroke: var(--faint); stroke-dasharray: 3 4; }
.month-point { stroke: var(--card); stroke-width: 1; }
.trend-legend { display: grid; gap: .35rem; border-left: 1px solid var(--line); padding-left: .8rem; }
.month-control { display: grid; grid-template-columns: auto 1fr; align-items: center; gap: .5rem; font-size: .8rem; color: var(--muted); margin-bottom: .4rem; }
.month-control select { width: 100%; font-size: inherit; }
.trend-legend button { display: grid; grid-template-columns: 9px minmax(0, 1fr) auto; gap: .45rem; align-items: center; text-align: left; padding: .35rem; font-size: .78rem; background: var(--bg); color: var(--fg); border-color: var(--line); overflow-wrap: anywhere; }
.trend-legend button[aria-pressed='false'] { opacity: .56; }
.legend-swatch { width: 9px; height: 9px; border-radius: 2px; }
.trend-legend strong { font-family: var(--mono); font-weight: 550; }
.trend-note { border-top: 1px solid var(--line); padding-top: .7rem; margin-top: .55rem; }
details { margin-top: .6rem; font-size: .82rem; }
summary { color: var(--accent-ink); cursor: pointer; }
@media (max-width: 850px) {
  .figure-layout { grid-template-columns: 1fr; }
  .trend-legend { border-left: 0; padding-left: 0; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
}
@media (max-width: 560px) {
  svg text { font-size: 18px; }
  svg .axis-label { font-size: 17px; }
  .secondary-tick { display: none; }
}
</style>
