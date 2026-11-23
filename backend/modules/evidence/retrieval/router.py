"""任务 3：检索与候选提取接口。

只负责「读来源、提候选、存证据」；判定与入图在任务 4 的 verification/。
"""

from __future__ import annotations

from fastapi import APIRouter

from modules.evidence.retrieval import extract
from shared.contracts import ExtractionRequest, ExtractionResult

router = APIRouter(prefix="/api", tags=["retrieval"])


@router.post("/extractions", response_model=ExtractionResult)
def run_extraction(payload: ExtractionRequest) -> ExtractionResult:
    """按规则扫本地模型卡，写入候选关系与证据片段（幂等）。"""
    result = extract.extract_candidates(payload.snapshot_id, payload.source)
    return ExtractionResult(**result)
