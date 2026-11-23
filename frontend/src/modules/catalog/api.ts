import { api, buildQuery } from '@/shared/api'
import type { ItemList, ModelDetail, ModelSummary, Snapshot } from '@/shared/types'

export interface ModelQuery {
  q?: string
  family?: string
  include_ghost?: boolean
  page?: number
  page_size?: number
}

export const fetchModels = (params: ModelQuery) =>
  api<ItemList<ModelSummary>>(`/api/models${buildQuery(params)}`)

export const fetchModel = (modelId: string) =>
  api<ModelDetail>(`/api/model${buildQuery({ model_id: modelId })}`)

export const fetchSnapshots = () => api<ItemList<Snapshot>>('/api/snapshots')
