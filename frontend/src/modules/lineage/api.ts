import { api, buildQuery } from '@/shared/api'
import type { ItemList, ModelSummary, RelationType } from '@/shared/types'

export type Direction = 'upstream' | 'downstream' | 'both'

export interface GraphNode {
  id: string
  label: string
  ghost: boolean
  family: string | null
  downloads: number | null
  pipeline: string | null
  author: string | null
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: RelationType
  source_field: string | null
}

export interface GraphResponse {
  snapshot_id: string
  root: string
  direction: Direction
  depth: number
  nodes: GraphNode[]
  edges: GraphEdge[]
  truncated: boolean
  node_limit: number
  node_count: number
  edge_count: number
}

export const fetchGraph = (params: {
  model_id: string
  direction?: Direction
  depth?: number
  relation_type?: string
  limit?: number
}) => api<GraphResponse>(`/api/graph${buildQuery(params)}`)

export const searchModels = (q: string) =>
  api<ItemList<ModelSummary>>(`/api/models${buildQuery({ q, page_size: 8 })}`)
