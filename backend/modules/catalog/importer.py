"""任务 1：导入器。

三个数据源：
    fixtures  platform/fixtures/seed.json                     小型样例，四人并行开发用
    hubstats  仓库根目录 models.parquet（hub-stats dump）     完整边 + 属性
    modeltree model-family-tree-main/dist/*.json              已算好的派生统计，无重依赖

关系抽取口径参考 model-family-tree（MIT, Copyright (c) 2026 Hesham Haroon）的
modeltree/fetch.py：baseModels 是一个结构体，relation 为关系类型，
models 为父模型列表。这里改用 DuckDB 读取，避免引入 polars。

重复导入不产生重复记录：关系有唯一键，写入一律 INSERT OR IGNORE / UPSERT。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from shared import config, graph_read
from shared.db import connect, init_schema
from shared.errors import ApiError, invalid, not_ready

SNAPSHOT_SECRET_RE = ("hf_", "sk-", "ghp_")


def _relation_id(snapshot_id: str, parent: str, child: str, rtype: str) -> str:
    key = f"{snapshot_id}|{parent}|{child}|{rtype}"
    return "rel_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_type(value: str | None) -> str:
    return value if value in config.RELATION_TYPES else "unknown"


def _write_snapshot(conn, snapshot: dict) -> None:
    conn.execute(
        """INSERT INTO snapshots (id, source, snapshot_date, input_hash, rule_version, scope_note)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             source = excluded.source,
             snapshot_date = excluded.snapshot_date,
             input_hash = excluded.input_hash,
             rule_version = excluded.rule_version,
             scope_note = excluded.scope_note""",
        (
            snapshot["id"],
            snapshot["source"],
            snapshot["snapshot_date"],
            snapshot.get("input_hash"),
            snapshot.get("rule_version", config.RULE_VERSION),
            snapshot.get("scope_note"),
        ),
    )


def _upsert_models(conn, snapshot_id: str, rows: Iterable[dict]) -> None:
    conn.executemany(
        """INSERT INTO models (snapshot_id, model_id, author, pipeline, library,
                               downloads, downloads_all, likes, created, family, ghost)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(snapshot_id, model_id) DO UPDATE SET
             author        = coalesce(excluded.author, models.author),
             pipeline      = coalesce(excluded.pipeline, models.pipeline),
             library       = coalesce(excluded.library, models.library),
             downloads     = coalesce(excluded.downloads, models.downloads),
             downloads_all = coalesce(excluded.downloads_all, models.downloads_all),
             likes         = coalesce(excluded.likes, models.likes),
             created       = coalesce(excluded.created, models.created),
             family        = coalesce(nullif(excluded.family, ''), models.family),
             ghost         = min(models.ghost, excluded.ghost)""",
        [
            (
                snapshot_id,
                row["model_id"],
                row.get("author"),
                row.get("pipeline"),
                row.get("library"),
                row.get("downloads"),
                row.get("downloads_all"),
                row.get("likes"),
                row.get("created"),
                row.get("family"),
                1 if row.get("ghost") else 0,
            )
            for row in rows
        ],
    )


def _insert_relations(conn, snapshot_id: str, rows: Iterable[dict]) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO relations
             (id, snapshot_id, parent_id, child_id, relation_type, is_baseline, source_field)
           VALUES (?, ?, ?, ?, ?, 1, ?)""",
        [
            (
                _relation_id(snapshot_id, row["parent_id"], row["child_id"], row["relation_type"]),
                snapshot_id,
                row["parent_id"],
                row["child_id"],
                row["relation_type"],
                row.get("source_field"),
            )
            for row in rows
        ],
    )


def _insert_datasets(conn, snapshot_id: str, rows: Iterable[dict]) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO model_datasets
             (snapshot_id, model_id, dataset_id, source_field, raw_value)
           VALUES (?, ?, ?, ?, ?)""",
        [
            (
                snapshot_id,
                row["model_id"],
                row["dataset_id"],
                row.get("source_field"),
                row.get("raw_value"),
            )
            for row in rows
        ],
    )


def _result(conn, snapshot_id: str, source: str, input_hash: str | None) -> dict:
    row = conn.execute(
        "SELECT count(*) AS c FROM model_datasets WHERE snapshot_id = ?", (snapshot_id,)
    ).fetchone()
    snap = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    return {
        "snapshot_id": snapshot_id,
        "source": source,
        "input_hash": input_hash,
        "model_count": graph_read.count_models(conn, snapshot_id),
        "relation_count": graph_read.count_relations(conn, snapshot_id),
        "dataset_link_count": int(row["c"]),
        "created_at": snap["created_at"] if snap else "",
    }


def _record_import(conn, result: dict) -> None:
    conn.execute(
        """INSERT INTO imports (snapshot_id, source, input_hash, model_count,
                                relation_count, dataset_link_count)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            result["snapshot_id"],
            result["source"],
            result["input_hash"],
            result["model_count"],
            result["relation_count"],
            result["dataset_link_count"],
        ),
    )


# ------------------------------------------------------------------ fixtures


def import_fixtures(snapshot_id: str | None = None) -> dict:
    path = config.fixtures_dir() / "seed.json"
    if not path.exists():
        raise not_ready(f"样例文件不存在: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    meta = dict(payload["snapshot"])
    sid = snapshot_id or meta["id"]
    meta["id"] = sid
    meta.setdefault("rule_version", config.RULE_VERSION)
    meta["input_hash"] = _file_hash(path)

    conn = connect()
    try:
        init_schema(conn)
        _write_snapshot(conn, meta)

        models = [dict(m) for m in payload.get("models", [])]
        known = {m["model_id"] for m in models}
        for rel in payload.get("relations", []):
            if rel["parent_id"] not in known:
                models.append({"model_id": rel["parent_id"], "ghost": True})
                known.add(rel["parent_id"])

        _upsert_models(conn, sid, models)
        _insert_relations(conn, sid, payload.get("relations", []))
        _insert_datasets(conn, sid, payload.get("model_datasets", []))

        result = _result(conn, sid, "fixtures", meta["input_hash"])
        _record_import(conn, result)
        conn.commit()
        return result
    finally:
        conn.close()


# ------------------------------------------------------------------ hubstats


def import_hubstats(limit: int | None = None, snapshot_id: str | None = None) -> dict:
    """从 hub-stats dump 抽边。

    SQL 里直接 unnest baseModels.models，只把需要的列拉进内存。
    """
    path = config.hubstats_parquet_path()
    if not path.exists():
        raise not_ready(f"hub-stats dump 不存在: {path}", {"hint": "放到仓库根目录或设置 PLATFORM_HUBSTATS"})

    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover
        raise not_ready("导入需要 duckdb，请先 pip install duckdb") from exc

    row_limit = limit or config.DEFAULT_IMPORT_LIMIT
    if row_limit <= 0:
        raise invalid("limit 必须为正整数")

    sid = snapshot_id or "hubstats-2026-11-23"

    nodes_sql = """
        SELECT id, author, pipeline_tag, library_name, downloads, downloadsAllTime,
               likes, createdAt
        FROM read_parquet(?)
        WHERE baseModels IS NOT NULL
        ORDER BY downloads DESC NULLS LAST
        LIMIT ?
    """
    edges_sql = """
        WITH picked AS (
            SELECT id, baseModels
            FROM read_parquet(?)
            WHERE baseModels IS NOT NULL
            ORDER BY downloads DESC NULLS LAST
            LIMIT ?
        )
        SELECT p.id AS child, p.baseModels.relation AS relation, m.id AS parent
        FROM picked p, unnest(p.baseModels.models) AS u(m)
    """

    con = duckdb.connect()
    try:
        node_rows = con.execute(nodes_sql, [str(path), row_limit]).fetchall()
        edge_rows = con.execute(edges_sql, [str(path), row_limit]).fetchall()
    finally:
        con.close()

    if not edge_rows:
        raise not_ready("dump 中没有找到带 baseModels 的记录")

    models: dict[str, dict] = {}
    for model_id, author, pipeline, library, downloads, downloads_all, likes, created in node_rows:
        if any(secret in (model_id or "") for secret in SNAPSHOT_SECRET_RE):
            continue
        models[model_id] = {
            "model_id": model_id,
            "author": author,
            "pipeline": pipeline,
            "library": library,
            "downloads": downloads,
            "downloads_all": downloads_all,
            "likes": likes,
            "created": created,
            "family": None,
        }

    relations: list[dict] = []
    for child, relation, parent in edge_rows:
        if not parent or not child or parent == child:
            continue  # 自环丢弃
        if child not in models:
            continue
        relations.append(
            {
                "parent_id": parent,
                "child_id": child,
                "relation_type": _normalize_type(relation),
                "source_field": "baseModels",
            }
        )
        models.setdefault(parent, {"model_id": parent, "ghost": True})

    family_of = _family_map()
    for model in models.values():
        if model.get("family"):
            continue
        key = (model.get("author") or model["model_id"].split("/")[0]).lower()
        model["family"] = family_of.get(key, "")

    input_hash = _file_hash(path)
    conn = connect()
    try:
        init_schema(conn)
        _write_snapshot(
            conn,
            {
                "id": sid,
                "source": f"hubstats:{path.name}",
                "snapshot_date": "2026-11-23",
                "input_hash": input_hash,
                "rule_version": config.RULE_VERSION,
                "scope_note": (
                    f"hub-stats dump 按下载量取前 {row_limit} 个带 baseModels 的模型；"
                    "关系来自模型卡声明的 base_model 标签；集合外上游以占位节点保留"
                ),
            },
        )
        _upsert_models(conn, sid, models.values())
        _insert_relations(conn, sid, relations)

        result = _result(conn, sid, "hubstats", input_hash)
        _record_import(conn, result)
        conn.commit()
        return result
    finally:
        conn.close()


def _family_map() -> dict[str, str]:
    """作者 -> 家族名，取自 model-family-tree 的派生数据；缺失时返回空表。"""
    path = config.modeltree_dir() / "dist" / "parents.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    columns = payload["columns"]
    rows = payload["rows"]
    idx_id = columns.index("id")
    idx_family = columns.index("family")
    mapping: dict[str, str] = {}
    for row in rows:
        model_id = row[idx_id]
        family = row[idx_family]
        if family:
            mapping.setdefault(model_id.split("/")[0].lower(), family)
    return mapping


# ----------------------------------------------------------------- modeltree


def import_modeltree(limit: int | None = None, snapshot_id: str | None = None) -> dict:
    """直接用 model-family-tree 的 dist/ 派生数据建库，不依赖 1.7G dump。

    边只覆盖 top 3000 上游的 top 25 下游（children_top.json 的取样范围），
    关系类型在这些边上不可知，统一记为 unknown。
    """
    base = config.modeltree_dir() / "dist"
    parents_path = base / "parents.json"
    children_path = base / "children_top.json"
    if not parents_path.exists() or not children_path.exists():
        raise not_ready(f"缺少 model-family-tree 派生数据: {base}")

    parents = json.loads(parents_path.read_text(encoding="utf-8"))
    children = json.loads(children_path.read_text(encoding="utf-8"))["children"]
    columns = parents["columns"]
    idx = {name: i for i, name in enumerate(columns)}

    row_limit = limit or 3000
    sid = snapshot_id or "modeltree-2026-11-23"

    models: dict[str, dict] = {}
    relations: list[dict] = []
    for parent_id, kids in list(children.items())[:row_limit]:
        models.setdefault(parent_id, {"model_id": parent_id})
        for child_id, downloads, _total in kids:
            models.setdefault(
                child_id,
                {
                    "model_id": child_id,
                    "downloads": downloads,
                    "author": child_id.split("/")[0],
                },
            )
            relations.append(
                {
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "relation_type": "unknown",
                    "source_field": "children_top",
                }
            )

    for row in parents["rows"]:
        model_id = row[idx["id"]]
        if model_id in models:
            models[model_id]["family"] = row[idx["family"]]

    input_hash = _file_hash(parents_path)
    conn = connect()
    try:
        init_schema(conn)
        _write_snapshot(
            conn,
            {
                "id": sid,
                "source": "modeltree:dist",
                "snapshot_date": "2026-11-23",
                "input_hash": input_hash,
                "rule_version": config.RULE_VERSION,
                "scope_note": (
                    f"取 model-family-tree children_top 前 {row_limit} 个上游，"
                    "每个上游保留下载量最高的 25 个下游；关系类型不可知，记为 unknown"
                ),
            },
        )
        _upsert_models(conn, sid, models.values())
        _insert_relations(conn, sid, relations)

        result = _result(conn, sid, "modeltree", input_hash)
        _record_import(conn, result)
        conn.commit()
        return result
    finally:
        conn.close()


def run_import(source: str, limit: int | None = None, snapshot_id: str | None = None) -> dict:
    if source == "fixtures":
        return import_fixtures(snapshot_id)
    if source == "hubstats":
        return import_hubstats(limit, snapshot_id)
    if source == "modeltree":
        return import_modeltree(limit, snapshot_id)
    raise ApiError(
        "invalid_parameter",
        f"未知数据源: {source}",
        400,
        {"allowed": ["fixtures", "hubstats", "modeltree"]},
    )
