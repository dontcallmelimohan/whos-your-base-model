"""工作包 B：图接口。

/api/graph 的返回形状直接对齐 Cytoscape 的 elements 语义，
前端拿到 nodes/edges 后不需要再做字段映射。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from modules.lineage.traversal import build_local_graph
from shared import config, graph_read
from shared.contracts import Direction, GraphResponse
from shared.db import get_conn

router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/graph", response_model=GraphResponse)
def get_graph(
    model_id: str = Query(..., description="根节点模型 ID，含斜杠时需 URL 编码"),
    snapshot_id: str | None = Query(default=None),
    direction: Direction = Query(default=Direction.BOTH),
    depth: int = Query(default=1, ge=1, le=config.MAX_DEPTH),
    relation_type: str | None = Query(default=None),
    limit: int = Query(default=config.DEFAULT_GRAPH_NODES, ge=1, le=config.MAX_GRAPH_NODES),
    view: str = Query(default="declared", description="declared = 仅声明；completed = 加上核验通过的候选"),
    conn: sqlite3.Connection = Depends(get_conn),
) -> GraphResponse:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    return build_local_graph(
        conn=conn,
        snapshot_id=snapshot["id"],
        root_id=model_id,
        direction=direction.value,
        depth=depth,
        relation_type=relation_type,
        limit=limit,
        view=view,
    )
