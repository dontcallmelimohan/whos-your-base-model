"""工作包 A：数据管理服务（导入记录、快照概况、数据集关联）。"""

from __future__ import annotations

import sqlite3

from shared.contracts import DatasetUsage, ImportRecord, RelationType, SnapshotStats, TypeBucket


def recent_imports(conn: sqlite3.Connection, limit: int = 20) -> list[ImportRecord]:
    rows = conn.execute(
        "SELECT * FROM imports ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [
        ImportRecord(
            id=row["id"],
            snapshot_id=row["snapshot_id"],
            source=row["source"],
            input_hash=row["input_hash"],
            model_count=row["model_count"],
            relation_count=row["relation_count"],
            dataset_link_count=row["dataset_link_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def _count(conn: sqlite3.Connection, sql: str, params: tuple) -> int:
    return int(conn.execute(sql, params).fetchone()["c"])


def snapshot_stats(conn: sqlite3.Connection, snapshot_id: str) -> SnapshotStats:
    rows = conn.execute(
        """SELECT relation_type, count(*) AS c FROM relations
           WHERE snapshot_id = ? AND is_baseline = 1
           GROUP BY relation_type ORDER BY c DESC""",
        (snapshot_id,),
    ).fetchall()
    distribution = []
    for row in rows:
        try:
            rtype = RelationType(row["relation_type"])
        except ValueError:
            rtype = RelationType.UNKNOWN
        distribution.append(TypeBucket(type=rtype, count=int(row["c"])))

    return SnapshotStats(
        snapshot_id=snapshot_id,
        model_count=_count(
            conn, "SELECT count(*) AS c FROM models WHERE snapshot_id = ?", (snapshot_id,)
        ),
        relation_count=_count(
            conn, "SELECT count(*) AS c FROM relations WHERE snapshot_id = ?", (snapshot_id,)
        ),
        ghost_count=_count(
            conn,
            "SELECT count(*) AS c FROM models WHERE snapshot_id = ? AND ghost = 1",
            (snapshot_id,),
        ),
        family_count=_count(
            conn,
            """SELECT count(DISTINCT family) AS c FROM models
               WHERE snapshot_id = ? AND family IS NOT NULL AND family <> ''""",
            (snapshot_id,),
        ),
        dataset_link_count=_count(
            conn,
            "SELECT count(*) AS c FROM model_datasets WHERE snapshot_id = ?",
            (snapshot_id,),
        ),
        type_distribution=distribution,
    )


def dataset_usage(conn: sqlite3.Connection, snapshot_id: str, limit: int = 20) -> list[DatasetUsage]:
    rows = conn.execute(
        """SELECT dataset_id, count(DISTINCT model_id) AS c, min(source_field) AS field
           FROM model_datasets WHERE snapshot_id = ?
           GROUP BY dataset_id ORDER BY c DESC, dataset_id LIMIT ?""",
        (snapshot_id, limit),
    ).fetchall()
    return [
        DatasetUsage(
            dataset_id=row["dataset_id"],
            model_count=int(row["c"]),
            source_field=row["field"],
        )
        for row in rows
    ]
