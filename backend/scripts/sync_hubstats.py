"""将 Hugging Face 上最新的 hub-stats 模型快照导入本地平台。"""

import argparse
import json
import sys

from modules.catalog.hubstats_sync import sync_hubstats
from shared.errors import ApiError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="按下载量取前 N 个模型，默认 20000，0 表示全量")
    args = parser.parse_args()
    try:
        result = sync_hubstats(args.limit)
    except ApiError as exc:
        print(exc.message, file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
