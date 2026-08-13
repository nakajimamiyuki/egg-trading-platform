from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.delivery.router import router as delivery_router
from app.modules.dict.router import router as dict_router
from app.modules.enterprise.router import router as enterprise_router
from app.modules.file.router import router as file_router
from app.modules.finance.router import router as finance_router
from app.modules.inventory.router import router as inventory_router
from app.modules.iot.router import router as iot_router
from app.modules.message.router import router as message_router
from app.modules.order.router import router as order_router
from app.modules.production.router import router as production_router
from app.modules.shelf.router import router as shelf_router
from app.modules.warehouse.router import router as warehouse_router
from app.modules.workflow.router import router as workflow_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(enterprise_router, prefix="/enterprise", tags=["企业"])
api_router.include_router(workflow_router, prefix="/workflow", tags=["审批流"])
api_router.include_router(file_router, prefix="/file", tags=["文件"])
api_router.include_router(message_router, prefix="/message", tags=["消息"])
api_router.include_router(dict_router, prefix="/common", tags=["字典与配置"])
api_router.include_router(warehouse_router, prefix="/warehouse", tags=["仓库与交割仓"])
api_router.include_router(production_router, prefix="/production", tags=["产蛋数据"])
api_router.include_router(iot_router, prefix="/iot", tags=["IoT监控"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["库存"])
api_router.include_router(shelf_router, prefix="/shelf", tags=["现货货架"])
api_router.include_router(order_router, prefix="/orders", tags=["订单"])
api_router.include_router(finance_router, prefix="/finance", tags=["资金结算"])
api_router.include_router(delivery_router, prefix="/delivery", tags=["提货交付"])
