# 大图 Galaxy（工作包 C）

**归属：工作包 C。** 其他人不要改这个目录；需要改契约请提 Issue。

## 这里放什么

全局点云接口：/api/galaxy、/api/galaxy/point。
- 坐标在离线阶段算好（复用 model-family-tree 的 galaxy 布局），接口只读结果；
- 前端不负责布局，只负责渲染与交互。
- 依赖：shared/ 的契约；不 import 其他 modules。

## 验收标准

- 关掉其他三个模块，本模块的页面 + 接口 + 样例测试仍能跑通；
- 只读 `shared/`（后端）或 `@/shared`（前端），不 import 其他人的模块；
- 有自己的测试目录：`backend/tests/galaxy/`。

## 怎么开始

1. 读 `platform/docs/CONTRACTS.md` 里的接口契约；
2. 后端在 `backend/modules/galaxy/` 建 `router.py`，在 `app.py` 加一行 `include_router`；
3. 前端在 `src/app/router.ts` 把 `PlaceholderPage` 换成自己的页面组件。
