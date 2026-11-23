/**
 * 前端类型契约：与 backend/shared/contracts.py 一一对应。
 * 改这里必须同时改 contracts.py，否则 CI 里的契约测试会失败。
 */

export type RelationType = 'finetune' | 'adapter' | 'quantized' | 'merge' | 'unknown'

export interface ItemList<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Snapshot {
  id: string
  source: string
  snapshot_date: string
  input_hash: string | null
  rule_version: string
  scope_note: string | null
}

export interface ModelSummary {
  model_id: string
  author: string | null
  pipeline: string | null
  library: string | null
  downloads: number | null
  downloads_all: number | null
  likes: number | null
  created: string | null
  family: string | null
  ghost: boolean
}

export interface ImportRecord {
  id: number
  snapshot_id: string
  source: string
  input_hash: string | null
  model_count: number
  relation_count: number
  dataset_link_count: number
  created_at: string
}

export interface TypeBucket {
  type: RelationType
  count: number
}

export interface SnapshotStats {
  snapshot_id: string
  model_count: number
  relation_count: number
  ghost_count: number
  family_count: number
  dataset_link_count: number
  type_distribution: TypeBucket[]
}

export interface DatasetUsage {
  dataset_id: string
  model_count: number
  source_field: string | null
}

export interface Health {
  status: string
  data_ready: boolean
  snapshot_id: string | null
  model_count: number
  relation_count: number
}

export interface Meta {
  max_page_size: number
  max_depth: number
  default_graph_nodes: number
  max_graph_nodes: number
  rule_version: string
  relation_types: RelationType[]
}
