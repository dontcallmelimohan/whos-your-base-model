"""工作包 4 的验收测试：补全前后对比与 CSV 导出。"""

from __future__ import annotations


def test_diff_reports_added_edge_after_confirm(client):
    client.post("/api/extractions", json={"source": "fixtures"})
    before = client.get("/api/diff").json()
    assert before["added_edges"] == []
    assert before["pending_count"] >= 1

    candidate = client.get("/api/candidates", params={"status": "pending"}).json()["items"][0]
    client.post(f"/api/relations/{candidate['relation_id']}/reviews", json={"decision": "confirmed"})

    after = client.get("/api/diff").json()
    assert len(after["added_edges"]) == 1
    edge = after["added_edges"][0]
    assert edge["relation_id"] == candidate["relation_id"]
    assert after["metrics"]["edge_count"]["delta"] == 1
    assert after["metrics"]["edge_count"]["completed"] == before["metrics"]["edge_count"]["declared"] + 1


def test_diff_metrics_have_declared_and_completed(client):
    body = client.get("/api/diff").json()
    for name in ("edge_count", "unique_pair_count", "parent_count", "hhi_scaled", "top10_share"):
        metric = body["metrics"][name]
        assert set(metric) == {"declared", "completed", "delta"}


def test_csv_export_contains_snapshot_and_rows(client):
    resp = client.get("/api/analysis/export.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    text = resp.text
    assert "# snapshot_id=demo-2026-11" in text
    assert "# view=declared" in text
    lines = [line for line in text.strip().splitlines() if not line.startswith("#")]
    assert lines[0] == "rank,model_id,family,direct,total,share_of_edges"
    assert len(lines) >= 3  # 表头 + 至少两行
    first_row = lines[1].split(",")
    assert first_row[1] == "Qwen/Qwen2.5-7B"


def test_csv_export_respects_view(client):
    declared = client.get("/api/analysis/export.csv").text
    completed = client.get("/api/analysis/export.csv", params={"view": "completed"}).text
    assert "# view=declared" in declared
    assert "# view=completed" in completed
