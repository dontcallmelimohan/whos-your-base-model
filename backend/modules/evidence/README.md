# 证据模块（任务 3 + 任务 4）

一个模块、两个工作包，按「谁产出候选、谁产出结论」拆目录：

| 目录 | 归属 | 产出 |
|---|---|---|
| `retrieval/` | 任务 3 证据检索与候选提取 | 来源读取、候选关系、证据片段与检索记录 |
| `verification/` | 任务 4 自动核验与谱系补全 | 判定结论、核验记录、入图状态、批处理 |

`router.py` 只是聚合层，`app.py` 不需要知道内部怎么拆。

```text
evidence/
  router.py          聚合 retrieval + verification（两边都不改这个文件）
  retrieval/
    sources.py       本地字段 → modelCard/配置 → 线上补查（失败原因要留下）
    extract.py       明确关键词规则 → 候选 + 证据（quote/path/locator/revision）
    router.py        POST /api/extractions
  verification/
    service.py       候选列表、关系详情、复核记录
    judge.py         四类结论（接口占位：支持 / 反驳 / 冲突 / 不足）
    batch.py         本地批处理入口（接口占位）
    router.py        /api/candidates、/api/relations/{id}
```

## 共同约定

1. **候选 ≠ 结论。** 只有任务 4 判为 support 且来源无冲突、版本对齐的关系才进补全图。
2. **每条证据都要能回指。** 原文或配置值、文件路径/链接、行号或字段名、commit SHA 或快照标识。
3. **访问失败要返回，不能吞。** 未找到、指向不清、来源不可访问是三种不同的「证据不足」。
4. **重复运行幂等。** 关系唯一键 `snapshot_id + parent + child + relation_type`，证据 ID 由内容位置派生，`INSERT OR IGNORE`。
5. **版本对齐。** 线上证据与快照不同版本时单独展示，不计入同快照差分。

交接字段、四类结论样例与入图门槛见 [`docs/EVIDENCE_HANDOFF.md`](../../../docs/EVIDENCE_HANDOFF.md)。

## 本地怎么跑

```bash
cd backend
python -m scripts.seed
python -m uvicorn app:app --reload --port 8000
curl -X POST localhost:8000/api/extractions -H 'content-type: application/json' -d '{"source":"fixtures"}'
curl 'localhost:8000/api/candidates?status=pending'
```

测试：`tests/evidence/retrieval/`（任务 3）、`tests/evidence/verification/`（任务 4）。
