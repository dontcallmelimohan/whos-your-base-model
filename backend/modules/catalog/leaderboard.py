"""Compute the declared lineage leaderboard for a catalog snapshot.

Descendant closure adapted from model-family-tree/modeltree/graph.py.
Copyright (c) 2026 Hesham Haroon, MIT. See THIRD_PARTY_NOTICES.md.
"""

from collections import Counter, defaultdict, deque
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Literal

from pydantic import BaseModel, Field

from shared.db import connect

_cache_lock = Lock()

Ranking = Literal["total", "direct", "recent", "finetune", "adapter", "quantized", "merge", "model_id"]


class BoardRow(BaseModel):
    model_id: str
    family: str | None
    ghost: bool
    total: int
    direct: int
    recent: int
    finetune: int
    adapter: int
    quantized: int
    merge: int


class BoardPage(BaseModel):
    items: list[BoardRow]
    total: int
    families: list[str] = Field(default_factory=list)


def _reachable(root: str, children: dict[str, set[str]]) -> set[str]:
    seen = {root}
    queue = deque([root])
    while queue:
        node = queue.popleft()
        for child in children.get(node, ()):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    seen.remove(root)
    return seen


def descendants(
    children: dict[str, set[str]], parents: dict[str, set[str]], recent: set[str],
) -> dict[str, tuple[int, int]]:
    """Fold from leaves toward roots. For nodes blocked by cycles, count reachable nodes."""
    remaining = {node: len(kids) for node, kids in children.items()}
    consumers = {node: len(links) for node, links in parents.items()}
    queue = deque(node for node in parents if node not in children)
    closure: dict[str, set[str]] = {}
    counts: dict[str, tuple[int, int]] = {}
    while queue:
        node = queue.popleft()
        if node in children:
            members = set(children[node])
            for child in children[node]:
                members.update(closure.get(child, ()))
                consumers[child] -= 1
                if consumers[child] == 0:
                    closure.pop(child, None)
            counts[node] = len(members), len(members & recent)
            if consumers.get(node):
                closure[node] = members
        for parent in parents.get(node, ()):
            remaining[parent] -= 1
            if remaining[parent] == 0:
                queue.append(parent)
    for node in children.keys() - counts.keys():
        members = _reachable(node, children)
        counts[node] = len(members), len(members & recent)
    return counts


@lru_cache(maxsize=2)
def _rows(database: str, snapshot_id: str, snapshot_date: str, import_id: int) -> tuple[BoardRow, ...]:
    # import_id invalidates cached legacy snapshots after re-import.
    end = date.fromisoformat(snapshot_date[:10])
    start_day = (end - timedelta(days=89)).isoformat()
    end_day = end.isoformat()
    children: dict[str, set[str]] = defaultdict(set)
    parents: dict[str, set[str]] = defaultdict(set)
    recent: set[str] = set()
    types: dict[str, Counter] = defaultdict(Counter)
    metadata: dict[str, tuple[str | None, bool]] = {}

    conn = connect(Path(database))
    try:
        edges = conn.execute("""
            SELECT r.parent_id, r.child_id, r.relation_type, p.family, p.ghost, c.created
            FROM relations r
            LEFT JOIN models p ON p.snapshot_id = r.snapshot_id AND p.model_id = r.parent_id
            LEFT JOIN models c ON c.snapshot_id = r.snapshot_id AND c.model_id = r.child_id
            WHERE r.snapshot_id = ? AND r.is_baseline = 1 AND r.parent_id <> r.child_id
        """, (snapshot_id,))
        for parent, child, kind, family, ghost, created in edges:
            children[parent].add(child)
            parents[child].add(parent)
            types[parent][kind] += 1
            metadata[parent] = (family or None, ghost is None or bool(ghost))
            if created and start_day <= created[:10] <= end_day:
                recent.add(child)
    finally:
        conn.close()

    counts = descendants(children, parents, recent)
    return tuple(
        BoardRow(
            model_id=model_id, family=metadata[model_id][0], ghost=metadata[model_id][1],
            total=total, direct=len(children[model_id]), recent=recent_count,
            **{kind: types[model_id][kind] for kind in ("finetune", "adapter", "quantized", "merge")},
        )
        for model_id, (total, recent_count) in counts.items()
    )


def board_page(
    conn, snapshot, query: str, family: str, ranking: Ranking, ascending: bool, page: int, size: int, include_ghost: bool,
) -> BoardPage:
    database = conn.execute("PRAGMA database_list").fetchone()["file"]
    import_id = conn.execute(
        "SELECT coalesce(max(id), 0) FROM imports WHERE snapshot_id = ?", (snapshot["id"],)
    ).fetchone()[0]
    with _cache_lock:
        rows = _rows(database, snapshot["id"], snapshot["snapshot_date"], import_id)
    search = query.strip().casefold()
    filtered = [
        row for row in rows
        if (include_ghost or not row.ghost) and (not family or row.family == family)
        and search in row.model_id.casefold()
    ]
    filtered.sort(key=lambda row: row.model_id.casefold())
    if ranking != "model_id":
        filtered.sort(key=lambda row: getattr(row, ranking), reverse=not ascending)
    elif not ascending:
        filtered.reverse()
    offset = (page - 1) * size
    return BoardPage(
        items=filtered[offset:offset + size], total=len(filtered),
        families=sorted({row.family for row in rows if row.family}),
    )
