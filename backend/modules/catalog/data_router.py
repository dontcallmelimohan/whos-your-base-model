"""任务 1：数据管理接口。

导入、数据版本、快照概况、数据集关联。页面只需要这几个接口。
"""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Query
from pydantic import BaseModel, Field

from modules.catalog import data_service as service
from modules.catalog.hubstats_sync import sync_hubstats
from modules.catalog.importer import run_import
from shared import graph_read
from shared.contracts import (
    DatasetUsage,
    ImportRecord,
    ImportRequest,
    ImportResult,
    ItemList,
    SnapshotOut,
    SnapshotStats,
)
from shared.db import get_conn, init_database

@asynccontextmanager
async def catalog_lifespan(_: FastAPI):
    init_database()
    yield


router = APIRouter(prefix="/api", tags=["data"], lifespan=catalog_lifespan)


class HubStatsSyncRequest(BaseModel):
    limit: int | None = Field(default=None, ge=0, description="默认 20000，0 表示全量")


class HubStatsSyncResult(ImportResult):
    updated: bool


@router.post("/hubstats/sync", response_model=HubStatsSyncResult)
def sync_latest_hubstats(payload: HubStatsSyncRequest) -> HubStatsSyncResult:
    return HubStatsSyncResult(**sync_hubstats(payload.limit))


@router.post("/imports", response_model=ImportResult)
def create_import(payload: ImportRequest) -> ImportResult:
    return ImportResult(**run_import(payload.source, payload.limit, payload.snapshot_id))


@router.get("/imports", response_model=ItemList[ImportRecord])
def list_imports(
    limit: int = Query(default=20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_conn),
) -> ItemList[ImportRecord]:
    items = service.recent_imports(conn, limit)
    return ItemList[ImportRecord](items=items, total=len(items), page=1, page_size=limit)


@router.get("/snapshots", response_model=ItemList[SnapshotOut])
def list_snapshots(conn: sqlite3.Connection = Depends(get_conn)) -> ItemList[SnapshotOut]:
    rows = graph_read.list_snapshots(conn)
    items = [
        SnapshotOut(
            id=row["id"],
            source=row["source"],
            snapshot_date=row["snapshot_date"],
            input_hash=row["input_hash"],
            rule_version=row["rule_version"],
            scope_note=row["scope_note"],
        )
        for row in rows
    ]
    return ItemList[SnapshotOut](items=items, total=len(items), page=1, page_size=max(len(items), 1))


@router.get("/snapshots/{snapshot_id}/stats", response_model=SnapshotStats)
def snapshot_stats(
    snapshot_id: str,
    conn: sqlite3.Connection = Depends(get_conn),
) -> SnapshotStats:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    return service.snapshot_stats(conn, snapshot["id"])


@router.get("/datasets", response_model=ItemList[DatasetUsage])
def list_datasets(
    limit: int = Query(default=20, ge=1, le=100),
    snapshot_id: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> ItemList[DatasetUsage]:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    items = service.dataset_usage(conn, snapshot["id"], limit)
    return ItemList[DatasetUsage](items=items, total=len(items), page=1, page_size=limit)
