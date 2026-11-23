# 任务 3：证据检索与候选提取

**归属：任务 3。** 只改 `retrieval/`（以及 `frontend/src/modules/evidence/fields.ts` 这类字段定义）。
判定、入图、批处理在 `../verification/`，不要在这里写结论。

## 交付

| 能力 | 落点 | 状态 |
|---|---|---|
| 本地 modelCard 正文读取 | `sources.py` → `collect_local_documents` | 可用（fixtures） |
| 明确规则的候选提取 | `extract.py` → `extract_candidates` | 可用（4 条规则） |
| 本地配置（config.json）读取 | `sources.py` → `local_documents` | 可用（随 card 附带 config 时） |
| 快照字段（五个父模型字段）读取 | `sources.py` | 待接 Model Biome 快照 |
| 线上补查 Hugging Face | `sources.py` → `collect_hf_documents` | 未实现，显式报错 |
| 检索记录（检查了哪些来源、失败原因） | `sources.SourceScan` | 结构已定，待接到接口 |

## 验收对应

- 能从真实模型卡提取**缺失**的上游候选及证据 → 用答辩案例
  `stabilityai/stable-video-diffusion-img2vid-xt` 的 README 验证；
- 也能为已有边收集支持或冲突材料 → 同一条关系可能有多句/多来源；
- 返回已检查的来源和访问失败原因 → `SourceScan.checked` / `failures`。

## 规则边界

只认明确写法，宁可少召回：

- `merged from X` / `merge of X` → merge
- `fine-tuned from X` / `finetuned on X` / `based on X` → finetune
- `LoRA adapter for X` / `adapter of X` → adapter

拿到候选后不要自己改成结论；`quote` 保留原文（截断到 400 字符），
`locator` 用行号，`revision` 有 commit SHA 就写，没有就留空并在页面标注快照。

## 待办（按 v5 节奏）

1. 第 2–3 天：把快照里的 `modelCard` / 父模型字段接进 `sources.py`；
2. 第 8–10 天：`collect_hf_documents` 用 `huggingface_hub` 取 README/config.json，
   403/404/超时分别记为 `access_denied` / `not_found` / `timeout`；
3. 用 `docs/EVIDENCE_HANDOFF.md` 的样例补测试到 `tests/evidence/retrieval/`。

## 测试

```bash
make test          # 全量
.venv/bin/python -m pytest tests/evidence/retrieval -q
```
