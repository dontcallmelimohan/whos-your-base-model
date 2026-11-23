"""同步流程用本地 Parquet 检查，避免测试依赖在线数据和网络。"""

from pathlib import Path
from shutil import copyfile

import duckdb
import pytest

from modules.catalog import hubstats_sync
from modules.catalog.importer import _file_hash


@pytest.fixture()
def remote_parquet(tmp_path):
    path = tmp_path / "remote.parquet"
    with duckdb.connect() as conn:
        conn.execute("""
            CREATE TABLE dump (
                _id VARCHAR, id VARCHAR, author VARCHAR DEFAULT 'org', pipeline_tag VARCHAR DEFAULT 'text-generation',
                library_name VARCHAR DEFAULT 'transformers', downloads BIGINT, downloadsAllTime BIGINT DEFAULT 1000,
                likes BIGINT DEFAULT 1, createdAt TIMESTAMP DEFAULT '2026-11-01',
                lastModified TIMESTAMP DEFAULT '2026-11-12',
                baseModels STRUCT(relation VARCHAR, models STRUCT(id VARCHAR)[]),
                tags VARCHAR[], cardData VARCHAR
            )
        """)
        conn.execute("""
            INSERT INTO dump (_id, id, downloads, baseModels, tags, cardData) VALUES
            ('a', 'org/fine', 200, {'relation': 'finetune', 'models': [{'id': 'org/root'}]},
             ['base_model:org/root'], '{"datasets":["org/data"],"license":"apache-2.0"}'),
            ('b', 'org/adapter', 100, NULL,
             ['base_model:org/root','base_model:adapter:org/root','base_model:org/missing'], '{}'),
            ('c', 'org/root', 10, NULL, [], '{"license":"other","license_name":"Custom"}'),
            ('d', 'org/independent', 5, NULL, [], 'invalid')
        """)
        conn.execute("COPY dump TO (?) (FORMAT PARQUET)", [str(path)])
    return path


def test_sync_versions_are_reproducible(client, monkeypatch, tmp_path, remote_parquet):
    monkeypatch.setenv("PLATFORM_DB", str(tmp_path / "sync.db"))
    digest = _file_hash(remote_parquet)
    version = ["a" * 40, "2026-11-24", digest]
    monkeypatch.setattr(hubstats_sync, "latest_file", lambda: tuple(version))
    downloads = []

    def download(revision: str, destination: Path):
        downloads.append(revision)
        copyfile(remote_parquet, destination)

    monkeypatch.setattr(hubstats_sync, "download_file", download)
    created = client.post("/api/hubstats/sync", json={"limit": 2})
    assert created.status_code == 200, created.text
    sample = created.json()
    assert sample["updated"] and sample["model_count"] == 4 and sample["relation_count"] == 3

    unchanged = client.post("/api/hubstats/sync", json={"limit": 2}).json()
    assert not unchanged["updated"] and unchanged["snapshot_id"] == sample["snapshot_id"]
    assert downloads == ["a" * 40]
    conflict = client.post("/api/imports", json={"source": "fixtures", "snapshot_id": sample["snapshot_id"]})
    assert conflict.status_code == 409

    fine = client.get("/api/model", params={"model_id": "org/fine"}).json()
    assert fine["datasets"][0]["dataset_id"] == "org/data"
    assert fine["license_declaration"]["license"] == "apache-2.0"
    assert fine["declared_parents"] == [
        {"model_id": "org/root", "relation_type": "finetune", "source_field": "baseModels"}
    ]
    adapter = client.get("/api/model", params={"model_id": "org/adapter"}).json()
    assert {(p["model_id"], p["relation_type"]) for p in adapter["declared_parents"]} == {
        ("org/root", "adapter"), ("org/missing", "unknown"),
    }
    root = client.get("/api/model", params={"model_id": "org/root"}).json()
    assert not root["ghost"] and root["license_declaration"]["license_name"] == "Custom"

    full = client.post("/api/hubstats/sync", json={"limit": 0}).json()
    assert full["updated"] and full["model_count"] == 5
    assert full["snapshot_id"] != sample["snapshot_id"]
    assert client.get("/api/model", params={"model_id": "org/independent"}).status_code == 200
    assert client.get("/api/model", params={
        "model_id": "org/independent", "snapshot_id": sample["snapshot_id"],
    }).status_code == 404

    version[:] = ["b" * 40, "2026-11-25", "0" * 64]
    rejected = client.post("/api/hubstats/sync", json={"limit": 2})
    assert rejected.status_code == 502
    assert rejected.json()["error"]["code"] == "hubstats_checksum_mismatch"
    assert client.get("/api/health").json()["snapshot_id"] == full["snapshot_id"]
    assert client.get("/api/imports").json()["total"] == 2
    assert not list(tmp_path.glob("hubstats-*"))

    version[2] = digest
    latest = client.post("/api/hubstats/sync", json={"limit": 2}).json()
    assert latest["updated"]
    assert client.get("/api/health").json()["snapshot_id"] == latest["snapshot_id"]
    history = client.get("/api/snapshots").json()["items"]
    assert len(history) == 3
    assert history[0]["source"] == "hubstats:" + "b" * 40
