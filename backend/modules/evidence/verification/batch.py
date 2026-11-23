"""任务 4：本地批处理入口。

实现后的用法（在 backend/ 下）：

    python -m modules.evidence.verification.batch --snapshot demo-2026-11
    python -m modules.evidence.verification.batch --snapshot demo-2026-11 --limit 50

流程：候选关系逐条 ``judge.judge_relation`` → 结论为 support 且版本对齐时
置为 confirmed（进入补全图）→ 重复运行不会重复加边（关系唯一键 + 状态幂等）。

现在只留入口与参数解析，判定规则实现前显式失败，避免批处理静默跑空。
"""

from __future__ import annotations

import argparse
import sys

from shared import graph_read
from shared.db import connect
from shared.errors import ApiError, not_ready


def run_batch(snapshot_id: str | None = None, limit: int | None = None) -> dict:
    """批处理一个快照内的候选关系。"""
    raise not_ready(
        "自动核验的本地批处理尚未实现（任务 4）",
        {"snapshot_id": snapshot_id, "limit": limit, "stage": "batch"},
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="对快照内的候选关系做批量核验与补全")
    parser.add_argument("--snapshot", default=None, help="快照 ID，缺省用最新快照")
    parser.add_argument("--limit", type=int, default=None, help="最多处理多少条候选")
    args = parser.parse_args(argv)

    conn = connect()
    try:
        snapshot = graph_read.get_snapshot(conn, args.snapshot)
        summary = run_batch(snapshot["id"], args.limit)
    except ApiError as exc:
        print(f"[{exc.code}] {exc.message}", file=sys.stderr)
        if exc.detail:
            print(f"  detail: {exc.detail}", file=sys.stderr)
        return 2
    finally:
        conn.close()

    print(summary)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
