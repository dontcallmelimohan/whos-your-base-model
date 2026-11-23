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

export interface DatasetLink {
  dataset_id: string
  source_field: string | null
  raw_value: string | null
}

export interface ModelDetail extends ModelSummary {
  snapshot_id: string
  datasets: DatasetLink[]
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

export interface Metrics {
  model_count: number
  edge_count: number
  unique_pair_count: number
  parent_count: number
  root_count: number
  ghost_count: number
  family_count: number
  cyclic_node_count: number
}

export interface Concentration {
  hhi: number
  hhi_scaled: number
  top10_share: number
  parent_count: number
}

export interface DataQuality {
  ghost_ratio: number
  ghost_parent_count: number
  cyclic_node_count: number
}

export interface UpstreamRank {
  model_id: string
  direct: number
  total: number
  family: string | null
}

export interface FamilyBucket {
  family: string
  models: number
  total_descendants: number
}

export interface CaseRef {
  title: string
  model_id: string
  note: string
}

export interface AnalysisResponse {
  snapshot_id: string
  rule_version: string
  scope_note: string | null
  metrics: Metrics
  concentration: Concentration
  data_quality: DataQuality
  type_distribution: TypeBucket[]
  top_upstream: UpstreamRank[]
  family_distribution: FamilyBucket[]
  cases: CaseRef[]
}
