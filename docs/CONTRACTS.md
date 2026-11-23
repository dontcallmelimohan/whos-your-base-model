# 接口契约（冻结层）

> 改这个文件里的任何字段，必须先在群里说明，并同步改：
> `backend/shared/contracts.py`、`frontend/src/shared/types.ts`、`tests/integration/`。
> 证据相关的字段与判定约定另见 `docs/EVIDENCE_HANDOFF.md`。

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

## 2. 数据（任务 1）

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

## 3. 目录（任务 1）

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

## 4. 谱系图（任务 2）

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

## 5. 分析（任务 1）

### GET /api/analysis?snapshot_id=

```json
{
  "snapshot_id": "demo-2026-11", "rule_version": "rules-v2", "scope_note": "…",
  "metrics": { "model_count": 14, "edge_count": 12, "unique_pair_count": 12,
               "parent_count": 8, "root_count": 3, "ghost_count": 1,
               "family_count": 3, "cyclic_node_count": 2 },
  "concentration": { "hhi": 0.1806, "hhi_scaled": 1806.0,
                     "top10_share": 0.75, "parent_count": 8 },
  "data_quality": { "ghost_ratio": 0.125, "ghost_parent_count": 1,
                    "cyclic_node_count": 2 },
  "type_distribution": [{ "type": "finetune", "count": 7 }],
  "top_upstream": [{ "model_id": "Qwen/Qwen2.5-7B", "direct": 4, "total": 5,
                     "family": "qwen2.5" }],
  "family_distribution": [{ "family": "qwen2.5", "models": 5, "total_descendants": 0 }],
  "cases": [{ "title": "…", "model_id": "Qwen/Qwen2.5-7B", "note": "…" }]
}
```

口径：

- `hhi` = Σ (某上游直接下游数 ÷ 关系总数)²，`hhi_scaled` = hhi × 10000；
  越低越分散，10000 表示完全垄断；
- `top10_share` = 前 10 上游的直接下游数之和 ÷ 关系总数；
- `ghost_ratio` = 有下游但属性未收录的上游数 ÷ 全部上游数；
  导入子集时该值会偏高，页面需注明这是范围问题而非生态缺失；
- `cyclic_node_count` 只统计**互相指向的二元环**，不做全图闭包（成本考虑）；
- `edge_count`（带类型的关系条数）与 `unique_pair_count`（唯一上下游对）**必须分开显示**；
- `top_upstream` 按 `direct` 降序；`direct` 是直接下游数，`total` 是可达后代数（含间接），两者不可混用；
- `parent_count` = 有下游的模型数，`root_count` = 没有上游的模型数。

## 6. 待接入（扩展，不在 v5 验收范围）

```text
GET /api/galaxy?family=&relation_type=&limit=
GET /api/galaxy/point?model_id=
```

返回预计算坐标，前端不算布局。认领扩展项后再定义并补进本节。

## 7. 证据检索与核验（任务 3 产出，任务 4 判定/记录）

> 候选与证据由任务 3 写入；`/api/candidates`、`/api/relations/{id}` 与复核记录归任务 4。
> 四类结论、版本对齐与入图门槛见 `docs/EVIDENCE_HANDOFF.md`。

### POST /api/extractions

对指定快照跑规则抽取。请求：

```json
{ "snapshot_id": "demo-2026-11", "source": "fixtures" }
```

返回：

```json
{ "snapshot_id": "demo-2026-11", "source": "fixtures", "scanned_models": 4,
  "created_candidates": 2, "created_evidence": 2, "skipped_declared": 3 }
```

重复运行不产生重复记录；`skipped_declared` 是「正文提到的上游已在声明里」的反例计数。

### GET /api/candidates?snapshot_id=&status=&page=&page_size=

`status` 取 `pending` / `confirmed` / `rejected` / `unknown`，不传则全部。

```json
{ "items": [{ "relation_id": "rel_ab12", "parent_id": "Qwen/Qwen2.5-7B-Instruct",
              "child_id": "someone/Merge-7B", "relation_type": "merge",
              "origin": "candidate", "status": "pending",
              "source_field": "r_merge_from", "evidence_count": 1 }],
  "total": 2, "page": 1, "page_size": 20 }
```

### GET /api/relations/{relation_id}

```json
{ "relation": { "...": "同上" },
  "evidence": [{ "id": "ev_1", "source_type": "model_card_text",
                 "source_path": "README.md", "locator": "L3",
                 "quote": "This model is a merge of …", "revision": null }],
  "reviews": [{ "id": 1, "decision": "confirmed", "note": "原文明确",
                "reviewer": null, "created_at": "2026-11-23 11:20:00" }] }
```

`revision` 为空表示「仅有数据快照」，页面不能写成文件提交版本。

### POST /api/relations/{relation_id}/reviews

```json
{ "decision": "confirmed", "note": "README 原文明确" }
```

- 只允许核验 `origin=candidate` 的关系，声明关系返回 400；
- 核验记录**追加**，最新一条决定 `status`；
- 返回更新后的 `RelationDetail`。

## 8. 对比与导出（任务 1）

### GET /api/analysis?view=declared|completed

`declared` 只看模型卡声明；`completed` 额外包含 `status=confirmed` 的候选。
过滤规则由 `backend/shared/graph_read.py`（任务 2）统一提供，图与统计共用。

### GET /api/diff?snapshot_id=

```json
{ "snapshot_id": "demo-2026-11", "rule_version": "rules-v2",
  "added_edges": [{ "relation_id": "rel_ab12", "parent_id": "Qwen/Qwen2.5-7B-Instruct",
                    "child_id": "someone/Merge-7B", "relation_type": "merge",
                    "status": "confirmed" }],
  "pending_count": 1,
  "metrics": { "edge_count": { "declared": 12, "completed": 13, "delta": 1 } } }
```

固定返回 `edge_count`、`unique_pair_count`、`parent_count`、`hhi_scaled`、`top10_share` 五项。
v5 首版分析必须包含：按关系类型的核验汇总、受影响模型的直接下游差分、可导出的 CSV；
多级后代与家族排名是扩展项。

### GET /api/analysis/export.csv?snapshot_id=&view=

`text/csv`，首部是 `#` 注释行（快照、视图、规则版本、计数），随后是：

```text
rank,model_id,family,direct,total,share_of_edges
```

导出内容必须能凭注释行复算，不能只给数字。

## 9. v5 待增接口（未冻结）

v5 要求「单模型核验 / 单条边核验」和「核验结论查询」，目前还没有对应接口。
拟议形状（需四人同意后再写进契约与实现）：

```text
POST /api/verifications          body: { snapshot_id, model_id? , relation_id? }
GET  /api/verifications?relation_id=&snapshot_id=
```

返回 `VerdictRecord`（字段见 `docs/EVIDENCE_HANDOFF.md` 第 3 节）。
在定稿前，前端不要依赖这两个路径。
