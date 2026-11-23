"""任务 1：搜索与详情。"""

from __future__ import annotations

import sqlite3

from shared import graph_read
from shared.contracts import DatasetLink, ModelDetail, ModelSummary
from shared.errors import invalid, not_found


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _summary(row: sqlite3.Row) -> ModelSummary:
    return ModelSummary(
        model_id=row["model_id"],
        author=row["author"],
        pipeline=row["pipeline"],
        library=row["library"],
        downloads=row["downloads"],
        downloads_all=row["downloads_all"],
        likes=row["likes"],
        created=row["created"],
        family=row["family"] or None,
        ghost=bool(row["ghost"]),
    )


def search_models(
    conn: sqlite3.Connection,
    snapshot_id: str,
    q: str | None,
    page: int,
    page_size: int,
    family: str | None = None,
    include_ghost: bool = True,
) -> tuple[list[ModelSummary], int]:
    if page < 1:
        raise invalid("page 必须 >= 1", {"page": page})
    if not 1 <= page_size <= 100:
        raise invalid("page_size 必须在 1..100 之间", {"page_size": page_size})

    where = "snapshot_id = ?"
    params: list[object] = [snapshot_id]
    if q:
        where += " AND model_id LIKE ? ESCAPE '\\'"
        params.append(f"%{_escape_like(q.strip())}%")
    if family:
        where += " AND family = ?"
        params.append(family)
    if not include_ghost:
        where += " AND ghost = 0"

    total = int(
        conn.execute(f"SELECT count(*) AS c FROM models WHERE {where}", params).fetchone()["c"]
    )
    rows = conn.execute(
        f"""SELECT * FROM models WHERE {where}
            ORDER BY (downloads IS NULL), downloads DESC, model_id
            LIMIT ? OFFSET ?""",
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()

    return [_summary(row) for row in rows], total


def model_detail(conn: sqlite3.Connection, snapshot_id: str, model_id: str) -> ModelDetail:
    row = graph_read.get_model(conn, snapshot_id, model_id)
    if row is None:
        raise not_found(f"模型不存在: {model_id}", {"snapshot_id": snapshot_id})

    links = [
        DatasetLink(
            dataset_id=link["dataset_id"],
            source_field=link["source_field"],
            raw_value=link["raw_value"],
        )
        for link in graph_read.dataset_links(conn, snapshot_id, model_id)
    ]
    return ModelDetail(
        **_summary(row).model_dump(),
        snapshot_id=snapshot_id,
        datasets=links,
    )
