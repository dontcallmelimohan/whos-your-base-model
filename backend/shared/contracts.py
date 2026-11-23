"""跨模块数据契约。

字段与关系类型沿用 model-family-tree（MIT，Hesham Haroon）的 dist 口径：
    parents.json  : id, direct, total, d90, finetune, adapter, quantized, merge, family
    children_top  : parent -> [[child, downloads, total], ...]
    stats.json    : models / with_ancestry / edges / parents / roots / ghost_parents / cyclic_nodes / families

四个工作包都从这里取类型；改字段必须先改本文件并同步 docs/CONTRACTS.md。
"""

from __future__ import annotations

from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class RelationType(str, Enum):
    """与 model-family-tree 完全一致的四种关系 + unknown。"""

    FINETUNE = "finetune"
    ADAPTER = "adapter"
    QUANTIZED = "quantized"
    MERGE = "merge"
    UNKNOWN = "unknown"


class Direction(str, Enum):
    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"
    BOTH = "both"


class ItemList(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------- 目录（A）


class SnapshotOut(BaseModel):
    id: str
    source: str
    snapshot_date: str
    input_hash: str | None = None
    rule_version: str
    scope_note: str | None = None


class ModelSummary(BaseModel):
    model_id: str
    author: str | None = None
    pipeline: str | None = None
    library: str | None = None
    downloads: int | None = None
    downloads_all: int | None = None
    likes: int | None = None
    created: str | None = None
    family: str | None = None
    ghost: bool = Field(default=False, description="属性未收录的占位节点（上游 model-family-tree 称 ghost）")


class DatasetLink(BaseModel):
    dataset_id: str
    source_field: str | None = None
    raw_value: str | None = None


class ModelDetail(ModelSummary):
    snapshot_id: str
    datasets: list[DatasetLink] = Field(default_factory=list)


class ImportRequest(BaseModel):
    source: str = Field(default="fixtures", description="fixtures | hubstats | modeltree")
    limit: int | None = Field(default=None, description="最多导入多少个模型")
    snapshot_id: str | None = None


class ImportResult(BaseModel):
    snapshot_id: str
    source: str
    input_hash: str | None = None
    model_count: int
    relation_count: int
    dataset_link_count: int
    created_at: str


class ImportRecord(BaseModel):
    id: int
    snapshot_id: str
    source: str
    input_hash: str | None = None
    model_count: int
    relation_count: int
    dataset_link_count: int
    created_at: str


class SnapshotStats(BaseModel):
    """数据页用的快照概况。"""

    snapshot_id: str
    model_count: int
    relation_count: int
    ghost_count: int
    family_count: int
    dataset_link_count: int
    type_distribution: list["TypeBucket"] = Field(default_factory=list)


class DatasetUsage(BaseModel):
    dataset_id: str
    model_count: int
    source_field: str | None = None


# ---------------------------------------------------------------- 图（B/C）


class GraphNode(BaseModel):
    """形状直接对齐 Cytoscape 的 node.data，前端零转换。"""

    id: str
    label: str
    ghost: bool = False
    family: str | None = None
    downloads: int | None = None
    pipeline: str | None = None
    author: str | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: RelationType = RelationType.UNKNOWN
    source_field: str | None = None


class GraphResponse(BaseModel):
    snapshot_id: str
    root: str
    direction: Direction
    depth: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: bool = False
    node_limit: int = 100
    node_count: int = 0
    edge_count: int = 0


# ---------------------------------------------------------------- 分析（D）


class Metrics(BaseModel):
    model_count: int
    edge_count: int = Field(description="关系条数（带类型去重后）")
    unique_pair_count: int = Field(description="唯一上下游对，用于总边数")
    parent_count: int = Field(description="有下游的模型数")
    root_count: int = Field(description="没有上游的模型数")
    ghost_count: int = Field(description="属性未收录的占位节点数")
    family_count: int
    cyclic_node_count: int = Field(description="处在环上的节点数，用可达性自环判定")


class TypeBucket(BaseModel):
    type: RelationType
    count: int


class UpstreamRank(BaseModel):
    model_id: str
    direct: int = Field(description="直接下游数")
    total: int = Field(description="可达后代数（含间接）")
    family: str | None = None


class FamilyBucket(BaseModel):
    family: str
    models: int
    total_descendants: int


class CaseRef(BaseModel):
    title: str
    model_id: str
    note: str


class AnalysisResponse(BaseModel):
    snapshot_id: str
    rule_version: str
    scope_note: str | None = None
    metrics: Metrics
    type_distribution: list[TypeBucket]
    top_upstream: list[UpstreamRank]
    family_distribution: list[FamilyBucket]
    cases: list[CaseRef] = Field(default_factory=list)


# ---------------------------------------------------------------- 公共


class HealthResponse(BaseModel):
    status: str
    data_ready: bool
    snapshot_id: str | None = None
    model_count: int = 0
    relation_count: int = 0


class MetaResponse(BaseModel):
    max_page_size: int
    max_depth: int
    default_graph_nodes: int
    max_graph_nodes: int
    rule_version: str
    relation_types: list[str]


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: object | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
