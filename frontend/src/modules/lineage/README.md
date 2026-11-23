# 谱系探索与可视化（任务 2）

**归属：任务 2（谱系探索与可视化）。** 后端还包含 `backend/shared/graph_read.py`，
其他模块读图必须走它，不要各自拼 SQL。

## 这里放什么

`/lineage` 页面：局部关系图、上下游展开、关系类型筛选、点节点、点边看证据、
基线图（declared）与补全图（completed）切换、大分支分批展开。

- 后端：`backend/modules/lineage/`（`router.py`、`traversal.py`）+ `shared/graph_read.py`
- 接口：`GET /api/graph?model_id=&direction=&depth=&relation_type=&view=`
- 测试：`tests/lineage/`

## v5 验收对应

| 要求 | 落点 |
|---|---|
| 上下游展开、类型筛选 | `LineagePage.vue` 的控件 + `/api/graph` 参数 |
| 点击节点 / 边 | `GraphCanvas.vue`、`DetailPanel.vue` |
| 基线图 / 补全图切换 | `view=declared\|completed`，过滤规则只在 `graph_read.py` |
| 点一条边跳到证据 | 边详情按 `relation_id` 跳 `/evidence`，证据由任务 3/4 提供 |
| 上千下游先显示总数再分批展开 | 先返回 `edge_count` / `truncated`，再按 `limit` 拉取 |

## 边界

- 只读 `shared/`（后端）与 `@/shared`（前端）；
- 补全图的判定不在这里：任务 4 写状态，这里只按 `graph_read` 的口径读；
- 统计模块复用同一套 `view_filter`，改口径要同步任务 1。
