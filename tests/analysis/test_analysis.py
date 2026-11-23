"""任务 1 的验收测试：固定样例上的可核对数值。

样例事实（fixtures/seed.json）：
    14 个模型（其中 1 个 ghost）+ 12 条关系，唯一上下游对也是 12
    类型分布 finetune 7 / quantized 2 / merge 2 / adapter 1
    有下游的模型 8 个，没有上游的模型 3 个，家族 3 个，环上节点 2 个
    上游排名第一 Qwen/Qwen2.5-7B：直接下游 4，可达后代 5
"""

from __future__ import annotations


def test_metrics_are_hand_checkable(client):
    metrics = client.get("/api/analysis").json()["metrics"]
    assert metrics["model_count"] == 14
    assert metrics["edge_count"] == 12
    assert metrics["unique_pair_count"] == 12
    assert metrics["parent_count"] == 8
    assert metrics["root_count"] == 3
    assert metrics["ghost_count"] == 1
    assert metrics["family_count"] == 3
    assert metrics["cyclic_node_count"] == 2


def test_type_distribution(client):
    body = client.get("/api/analysis").json()
    dist = {bucket["type"]: bucket["count"] for bucket in body["type_distribution"]}
    assert dist == {"finetune": 7, "quantized": 2, "merge": 2, "adapter": 1}
    assert sum(dist.values()) == body["metrics"]["edge_count"]


def test_top_upstream_distinguishes_direct_and_total(client):
    top = client.get("/api/analysis").json()["top_upstream"]
    assert top[0]["model_id"] == "Qwen/Qwen2.5-7B"
    assert top[0]["direct"] == 4
    assert top[0]["total"] == 5
    # meta-llama/Llama-3.2-1B 只有一个直接下游，但可达后代有 4 个
    llama = next(item for item in top if item["model_id"] == "meta-llama/Llama-3.2-1B")
    assert llama["direct"] == 1
    assert llama["total"] == 4
    # 榜单按「直接下游数」排序，`total` 是附带的可达后代数
    assert top == sorted(top, key=lambda item: (-item["direct"], item["model_id"]))


def test_family_distribution(client):
    families = {item["family"]: item["models"] for item in client.get("/api/analysis").json()["family_distribution"]}
    assert families["qwen2.5"] == 5
    assert families["llama-3.2"] == 4


def test_analysis_carries_scope_and_version(client):
    body = client.get("/api/analysis").json()
    assert body["snapshot_id"] == "demo-2026-11"
    assert body["rule_version"] == "rules-v2"
    assert body["scope_note"]


def test_cases_only_reference_existing_models(client):
    body = client.get("/api/analysis").json()
    assert body["cases"]
    for case in body["cases"]:
        resp = client.get("/api/model", params={"model_id": case["model_id"]})
        assert resp.status_code == 200, case


def test_concentration_and_quality(client):
    body = client.get("/api/analysis").json()
    concentration = body["concentration"]
    # 12 条关系，最大上游 4 个直接下游 → HHI = (4/12)² + (2/12)² + 6×(1/12)²
    assert concentration["parent_count"] == 8
    assert 0 < concentration["hhi"] <= 1
    assert 0 < concentration["top10_share"] <= 1
    assert concentration["hhi_scaled"] == round(concentration["hhi"] * 10000, 1)

    quality = body["data_quality"]
    # 样例里 8 个上游，其中 bigscience/bloom-560m 是 ghost
    assert quality["ghost_parent_count"] == 1
    assert quality["ghost_ratio"] == 0.125
    assert quality["cyclic_node_count"] == 2
