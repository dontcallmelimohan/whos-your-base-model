"""任务 4：自动核验与谱系补全。

| 文件 | 做什么 |
|---|---|
| `service.py` | 候选查询、关系详情、核验记录（人工复核仍保留） |
| `judge.py` | 单条边判定：支持 / 反驳 / 冲突 / 证据不足（接口占位） |
| `batch.py` | 本地批处理入口（接口占位） |
| `router.py` | `/api/candidates`、`/api/relations/{id}`、复核记录 |

入图状态沿用 `relations.status = 'confirmed'`；补全视图的读取规则在
`shared/graph_read.py`（任务 2 维护），图和统计共用同一套过滤条件。
"""
