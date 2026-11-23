-- 模块三：依赖发现与证据核验
-- 关系表加两列：origin（declared = 模型卡字段声明 / candidate = 规则发现的候选）
--               status（pending / confirmed / rejected / unknown）
-- 已有声明的基线关系固定为 declared + confirmed。

ALTER TABLE relations ADD COLUMN origin TEXT NOT NULL DEFAULT 'declared';
ALTER TABLE relations ADD COLUMN status TEXT NOT NULL DEFAULT 'confirmed';

CREATE TABLE IF NOT EXISTS evidence (
    id          TEXT PRIMARY KEY,
    relation_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    source_type TEXT NOT NULL,   -- model_card_text / model_card_yaml / config
    source_path TEXT,            -- 例如 README.md
    locator     TEXT,            -- 行号或字段名，例如 L42 或 base_model
    quote       TEXT,            -- 原文片段
    revision    TEXT,            -- 无仓库 revision 时留空，页面显示「仅有数据快照」
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_evidence_relation ON evidence (relation_id);

CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    relation_id TEXT NOT NULL,
    decision    TEXT NOT NULL,   -- confirmed / rejected / unknown
    note        TEXT,
    reviewer    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reviews_relation ON reviews (relation_id);
