"""初始化数据库并导入数据。

用法：
    cd platform/backend
    python -m scripts.seed                                  # 样例数据（最快，开发用）
    python -m scripts.seed --source hubstats --limit 20000  # 真实数据（需要仓库根目录的 models.parquet）
    python -m scripts.seed --source modeltree --limit 3000  # 用 model-family-tree 的 dist 派生数据
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# 允许直接 `python scripts/seed.py` 运行
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.catalog.importer import run_import  # noqa: E402
from shared.db import init_database  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化平台数据库并导入数据")
    parser.add_argument(
        "--source",
        default="fixtures",
        choices=["fixtures", "hubstats", "modeltree"],
        help="fixtures=样例 / hubstats=hub-stats dump / modeltree=model-family-tree 派生数据",
    )
    parser.add_argument("--limit", type=int, default=None, help="最多导入多少个模型")
    parser.add_argument("--snapshot-id", default=None)
    args = parser.parse_args()

    path = init_database()
    print(f"[seed] 数据库: {path}")

    started = time.time()
    result = run_import(args.source, args.limit, args.snapshot_id)
    elapsed = time.time() - started

    print(f"[seed] 数据版本: {result['snapshot_id']}")
    print(f"[seed] 模型: {result['model_count']}")
    print(f"[seed] 关系: {result['relation_count']}")
    print(f"[seed] 模型—数据集关联: {result['dataset_link_count']}")
    print(f"[seed] 耗时: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
