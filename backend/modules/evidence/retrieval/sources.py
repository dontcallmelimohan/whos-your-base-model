"""任务 3：证据来源读取（本地字段 → 本地正文/配置 → 必要时补查 Hugging Face）。

这里只负责「把来源读出来」，不判断关系是否成立；判定在任务 4。

来源顺序（v5 数据流）：

    1. 本地字段：快照里已存的父模型字段与模型元数据；
    2. 本地正文/配置：快照保存的 modelCard（README）、config.json；
    3. 线上补查：目标仓库的 README 与相关配置，只取做核验所需的最少文件。

每条来源都带 ``path`` 与 ``revision``：revision 是 commit SHA 或快照标识，
用来判断证据与快照是否同版本。不同版本的证据由任务 4 单独展示，
不计入同快照差分（见 docs/EVIDENCE_HANDOFF.md）。

当前实现：本地 modelCard 样例（fixtures/model_cards.json）。
其余来源留了明确的入口，由认领者按 v5 补上，不要静默返回空列表。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from shared import config
from shared.errors import not_ready

# source_type 取值与 002_evidence.sql 的注释保持一致
SOURCE_TYPES = ("model_field", "model_card_text", "model_card_yaml", "config")

# 线上补查只取这些文件；多了既慢也没必要
HF_FILES = ("README.md", "config.json")

LOCAL_CARD_INDEX = "fixtures/model_cards.json"


@dataclass(frozen=True)
class SourceDocument:
    """一份可被规则检索的文本来源。"""

    model_id: str
    source_type: str
    path: str
    text: str
    revision: str | None = None
    locator_prefix: str = ""


@dataclass(frozen=True)
class SourceFailure:
    """访问失败的原因，要原样返回给核验页，不能吞掉。"""

    model_id: str
    path: str
    reason: str  # not_found / access_denied / timeout / not_in_snapshot / no_card
    detail: str | None = None


@dataclass
class SourceScan:
    """一次检索的范围与结果：任务 4 需要知道「检查了哪些来源、哪些打不开」。"""

    documents: list[SourceDocument] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    failures: list[SourceFailure] = field(default_factory=list)


def load_local_cards(path: Path | None = None) -> list[dict]:
    """读取本地 modelCard 索引（快照里保存的正文）。"""
    target = path or (config.fixtures_dir() / "model_cards.json")
    if not target.exists():
        raise not_ready(f"模型卡样例不存在: {target}")
    payload = json.loads(target.read_text(encoding="utf-8"))
    return payload.get("cards", [])


def local_documents(card: dict) -> list[SourceDocument]:
    """把一条 modelCard 记录转成来源文档。

    之后接入 Model Biome 快照时，只需要把「card 从哪来」换掉，
    下游的规则抽取与证据写入不用改。
    """
    model_id = card["model_id"]
    docs = [
        SourceDocument(
            model_id=model_id,
            source_type="model_card_text",
            path=card.get("path", "README.md"),
            text=card.get("text", ""),
            revision=card.get("revision"),
        )
    ]
    for config_path, value in (card.get("config") or {}).items():
        docs.append(
            SourceDocument(
                model_id=model_id,
                source_type="config",
                path=config_path,
                text=json.dumps(value, ensure_ascii=False),
                revision=card.get("revision"),
                locator_prefix=config_path,
            )
        )
    return docs


def collect_local_documents(model_ids: set[str] | None = None) -> SourceScan:
    """读本地模型卡；``model_ids`` 用于只看当前快照里的模型。"""
    scan = SourceScan()
    for card in load_local_cards():
        if model_ids is not None and card["model_id"] not in model_ids:
            continue
        if not card.get("text"):
            scan.failures.append(
                SourceFailure(card["model_id"], card.get("path", "README.md"), "no_card")
            )
            continue
        docs = local_documents(card)
        scan.documents.extend(docs)
        scan.checked.extend(doc.path for doc in docs)
    return scan


def collect_hf_documents(
    model_id: str,
    files: tuple[str, ...] = HF_FILES,
    revision: str | None = None,
) -> SourceScan:
    """线上补查：只读目标仓库的 README 与配置文件。

    TODO(任务 3)：接 huggingface_hub，按 revision 取文件；403/404/超时
    分别记成 access_denied / not_found / timeout，写进 SourceFailure。
    在实现之前显式报错，避免上层把「没查」当成「没证据」。
    """
    raise not_ready(
        "Hugging Face 线上补查尚未实现（任务 3）",
        {"model_id": model_id, "files": list(files), "revision": revision},
    )
