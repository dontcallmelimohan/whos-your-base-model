"""将 hub-stats 元数据整理为可分批写入 SQLite 的表。"""

from pathlib import Path


def prepare_tables(conn, path: Path, limit: int) -> None:
    conn.read_parquet(str(path)).create_view("hub_models")
    # 排除空 ID 和异常 ID。SQL 中所有输入来自 Parquet 而非动态拼接。
    conn.execute("""
        CREATE MACRO valid_id(id) AS (
            regexp_full_match(id, '[A-Za-z0-9_][A-Za-z0-9_.-]*(/[A-Za-z0-9_][A-Za-z0-9_.-]*)?')
            AND NOT regexp_matches(id, '(^|/)(hf_|sk-|ghp_)')
        );
        CREATE MACRO known_type(kind) AS (
            CASE WHEN kind IN ('finetune', 'adapter', 'quantized', 'merge') THEN kind ELSE 'unknown' END
        );
    """)
    pick = """
        CREATE TEMP TABLE selected_models AS
        SELECT id, baseModels, list_filter(tags, tag -> starts_with(tag, 'base_model:')) AS base_tags
        FROM hub_models WHERE valid_id(id)
    """
    if limit:
        conn.execute(pick + " ORDER BY downloads DESC NULLS LAST, id LIMIT ?", [limit])
    else:
        conn.execute(pick)

    conn.execute("""
        CREATE TEMP TABLE catalog_edges AS
        WITH structured AS (
            SELECT id AS child_id, parent.id AS parent_id, known_type(baseModels.relation) AS relation_type,
                   'baseModels' AS source_field
            FROM selected_models, unnest(baseModels.models) AS parents(parent)
            WHERE valid_id(parent.id) AND parent.id <> id
        ), tags AS (
            SELECT model.id AS child_id, split_part(tag, ':', -1) AS parent_id,
                   known_type(split_part(tag, ':', 2)) AS relation_type, 'tags' AS source_field
            FROM selected_models model, unnest(base_tags) AS tags(tag)
            WHERE regexp_full_match(tag, 'base_model:([^:]+:)?[^:]+')
              AND valid_id(split_part(tag, ':', -1)) AND split_part(tag, ':', -1) <> model.id
        ), fallback AS (
            SELECT DISTINCT tags.* FROM tags
            ANTI JOIN structured USING (child_id, parent_id)
        )
        SELECT DISTINCT * FROM structured
        UNION ALL
        SELECT * FROM fallback
        WHERE relation_type <> 'unknown' OR NOT EXISTS (
            SELECT 1 FROM fallback typed WHERE typed.child_id = fallback.child_id
              AND typed.parent_id = fallback.parent_id AND typed.relation_type <> 'unknown'
        )
    """)

    if limit:
        conn.execute("""
            CREATE TEMP TABLE catalog_ids AS
            SELECT id FROM selected_models UNION SELECT parent_id FROM catalog_edges
        """)
        scope = "SEMI JOIN catalog_ids USING (id)"
    else:
        scope = ""
    conn.execute(f"""
        CREATE TEMP TABLE catalog_models AS
        SELECT id, author, pipeline_tag, library_name, downloads, downloadsAllTime, likes, createdAt
        FROM hub_models {scope}
        WHERE valid_id(id)
        QUALIFY row_number() OVER (PARTITION BY id ORDER BY lastModified DESC NULLS LAST, _id) = 1
    """)
    conn.execute("""
        CREATE TEMP TABLE catalog_metadata AS
        SELECT id, fields[1] AS datasets,
               json_extract_string(fields[2], '$') AS license,
               json_extract_string(fields[3], '$') AS license_name,
               json_extract_string(fields[4], '$') AS license_link
        FROM (
            SELECT id, json_extract(try_cast(cardData AS JSON),
                ['$.datasets', '$.license', '$.license_name', '$.license_link']) AS fields
            FROM hub_models SEMI JOIN catalog_models USING (id)
            WHERE cardData IS NOT NULL
            QUALIFY row_number() OVER (PARTITION BY id ORDER BY lastModified DESC NULLS LAST, _id) = 1
        )
    """)
