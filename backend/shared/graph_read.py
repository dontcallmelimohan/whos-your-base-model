"""公共读取层：图模块与分析模块共用同一套读法，避免各算一套。

边界约定（v5 四个任务都要遵守）：
    * 只有本文件直接拼 relations / models 的读取 SQL；
    * 后面的核验类扩展（如果做）只允许在这里加过滤条件，不允许在调用方各自加；
    * 返回的都是 sqlite3.Row，转成 pydantic 模型由各模块自己做。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from shared import config
from shared.errors import not_found


def list_snapshots(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """与 default_snapshot_id 同一排序：日期最新，同一天取模型更多的。"""
    return conn.execute(
        """SELECT s.* FROM snapshots s
           ORDER BY s.snapshot_date DESC,
                    (SELECT count(*) FROM models m WHERE m.snapshot_id = s.id) DESC,
                    s.created_at DESC"""
    ).fetchall()


def default_snapshot_id(conn: sqlite3.Connection) -> str | None:
    """默认快照：日期最新，同一天则取模型更多的那个（避免样例盖掉真实数据）。"""
    row = conn.execute(
        """SELECT s.id AS id FROM snapshots s
           ORDER BY s.snapshot_date DESC,
                    (SELECT count(*) FROM models m WHERE m.snapshot_id = s.id) DESC,
                    s.created_at DESC
           LIMIT 1"""
    ).fetchone()
    return row["id"] if row else None


def get_snapshot(conn: sqlite3.Connection, snapshot_id: str | None) -> sqlite3.Row:
    sid = snapshot_id or default_snapshot_id(conn)
    if not sid:
        from shared.errors import not_ready

        raise not_ready("尚未导入任何数据版本，请先运行 scripts/seed.py 或调用 /api/imports")
    row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (sid,)).fetchone()
    if row is None:
        raise not_found(f"数据版本不存在: {sid}")
    return row


def view_filter(view: str = "declared", alias: str = "") -> str:
    """两种视图：declared = 只读模型卡声明；completed = 再加上核验通过的候选。"""
    prefix = f"{alias}." if alias else ""
    if view == "completed":
        return (
            f"({prefix}is_baseline = 1 OR "
            f"({prefix}origin = 'candidate' AND {prefix}status = 'confirmed'))"
        )
    return f"{prefix}is_baseline = 1"


def count_models(conn: sqlite3.Connection, snapshot_id: str) -> int:
    row = conn.execute(
        "SELECT count(*) AS c FROM models WHERE snapshot_id = ?", (snapshot_id,)
    ).fetchone()
    return int(row["c"])


def count_relations(conn: sqlite3.Connection, snapshot_id: str, view: str = "declared") -> int:
    row = conn.execute(
        f"SELECT count(*) AS c FROM relations WHERE snapshot_id = ? AND {view_filter(view)}",
        (snapshot_id,),
    ).fetchone()
    return int(row["c"])


def get_model(conn: sqlite3.Connection, snapshot_id: str, model_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM models WHERE snapshot_id = ? AND model_id = ?",
        (snapshot_id, model_id),
    ).fetchone()


def get_models(conn: sqlite3.Connection, snapshot_id: str, ids: Iterable[str]) -> dict[str, sqlite3.Row]:
    id_list = list(dict.fromkeys(ids))
    if not id_list:
        return {}
    placeholders = ",".join("?" for _ in id_list)
    rows = conn.execute(
        f"SELECT * FROM models WHERE snapshot_id = ? AND model_id IN ({placeholders})",
        (snapshot_id, *id_list),
    ).fetchall()
    return {row["model_id"]: row for row in rows}


def neighbours(
    conn: sqlite3.Connection,
    snapshot_id: str,
    node_ids: Iterable[str],
    direction: str,
    relation_type: str | None = None,
    view: str = "declared",
) -> list[sqlite3.Row]:
    """取一层邻居关系。

    direction = upstream  -> 这些节点作为下游，查它们的上游
    direction = downstream-> 这些节点作为上游，查它们的下游
    """
    ids = list(dict.fromkeys(node_ids))
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    column = "child_id" if direction == "upstream" else "parent_id"
    sql = (
        f"SELECT * FROM relations WHERE snapshot_id = ? AND {column} IN ({placeholders})"
        f" AND {view_filter(view)}"
    )
    params: list[object] = [snapshot_id, *ids]
    if relation_type:
        sql += " AND relation_type = ?"
        params.append(relation_type)
    sql += " ORDER BY parent_id, child_id, relation_type"
    return conn.execute(sql, params).fetchall()


def all_relations(
    conn: sqlite3.Connection, snapshot_id: str, view: str = "declared"
) -> list[sqlite3.Row]:
    return conn.execute(
        f"SELECT * FROM relations WHERE snapshot_id = ? AND {view_filter(view)}"
        " ORDER BY parent_id, child_id, relation_type",
        (snapshot_id,),
    ).fetchall()


def dataset_links(conn: sqlite3.Connection, snapshot_id: str, model_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM model_datasets WHERE snapshot_id = ? AND model_id = ?"
        " ORDER BY dataset_id",
        (snapshot_id, model_id),
    ).fetchall()


def graph_limits() -> dict[str, int]:
    return {
        "max_depth": config.MAX_DEPTH,
        "max_nodes": config.MAX_GRAPH_NODES,
        "default_nodes": config.DEFAULT_GRAPH_NODES,
    }
