-- 平台在线库（SQLite）表结构
-- 口径参照 model-family-tree（MIT）的 dist 文件：
--   关系类型 finetune / adapter / quantized / merge / unknown
--   ghost = 属性未收录的占位上游
-- 约定：
--   1. 关系方向统一为「上游 -> 下游」
--   2. 关系唯一键 = snapshot_id + parent_id + child_id + relation_type
--   3. 同一快照重复导入不产生重复记录（唯一键 + INSERT OR IGNORE）

CREATE TABLE IF NOT EXISTS snapshots (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    input_hash    TEXT,
    rule_version  TEXT NOT NULL,
    scope_note    TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS models (
    snapshot_id   TEXT NOT NULL,
    model_id      TEXT NOT NULL,
    author        TEXT,
    pipeline      TEXT,
    library       TEXT,
    downloads     INTEGER,
    downloads_all INTEGER,
    likes         INTEGER,
    created       TEXT,
    family        TEXT,
    ghost         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_id, model_id),
    FOREIGN KEY (snapshot_id) REFERENCES snapshots (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS relations (
    id            TEXT PRIMARY KEY,
    snapshot_id   TEXT NOT NULL,
    parent_id     TEXT NOT NULL,
    child_id      TEXT NOT NULL,
    relation_type TEXT NOT NULL DEFAULT 'unknown',
    is_baseline   INTEGER NOT NULL DEFAULT 1,
    source_field  TEXT,
    UNIQUE (snapshot_id, parent_id, child_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_rel_parent ON relations (snapshot_id, parent_id);
CREATE INDEX IF NOT EXISTS idx_rel_child  ON relations (snapshot_id, child_id);

CREATE TABLE IF NOT EXISTS model_datasets (
    snapshot_id  TEXT NOT NULL,
    model_id     TEXT NOT NULL,
    dataset_id   TEXT NOT NULL,
    source_field TEXT,
    raw_value    TEXT,
    PRIMARY KEY (snapshot_id, model_id, dataset_id)
);

CREATE TABLE IF NOT EXISTS imports (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id        TEXT NOT NULL,
    source             TEXT NOT NULL,
    input_hash         TEXT,
    model_count        INTEGER NOT NULL DEFAULT 0,
    relation_count     INTEGER NOT NULL DEFAULT 0,
    dataset_link_count INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);
