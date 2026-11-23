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
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path

from modules.catalog.hubstats_data import prepare_tables
from shared import config, graph_read
from shared.db import connect, init_schema
from shared.errors import ApiError, invalid, not_ready

def _relation_id(snapshot_id: str, parent: str, child: str, rtype: str) -> str:
    key = f"{snapshot_id}|{parent}|{child}|{rtype}"
    return "rel_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_snapshot(conn, snapshot: dict) -> None:
    cursor = conn.execute(
        """INSERT INTO snapshots (id, source, snapshot_date, input_hash, rule_version, scope_note)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             source = excluded.source,
             snapshot_date = excluded.snapshot_date,
             input_hash = excluded.input_hash,
             rule_version = excluded.rule_version,
             scope_note = excluded.scope_note
           WHERE snapshots.rule_version <> ?""",
        (
            snapshot["id"],
            snapshot["source"],
            snapshot["snapshot_date"],
            snapshot.get("input_hash"),
            snapshot.get("rule_version", config.RULE_VERSION),
            snapshot.get("scope_note"),
            config.HUBSTATS_RULE_VERSION,
        ),
    )

    if cursor.rowcount == 0:
        raise ApiError("conflict", "该 hub-stats 快照已存在，请使用新的版本 ID", 409)


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
        (
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
        ),
    )


def _insert_relations(conn, snapshot_id: str, rows: Iterable[dict]) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO relations
             (id, snapshot_id, parent_id, child_id, relation_type, is_baseline, source_field)
           VALUES (?, ?, ?, ?, ?, 1, ?)""",
        (
            (
                _relation_id(snapshot_id, row["parent_id"], row["child_id"], row["relation_type"]),
                snapshot_id,
                row["parent_id"],
                row["child_id"],
                row["relation_type"],
                row.get("source_field"),
            )
            for row in rows
        ),
    )


def _insert_datasets(conn, snapshot_id: str, rows: Iterable[dict]) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO model_datasets
             (snapshot_id, model_id, dataset_id, source_field, raw_value)
           VALUES (?, ?, ?, ?, ?)""",
        (
            (
                snapshot_id,
                row["model_id"],
                row["dataset_id"],
                row.get("source_field"),
                row.get("raw_value"),
            )
            for row in rows
        ),
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


def hubstats_snapshot_id(source_key: str, limit: int, snapshot_date: str) -> str:
    scope = f"top{limit}" if limit else "full"
    return f"hubstats-{snapshot_date}-{config.HUBSTATS_RULE_VERSION}-{scope}-{source_key[:12]}"


def _duckdb_batches(cursor) -> Iterator[tuple]:
    while rows := cursor.fetchmany(5000):
        yield from rows


def _hubstats_models(rows: Iterable[tuple], family_by_model: dict[str, str]) -> Iterator[dict]:
    for model_id, author, pipeline, library, downloads, total_downloads, likes, created, ghost in rows:
        yield {
            "model_id": model_id,
            "author": author,
            "pipeline": pipeline,
            "library": library,
            "downloads": downloads,
            "downloads_all": total_downloads,
            "likes": likes,
            "created": created,
            "family": family_by_model.get(model_id),
            "ghost": ghost,
        }


def _hubstats_datasets(rows: Iterable[tuple[str, str]]) -> Iterator[dict]:
    for model_id, raw in rows:
        declared = json.loads(raw)
        values = declared if isinstance(declared, list) else [declared]
        for dataset_id in values:
            if isinstance(dataset_id, str) and dataset_id.strip():
                yield {
                    "model_id": model_id,
                    "dataset_id": dataset_id.strip(),
                    "source_field": "cardData.datasets",
                    "raw_value": dataset_id,
                }


def import_hubstats(
    limit: int | None = None,
    snapshot_id: str | None = None,
    *,
    path: Path | None = None,
    revision: str | None = None,
    snapshot_date: str | None = None,
    expected_hash: str | None = None,
) -> dict:
    """导入不可变的快照。limit=0 表示全量，限量时额外保留已收录的直接上游。"""
    path = path if path is not None else config.hubstats_parquet_path()
    if not path.is_file():
        raise not_ready(f"hub-stats 文件不存在: {path}", {"hint": "可从数据页同步，或设置 PLATFORM_HUBSTATS"})

    import duckdb

    row_limit = config.DEFAULT_IMPORT_LIMIT if limit is None else limit
    if row_limit < 0:
        raise invalid("limit 必须 >= 0，0 表示全量")
    input_hash = _file_hash(path)
    if expected_hash is not None and input_hash != expected_hash:
        raise ApiError("hubstats_checksum_mismatch", "hub-stats 文件校验失败，请重新同步", 502)

    source_date = snapshot_date or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()
    sid = snapshot_id or hubstats_snapshot_id(revision or input_hash, row_limit, source_date)
    source = f"hubstats:{revision}" if revision else f"hubstats:{path.name}"
    scope = f"按下载量取前 {row_limit:,} 个模型，另收录它们可找到的直接上游" if row_limit else "全量模型"
    scope_note = f"{scope}，缺少记录的上游保留为占位节点。关系来自 baseModels 或 base_model 标签。"
    if snapshot_date is None:
        scope_note += "日期取自本地文件修改时间。"

    conn = connect()
    con = duckdb.connect(config={"memory_limit": "768MB", "threads": 4})
    try:
        init_schema(conn)
        result = _existing_hubstats(conn, sid, input_hash, scope_note)
        if result is not None:
            return result

        prepare_tables(con, path, row_limit)
        if not con.execute("SELECT 1 FROM selected_models LIMIT 1").fetchone():
            raise not_ready("hub-stats 文件里没有可导入的模型")

        conn.execute("BEGIN IMMEDIATE")
        result = _existing_hubstats(conn, sid, input_hash, scope_note)
        if result is not None:
            return result
        _write_snapshot(conn, {
            "id": sid,
            "source": source,
            "snapshot_date": source_date,
            "input_hash": input_hash,
            "rule_version": config.HUBSTATS_RULE_VERSION,
            "scope_note": scope_note,
        })

        cursor = con.execute("""
            SELECT id, author, pipeline_tag, library_name, downloads, downloadsAllTime, likes,
                   CAST(createdAt AS VARCHAR), false
            FROM catalog_models
            UNION ALL
            SELECT DISTINCT parent_id, NULL, NULL, NULL, NULL, NULL, NULL, NULL, true
            FROM catalog_edges ANTI JOIN catalog_models ON catalog_edges.parent_id = catalog_models.id
        """)
        _upsert_models(conn, sid, _hubstats_models(_duckdb_batches(cursor), _family_map()))
        cursor = con.execute("SELECT parent_id, child_id, relation_type, source_field FROM catalog_edges")
        _insert_relations(conn, sid, (
            {"parent_id": parent, "child_id": child, "relation_type": kind, "source_field": field}
            for parent, child, kind, field in _duckdb_batches(cursor)
        ))
        cursor = con.execute("SELECT id, datasets FROM catalog_metadata WHERE datasets IS NOT NULL")
        _insert_datasets(conn, sid, _hubstats_datasets(_duckdb_batches(cursor)))
        cursor = con.execute("""
            SELECT id, license, license_name, license_link FROM catalog_metadata
            WHERE coalesce(license, license_name, license_link) IS NOT NULL
        """)
        conn.executemany(
            "INSERT INTO catalog_licenses VALUES (?, ?, ?, ?, ?)",
            ((sid, *row) for row in _duckdb_batches(cursor)),
        )
        result = _result(conn, sid, "hubstats", input_hash)
        _record_import(conn, result)
        conn.commit()
        return result
    except duckdb.Error as exc:
        raise not_ready("无法读取 hub-stats 文件，请检查 Parquet 格式或可用磁盘空间") from exc
    finally:
        con.close()
        conn.close()


def _existing_hubstats(conn, sid: str, input_hash: str, scope_note: str) -> dict | None:
    row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (sid,)).fetchone()
    if row is None:
        return None
    if (row["input_hash"], row["rule_version"], row["scope_note"]) != (
        input_hash, config.HUBSTATS_RULE_VERSION, scope_note,
    ):
        raise ApiError("conflict", "数据版本已存在且导入范围或来源不同，请使用新的版本 ID", 409)
    return _result(conn, sid, "hubstats", input_hash)


def _family_map() -> dict[str, str]:
    """精确模型 ID 对应的家族，作为可选的目录标签。"""
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
            mapping[model_id] = family
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
