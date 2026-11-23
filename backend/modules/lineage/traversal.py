"""工作包 B：有限深度邻接遍历。

实现要点（对应方案 F3）：
    * 默认一层，最多两层，由 config.MAX_DEPTH 强制
    * 用 visited 集合防环，同一节点只入队一次
    * 先按 BFS 顺序收集，再按节点上限截断，保证保留离根最近的节点
    * 截断时返回 truncated=True，前端必须显示提示

口径与 model-family-tree 一致：关系方向为「上游 -> 下游」；
属性未收录的上游节点保留为 ghost=True。
"""

from __future__ import annotations

import sqlite3

from shared import config, graph_read
from shared.contracts import GraphEdge, GraphNode, GraphResponse, RelationType
from shared.errors import invalid, not_found


def _node_from_row(node_id: str, row: sqlite3.Row | None) -> GraphNode:
    if row is None:
        return GraphNode(id=node_id, label=node_id, ghost=True)
    return GraphNode(
        id=row["model_id"],
        label=row["model_id"],
        ghost=bool(row["ghost"]),
        family=row["family"] or None,
        downloads=row["downloads"],
        pipeline=row["pipeline"],
        author=row["author"],
    )


def _edge_from_row(row: sqlite3.Row) -> GraphEdge:
    try:
        rtype = RelationType(row["relation_type"])
    except ValueError:
        rtype = RelationType.UNKNOWN
    return GraphEdge(
        id=row["id"],
        source=row["parent_id"],
        target=row["child_id"],
        type=rtype,
        source_field=row["source_field"],
    )


def build_local_graph(
    conn: sqlite3.Connection,
    snapshot_id: str,
    root_id: str,
    direction: str = "both",
    depth: int = 1,
    relation_type: str | None = None,
    limit: int = config.DEFAULT_GRAPH_NODES,
    view: str = "declared",
) -> GraphResponse:
    if not 1 <= depth <= config.MAX_DEPTH:
        raise invalid(f"depth 必须在 1..{config.MAX_DEPTH} 之间", {"depth": depth})
    if not 1 <= limit <= config.MAX_GRAPH_NODES:
        raise invalid(f"limit 必须在 1..{config.MAX_GRAPH_NODES} 之间", {"limit": limit})
    if direction not in ("upstream", "downstream", "both"):
        raise invalid("direction 只能是 upstream / downstream / both", {"direction": direction})
    if view not in ("declared", "completed"):
        raise invalid("view 只能是 declared / completed", {"view": view})
    if relation_type and relation_type not in config.RELATION_TYPES:
        raise invalid(
            "relation_type 不在允许范围内",
            {"relation_type": relation_type, "allowed": list(config.RELATION_TYPES)},
        )

    root_row = graph_read.get_model(conn, snapshot_id, root_id)
    if root_row is None:
        raise not_found(f"模型不存在: {root_id}", {"snapshot_id": snapshot_id})

    directions = ["upstream", "downstream"] if direction == "both" else [direction]

    nodes: dict[str, GraphNode] = {root_id: _node_from_row(root_id, root_row)}
    edges: dict[str, GraphEdge] = {}
    visited: set[str] = {root_id}
    order: list[str] = [root_id]
    frontier: list[str] = [root_id]

    for _level in range(depth):
        next_frontier: list[str] = []
        for way in directions:
            for row in graph_read.neighbours(conn, snapshot_id, frontier, way, relation_type, view):
                edge = _edge_from_row(row)
                edges.setdefault(edge.id, edge)
                for node_id in (row["parent_id"], row["child_id"]):
                    if node_id not in visited:
                        visited.add(node_id)
                        order.append(node_id)
                        next_frontier.append(node_id)
        frontier = next_frontier
        if not frontier:
            break

    props = graph_read.get_models(conn, snapshot_id, order)
    for node_id in order:
        if node_id in nodes:
            continue
        nodes[node_id] = _node_from_row(node_id, props.get(node_id))

    truncated = len(order) > limit
    kept = order[:limit]
    kept_set = set(kept)

    kept_nodes = [nodes[nid] for nid in kept]
    kept_edges = [
        edge for edge in edges.values() if edge.source in kept_set and edge.target in kept_set
    ]

    return GraphResponse(
        snapshot_id=snapshot_id,
        root=root_id,
        view=view,
        direction=direction,  # type: ignore[arg-type]
        depth=depth,
        nodes=kept_nodes,
        edges=kept_edges,
        truncated=truncated,
        node_limit=limit,
        node_count=len(kept_nodes),
        edge_count=len(kept_edges),
    )
