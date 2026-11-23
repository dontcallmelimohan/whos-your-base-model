"""任务 4：核验判定（接口占位）。

结论只有四类，和 v5 一致：

    support       原文/配置明确支持这条关系的两端、方向与类型
    refute        原文/配置明确指向另一个上游，或明确否认这条关系
    conflict      已检查的来源之间互相矛盾（含与已有声明冲突）
    insufficient  证据不足，再细分：
                    not_found    没找到证据
                    ambiguous    文档指向不清（只提到名字、没有方向/类型）
                    unreachable  来源不可访问

入图门槛（v5 第 3 节）：

    * 结论为 support；
    * 来源之间没有 conflict；
    * 证据与当前快照同版本（revision 对齐）；未对齐的单独展示，不计入同快照差分。

自动入图不经过人工审批；已有声明关系的异议只作为核验记录展示，
基线图仍使用原始声明。

TODO(任务 4)：实现 ``judge_relation``。第 1 天先固定四类证据样例，
让这里对样例稳定输出，再接单模型 / 单条边与本地批处理。
在实现之前显式报错，避免上层把「还没判」当成「没证据」。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from enum import Enum

from shared.errors import not_ready


class Verdict(str, Enum):
    SUPPORT = "support"
    REFUTE = "refute"
    CONFLICT = "conflict"
    INSUFFICIENT = "insufficient"


class InsufficientReason(str, Enum):
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    UNREACHABLE = "unreachable"


# 只有 support 能自动进补全图
PUBLISHABLE: frozenset[Verdict] = frozenset({Verdict.SUPPORT})


@dataclass(frozen=True)
class VerdictResult:
    """一次核验的结论，也是核验页展示与差分计算的最小单位。"""

    relation_id: str
    verdict: Verdict
    reason: str
    evidence_ids: list[str] = field(default_factory=list)
    insufficient_reason: InsufficientReason | None = None
    rule_id: str | None = None
    rule_version: str | None = None
    version_aligned: bool = True


def judge_relation(conn: sqlite3.Connection, relation_id: str) -> VerdictResult:
    """判定一条关系，并返回带证据 ID 的结论。"""
    raise not_ready(
        "自动核验规则尚未实现（任务 4）",
        {
            "relation_id": relation_id,
            "stage": "judge",
            "hint": "先跑 POST /api/extractions 拿到候选与证据，再按 docs/EVIDENCE_HANDOFF.md 的样例实现规则",
        },
    )
