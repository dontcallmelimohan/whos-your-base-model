"""任务 4：核验记录、关系详情与人工复核接口。

候选与证据由任务 3 写入；这里负责查询入口、核验记录和「已确认才进补全图」。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from modules.evidence.verification import service
from shared import graph_read
from shared.contracts import (
    CandidateItem,
    ItemList,
    RelationDetail,
    ReviewRequest,
)
from shared.db import get_conn

router = APIRouter(prefix="/api", tags=["verification"])


@router.get("/candidates", response_model=ItemList[CandidateItem])
def list_candidates(
    snapshot_id: str | None = Query(default=None),
    status: str | None = Query(default=None, description="pending / confirmed / rejected / unknown"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_conn),
) -> ItemList[CandidateItem]:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    items, total = service.list_candidates(conn, snapshot["id"], status, page, page_size)
    return ItemList[CandidateItem](items=items, total=total, page=page, page_size=page_size)


@router.get("/candidates/summary")
def candidates_summary(
    snapshot_id: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    return {"snapshot_id": snapshot["id"], **service.status_counts(conn, snapshot["id"])}


@router.get("/relations/{relation_id}", response_model=RelationDetail)
def get_relation(relation_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> RelationDetail:
    return service.relation_detail(conn, relation_id)


@router.post("/relations/{relation_id}/reviews", response_model=RelationDetail)
def post_review(
    relation_id: str,
    payload: ReviewRequest,
    conn: sqlite3.Connection = Depends(get_conn),
) -> RelationDetail:
    return service.add_review(conn, relation_id, payload.decision, payload.note, payload.reviewer)
