import sqlite3

from modules.catalog.trends import snapshot_trends


def test_snapshot_trends_count_each_child_once_per_family():
    with sqlite3.connect(":memory:") as conn:
        conn.executescript("""
            CREATE TABLE models (snapshot_id TEXT, model_id TEXT, family TEXT, created TEXT);
            CREATE TABLE relations (snapshot_id TEXT, parent_id TEXT, child_id TEXT, is_baseline INTEGER);
            INSERT INTO models VALUES
                ('s', 'root1', 'alpha', NULL), ('s', 'root2', 'alpha', NULL),
                ('s', 'other', 'beta', NULL), ('s', 'november', NULL, '2026-11-12'),
                ('s', 'old', NULL, '2024-10-20'), ('s', 'undated', NULL, NULL),
                ('s', 'after-cutoff', NULL, '2026-11-30'), ('s', 'inferred', NULL, '2026-11-02');
            INSERT INTO relations VALUES
                ('s', 'root1', 'november', 1), ('s', 'root2', 'november', 1),
                ('s', 'other', 'november', 1), ('s', 'root1', 'old', 1),
                ('s', 'root1', 'undated', 1), ('s', 'root1', 'after-cutoff', 1),
                ('s', 'root1', 'inferred', 0);
        """)
        result = snapshot_trends(conn, {"id": "s", "snapshot_date": "2026-11-23"})
    assert len(result.months) == 24
    assert result.months[0] == "2024-12"
    alpha, beta = result.series
    assert (alpha.family, alpha.before_window, sum(alpha.monthly), alpha.monthly[-1], alpha.undated) == (
        "alpha", 1, 1, 1, 1,
    )
    assert beta.monthly[-1] == 1


def test_catalog_sort_both_directions(client):
    for key in ("downloads", "downloads_all", "likes", "created", "model_id"):
        for ascending in (True, False):
            response = client.get("/api/models", params={"sort": key, "ascending": ascending})
            assert response.status_code == 200
            values = [row[key] for row in response.json()["items"]]
            present = [value for value in values if value is not None]
            assert values == sorted(present, reverse=not ascending) + [None] * (len(values) - len(present))
