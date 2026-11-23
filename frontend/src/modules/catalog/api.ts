import { api, buildQuery } from '@/shared/api'
import type { ItemList, ModelDetail, ModelSummary, Snapshot } from '@/shared/types'

export interface CatalogDetail extends ModelDetail {
  declared_parents: { model_id: string; relation_type: string; source_field: string | null }[]
  license_declaration: { license: string | null; license_name: string | null; license_link: string | null; source_field: string } | null
}

export interface ModelQuery {
  snapshot_id?: string
  q?: string
  family?: string
  include_ghost?: boolean
  page?: number
  page_size?: number
}

export const fetchModels = (params: ModelQuery & { sort?: CatalogMetric; ascending?: boolean }) =>
  api<ItemList<ModelSummary>>(`/api/models${buildQuery(params)}`)

export const fetchModel = (modelId: string, snapshotId?: string) =>
  api<CatalogDetail>(`/api/model${buildQuery({ model_id: modelId, snapshot_id: snapshotId })}`)

export const fetchSnapshots = () => api<ItemList<Snapshot>>('/api/snapshots')

export type BoardMetric = 'model_id' | 'total' | 'direct' | 'recent' | 'finetune' | 'adapter' | 'quantized' | 'merge'

export type BoardRow = Record<Exclude<BoardMetric, 'model_id'>, number> & {
  model_id: string
  family: string | null
  ghost: boolean
}

export const fetchBoard = (params: ModelQuery & { sort: BoardMetric; ascending: boolean }) =>
  api<{ items: BoardRow[]; total: number; families: string[] }>(
    `/api/catalog/leaderboard${buildQuery(params)}`,
  )

export type CatalogMetric = 'downloads' | 'downloads_all' | 'likes' | 'created' | 'model_id'

export interface SnapshotTrends {
  snapshot_id: string
  snapshot_date: string
  months: string[]
  series: { family: string; before_window: number; monthly: number[]; undated: number }[]
}

export const fetchTrends = (snapshotId: string) =>
  api<SnapshotTrends>(`/api/catalog/trends${buildQuery({ snapshot_id: snapshotId })}`)
