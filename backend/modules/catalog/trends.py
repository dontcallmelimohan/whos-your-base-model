"""Monthly creation counts of unique direct descendants by parent family."""

from collections import defaultdict
from datetime import date

from pydantic import BaseModel


class FamilySeries(BaseModel):
    family: str
    before_window: int
    monthly: list[int]
    undated: int


class SnapshotTrends(BaseModel):
    snapshot_id: str
    snapshot_date: str
    months: list[str]
    series: list[FamilySeries]


def snapshot_trends(conn, snapshot) -> SnapshotTrends:
    end = date.fromisoformat(snapshot["snapshot_date"])
    end_index = end.year * 12 + end.month - 1
    months = [
        f"{index // 12:04d}-{index % 12 + 1:02d}"
        for index in range(end_index - 23, end_index + 1)
    ]
    rows = conn.execute("""
        WITH children AS (
            SELECT DISTINCT p.family, r.child_id, strftime('%Y-%m', c.created) AS month
            FROM relations r
            JOIN models p ON p.snapshot_id = r.snapshot_id AND p.model_id = r.parent_id
            LEFT JOIN models c ON c.snapshot_id = r.snapshot_id AND c.model_id = r.child_id
            WHERE r.snapshot_id = ? AND r.is_baseline = 1 AND r.child_id <> r.parent_id
              AND p.family <> ''
              AND (date(c.created) IS NULL OR date(c.created) <= ?)
        )
        SELECT family, month, count(*) AS total
        FROM children GROUP BY family, month
    """, (snapshot["id"], end.isoformat()))
    counts: dict[str, dict[str | None, int]] = defaultdict(dict)
    for family, month, total in rows:
        counts[family][month] = total
    dated = {family: sum(count for month, count in values.items() if month) for family, values in counts.items()}
    families = sorted((family for family in counts if dated[family]), key=lambda name: (-dated[name], name))
    return SnapshotTrends(
        snapshot_id=snapshot["id"], snapshot_date=end.isoformat(), months=months,
        series=[
            FamilySeries(
                family=family,
                before_window=sum(count for month, count in counts[family].items() if month and month < months[0]),
                monthly=[counts[family].get(month, 0) for month in months],
                undated=counts[family].get(None, 0),
            )
            for family in families[:6]
        ],
    )
