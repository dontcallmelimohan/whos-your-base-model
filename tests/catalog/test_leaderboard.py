from collections import defaultdict

from modules.catalog.leaderboard import descendants


def test_descendants_deduplicate_merges_and_exclude_the_root_from_cycles():
    children = {
        "base": {"left", "right"}, "left": {"merge"}, "right": {"merge"},
        "loop_a": {"loop_b"}, "loop_b": {"loop_a", "merge"},
    }
    parents = defaultdict(set)
    for parent, nodes in children.items():
        for child in nodes:
            parents[child].add(parent)

    result = descendants(children, parents, {"merge", "right"})
    assert result["base"] == (3, 2)
    assert result["left"] == (1, 1)
    assert result["loop_a"] == (2, 1)
    assert result["loop_b"] == (2, 1)


def test_board_search_filters_and_paginates_fixture_snapshot(client):
    endpoint = "/api/catalog/leaderboard"
    body = client.get(endpoint, params={"page_size": 1}).json()
    assert body["total"] > 1 and len(body["items"]) == 1
    first = body["items"][0]
    assert first["total"] >= first["direct"] > 0
    assert first["total"] >= first["recent"]

    filtered = client.get(endpoint, params={
        "family": "llama-3.2", "q": "llama", "include_ghost": False, "sort": "direct",
    }).json()
    assert filtered["items"] and "llama-3.2" in filtered["families"]
    assert all(row["family"] == "llama-3.2" and not row["ghost"] for row in filtered["items"])
    direct = [row["direct"] for row in filtered["items"]]
    assert direct == sorted(direct, reverse=True)
