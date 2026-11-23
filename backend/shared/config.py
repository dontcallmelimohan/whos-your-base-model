"""平台路径与上限常量。

所有路径都在调用时计算，方便测试用环境变量指向临时目录。

数据来源（两个都在仓库根目录，均不进入 Git）：
    models.parquet              hub-stats 每日全量 dump（Apache-2.0），字段含 baseModels
    model-family-tree-main/dist model-family-tree（MIT）生成的派生数据
"""

from __future__ import annotations

import os
from pathlib import Path

# platform/backend/shared/config.py -> platform/ -> 仓库根目录
PLATFORM_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = PLATFORM_DIR.parent


def data_dir() -> Path:
    return Path(os.getenv("PLATFORM_DATA_DIR", PLATFORM_DIR / "data"))


def db_path() -> Path:
    return Path(os.getenv("PLATFORM_DB", data_dir() / "platform.db"))


def fixtures_dir() -> Path:
    return Path(os.getenv("PLATFORM_FIXTURES", PLATFORM_DIR / "fixtures"))


def hubstats_parquet_path() -> Path:
    return Path(os.getenv("PLATFORM_HUBSTATS", REPO_ROOT / "models.parquet"))


def modeltree_dir() -> Path:
    return Path(os.getenv("PLATFORM_MODELTREE", REPO_ROOT / "model-family-tree-main"))


# ---- 服务端硬上限（方案 F3：默认一层、最多两层、默认 100 节点）----
MAX_PAGE_SIZE = 100
MAX_DEPTH = 2
MAX_GRAPH_NODES = 200
DEFAULT_GRAPH_NODES = 100

# ---- 数据版本 ----
DEMO_SNAPSHOT_ID = "demo-2026-11"
DEFAULT_IMPORT_LIMIT = 20000

# 处理规则版本：改了导入逻辑就升这个号，写进 snapshot 元数据
RULE_VERSION = "rules-v2"
HUBSTATS_RULE_VERSION = "catalog-v3"

# 关系类型，与 model-family-tree 一致
RELATION_TYPES = ("finetune", "adapter", "quantized", "merge", "unknown")
