# 大图 Galaxy（扩展，不在 v5 验收范围）

**状态：保留占位。** v5 的图形可视化集中在任务 2 的局部图；全量点云是扩展项，
认领前先说明，不要为它改公共契约。

## 这里放什么

全局点云接口：`/api/galaxy`、`/api/galaxy/point`（未实现）。

- 坐标在离线阶段算好（复用 model-family-tree 的 galaxy 布局），接口只读结果；
- 前端不负责布局，只负责渲染与交互；
- 依赖 `shared/` 的契约；不 import 其他 modules。

## 验收标准（若认领）

- 首屏 ≤ 5MB、≤ 3s 可交互，超过 20 万点降采样；
- 只读 `shared/`（后端）或 `@/shared`（前端），不 import 其他人的模块；
- 测试放 `tests/galaxy/`，并在本文件更新状态。

## 怎么开始

1. 读 `docs/CONTRACTS.md` 第 6 节；
2. 后端在 `backend/modules/galaxy/` 建 `router.py`，在 `app.py` 加一行 `include_router`；
3. 前端在 `src/app/router.ts` 把 `PlaceholderPage` 换成自己的页面组件。
