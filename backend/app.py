"""平台入口：只注册路由，不写业务逻辑。

模块归属（谁改哪一块）：
    modules/data        A  数据与框架     /api/imports /api/snapshots /api/datasets
    modules/catalog     B  目录搜索       /api/models /api/model
    modules/lineage     B  小图           /api/graph
    modules/analysis    D  生态分析       /api/analysis
    modules/galaxy      C  大图           待接入

公共部分（app、shared/*）由 A 维护；其他人只加一行 include_router。
"""

from __future__ import annotations

import sqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from modules.analysis.router import router as analysis_router
from modules.catalog.router import router as catalog_router
from modules.data.router import router as data_router
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
            "课程大作业骨架。四个工作包：A 数据与框架 / B 目录与小图 / C 大图 / D 生态分析。"
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
            return FileResponse(dist / "index.html")

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
