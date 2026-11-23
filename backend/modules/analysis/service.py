"""工作包 D：统计口径。

指标命名与 model-family-tree 的 dist/stats.json 对齐，便于直接和上游结果对账：
    model_count   models
    edge_count    edges
    parent_count  parents     有下游的模型数
    root_count    roots       没有上游的模型数
    ghost_count   ghost_parents 属性未收录的占位上游
    family_count  families
    cyclic_node_count  cyclic_nodes

两个计数必须分开，页面也要分开标注：
    unique_pair_count  唯一上下游对 —— 用于「总边数」
    edge_count         带类型的关系条数 —— 用于「类型分布」
"""

from __future__ import annotations

import json
import sqlite3

from shared import config, graph_read
from shared.contracts import (
    AnalysisResponse,
    CaseRef,
    FamilyBucket,
    Metrics,
    RelationType,
    TypeBucket,
    UpstreamRank,
)

TOP_N = 10


def _type_distribution(conn: sqlite3.Connection, snapshot_id: str) -> list[TypeBucket]:
    rows = conn.execute(
        """SELECT relation_type, count(*) AS c
           FROM relations
           WHERE snapshot_id = ? AND is_baseline = 1
           GROUP BY relation_type
           ORDER BY c DESC, relation_type""",
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


def _reachability(conn: sqlite3.Connection, snapshot_id: str) -> list[sqlite3.Row]:
    """一次递归算出所有「上游 -> 可达后代」对。

    用 UNION（不是 UNION ALL）：重复对自动去重，环不会导致无限递归。
    """
    return conn.execute(
        """WITH RECURSIVE reach(anc, node) AS (
               SELECT parent_id, child_id FROM relations
               WHERE snapshot_id = ? AND is_baseline = 1
               UNION
               SELECT r.anc, rel.child_id FROM reach r
               JOIN relations rel ON rel.parent_id = r.node
               WHERE rel.snapshot_id = ? AND rel.is_baseline = 1
           )
           SELECT anc,
                  count(*) AS total,
                  sum(CASE WHEN anc = node THEN 1 ELSE 0 END) AS cyclic
           FROM reach GROUP BY anc""",
        (snapshot_id, snapshot_id),
    ).fetchall()


def _metrics(conn: sqlite3.Connection, snapshot_id: str, reach: list[sqlite3.Row]) -> Metrics:
    model_count = graph_read.count_models(conn, snapshot_id)
    edge_count = graph_read.count_relations(conn, snapshot_id)
    unique_pairs = int(
        conn.execute(
            """SELECT count(*) AS c FROM (
                   SELECT DISTINCT parent_id, child_id FROM relations
                   WHERE snapshot_id = ? AND is_baseline = 1
               )""",
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
            """SELECT count(*) AS c FROM models m
               WHERE m.snapshot_id = ?
                 AND NOT EXISTS (
                     SELECT 1 FROM relations r
                     WHERE r.snapshot_id = m.snapshot_id AND r.child_id = m.model_id)""",
            (snapshot_id,),
        ).fetchone()["c"]
    )
    cyclic = sum(1 for row in reach if int(row["cyclic"]) > 0)
    return Metrics(
        model_count=model_count,
        edge_count=edge_count,
        unique_pair_count=unique_pairs,
        parent_count=len(reach),
        root_count=root_count,
        ghost_count=ghost_count,
        family_count=family_count,
        cyclic_node_count=cyclic,
    )


def _top_upstream(
    conn: sqlite3.Connection, snapshot_id: str, reach: list[sqlite3.Row], n: int = TOP_N
) -> list[UpstreamRank]:
    totals = {row["anc"]: int(row["total"]) for row in reach}
    rows = conn.execute(
        """SELECT parent_id, count(DISTINCT child_id) AS direct,
                  coalesce(m.family, '') AS family
           FROM relations r
           LEFT JOIN models m
             ON m.snapshot_id = r.snapshot_id AND m.model_id = r.parent_id
           WHERE r.snapshot_id = ? AND r.is_baseline = 1
           GROUP BY parent_id""",
        (snapshot_id,),
    ).fetchall()
    ranks = [
        UpstreamRank(
            model_id=row["parent_id"],
            direct=int(row["direct"]),
            total=totals.get(row["parent_id"], int(row["direct"])),
            family=row["family"] or None,
        )
        for row in rows
    ]
    ranks.sort(key=lambda item: (-item.total, -item.direct, item.model_id))
    return ranks[:n]


def _family_distribution(conn: sqlite3.Connection, snapshot_id: str, n: int = TOP_N) -> list[FamilyBucket]:
    rows = conn.execute(
        """SELECT family, count(*) AS models
           FROM models
           WHERE snapshot_id = ? AND family IS NOT NULL AND family <> ''
           GROUP BY family
           ORDER BY models DESC, family
           LIMIT ?""",
        (snapshot_id, n),
    ).fetchall()
    return [FamilyBucket(family=row["family"], models=int(row["models"]), total_descendants=0) for row in rows]


def _cases(model_ids: set[str]) -> list[CaseRef]:
    """案例清单放在 fixtures/cases.json，由工作包 D 维护。"""
    path = config.fixtures_dir() / "cases.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [CaseRef(**item) for item in payload.get("cases", [])]
    return [case for case in cases if case.model_id in model_ids]


def build_analysis(conn: sqlite3.Connection, snapshot_id: str) -> AnalysisResponse:
    snapshot = graph_read.get_snapshot(conn, snapshot_id)
    reach = _reachability(conn, snapshot_id)
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
        metrics=_metrics(conn, snapshot_id, reach),
        type_distribution=_type_distribution(conn, snapshot_id),
        top_upstream=_top_upstream(conn, snapshot_id, reach),
        family_distribution=_family_distribution(conn, snapshot_id),
        cases=_cases(ids),
    )
