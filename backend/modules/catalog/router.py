"""工作包 A：目录相关接口。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from modules.catalog import service
from shared import graph_read
from shared.contracts import ItemList, ModelDetail, ModelSummary
from shared.db import get_conn

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/models", response_model=ItemList[ModelSummary])
def list_models(
    q: str | None = Query(default=None, description="按模型名称模糊搜索"),
    snapshot_id: str | None = Query(default=None),
    family: str | None = Query(default=None, description="按家族过滤，取自派生数据"),
    include_ghost: bool = Query(default=True, description="是否包含属性未收录的占位节点"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_conn),
) -> ItemList[ModelSummary]:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    items, total = service.search_models(
        conn, snapshot["id"], q, page, page_size, family=family, include_ghost=include_ghost
    )
    return ItemList[ModelSummary](items=items, total=total, page=page, page_size=page_size)


@router.get("/model", response_model=ModelDetail)
def get_model(
    model_id: str = Query(..., description="完整模型 ID，含斜杠，前端需 URL 编码"),
    snapshot_id: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> ModelDetail:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    return service.model_detail(conn, snapshot["id"], model_id)
