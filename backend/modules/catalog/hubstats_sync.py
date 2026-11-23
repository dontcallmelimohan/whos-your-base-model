"""同步 hub-stats 的模型文件，并保留 SQLite 中的历史快照。"""

from __future__ import annotations

import json
import logging
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
from urllib.request import urlopen

from modules.catalog.importer import _result, hubstats_snapshot_id, import_hubstats
from shared import config
from shared.db import connect, init_schema
from shared.errors import ApiError, invalid

HUBSTATS_URL = "https://huggingface.co/datasets/cfahlgren1/hub-stats"
HUBSTATS_TREE = "https://huggingface.co/api/datasets/cfahlgren1/hub-stats/tree/main?expand=true"
logger = logging.getLogger(__name__)


def latest_file() -> tuple[str, str, str]:
    with urlopen(HUBSTATS_TREE, timeout=20) as response:
        files = json.load(response)
    file = next(entry for entry in files if entry["path"] == "models.parquet")
    revision = file["lastCommit"]["id"]
    date = datetime.fromisoformat(file["lastCommit"]["date"]).date().isoformat()
    checksum = file["lfs"]["oid"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError("invalid hub-stats metadata")
    return revision, date, checksum


def download_file(revision: str, destination: Path) -> None:
    url = f"{HUBSTATS_URL}/resolve/{revision}/models.parquet"
    with urlopen(url, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)


def sync_hubstats(limit: int | None = None) -> dict:
    row_limit = config.DEFAULT_IMPORT_LIMIT if limit is None else limit
    if row_limit < 0:
        raise invalid("limit 必须 >= 0，0 表示全量")

    # 独立锁文件让 CLI 与 Web 共用互斥锁，下载期间主数据库仍可读写。
    database = config.db_path()
    database.parent.mkdir(parents=True, exist_ok=True)
    lock = sqlite3.connect(database.with_name(f"{database.stem}.hubstats-sync.db"), timeout=0)
    try:
        try:
            lock.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError as exc:
            if exc.sqlite_errorcode != sqlite3.SQLITE_BUSY:
                raise
            raise ApiError("conflict", "正在同步 hub-stats，请稍后刷新数据页", 409) from exc

        revision, date, checksum = latest_file()
        snapshot_id = hubstats_snapshot_id(revision, row_limit, date)
        conn = connect()
        try:
            init_schema(conn)
            existing = conn.execute(
                "SELECT input_hash FROM snapshots WHERE id = ?", (snapshot_id,)
            ).fetchone()
            if existing is not None:
                if existing["input_hash"] != checksum:
                    raise ApiError("conflict", "该快照的校验值与 Hugging Face 不一致", 409)
                return {**_result(conn, snapshot_id, "hubstats", checksum), "updated": False}
        finally:
            conn.close()

        with TemporaryDirectory(prefix="hubstats-", dir=database.parent) as temp_dir:
            destination = Path(temp_dir) / "models.parquet"
            download_file(revision, destination)
            result = import_hubstats(
                row_limit, path=destination, revision=revision,
                snapshot_date=date, expected_hash=checksum,
            )
        return {**result, "updated": True}
    except (URLError, OSError, ValueError, TypeError, KeyError, StopIteration) as exc:
        logger.warning("hub-stats sync failed (%s)", type(exc).__name__)
        raise ApiError("hubstats_sync_failed", "无法同步 hub-stats，请检查网络及可用磁盘空间后重试", 502) from exc
    finally:
        lock.close()
