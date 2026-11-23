"""任务 1：分析接口。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, Response

from modules.analysis.service import analysis_csv, build_analysis, build_diff
from shared import graph_read
from shared.contracts import AnalysisResponse, DiffResponse
from shared.db import get_conn

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/analysis", response_model=AnalysisResponse)
def get_analysis(
    snapshot_id: str | None = Query(default=None),
    view: str = Query(default="declared", description="declared / completed"),
    conn: sqlite3.Connection = Depends(get_conn),
) -> AnalysisResponse:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    return build_analysis(conn, snapshot["id"], view)


@router.get("/diff", response_model=DiffResponse)
def get_diff(
    snapshot_id: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> DiffResponse:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    return build_diff(conn, snapshot["id"])


@router.get("/analysis/export.csv")
def export_analysis_csv(
    snapshot_id: str | None = Query(default=None),
    view: str = Query(default="declared"),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Response:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    body = analysis_csv(conn, snapshot["id"], view)
    filename = f"analysis-{snapshot['id']}-{view}.csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
