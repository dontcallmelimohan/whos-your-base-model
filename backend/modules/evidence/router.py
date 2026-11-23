"""证据模块路由聚合。

拆成两个子路由，各自归一个工作包：

    retrieval/router.py      任务 3：POST /api/extractions
    verification/router.py   任务 4：/api/candidates、/api/relations/{id}

`app.py` 只 import 这里的 `router`，两个认领者互不改对方的文件。
"""

from __future__ import annotations

from fastapi import APIRouter

from modules.evidence.retrieval.router import router as retrieval_router
from modules.evidence.verification.router import router as verification_router

router = APIRouter()
router.include_router(retrieval_router)
router.include_router(verification_router)
