import { api, buildQuery } from '@/shared/api'
import type {
  DatasetUsage,
  Health,
  ImportRecord,
  ItemList,
  Snapshot,
  SnapshotStats,
} from '@/shared/types'

export interface ImportResult {
  snapshot_id: string
  source: string
  input_hash: string | null
  model_count: number
  relation_count: number
  dataset_link_count: number
  created_at: string
}

export const fetchHealth = () => api<Health>('/api/health')

export const fetchSnapshots = () => api<ItemList<Snapshot>>('/api/snapshots')

export const fetchStats = (snapshotId: string) =>
  api<SnapshotStats>(`/api/snapshots/${encodeURIComponent(snapshotId)}/stats`)

export const fetchImports = (limit = 10) =>
  api<ItemList<ImportRecord>>(`/api/imports${buildQuery({ limit })}`)

export const fetchDatasets = (snapshotId: string, limit = 10) =>
  api<ItemList<DatasetUsage>>(`/api/datasets${buildQuery({ snapshot_id: snapshotId, limit })}`)

export const postImport = (source: string, limit: number | null, snapshotId?: string) =>
  api<ImportResult>('/api/imports', {
    method: 'POST',
    body: JSON.stringify({ source, limit, snapshot_id: snapshotId }),
  })
