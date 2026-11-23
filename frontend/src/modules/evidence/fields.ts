/**
 * 证据字段与样例响应（任务 3 维护，任务 4 消费）。
 *
 * 目的：让「检索记录」「四类结论」在前后端只有一个文案与取值来源，
 * 页面不要自己写死中文字符串。字段含义与后端约定见
 * docs/EVIDENCE_HANDOFF.md，改这里要同步那份文档。
 */

/** 证据来源类型，和 002_evidence.sql 的 source_type 一致。 */
export type EvidenceSourceType = 'model_field' | 'model_card_text' | 'model_card_yaml' | 'config'

export const SOURCE_TYPE_LABEL: Record<EvidenceSourceType, string> = {
  model_field: '模型字段',
  model_card_text: '模型卡正文',
  model_card_yaml: '模型卡元数据',
  config: '配置文件',
}

/** 来源读取状态：失败原因要显示给用户，不能笼统写「无证据」。 */
export type SourceStatus = 'checked' | 'not_found' | 'access_denied' | 'timeout' | 'unsupported'

export const SOURCE_STATUS_LABEL: Record<SourceStatus, string> = {
  checked: '已检查',
  not_found: '未找到',
  access_denied: '无权访问',
  timeout: '访问超时',
  unsupported: '尚未支持',
}

export interface SourceFailure {
  model_id: string
  path: string
  reason: Exclude<SourceStatus, 'checked'>
  detail?: string | null
}

/** 任务 3 → 任务 4 的检索记录（当前通过接口返回的是计数，结构先在这里定）。 */
export interface RetrievalRecord {
  snapshot_id: string
  model_id: string
  rule_version: string
  checked: string[]
  failures: SourceFailure[]
  created_candidates: number
  created_evidence: number
}

/** 四类结论，和 backend/modules/evidence/verification/judge.py 的 Verdict 一致。 */
export type Verdict = 'support' | 'refute' | 'conflict' | 'insufficient'

export const VERDICT_LABEL: Record<Verdict, string> = {
  support: '支持',
  refute: '反驳',
  conflict: '来源冲突',
  insufficient: '证据不足',
}

export const VERDICT_TONE: Record<Verdict, 'ok' | 'danger' | 'warn' | 'muted'> = {
  support: 'ok',
  refute: 'danger',
  conflict: 'warn',
  insufficient: 'muted',
}

/** 证据不足的三种细分。 */
export type InsufficientReason = 'not_found' | 'ambiguous' | 'unreachable'

export const INSUFFICIENT_REASON_LABEL: Record<InsufficientReason, string> = {
  not_found: '未找到证据',
  ambiguous: '文档指向不清',
  unreachable: '来源不可访问',
}

/** 一条核验结论（后端 VerdictResult 的镜像，供页面与样例响应共用）。 */
export interface VerdictRecord {
  relation_id: string
  verdict: Verdict
  reason: string
  evidence_ids: string[]
  insufficient_reason?: InsufficientReason | null
  rule_id?: string | null
  rule_version?: string | null
  /** 证据 revision 与快照是否对齐；false 时不计入同快照差分 */
  version_aligned: boolean
}

/** 样例：答辩案例的支持结论（原文见 docs/EVIDENCE_HANDOFF.md）。 */
export const SAMPLE_SUPPORT: VerdictRecord = {
  relation_id: 'rel_<sha1>',
  verdict: 'support',
  reason: 'README 明确写 "finetuned from stabilityai/stable-video-diffusion-img2vid"',
  evidence_ids: ['ev_<sha1>'],
  rule_id: 'r_finetuned_from',
  rule_version: 'rules-v2',
  version_aligned: true,
}
