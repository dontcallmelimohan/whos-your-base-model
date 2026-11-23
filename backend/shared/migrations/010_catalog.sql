CREATE TABLE IF NOT EXISTS catalog_licenses (
    snapshot_id  TEXT NOT NULL,
    model_id     TEXT NOT NULL,
    license      TEXT,
    license_name TEXT,
    license_link TEXT,
    PRIMARY KEY (snapshot_id, model_id),
    FOREIGN KEY (snapshot_id, model_id) REFERENCES models (snapshot_id, model_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_catalog_downloads ON models (snapshot_id, downloads DESC, model_id);
