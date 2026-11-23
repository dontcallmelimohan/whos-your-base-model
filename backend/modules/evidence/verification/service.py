"""任务 4：候选查询、关系详情与核验记录。"""

from __future__ import annotations

import sqlite3

from shared.contracts import CandidateItem, EvidenceItem, RelationDetail, ReviewItem, RelationType
from shared.errors import invalid, not_found

DECISIONS = ("confirmed", "rejected", "unknown")


def _rtype(value: str) -> RelationType:
    try:
        return RelationType(value)
    except ValueError:
        return RelationType.UNKNOWN


def _candidate(row: sqlite3.Row, evidence_count: int = 0) -> CandidateItem:
    return CandidateItem(
        relation_id=row["id"],
        parent_id=row["parent_id"],
        child_id=row["child_id"],
        relation_type=_rtype(row["relation_type"]),
        origin=row["origin"],
        status=row["status"],
        source_field=row["source_field"],
        evidence_count=evidence_count,
    )


def list_candidates(
    conn: sqlite3.Connection,
    snapshot_id: str,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CandidateItem], int]:
    if status and status not in ("pending", *DECISIONS):
        raise invalid("status 不合法", {"allowed": ["pending", *DECISIONS]})

    where = "r.snapshot_id = ? AND r.origin = 'candidate'"
    params: list[object] = [snapshot_id]
    if status:
        where += " AND r.status = ?"
        params.append(status)

    total = int(
        conn.execute(f"SELECT count(*) AS c FROM relations r WHERE {where}", params).fetchone()["c"]
    )
    rows = conn.execute(
        f"""SELECT r.*, (SELECT count(*) FROM evidence e WHERE e.relation_id = r.id) AS ev
            FROM relations r WHERE {where}
            ORDER BY (r.status <> 'pending'), r.child_id, r.parent_id
            LIMIT ? OFFSET ?""",
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()
    return [_candidate(row, int(row["ev"])) for row in rows], total


def relation_detail(conn: sqlite3.Connection, relation_id: str) -> RelationDetail:
    row = conn.execute("SELECT * FROM relations WHERE id = ?", (relation_id,)).fetchone()
    if row is None:
        raise not_found(f"关系不存在: {relation_id}")

    evidence = [
        EvidenceItem(
            id=item["id"],
            relation_id=item["relation_id"],
            source_type=item["source_type"],
            source_path=item["source_path"],
            locator=item["locator"],
            quote=item["quote"],
            revision=item["revision"],
        )
        for item in conn.execute(
            "SELECT * FROM evidence WHERE relation_id = ? ORDER BY source_path, locator",
            (relation_id,),
        ).fetchall()
    ]
    reviews = [
        ReviewItem(
            id=item["id"],
            relation_id=item["relation_id"],
            decision=item["decision"],
            note=item["note"],
            reviewer=item["reviewer"],
            created_at=item["created_at"],
        )
        for item in conn.execute(
            "SELECT * FROM reviews WHERE relation_id = ? ORDER BY id", (relation_id,)
        ).fetchall()
    ]
    return RelationDetail(
        relation=_candidate(row, len(evidence)), evidence=evidence, reviews=reviews
    )


def add_review(
    conn: sqlite3.Connection,
    relation_id: str,
    decision: str,
    note: str | None,
    reviewer: str | None,
) -> RelationDetail:
    if decision not in DECISIONS:
        raise invalid("decision 只能是 confirmed / rejected / unknown", {"allowed": list(DECISIONS)})

    row = conn.execute("SELECT * FROM relations WHERE id = ?", (relation_id,)).fetchone()
    if row is None:
        raise not_found(f"关系不存在: {relation_id}")
    if row["origin"] != "candidate":
        raise invalid("基线声明关系不可核验，只有候选关系需要人工判断")

    conn.execute(
        "INSERT INTO reviews (relation_id, decision, note, reviewer) VALUES (?, ?, ?, ?)",
        (relation_id, decision, note, reviewer),
    )
    # 最新一条决定当前状态
    conn.execute("UPDATE relations SET status = ? WHERE id = ?", (decision, relation_id))
    conn.commit()
    return relation_detail(conn, relation_id)


def status_counts(conn: sqlite3.Connection, snapshot_id: str) -> dict[str, int]:
    rows = conn.execute(
        """SELECT status, count(*) AS c FROM relations
           WHERE snapshot_id = ? AND origin = 'candidate' GROUP BY status""",
        (snapshot_id,),
    ).fetchall()
    counts = {row["status"]: int(row["c"]) for row in rows}
    return {
        "pending": counts.get("pending", 0),
        "confirmed": counts.get("confirmed", 0),
        "rejected": counts.get("rejected", 0),
        "unknown": counts.get("unknown", 0),
        "total": sum(counts.values()),
    }
