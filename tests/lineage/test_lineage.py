"""任务 2 的验收测试：上下游、深度、环、截断、占位节点。"""

from __future__ import annotations


def _graph(client, **params):
    return client.get("/api/graph", params=params)


def test_upstream_depth_two(client):
    body = _graph(client, model_id="someone/Merge-7B", direction="upstream", depth=2).json()
    assert {node["id"] for node in body["nodes"]} == {
        "someone/Merge-7B",
        "Qwen/Qwen2.5-Coder-7B",
        "meta-llama/Llama-3.2-1B-Instruct",
        "Qwen/Qwen2.5-7B",
        "meta-llama/Llama-3.2-1B",
    }
    assert body["node_count"] == 5
    assert body["edge_count"] == 4
    assert body["truncated"] is False


def test_depth_one_only_returns_direct_parents(client):
    body = _graph(client, model_id="someone/Merge-7B", direction="upstream", depth=1).json()
    assert {node["id"] for node in body["nodes"]} == {
        "someone/Merge-7B",
        "Qwen/Qwen2.5-Coder-7B",
        "meta-llama/Llama-3.2-1B-Instruct",
    }


def test_downstream_direction(client):
    body = _graph(client, model_id="Qwen/Qwen2.5-7B", direction="downstream").json()
    assert {edge["target"] for edge in body["edges"]} == {
        "Qwen/Qwen2.5-7B-Instruct",
        "Qwen/Qwen2.5-Coder-7B",
        "TheBloke/Qwen2.5-7B-GGUF",
        "someone/lora-adapter-qwen",
    }


def test_cycle_does_not_loop_forever(client):
    body = _graph(client, model_id="test/cycle-a", direction="both", depth=2).json()
    assert {node["id"] for node in body["nodes"]} == {"test/cycle-a", "test/cycle-b"}
    assert body["edge_count"] == 2


def test_truncation_flag(client):
    body = _graph(client, model_id="Qwen/Qwen2.5-7B", direction="downstream", limit=3).json()
    assert body["truncated"] is True
    assert body["node_count"] == 3
    assert body["node_limit"] == 3


def test_ghost_node_kept(client):
    body = _graph(client, model_id="someone/bloom-finetune", direction="upstream").json()
    ghost = [node for node in body["nodes"] if node["id"] == "bigscience/bloom-560m"]
    assert len(ghost) == 1
    assert ghost[0]["ghost"] is True
    assert ghost[0]["pipeline"] is None


def test_relation_type_filter(client):
    body = _graph(
        client, model_id="Qwen/Qwen2.5-7B", direction="downstream", relation_type="quantized"
    ).json()
    assert body["edge_count"] == 1
    assert body["edges"][0]["type"] == "quantized"


def test_invalid_relation_type_rejected(client):
    resp = _graph(client, model_id="Qwen/Qwen2.5-7B", relation_type="trained_on")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_parameter"


def test_invalid_depth_rejected(client):
    resp = _graph(client, model_id="Qwen/Qwen2.5-7B", depth=3)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_parameter"


def test_unknown_root_rejected(client):
    resp = _graph(client, model_id="nobody/missing")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_edge_carries_source_field(client):
    body = _graph(client, model_id="someone/Merge-7B", direction="upstream").json()
    assert {edge["source_field"] for edge in body["edges"]} == {"baseModels"}
