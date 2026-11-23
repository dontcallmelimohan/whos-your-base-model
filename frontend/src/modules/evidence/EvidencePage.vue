<script setup lang="ts">
/**
 * 工作包 3：依赖发现与证据核验。
 *
 * 流程：跑抽取 → 候选列表 → 点开一条看原文 → 确认 / 驳回 / 保留未知 → 记录追加。
 * 规则输出只是「候选」，不是结论；只有 confirmed 才会进入补全图。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { errorText } from '@/shared/api'
import type { CandidateItem, RelationDetail, ReviewDecision } from '@/shared/types'

import { fetchCandidates, fetchRelation, fetchSnapshots, fetchSummary, postReview, runExtraction } from './api'

const router = useRouter()

const snapshotId = ref('')
const status = ref<string>('pending')
const items = ref<CandidateItem[]>([])
const summary = ref<Record<string, number> | null>(null)
const detail = ref<RelationDetail | null>(null)
const note = ref('')

const loading = ref(false)
const running = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const statusTabs = [
  { key: 'pending', label: '待核验' },
  { key: 'confirmed', label: '已确认' },
  { key: 'rejected', label: '已驳回' },
  { key: 'unknown', label: '未知' },
  { key: '', label: '全部' },
]

const activeCandidate = computed(() => detail.value?.relation ?? null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [list, counts] = await Promise.all([
      fetchCandidates({ status: status.value || undefined, page_size: 50, snapshot_id: snapshotId.value }),
      fetchSummary(snapshotId.value),
    ])
    items.value = list.items
    summary.value = counts as unknown as Record<string, number>
    if (!items.value.length) detail.value = null
    else if (!detail.value || !items.value.some((i) => i.relation_id === detail.value!.relation.relation_id)) {
      await select(items.value[0].relation_id)
    }
  } catch (err) {
    error.value = errorText(err)
  } finally {
    loading.value = false
  }
}

async function select(relationId: string) {
  try {
    detail.value = await fetchRelation(relationId)
    note.value = ''
  } catch (err) {
    error.value = errorText(err)
  }
}

async function extract() {
  running.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await runExtraction(snapshotId.value)
    notice.value = `抽取完成：扫描 ${result.scanned_models} 个模型卡，新增候选 ${result.created_candidates} 条、证据 ${result.created_evidence} 条`
    status.value = 'pending'
    await load()
  } catch (err) {
    error.value = errorText(err)
  } finally {
    running.value = false
  }
}

async function decide(decision: ReviewDecision) {
  if (!activeCandidate.value) return
  saving.value = true
  error.value = ''
  try {
    detail.value = await postReview(activeCandidate.value.relation_id, decision, note.value)
    notice.value = `已保存：${decision}`
    summary.value = (await fetchSummary(snapshotId.value)) as unknown as Record<string, number>
    if (status.value === 'pending') {
      items.value = items.value.filter((i) => i.relation_id !== activeCandidate.value!.relation_id)
      if (items.value.length) await select(items.value[0].relation_id)
      else detail.value = null
    }
  } catch (err) {
    error.value = errorText(err)
  } finally {
    saving.value = false
  }
}

function openInLineage(modelId: string) {
  router.push({ path: '/lineage', query: { model: modelId, view: 'completed' } })
}

function statusBadge(value: string): string {
  return { pending: 'badge-warn', confirmed: 'badge-ok', rejected: 'badge-danger' }[value] ?? ''
}

async function pickSnapshot() {
  try {
    const list = await fetchSnapshots()
    for (const item of list.items) {
      const summary = await fetchSummary(item.id)
      if (summary.total > 0) {
        snapshotId.value = item.id
        return
      }
    }
    snapshotId.value = list.items[0]?.id ?? ''
  } catch {
    /* 忽略，走默认快照 */
  }
}

onMounted(async () => {
  await pickSnapshot()
  await load()
})
</script>

<template>
  <section>
    <div class="page-head">
      <div>
        <h1>依赖核验</h1>
        <p class="lede">
          规则从模型卡正文里找「声明字段没写」的上游，附上原文，由人判断。
          只有确认为真的关系才会进入补全图。
        </p>
      </div>
      <div class="row">
        <span v-if="snapshotId" class="badge">{{ snapshotId }}</span>
        <button :disabled="running" @click="extract">
          {{ running ? '抽取中…' : '运行抽取' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="notice" class="alert alert-info">{{ notice }}</div>

    <!-- 状态统计 -->
    <div v-if="summary" class="chips">
      <span class="badge badge-warn">待核验 {{ summary.pending ?? 0 }}</span>
      <span class="badge badge-ok">已确认 {{ summary.confirmed ?? 0 }}</span>
      <span class="badge badge-danger">已驳回 {{ summary.rejected ?? 0 }}</span>
      <span class="badge">未知 {{ summary.unknown ?? 0 }}</span>
      <span class="chips-hint muted small">共 {{ summary.total ?? 0 }} 条候选</span>
    </div>

    <div class="tabs">
      <button
        v-for="tab in statusTabs"
        :key="tab.key"
        :class="{ active: status === tab.key }"
        @click="((status = tab.key), load())"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="!loading && !items.length" class="panel muted small">
      没有候选。点右上角「运行抽取」从模型卡样例里生成，或切换上面的状态标签。
    </div>

    <div class="evidence-body">
      <!-- 候选列表 -->
      <div class="panel" style="padding: 0">
        <table class="data-table">
          <thead>
            <tr>
              <th>候选关系</th>
              <th style="width: 92px">类型</th>
              <th style="width: 78px">状态</th>
              <th class="num" style="width: 60px">证据</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in items"
              :key="row.relation_id"
              class="row-click"
              :class="{ selected: row.relation_id === activeCandidate?.relation_id }"
              @click="select(row.relation_id)"
            >
              <td>
                <div class="rel-pair">
                  <code>{{ row.parent_id }}</code>
                  <span class="faint">→</span>
                  <code>{{ row.child_id }}</code>
                </div>
              </td>
              <td class="muted">{{ row.relation_type }}</td>
              <td><span class="badge" :class="statusBadge(row.status)">{{ row.status }}</span></td>
              <td class="num muted">{{ row.evidence_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 证据与核验 -->
      <div class="panel">
        <template v-if="detail">
          <div class="evidence-head">
            <code>{{ detail.relation.parent_id }}</code>
            <span class="faint">→</span>
            <code>{{ detail.relation.child_id }}</code>
            <span class="badge badge-accent">{{ detail.relation.relation_type }}</span>
          </div>

          <p class="faint small" style="margin: 6px 0 14px">
            来源字段：<code>{{ detail.relation.source_field ?? '—' }}</code>
            · 当前状态：<span class="badge" :class="statusBadge(detail.relation.status)">{{ detail.relation.status }}</span>
          </p>

          <h3 class="section-label">证据</h3>
          <div v-for="item in detail.evidence" :key="item.id" class="quote">
            <blockquote>{{ item.quote }}</blockquote>
            <div class="quote-meta">
              <code>{{ item.source_path }} · {{ item.locator }}</code>
              <span class="badge">{{ item.source_type }}</span>
              <span class="faint small">{{ item.revision ?? '仅有数据快照' }}</span>
            </div>
          </div>

          <h3 class="section-label" style="margin-top: 22px">核验</h3>
          <textarea v-model="note" rows="3" placeholder="备注（会写进核验记录）"></textarea>
          <div class="row" style="margin-top: 10px">
            <button :disabled="saving" @click="decide('confirmed')">确认</button>
            <button class="ghost" :disabled="saving" @click="decide('unknown')">保留未知</button>
            <button class="ghost danger" :disabled="saving" @click="decide('rejected')">驳回</button>
            <button class="ghost" @click="openInLineage(detail.relation.child_id)">在补全图中查看</button>
          </div>

          <h3 class="section-label" style="margin-top: 22px">
            核验记录 · {{ detail.reviews.length }}
          </h3>
          <p v-if="!detail.reviews.length" class="muted small" style="margin: 0">还没有核验记录。</p>
          <ul v-else class="review-list">
            <li v-for="review in detail.reviews" :key="review.id">
              <span class="badge" :class="statusBadge(review.decision)">{{ review.decision }}</span>
              <span class="muted small">{{ review.created_at }}</span>
              <span v-if="review.note" class="small">{{ review.note }}</span>
            </li>
          </ul>
        </template>
        <p v-else class="muted small" style="margin: 0">在左边选一条候选查看证据。</p>
      </div>
    </div>
  </section>
</template>
