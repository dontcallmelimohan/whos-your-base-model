# 核验与补全（任务 4）

**归属：任务 4（自动核验与谱系补全）。** 页面、接口调用和展示归任务 4；
证据字段的中文文案、来源类型和样例响应由任务 3 在 `fields.ts` 里维护，改之前先对一下。

## 这里放什么

`/evidence` 页面：候选列表与状态筛选、单条关系详情（原文 + 出处 + 版本）、
运行核验、结论与依据、补全入图提示。

- 后端：`backend/modules/evidence/verification/`（`router.py`、`service.py`、`judge.py`、`batch.py`）
- 接口：`POST /api/extractions`（任务 3 触发检索）、`GET /api/candidates`、
  `GET /api/relations/{id}`、`POST /api/relations/{id}/reviews`
- 测试：`tests/evidence/verification/`

## v5 验收对应

- 固定证据样例覆盖支持 / 反驳 / 冲突 / 证据不足四类结论；
- 真实案例里 support 的新增边自动出现在补全图；
- 重复运行不会重复加边（关系唯一键 + 状态幂等）。

## 展示约定

- 原文、文件路径/链接、行号、revision 必须同屏可见；
- 未对齐版本的证据单独分组，页面上标注「不计入同快照差分」；
- 证据不足要写清是哪一种：未找到 / 指向不清 / 来源不可访问。

字段与样例见 `docs/EVIDENCE_HANDOFF.md` 与 `fields.ts`。
