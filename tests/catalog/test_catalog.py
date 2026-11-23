"""任务 1 的验收测试：搜索、详情、重复导入。"""

from __future__ import annotations


def test_health_reports_seeded_snapshot(client):
    body = client.get("/api/health").json()
    assert body["data_ready"] is True
    assert body["snapshot_id"] == "demo-2026-11"
    assert body["relation_count"] == 12


def test_snapshots_list_shape(client):
    body = client.get("/api/snapshots").json()
    assert body["total"] >= 1
    snapshot = body["items"][0]
    assert snapshot["id"] == "demo-2026-11"
    assert snapshot["rule_version"] == "rules-v2"
    assert snapshot["scope_note"]


def test_search_by_name_and_pagination(client):
    body = client.get("/api/models", params={"q": "qwen", "page_size": 2}).json()
    assert body["total"] == 5  # Qwen 系 5 个模型
    assert len(body["items"]) == 2
    assert body["page_size"] == 2
    assert body["items"][0]["downloads"] >= body["items"][1]["downloads"]


def test_search_no_result_returns_empty_list(client):
    body = client.get("/api/models", params={"q": "no-such-model-xyz"}).json()
    assert body["total"] == 0
    assert body["items"] == []


def test_search_filters_by_family_and_ghost(client):
    family = client.get("/api/models", params={"family": "llama-3.2"}).json()
    assert family["total"] == 4
    ghost_only = client.get("/api/models", params={"include_ghost": False, "q": "bloom"}).json()
    assert ghost_only["total"] == 1  # 只剩 someone/bloom-finetune，占位上游被过滤掉


def test_model_detail_with_datasets(client):
    body = client.get("/api/model", params={"model_id": "Qwen/Qwen2.5-7B-Instruct"}).json()
    assert body["model_id"] == "Qwen/Qwen2.5-7B-Instruct"
    assert body["snapshot_id"] == "demo-2026-11"
    assert body["family"] == "qwen2.5"
    assert body["ghost"] is False
    assert {link["dataset_id"] for link in body["datasets"]} == {
        "HuggingFaceH4/ultrachat_200k",
        "openai/gsm8k",
    }
    # F8：只展示记录中的关联，不推断训练用途
    assert all(link["source_field"] == "datasets" for link in body["datasets"])


def test_model_not_found(client):
    resp = client.get("/api/model", params={"model_id": "nobody/missing"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_repeat_import_does_not_duplicate(client):
    first = client.post("/api/imports", json={"source": "fixtures"}).json()
    second = client.post("/api/imports", json={"source": "fixtures"}).json()
    assert first["model_count"] == second["model_count"]
    assert first["relation_count"] == second["relation_count"]
    assert second["relation_count"] == 12


def test_unknown_import_source_is_rejected(client):
    resp = client.post("/api/imports", json={"source": "crawl"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_parameter"
