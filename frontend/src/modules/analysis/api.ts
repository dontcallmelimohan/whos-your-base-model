import { api, buildQuery } from '@/shared/api'
import type { AnalysisResponse, DiffResponse, ItemList, Snapshot } from '@/shared/types'

export const fetchAnalysis = (snapshotId?: string) =>
  api<AnalysisResponse>(`/api/analysis${buildQuery({ snapshot_id: snapshotId })}`)

export const fetchDiff = (snapshotId?: string) =>
  api<DiffResponse>(`/api/diff${buildQuery({ snapshot_id: snapshotId })}`)

export const exportCsvUrl = (view: 'declared' | 'completed', snapshotId?: string) =>
  `/api/analysis/export.csv${buildQuery({ snapshot_id: snapshotId, view })}`

export const fetchSnapshots = () => api<ItemList<Snapshot>>('/api/snapshots')
