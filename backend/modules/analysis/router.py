"""工作包 D：分析接口。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from modules.analysis.service import build_analysis
from shared import graph_read
from shared.contracts import AnalysisResponse
from shared.db import get_conn

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/analysis", response_model=AnalysisResponse)
def get_analysis(
    snapshot_id: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> AnalysisResponse:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    return build_analysis(conn, snapshot["id"])
