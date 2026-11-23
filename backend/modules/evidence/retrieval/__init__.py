"""任务 3：证据检索与候选提取。

| 文件 | 归谁 | 做什么 |
|---|---|---|
| `sources.py` | 任务 3 | 读本地字段、modelCard 正文与配置；线上补查 Hugging Face |
| `extract.py` | 任务 3 | 用明确关键词规则提取候选上游，原文与出处一起落库 |
| `router.py` | 任务 3 | `POST /api/extractions` |

**不做判定。** 支持 / 反驳 / 来源冲突 / 证据不足的结论由任务 4 产出；
候选只是「值得去核验的线索」，不能直接进补全图。

交接给任务 4 的字段、版本与失败原因见 `docs/EVIDENCE_HANDOFF.md`。
"""

from __future__ import annotations

__all__ = ["extract", "router", "sources"]
