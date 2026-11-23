# 任务 4：自动核验与谱系补全

**归属：任务 4。** 前端也归这个任务：`frontend/src/modules/evidence/`。
候选和证据由任务 3 写入，这里只消费它们。

## 交付

| 能力 | 落点 | 状态 |
|---|---|---|
| 候选列表 / 详情 / 复核记录 | `service.py`、`router.py` | 可用 |
| 四类结论的判定 | `judge.py` → `judge_relation` | 接口占位 |
| 自动入图状态 | `relations.status = 'confirmed'` + `shared/graph_read.py` 的补全视图 | 可用（人工确认路径） |
| 本地批处理入口 | `batch.py` | 接口占位 |
| 证据相关迁移 | `shared/migrations/`（新文件，只加不改） | 已有 `002_evidence.sql` |

## 判定规矩

| 结论 | 何时给 | 能否入图 |
|---|---|---|
| support | 原文/配置明确支持两端、方向、类型 | 能 |
| refute | 原文明确指向别的上游，或明确否认 | 否 |
| conflict | 已检查来源互相矛盾，或与已有声明冲突 | 否 |
| insufficient | 没找到 / 指向不清 / 来源不可访问 | 否 |

- 已有声明关系的异议只作为核验记录展示，**基线图继续用原始声明**；
- 证据版本与快照不一致时单独展示，不参与同快照差分；
- 自动入图不需要人工审批，人工复核入口保留为兜底。

## 待办（按 v5 节奏）

1. 第 1 天：固定四类证据样例（支持 / 反驳 / 冲突 / 不足），写进
   `docs/EVIDENCE_HANDOFF.md` 并落到 `tests/evidence/verification/`；
2. 第 2–3 天：`judge_relation` 对固定样例稳定输出；
3. 第 4–5 天：单模型 / 单条边核验入口跑通，结论落库，support 自动进补全图；
4. 第 6–7 天：真实案例走通核验 → 补全图 → 差分 → 导出；
5. 第 8–10 天：`batch.py` 批处理 + 幂等校验（重复运行不重复加边）；
6. 迁移编号用新号段（如 `020_verification_*.sql`），只加表/列，不改已有表。

## 测试

```bash
make test
.venv/bin/python -m pytest tests/evidence/verification -q
```
