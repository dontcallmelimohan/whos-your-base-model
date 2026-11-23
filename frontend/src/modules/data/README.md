# 数据管理（任务 1）

**归属：任务 1（模型目录、数据与生态分析）。**

## 这里放什么

`/data` 页面：导入（fixtures / hubstats / modeltree）、快照列表、快照概况、数据集关联。

- 后端：`backend/modules/catalog/data_router.py`、`data_service.py`、`importer.py`
- 接口：`POST /api/imports`、`GET /api/imports`、`GET /api/snapshots`、
  `GET /api/snapshots/{id}/stats`、`GET /api/datasets`
- 测试：`tests/catalog/test_data.py`

## v5 相关约定

- 快照 ID 是后面所有证据与差分的锚点：核验记录、证据 revision、CSV 都要带；
- 导入只写声明（`is_baseline = 1`），核验新增边由任务 4 写入，不在这里混进去；
- 换数据版本后，任务 1/2 的图和统计必须用同一个快照，避免「图变了统计没变」。
