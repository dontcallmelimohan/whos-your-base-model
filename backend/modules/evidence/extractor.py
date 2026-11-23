"""工作包 3：从模型卡正文发现候选依赖。

只做少量明确规则，宁可少召回，也不制造无法核验的候选：

    merge       «merged from A and B» / «merge of A and B»
    finetune    «fine-tuned from A» / «finetuned on A»
    based_on    «based on A»
    adapter     «LoRA adapter for A»

命中的每一句都原样存档（quote + 行号），作为证据；规则输出不是结论，
必须经人工核验后才进入补全图。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from shared import config, graph_read
from shared.db import connect, init_schema
from shared.errors import not_found, not_ready

# 模型 ID：org/name，允许 . - _
MODEL_ID = r"([A-Za-z0-9][\w.-]*/[\w.-]+)"

RULES: list[tuple[str, str, re.Pattern[str]]] = [
    ("r_merge_from", "merge", re.compile(rf"merg(?:e|ed)\s+(?:of|from)\s+{MODEL_ID}", re.I)),
    ("r_finetuned_from", "finetune", re.compile(rf"fine-?tuned\s+(?:from|on)\s+{MODEL_ID}", re.I)),
    ("r_based_on", "finetune", re.compile(rf"based\s+on\s+{MODEL_ID}", re.I)),
    ("r_adapter_for", "adapter", re.compile(rf"(?:LoRA|adapter)\s+(?:for|of)\s+{MODEL_ID}", re.I)),
]

# 一句话里可能再出现第二个上游：「A and B」
SECOND_PARENT = re.compile(rf"(?:and|,)\s*(?:the\s+)?{MODEL_ID}", re.I)


def _evidence_id(snapshot_id: str, relation_id: str, rule_id: str, line_no: int) -> str:
    key = f"{snapshot_id}|{relation_id}|{rule_id}|{line_no}"
    return "ev_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _relation_id(snapshot_id: str, parent: str, child: str, rtype: str) -> str:
    key = f"{snapshot_id}|{parent}|{child}|{rtype}"
    return "rel_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def load_cards(path: Path | None = None) -> list[dict]:
    target = path or (config.fixtures_dir() / "model_cards.json")
    if not target.exists():
        raise not_ready(f"模型卡样例不存在: {target}")
    payload = json.loads(target.read_text(encoding="utf-8"))
    return payload.get("cards", [])


def extract_candidates(snapshot_id: str | None = None, source: str = "fixtures") -> dict:
    """跑一遍规则，写入候选关系与证据。重复运行不会产生重复记录。"""
    if source != "fixtures":
        raise not_ready(
            "当前只实现了 fixtures 源的规则抽取",
            {"allowed": ["fixtures"], "hint": "真实快照可用 modelbiome 的 modelCard 字段扩展"},
        )

    conn = connect()
    try:
        init_schema(conn)
        snapshot = graph_read.get_snapshot(conn, snapshot_id)
        sid = snapshot["id"]

        created_candidates = 0
        created_evidence = 0
        skipped_existing = 0
        scanned = 0

        for card in load_cards():
            child = card["model_id"]
            if graph_read.get_model(conn, sid, child) is None:
                continue  # 模型不在这个快照里，跳过
            scanned += 1

            for line_no, line in enumerate(card.get("text", "").splitlines(), start=1):
                for rule_id, rtype, pattern in RULES:
                    match = pattern.search(line)
                    if not match:
                        continue
                    parents = [match.group(1)]
                    second = SECOND_PARENT.search(line, match.end() - 1)
                    if second:
                        parents.append(second.group(1))

                    for parent in dict.fromkeys(parents):
                        if parent == child:
                            continue
                        rel_id = _relation_id(sid, parent, child, rtype)
                        existing = conn.execute(
                            "SELECT origin, status FROM relations WHERE id = ?", (rel_id,)
                        ).fetchone()
                        if existing and existing["origin"] == "declared":
                            skipped_existing += 1
                            continue

                        if existing is None:
                            conn.execute(
                                """INSERT INTO relations
                                     (id, snapshot_id, parent_id, child_id, relation_type,
                                      is_baseline, source_field, origin, status)
                                   VALUES (?, ?, ?, ?, ?, 0, ?, 'candidate', 'pending')""",
                                (rel_id, sid, parent, child, rtype, rule_id),
                            )
                            created_candidates += 1

                        quote = line.strip()[:400]
                        ev_id = _evidence_id(sid, rel_id, rule_id, line_no)
                        cursor = conn.execute(
                            """INSERT OR IGNORE INTO evidence
                                 (id, relation_id, snapshot_id, source_type, source_path,
                                  locator, quote, revision)
                               VALUES (?, ?, ?, 'model_card_text', ?, ?, ?, NULL)""",
                            (
                                ev_id,
                                rel_id,
                                sid,
                                card.get("path", "README.md"),
                                f"L{line_no}",
                                quote,
                            ),
                        )
                        created_evidence += cursor.rowcount

        conn.commit()
        return {
            "snapshot_id": sid,
            "source": source,
            "scanned_models": scanned,
            "created_candidates": created_candidates,
            "created_evidence": created_evidence,
            "skipped_declared": skipped_existing,
        }
    finally:
        conn.close()
