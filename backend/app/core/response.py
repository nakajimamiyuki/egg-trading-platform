from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一返回格式: {"code":0,"message":"success","data":{}}"""

    code: int = 0
    message: str = "success"
    data: Any = None


def ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 0, "message": message, "data": data}


class BizError(Exception):
    """业务异常, 由全局异常处理器转为统一返回格式"""

    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(message)
