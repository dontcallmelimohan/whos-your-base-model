# 接口契约（冻结层）

> 改这个文件里的任何字段，必须先在群里说明，并同步改：
> `backend/shared/contracts.py`、`frontend/src/shared/types.ts`、`backend/tests/integration/`。

## 0. 通用约定

- 所有接口前缀 `/api`。
- 列表返回统一形状：

```json
{ "items": [], "total": 0, "page": 1, "page_size": 20 }
```

- 失败返回统一形状（前端按 `code` 分支，不匹配中文文案）：

```json
{ "error": { "code": "not_found", "message": "模型不存在: a/b", "detail": null } }
```

| code | HTTP | 含义 |
|---|---|---|
| `invalid_parameter` | 400 | 参数不合法（越界、未知枚举） |
| `not_found` | 404 | 快照 / 模型不存在 |
| `data_not_ready` | 409 | 尚未导入数据，或数据文件缺失 |
| `conflict` | 409 | 状态冲突 |

- 模型 ID 含斜杠，一律用查询参数传，前端用 `encodeURIComponent`。
- 关系方向固定为 **上游 → 下游**。
- 关系类型只有五种：`finetune` `adapter` `quantized` `merge` `unknown`。

## 1. 公共

### GET /api/health

```json
{ "status": "ok", "data_ready": true, "snapshot_id": "demo-2026-11",
  "model_count": 14, "relation_count": 12 }
```

数据库不存在或为空时返回 `data_ready: false`，不报 500。

### GET /api/meta

```json
{ "max_page_size": 100, "max_depth": 2, "default_graph_nodes": 100,
  "max_graph_nodes": 200, "rule_version": "rules-v2",
  "relation_types": ["finetune", "adapter", "quantized", "merge", "unknown"] }
```

## 2. 数据（A）

### POST /api/imports

| 字段 | 类型 | 说明 |
|---|---|---|
| `source` | `fixtures` \| `hubstats` \| `modeltree` | 数据源 |
| `limit` | int? | 最多导入多少个模型（hubstats / modeltree 有效） |
| `snapshot_id` | string? | 不传则用默认版本号 |

返回：

```json
{ "snapshot_id": "demo-2026-11", "source": "fixtures",
  "input_hash": "sha256…", "model_count": 14, "relation_count": 12,
  "dataset_link_count": 4, "created_at": "2026-11-23 09:00:00" }
```

同一 `snapshot_id` 重复导入不产生重复记录（关系表有唯一键）。

### GET /api/snapshots

`ItemList<Snapshot>`，按 `snapshot_date` 倒序。

### GET /api/snapshots/{snapshot_id}/stats

```json
{ "snapshot_id": "demo-2026-11", "model_count": 14, "relation_count": 12,
  "ghost_count": 1, "family_count": 3, "dataset_link_count": 4,
  "type_distribution": [{ "type": "finetune", "count": 7 }] }
```

### GET /api/datasets?snapshot_id=&limit=

`ItemList<{dataset_id, model_count, source_field}>`，按关联模型数倒序。

## 3. 目录（B）

### GET /api/models?q=&snapshot_id=&family=&include_ghost=&page=&page_size=

- `page_size` 上限 100；`page` 从 1 开始。
- 排序：`downloads` 倒序，空值排最后。

`ItemList<ModelSummary>`：

```json
{ "model_id": "Qwen/Qwen2.5-7B", "author": "Qwen", "pipeline": "text-generation",
  "library": "transformers", "downloads": 1200000, "downloads_all": 32000000,
  "likes": 2100, "created": "2024-09-17", "family": "qwen2.5", "ghost": false }
```

### GET /api/model?model_id=&snapshot_id=

`ModelSummary` 的全部字段，外加：

```json
{ "snapshot_id": "demo-2026-11",
  "datasets": [{ "dataset_id": "openai/gsm8k", "source_field": "datasets", "raw_value": "['openai/gsm8k']" }] }
```

`source_field` 必须保留：只展示“记录中的关联”，不推断训练用途。

## 4. 小图（B）

### GET /api/graph

| 参数 | 默认 | 约束 |
|---|---|---|
| `model_id` | 必填 | 根节点 |
| `snapshot_id` | 最新 | |
| `direction` | `both` | `upstream` / `downstream` / `both` |
| `depth` | 1 | 1–2，超过返回 400 |
| `relation_type` | 全部 | 五种之一，非法返回 400 |
| `limit` | 100 | 1–200 |

```json
{
  "snapshot_id": "demo-2026-11", "root": "someone/Merge-7B",
  "direction": "upstream", "depth": 2,
  "nodes": [{ "id": "Qwen/Qwen2.5-7B", "label": "Qwen/Qwen2.5-7B",
              "ghost": false, "family": "qwen2.5", "downloads": 1200000,
              "pipeline": "text-generation", "author": "Qwen" }],
  "edges": [{ "id": "rel_ab12", "source": "Qwen/Qwen2.5-Coder-7B",
              "target": "someone/Merge-7B", "type": "merge",
              "source_field": "baseModels" }],
  "truncated": false, "node_limit": 100, "node_count": 5, "edge_count": 4
}
```

规则：

- `nodes` / `edges` 的形状直接对齐 Cytoscape 的 `data` 字段，前端不做映射；
- 截断时 `truncated: true`，且保留离根最近的节点；
- 环不会死循环（`visited` 集合）；
- 上游属性缺失时保留节点并置 `ghost: true`。

## 5. 分析（D）

### GET /api/analysis?snapshot_id=

```json
{
  "snapshot_id": "demo-2026-11", "rule_version": "rules-v2", "scope_note": "…",
  "metrics": { "model_count": 14, "edge_count": 12, "unique_pair_count": 12,
               "parent_count": 8, "root_count": 3, "ghost_count": 1,
               "family_count": 3, "cyclic_node_count": 2 },
  "type_distribution": [{ "type": "finetune", "count": 7 }],
  "top_upstream": [{ "model_id": "Qwen/Qwen2.5-7B", "direct": 4, "total": 5,
                     "family": "qwen2.5" }],
  "family_distribution": [{ "family": "qwen2.5", "models": 5, "total_descendants": 0 }],
  "cases": [{ "title": "…", "model_id": "Qwen/Qwen2.5-7B", "note": "…" }]
}
```

口径：

- `edge_count`（带类型的关系条数）与 `unique_pair_count`（唯一上下游对）**必须分开显示**；
- `direct` 是直接下游数，`total` 是可达后代数（含间接），两者不可混用；
- `parent_count` = 有下游的模型数，`root_count` = 没有上游的模型数。

## 6. 待接入（C）

```text
GET /api/galaxy?family=&relation_type=&limit=
GET /api/galaxy/point?model_id=
```

返回预计算坐标，前端不算布局。由工作包 C 定义后补进本节。
