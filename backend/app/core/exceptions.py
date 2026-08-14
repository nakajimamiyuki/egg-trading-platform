import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.response import BizError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizError)
    async def biz_error_handler(_: Request, exc: BizError) -> JSONResponse:
        return JSONResponse(status_code=200, content={"code": exc.code, "message": exc.message, "data": None})

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        err = exc.errors()[0]
        field = ".".join(str(loc) for loc in err.get("loc", []) if loc not in ("body", "query", "path"))
        label = f"字段 {field} " if field else ""
        reason = "缺失或格式不正确" if err.get("type") == "missing" else err.get("msg", "格式不正确")
        return JSONResponse(status_code=200, content={"code": 422, "message": f"参数校验失败: {label}{reason}", "data": None})

    @app.exception_handler(Exception)
    async def unknown_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理异常: %s", exc)
        return JSONResponse(status_code=200, content={"code": 500, "message": "服务器内部错误", "data": None})
