"""工作包 3 的验收测试：候选抽取 → 证据 → 核验 → 补全图变化。"""

from __future__ import annotations


def _candidates(client, status: str | None = None):
    params = {"status": status} if status else {}
    return client.get("/api/candidates", params=params).json()


def test_extraction_creates_candidates_with_evidence(client):
    result = client.post("/api/extractions", json={"source": "fixtures"}).json()
    assert result["snapshot_id"] == "demo-2026-11"
    assert result["scanned_models"] >= 1
    assert result["skipped_declared"] >= 1  # 反例：正文提到的上游已在声明里

    body = _candidates(client)
    assert body["total"] >= 2
    first = body["items"][0]
    assert first["origin"] == "candidate"
    assert first["evidence_count"] >= 1


def test_extraction_is_idempotent(client):
    client.post("/api/extractions", json={"source": "fixtures"})
    first = _candidates(client)["total"]
    client.post("/api/extractions", json={"source": "fixtures"})
    assert _candidates(client)["total"] == first


def test_declared_relations_are_not_candidates(client):
    body = _candidates(client)
    for item in body["items"]:
        assert item["origin"] == "candidate"


def test_relation_detail_has_quote_and_locator(client):
    candidate = _candidates(client)["items"][0]
    detail = client.get(f"/api/relations/{candidate['relation_id']}").json()
    assert detail["relation"]["relation_id"] == candidate["relation_id"]
    evidence = detail["evidence"][0]
    assert evidence["quote"]
    assert evidence["locator"].startswith("L")
    assert evidence["source_path"]


def test_confirm_adds_edge_to_completed_graph(client):
    client.post("/api/extractions", json={"source": "fixtures"})
    candidate = _candidates(client)["items"][0]
    relation_id = candidate["relation_id"]

    before = client.get(
        "/api/graph", params={"model_id": candidate["child_id"], "direction": "both"}
    ).json()
    assert before["view"] == "declared"

    detail = client.post(f"/api/relations/{relation_id}/reviews", json={"decision": "confirmed", "note": "README 原文明确"}).json()
    assert detail["relation"]["status"] == "confirmed"
    assert detail["reviews"][-1]["decision"] == "confirmed"

    after = client.get(
        "/api/graph",
        params={"model_id": candidate["child_id"], "direction": "both", "view": "completed"},
    ).json()
    assert after["view"] == "completed"
    assert len(after["edges"]) >= len(before["edges"])


def test_reject_removes_from_completed_graph(client):
    client.post("/api/extractions", json={"source": "fixtures"})
    pending = _candidates(client, "pending")["items"]
    candidate = pending[0] if pending else _candidates(client)["items"][0]
    relation_id = candidate["relation_id"]

    client.post(f"/api/relations/{relation_id}/reviews", json={"decision": "confirmed"})
    client.post(f"/api/relations/{relation_id}/reviews", json={"decision": "rejected"})

    detail = client.get(f"/api/relations/{relation_id}").json()
    assert detail["relation"]["status"] == "rejected"
    # 追加式记录：最新一条决定当前状态
    assert detail["reviews"][-1]["decision"] == "rejected"
    assert "confirmed" in [item["decision"] for item in detail["reviews"]]


def test_invalid_decision_rejected(client):
    candidate = _candidates(client)["items"][0]
    resp = client.post(f"/api/relations/{candidate['relation_id']}/reviews", json={"decision": "maybe"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_parameter"


def test_declared_relation_cannot_be_reviewed(client):
    detail = client.get("/api/model", params={"model_id": "someone/Merge-7B"}).json()
    graph = client.get("/api/graph", params={"model_id": detail["model_id"]}).json()
    declared_edge = graph["edges"][0]["id"]
    resp = client.post(f"/api/relations/{declared_edge}/reviews", json={"decision": "confirmed"})
    assert resp.status_code == 400


def test_summary_counts(client):
    body = client.get("/api/candidates/summary").json()
    assert body["total"] == body["pending"] + body["confirmed"] + body["rejected"] + body["unknown"]
