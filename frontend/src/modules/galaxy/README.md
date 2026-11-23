# 大图 Galaxy（扩展，不在 v5 验收范围）

**状态：保留占位。** v5 的图形可视化集中在任务 2 的局部图；全量点云是扩展项，
认领前不要为它改公共契约。

## 这里放什么

`/galaxy` 页面（占位）：全量点云、家族着色、缩放平移、点击跳到局部图。

- 后端：`backend/modules/galaxy/`
- 接口：`GET /api/galaxy`（未实现，见 `docs/CONTRACTS.md` 第 6 节）
- 若认领：测试放 `tests/lineage/` 或新开 `tests/galaxy/`，并在 README 里写明。

## 边界

- 只读 `shared/`（后端）与 `@/shared`（前端）；
- 首屏 ≤ 5MB、≤ 3s 可交互，超过 20 万点降采样；
- 大分支「先显示总数再分批展开」属于任务 2 的验收，不要等大图。
