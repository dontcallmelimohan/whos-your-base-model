"""任务 1 的验收测试：导入、快照、数据集关联。"""

from __future__ import annotations


def test_import_history_records_every_run(client):
    before = client.get("/api/imports").json()["total"]
    client.post("/api/imports", json={"source": "fixtures"})
    body = client.get("/api/imports").json()
    assert body["total"] == before + 1
    record = body["items"][0]
    assert record["source"] == "fixtures"
    assert record["relation_count"] == 12
    assert len(record["input_hash"]) == 64  # sha256


def test_snapshot_stats_add_up(client):
    stats = client.get("/api/snapshots/demo-2026-11/stats").json()
    assert stats["model_count"] == 14
    assert stats["relation_count"] == 12  # 只数声明关系，候选单独计数
    assert stats["ghost_count"] == 1
    assert stats["family_count"] == 3
    assert stats["dataset_link_count"] == 4
    dist = {bucket["type"]: bucket["count"] for bucket in stats["type_distribution"]}
    assert sum(dist.values()) == stats["relation_count"]


def test_dataset_usage_counts_models(client):
    body = client.get("/api/datasets").json()
    top = body["items"][0]
    assert top["dataset_id"] == "HuggingFaceH4/ultrachat_200k"
    assert top["model_count"] == 2
    assert top["source_field"] == "datasets"


def test_unknown_snapshot_stats_returns_404(client):
    resp = client.get("/api/snapshots/no-such-snapshot/stats")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_health_before_any_import(client, tmp_path, monkeypatch):
    """全新数据库上 health 应返回 data_ready=false，而不是 500。"""
    from fastapi.testclient import TestClient

    from app import create_app

    monkeypatch.setenv("PLATFORM_DB", str(tmp_path / "empty.db"))
    with TestClient(create_app()) as fresh:
        body = fresh.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["data_ready"] is False
