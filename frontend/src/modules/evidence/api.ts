import { api, buildQuery } from '@/shared/api'
import type { CandidateItem, ItemList, RelationDetail, ReviewDecision, Snapshot } from '@/shared/types'

export const fetchSnapshots = () => api<ItemList<Snapshot>>('/api/snapshots')

export interface CandidateQuery {
  status?: string
  page?: number
  page_size?: number
  snapshot_id?: string
}

export const fetchCandidates = (params: CandidateQuery) =>
  api<ItemList<CandidateItem>>(`/api/candidates${buildQuery(params)}`)

export const fetchSummary = (snapshotId?: string) =>
  api<{ snapshot_id: string; pending: number; confirmed: number; rejected: number; unknown: number; total: number }>(
    `/api/candidates/summary${buildQuery({ snapshot_id: snapshotId })}`,
  )

export const fetchRelation = (id: string) => api<RelationDetail>(`/api/relations/${id}`)

export const runExtraction = (snapshotId?: string) =>
  api<{ snapshot_id: string; scanned_models: number; created_candidates: number; created_evidence: number; skipped_declared: number }>(
    '/api/extractions',
    { method: 'POST', body: JSON.stringify({ source: 'fixtures', snapshot_id: snapshotId }) },
  )

export const postReview = (id: string, decision: ReviewDecision, note: string) =>
  api<RelationDetail>(`/api/relations/${id}/reviews`, {
    method: 'POST',
    body: JSON.stringify({ decision, note: note || null }),
  })
