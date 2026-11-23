"""工作包 D：统计口径。

指标分三类，页面上要分别标注：

1. 规模：模型数、关系数、有下游的模型数、根节点数、家族数
2. 集中度（产业组织学常用，参考 Open Model Evolution 的 concentration 视角）
      HHI        = Σ (直接下游数 / 总关系数)²  × 10000
      Top-10 份额 = 前 10 上游的直接下游数之和 / 总关系数
3. 数据质量
      断链率     = 属性未收录的上游数 / 全部上游数
      环节点数   = 互相指向的两节点环（便宜且可解释，不做全图闭包）

性能约束：不做全图传递闭包（2 万条边就会卡住）。
可达后代只对 Top-N 上游逐个算，深度上限 12，用 UNION 去重防环。
"""

from __future__ import annotations

import json
import sqlite3

from shared import config, graph_read
from shared.contracts import (
    AnalysisResponse,
    DiffEdge,
    DiffResponse,
    MetricDelta,
    CaseRef,
    Concentration,
    DataQuality,
    FamilyBucket,
    Metrics,
    RelationType,
    TypeBucket,
    UpstreamRank,
)

TOP_N = 10


def _type_distribution(
    conn: sqlite3.Connection, snapshot_id: str, view: str
) -> list[TypeBucket]:
    rows = conn.execute(
        f"""SELECT relation_type, count(*) AS c FROM relations
           WHERE snapshot_id = ? AND {graph_read.view_filter(view)}
           GROUP BY relation_type ORDER BY c DESC, relation_type""",
        (snapshot_id,),
    ).fetchall()
    buckets: list[TypeBucket] = []
    for row in rows:
        try:
            rtype = RelationType(row["relation_type"])
        except ValueError:
            rtype = RelationType.UNKNOWN
        buckets.append(TypeBucket(type=rtype, count=int(row["c"])))
    return buckets


def _direct_counts(
    conn: sqlite3.Connection, snapshot_id: str, view: str
) -> list[sqlite3.Row]:
    return conn.execute(
        f"""SELECT r.parent_id AS parent_id,
                  count(DISTINCT r.child_id) AS direct,
                  coalesce(m.family, '') AS family
           FROM relations r
           LEFT JOIN models m
             ON m.snapshot_id = r.snapshot_id AND m.model_id = r.parent_id
           WHERE r.snapshot_id = ? AND {graph_read.view_filter(view, "r")}
           GROUP BY r.parent_id""",
        (snapshot_id,),
    ).fetchall()


def _totals_for(
    conn: sqlite3.Connection, snapshot_id: str, parent_ids: list[str], view: str = "declared"
) -> dict[str, int]:
    """一次读出边表，在内存里对指定上游做 BFS。

    比每条上游各跑一次递归 CTE 快两个数量级（2 万条边：16s → 0.05s）。
    """
    rows = conn.execute(
        f"SELECT parent_id, child_id FROM relations WHERE snapshot_id = ? AND {graph_read.view_filter(view)}",
        (snapshot_id,),
    ).fetchall()
    adjacency: dict[str, list[str]] = {}
    for row in rows:
        adjacency.setdefault(row["parent_id"], []).append(row["child_id"])

    def descendants(start: str) -> int:
        seen: set[str] = set()
        stack = list(adjacency.get(start, ()))
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(adjacency.get(node, ()))
        return len(seen)

    return {parent_id: descendants(parent_id) for parent_id in parent_ids}


def _concentration(
    conn: sqlite3.Connection, snapshot_id: str, direct_rows: list[sqlite3.Row], relation_count: int
) -> Concentration:
    total = relation_count or 1
    shares = sorted((int(row["direct"]) / total for row in direct_rows), reverse=True)
    hhi = round(sum(share**2 for share in shares), 4)
    return Concentration(
        hhi=hhi,
        hhi_scaled=round(hhi * 10000, 1),
        top10_share=round(sum(shares[:TOP_N]), 4),
        parent_count=len(direct_rows),
    )


def _data_quality(conn: sqlite3.Connection, snapshot_id: str, view: str = "declared") -> DataQuality:
    # 断链率：有下游、但自身属性未收录的上游占比
    row = conn.execute(
        f"""SELECT
             count(*) AS parents,
             sum(CASE WHEN m.ghost = 1 OR m.model_id IS NULL THEN 1 ELSE 0 END) AS ghosts
           FROM (SELECT DISTINCT parent_id FROM relations
                 WHERE snapshot_id = ? AND {graph_read.view_filter(view)}) p
           LEFT JOIN models m
             ON m.snapshot_id = ? AND m.model_id = p.parent_id""",
        (snapshot_id, snapshot_id),
    ).fetchone()
    parents = int(row["parents"] or 0)
    ghosts = int(row["ghosts"] or 0)

    # 环：只统计互相指向的二元环（可解释、代价低）
    cycle = conn.execute(
        f"""SELECT count(DISTINCT a.parent_id) AS c
           FROM relations a
           JOIN relations b
             ON b.snapshot_id = a.snapshot_id
            AND b.parent_id = a.child_id
            AND b.child_id = a.parent_id
           WHERE a.snapshot_id = ? AND {graph_read.view_filter(view, "a")}
             AND {graph_read.view_filter(view, "b")}""",
        (snapshot_id,),
    ).fetchone()
    return DataQuality(
        ghost_ratio=round(ghosts / parents, 4) if parents else 0.0,
        ghost_parent_count=ghosts,
        cyclic_node_count=int(cycle["c"] or 0),
    )


def _metrics(
    conn: sqlite3.Connection, snapshot_id: str, parents: int, cyclic: int, view: str = "declared"
) -> Metrics:
    model_count = graph_read.count_models(conn, snapshot_id)
    edge_count = graph_read.count_relations(conn, snapshot_id, view)
    unique_pairs = int(
        conn.execute(
            f"""SELECT count(*) AS c FROM (
                   SELECT DISTINCT parent_id, child_id FROM relations
                   WHERE snapshot_id = ? AND {graph_read.view_filter(view)})""",
            (snapshot_id,),
        ).fetchone()["c"]
    )
    ghost_count = int(
        conn.execute(
            "SELECT count(*) AS c FROM models WHERE snapshot_id = ? AND ghost = 1", (snapshot_id,)
        ).fetchone()["c"]
    )
    family_count = int(
        conn.execute(
            """SELECT count(DISTINCT family) AS c FROM models
               WHERE snapshot_id = ? AND family IS NOT NULL AND family <> ''""",
            (snapshot_id,),
        ).fetchone()["c"]
    )
    root_count = int(
        conn.execute(
            f"""SELECT count(*) AS c FROM models m
               WHERE m.snapshot_id = ?
                 AND NOT EXISTS (
                     SELECT 1 FROM relations r
                     WHERE r.snapshot_id = m.snapshot_id AND r.child_id = m.model_id
                       AND {graph_read.view_filter(view, "r")})""",
            (snapshot_id,),
        ).fetchone()["c"]
    )
    return Metrics(
        model_count=model_count,
        edge_count=edge_count,
        unique_pair_count=unique_pairs,
        parent_count=parents,
        root_count=root_count,
        ghost_count=ghost_count,
        family_count=family_count,
        cyclic_node_count=cyclic,
    )


def _top_upstream(
    conn: sqlite3.Connection,
    snapshot_id: str,
    direct_rows: list[sqlite3.Row],
    n: int = TOP_N,
    view: str = "declared",
) -> list[UpstreamRank]:
    ranked = sorted(direct_rows, key=lambda row: (-int(row["direct"]), row["parent_id"]))[:n]
    totals = _totals_for(conn, snapshot_id, [row["parent_id"] for row in ranked], view)
    return [
        UpstreamRank(
            model_id=row["parent_id"],
            direct=int(row["direct"]),
            total=totals.get(row["parent_id"], int(row["direct"])),
            family=row["family"] or None,
        )
        for row in ranked
    ]


def _family_distribution(
    conn: sqlite3.Connection, snapshot_id: str, n: int = TOP_N
) -> list[FamilyBucket]:
    rows = conn.execute(
        """SELECT family, count(*) AS models FROM models
           WHERE snapshot_id = ? AND family IS NOT NULL AND family <> ''
           GROUP BY family ORDER BY models DESC, family LIMIT ?""",
        (snapshot_id, n),
    ).fetchall()
    return [
        FamilyBucket(family=row["family"], models=int(row["models"]), total_descendants=0)
        for row in rows
    ]


def _cases(model_ids: set[str]) -> list[CaseRef]:
    path = config.fixtures_dir() / "cases.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [CaseRef(**item) for item in payload.get("cases", [])]
    return [case for case in cases if case.model_id in model_ids]


def build_analysis(
    conn: sqlite3.Connection, snapshot_id: str, view: str = "declared"
) -> AnalysisResponse:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    direct_rows = _direct_counts(conn, snapshot_id, view)
    relation_count = graph_read.count_relations(conn, snapshot_id, view)
    quality = _data_quality(conn, snapshot_id, view)

    ids = {
        row["model_id"]
        for row in conn.execute(
            "SELECT model_id FROM models WHERE snapshot_id = ?", (snapshot_id,)
        ).fetchall()
    }

    return AnalysisResponse(
        snapshot_id=snapshot["id"],
        rule_version=snapshot["rule_version"],
        scope_note=snapshot["scope_note"],
        metrics=_metrics(conn, snapshot_id, len(direct_rows), quality.cyclic_node_count, view),
        concentration=_concentration(conn, snapshot_id, direct_rows, relation_count),
        data_quality=quality,
        type_distribution=_type_distribution(conn, snapshot_id, view),
        top_upstream=_top_upstream(conn, snapshot_id, direct_rows, TOP_N, view),
        family_distribution=_family_distribution(conn, snapshot_id),
        cases=_cases(ids),
    )


def build_diff(conn: sqlite3.Connection, snapshot_id: str) -> DiffResponse:
    """对比同一快照下的「声明图」与「补全图」。

    只算一次分析两次（声明 / 补全），在 2 万条边的量级下 < 0.5s。
    """
    declared = build_analysis(conn, snapshot_id, "declared")
    completed = build_analysis(conn, snapshot_id, "completed")

    def delta(name: str, a: float, b: float) -> MetricDelta:
        return MetricDelta(declared=round(a, 4), completed=round(b, 4), delta=round(b - a, 4))

    metrics = {
        "edge_count": delta("edge_count", declared.metrics.edge_count, completed.metrics.edge_count),
        "unique_pair_count": delta(
            "unique_pair_count", declared.metrics.unique_pair_count, completed.metrics.unique_pair_count
        ),
        "parent_count": delta(
            "parent_count", declared.metrics.parent_count, completed.metrics.parent_count
        ),
        "hhi_scaled": delta(
            "hhi_scaled", declared.concentration.hhi_scaled, completed.concentration.hhi_scaled
        ),
        "top10_share": delta(
            "top10_share", declared.concentration.top10_share, completed.concentration.top10_share
        ),
    }

    added_rows = conn.execute(
        """SELECT * FROM relations
           WHERE snapshot_id = ? AND origin = 'candidate' AND status = 'confirmed'
           ORDER BY parent_id, child_id""",
        (snapshot_id,),
    ).fetchall()
    pending = conn.execute(
        """SELECT count(*) AS c FROM relations
           WHERE snapshot_id = ? AND origin = 'candidate' AND status = 'pending'""",
        (snapshot_id,),
    ).fetchone()

    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    return DiffResponse(
        snapshot_id=snapshot["id"],
        rule_version=snapshot["rule_version"],
        added_edges=[
            DiffEdge(
                relation_id=row["id"],
                parent_id=row["parent_id"],
                child_id=row["child_id"],
                relation_type=_rtype(row["relation_type"]),
                status=row["status"],
            )
            for row in added_rows
        ],
        pending_count=int(pending["c"]),
        metrics=metrics,
    )


def _rtype(value: str) -> RelationType:
    try:
        return RelationType(value)
    except ValueError:
        return RelationType.UNKNOWN


def analysis_csv(conn: sqlite3.Connection, snapshot_id: str, view: str = "declared") -> str:
    """导出上游榜单为 CSV，并把快照与口径写进注释头，便于复算。"""
    result = build_analysis(conn, snapshot_id, view)
    lines = [
        f"# snapshot_id={result.snapshot_id}",
        f"# view={view}",
        f"# rule_version={result.rule_version}",
        f"# edge_count={result.metrics.edge_count}",
        f"# unique_pair_count={result.metrics.unique_pair_count}",
        f"# hhi_scaled={result.concentration.hhi_scaled}",
        f"# top10_share={result.concentration.top10_share}",
        "rank,model_id,family,direct,total,share_of_edges",
    ]
    for index, row in enumerate(result.top_upstream, start=1):
        share = row.direct / (result.metrics.edge_count or 1)
        lines.append(
            f"{index},{row.model_id},{row.family or ''},{row.direct},{row.total},{share:.6f}"
        )
    return "\n".join(lines) + "\n"
