"""pytest 公共夹具：每个测试会话用独立临时数据库，互不污染。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def seeded_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    db = tmp_path_factory.mktemp("platform-db") / "test.db"
    os.environ["PLATFORM_DB"] = str(db)
    os.environ.setdefault("PLATFORM_DATA_DIR", str(db.parent))

    from modules.catalog.importer import run_import
    from shared.db import init_database

    init_database()
    run_import("fixtures")
    return db


@pytest.fixture()
def client(seeded_db: Path):
    from fastapi.testclient import TestClient

    from app import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
