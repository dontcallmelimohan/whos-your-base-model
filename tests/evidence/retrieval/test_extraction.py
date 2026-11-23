"""任务 3 的验收测试：本地模型卡 → 候选关系 + 可回指的证据。"""

from __future__ import annotations


def _run(client):
    return client.post("/api/extractions", json={"source": "fixtures"}).json()


def _candidates(client, status: str | None = None):
    params = {"status": status} if status else {}
    return client.get("/api/candidates", params=params).json()


def test_extraction_creates_candidates_with_evidence(client):
    result = _run(client)
    assert result["snapshot_id"] == "demo-2026-11"
    assert result["scanned_models"] >= 1
    assert result["skipped_declared"] >= 1  # 正文提到的上游已在声明里，不重复建候选

    body = _candidates(client)
    assert body["total"] >= 2
    first = body["items"][0]
    assert first["origin"] == "candidate"
    assert first["evidence_count"] >= 1


def test_extraction_is_idempotent(client):
    _run(client)
    first = _candidates(client)["total"]
    _run(client)
    assert _candidates(client)["total"] == first


def test_evidence_keeps_quote_locator_and_source(client):
    """evidence 必须能回指：原文、文件、行号、版本字段都在。"""
    _run(client)
    candidate = _candidates(client)["items"][0]
    detail = client.get(f"/api/relations/{candidate['relation_id']}").json()
    evidence = detail["evidence"][0]

    assert evidence["quote"]
    assert evidence["locator"].startswith("L")
    assert evidence["source_path"]
    assert evidence["source_type"] in ("model_card_text", "model_card_yaml", "config")
    assert "revision" in evidence  # 没有 commit SHA 时为 null，不能省略


def test_unknown_source_is_reported_not_silently_empty(client):
    resp = client.post("/api/extractions", json={"source": "hubstats"})
    assert resp.status_code == 409
    body = resp.json()["error"]
    assert body["code"] == "data_not_ready"
    assert "allowed" in body["detail"]
