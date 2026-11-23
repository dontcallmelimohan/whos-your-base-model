"""跨模块契约测试：错误格式、常量、图与分析的计数一致性。"""

from __future__ import annotations


def test_error_shape_is_stable(client):
    resp = client.get("/api/model", params={"model_id": "nobody/missing"})
    body = resp.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "detail"}
    assert isinstance(body["error"]["message"], str)


def test_meta_exposes_limits_and_relation_types(client):
    body = client.get("/api/meta").json()
    assert body["max_depth"] == 2
    assert body["default_graph_nodes"] == 100
    assert body["max_page_size"] == 100
    assert body["relation_types"] == ["finetune", "adapter", "quantized", "merge", "unknown"]


def test_graph_agrees_with_analysis_edge_counts(client):
    """同一个快照：从排名第一的上游展开两层，边数不超过分析口径的关系总数。"""
    analysis = client.get("/api/analysis").json()
    root = analysis["top_upstream"][0]["model_id"]
    body = client.get(
        "/api/graph",
        params={"model_id": root, "direction": "downstream", "depth": 2, "limit": 200},
    ).json()
    assert body["snapshot_id"] == analysis["snapshot_id"]
    assert body["truncated"] is False
    assert body["edge_count"] <= analysis["metrics"]["unique_pair_count"]


def test_graph_nodes_carry_analysis_family(client):
    body = client.get(
        "/api/graph", params={"model_id": "Qwen/Qwen2.5-7B", "direction": "downstream"}
    ).json()
    node = next(item for item in body["nodes"] if item["id"] == "Qwen/Qwen2.5-7B-Instruct")
    assert node["family"] == "qwen2.5"
    assert node["ghost"] is False
