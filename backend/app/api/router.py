from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.dict.router import router as dict_router
from app.modules.enterprise.router import router as enterprise_router
from app.modules.file.router import router as file_router
from app.modules.message.router import router as message_router
from app.modules.workflow.router import router as workflow_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(enterprise_router, prefix="/enterprise", tags=["企业"])
api_router.include_router(workflow_router, prefix="/workflow", tags=["审批流"])
api_router.include_router(file_router, prefix="/file", tags=["文件"])
api_router.include_router(message_router, prefix="/message", tags=["消息"])
api_router.include_router(dict_router, prefix="/common", tags=["字典与配置"])
