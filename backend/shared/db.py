"""SQLite 连接与迁移。

迁移文件放在 shared/migrations/，按文件名排序依次执行，每个任务只加自己的编号：

    001_init.sql              公共骨架（已占用）
    002_evidence.sql          证据表（任务 4，已占用）
    003_verification_*.sql    任务 4：判定 / 核验记录
    010_catalog_*.sql         任务 1：目录与数据
    020_lineage_*.sql         任务 2：谱系
    030_analysis_*.sql        任务 1：分析

规则：只加表、只给自己的表加字段；改别人的表 = 改契约，要四人同意。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from shared import config

MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or config.db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def init_schema(conn: sqlite3.Connection) -> list[str]:
    """按文件名顺序执行未应用过的迁移。

    用 schema_migrations 记账，因为 ALTER TABLE ADD COLUMN 不是幂等的：
    每次启动都重放 002 会报 duplicate column。
    """
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
               name TEXT PRIMARY KEY,
               applied_at TEXT NOT NULL DEFAULT (datetime('now'))
           )"""
    )
    done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations").fetchall()}

    applied: list[str] = []
    for path in migration_files():
        if path.name in done:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations (name) VALUES (?)", (path.name,))
        applied.append(path.name)
    conn.commit()
    return applied


def init_database(path: Path | None = None) -> Path:
    target = path or config.db_path()
    conn = connect(target)
    try:
        init_schema(conn)
    finally:
        conn.close()
    return target


def get_conn() -> Iterator[sqlite3.Connection]:
    """FastAPI 依赖：每个请求一个连接，用完关闭。"""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def tables_present(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}
