# 模型目录（任务 1）

**归属：任务 1（模型目录、数据与生态分析）。** 其他人不要改这个目录；需要改契约先提 Issue。

## 这里放什么

`/catalog` 页面：搜索、筛选、分页、详情面板、数据集关联、跳到谱系图。

- 后端：`backend/modules/catalog/`（`router.py`、`service.py`、`importer.py`）
- 接口：`GET /api/models`、`GET /api/model`、`POST /api/imports`、`GET /api/snapshots`、`GET /api/datasets`
- 测试：`tests/catalog/`

## v5 对任务 1 的要求

- 能搜到真实模型，并定位它的证据材料（快照、modelCard、仓库文件索引）；
- 向任务 3 提供模型 ID、快照和本地材料索引，向任务 4 提供声明边与快照；
- 自动补边后能看同快照差分，导出包含快照、筛选条件和证据 ID；
- 分析首版只做**按关系类型的核验汇总、受影响模型的直接下游差分、CSV**；
  多级后代与家族排名是扩展项，图形可视化归任务 2。

目录只管「有哪些模型、哪些声明」，不判定关系真伪。

## 怎么接

1. 读 `docs/CONTRACTS.md` 的接口契约；
2. 只 import `shared/`（后端）与 `@/shared`（前端）；
3. 页面已接进 `src/app/router.ts`，新增路由也只改这一行。
