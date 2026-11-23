"""任务 4 的验收测试：候选查询、核验记录与入图状态。

自动判定（judge）与批处理的样例测试随实现补在 `test_judge.py` / `test_batch.py`，
四类结论的固定样例见 docs/EVIDENCE_HANDOFF.md。
"""

from __future__ import annotations


def _extract(client):
    client.post("/api/extractions", json={"source": "fixtures"})


def _candidates(client, status: str | None = None):
    params = {"status": status} if status else {}
    return client.get("/api/candidates", params=params).json()


def test_declared_relations_are_not_candidates(client):
    _extract(client)
    body = _candidates(client)
    for item in body["items"]:
        assert item["origin"] == "candidate"


def test_confirm_adds_edge_to_completed_graph(client):
    _extract(client)
    candidate = _candidates(client)["items"][0]
    relation_id = candidate["relation_id"]

    before = client.get(
        "/api/graph", params={"model_id": candidate["child_id"], "direction": "both"}
    ).json()
    assert before["view"] == "declared"

    detail = client.post(
        f"/api/relations/{relation_id}/reviews",
        json={"decision": "confirmed", "note": "README 原文明确"},
    ).json()
    assert detail["relation"]["status"] == "confirmed"
    assert detail["reviews"][-1]["decision"] == "confirmed"

    after = client.get(
        "/api/graph",
        params={"model_id": candidate["child_id"], "direction": "both", "view": "completed"},
    ).json()
    assert after["view"] == "completed"
    assert len(after["edges"]) >= len(before["edges"])


def test_reject_removes_from_completed_graph(client):
    _extract(client)
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
    resp = client.post(
        f"/api/relations/{candidate['relation_id']}/reviews", json={"decision": "maybe"}
    )
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
