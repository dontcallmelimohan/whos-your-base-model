"""统一错误格式。

所有失败响应都是：
    {"error": {"code": "...", "message": "...", "detail": ...}}

可识别错误码（前端按 code 分支，不要匹配中文文案）：
    invalid_parameter  参数不合法（400）
    not_found          对象不存在（404）
    data_not_ready     数据未就绪（409）
    conflict           重复或状态冲突（409）
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


def not_found(message: str, detail: Any = None) -> ApiError:
    return ApiError("not_found", message, 404, detail)


def invalid(message: str, detail: Any = None) -> ApiError:
    return ApiError("invalid_parameter", message, 400, detail)


def not_ready(message: str, detail: Any = None) -> ApiError:
    return ApiError("data_not_ready", message, 409, detail)


def _body(code: str, message: str, detail: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "detail": detail}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.code, exc.message, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_body("invalid_parameter", "请求参数不合法", exc.errors()),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "invalid_parameter"}.get(exc.status_code, "error")
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(code, str(exc.detail), None),
        )
