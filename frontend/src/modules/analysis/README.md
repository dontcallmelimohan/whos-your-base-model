# 生态分析（工作包 D）

**归属：工作包 D。** 其他人不要改这个目录；需要改契约请提 Issue。

## 这里放什么

/analysis 页面：指标卡、上游/家族/作者三张榜、口径切换、案例。
- 接口：GET /api/analysis；
- 直接下游 ≠ 可达后代，两个口径要在页面上写清楚。

## 验收标准

- 关掉其他三个模块，本模块的页面 + 接口 + 样例测试仍能跑通；
- 只读 `shared/`（后端）或 `@/shared`（前端），不 import 其他人的模块；
- 有自己的测试目录：`backend/tests/analysis/`。

## 怎么开始

1. 读 `platform/docs/CONTRACTS.md` 里的接口契约；
2. 后端在 `backend/modules/analysis/` 建 `router.py`，在 `app.py` 加一行 `include_router`；
3. 前端在 `src/app/router.ts` 把 `PlaceholderPage` 换成自己的页面组件。
