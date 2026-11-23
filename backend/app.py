"""平台入口：只注册路由，不写业务逻辑。

模块归属（v5 分工，谁改哪一块）：
    任务 1  目录、数据与分析  modules/catalog   /api/imports /api/snapshots /api/datasets
                                                  /api/models /api/model
                              modules/analysis  /api/analysis /api/diff /api/analysis/export.csv
    任务 2  谱系与可视化      modules/lineage   /api/graph（view=declared|completed）
    任务 3  检索与候选提取    modules/evidence/retrieval
                                                  /api/extractions
    任务 4  核验与补全        modules/evidence/verification
                                                  /api/candidates /api/relations/{id}
                                                  /api/relations/{id}/reviews
    扩展    大图 Galaxy       modules/galaxy    待接入，不在 v5 验收范围

公共部分（app、shared/contracts.py、shared/db.py）由四人共同约定；
shared/graph_read.py 由任务 2 维护。其他人只加一行 include_router。
"""

from __future__ import annotations

import sqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from modules.analysis.router import router as analysis_router
from modules.catalog.router import router as catalog_router
from modules.catalog.data_router import router as data_router
from modules.evidence.router import router as evidence_router
from modules.lineage.router import router as lineage_router
from shared import config, graph_read
from shared.contracts import HealthResponse, MetaResponse
from shared.db import connect, init_schema, tables_present
from shared.errors import install_error_handlers


def _health() -> HealthResponse:
    conn = connect()
    try:
        if "snapshots" not in tables_present(conn):
            return HealthResponse(status="ok", data_ready=False)
        init_schema(conn)  # 幂等：缺表时补上
        snapshot_id = graph_read.default_snapshot_id(conn)
        if snapshot_id is None:
            return HealthResponse(status="ok", data_ready=False)
        return HealthResponse(
            status="ok",
            data_ready=True,
            snapshot_id=snapshot_id,
            model_count=graph_read.count_models(conn, snapshot_id),
            relation_count=graph_read.count_relations(conn, snapshot_id),
        )
    except sqlite3.Error:
        return HealthResponse(status="ok", data_ready=False)
    finally:
        conn.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI 模型供应链交互与分析平台",
        version="0.2.0",
        description=(
            "开放模型谱系查询与证据核验平台。四个工作包：目录与数据/分析、谱系图、证据检索、自动核验与补全。"
            "接口契约见 docs/CONTRACTS.md。"
        ),
    )
    install_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(data_router)
    app.include_router(catalog_router)
    app.include_router(lineage_router)
    app.include_router(evidence_router)
    app.include_router(analysis_router)
    # TODO(C): app.include_router(galaxy_router)

    @app.get("/api/health", response_model=HealthResponse, tags=["shared"])
    def health() -> HealthResponse:
        return _health()

    @app.get("/api/meta", response_model=MetaResponse, tags=["shared"])
    def meta() -> MetaResponse:
        """给前端和文档用的常量，避免前后端各写一份上限。"""
        return MetaResponse(
            max_page_size=config.MAX_PAGE_SIZE,
            max_depth=config.MAX_DEPTH,
            default_graph_nodes=config.DEFAULT_GRAPH_NODES,
            max_graph_nodes=config.MAX_GRAPH_NODES,
            rule_version=config.RULE_VERSION,
            relation_types=list(config.RELATION_TYPES),
        )

    # 生产/演示：如果前端已经构建过，直接由后端托管（单进程、断网可用）
    dist = config.PLATFORM_DIR / "frontend" / "dist"
    if (dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            # 入口 HTML 必须每次回源，否则改了前端但浏览器还拿旧 index.html，
            # 会加载到旧的 hash 资源，出现"改了没生效"的错觉
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
