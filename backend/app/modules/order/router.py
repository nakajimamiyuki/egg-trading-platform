from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import OrderInfo
from app.modules.order import service as order_service

router = APIRouter()


class PurchaseCreate(BaseModel):
    shelf_item_id: int
    quantity: int
    sale_mode: str = "M1"
    credit_days: int | None = None
    designated: bool = False


@router.post("/purchase")
async def create_purchase(req: PurchaseCreate, ctx=Depends(require_roles("CUSTOMER")), db: AsyncSession = Depends(get_db)):
    """客户端建单采购 (F4.2)"""
    user, _ = ctx
    if req.sale_mode not in ("M1", "M2", "M3"):
        raise BizError("sale_mode 必须是 M1/M2/M3")
    order = await order_service.create_purchase_order(
        db, user, req.shelf_item_id, req.quantity, req.sale_mode, req.credit_days, req.designated)
    await db.commit()
    return ok(await order_service.order_detail(db, order), message="采购订单已提交, 待业务审核")


@router.get("/list")
async def list_orders(status: str | None = None, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """订单列表: 客户看买的, 养殖户看卖的, 业务/财务/管理员看全部 (F4.3)"""
    user, roles = ctx
    q = select(OrderInfo).where(OrderInfo.deleted == False)  # noqa: E712
    if "CUSTOMER" in roles:
        q = q.where(OrderInfo.buyer_id == user.enterprise_id)
    elif "FARM" in roles:
        q = q.where(OrderInfo.seller_id == user.enterprise_id)
    if status:
        q = q.where(OrderInfo.status == status)
    rows = await db.scalars(q.order_by(OrderInfo.created_time.desc()))
    return ok([
        {"id": o.id, "order_no": o.order_no, "sale_mode": o.sale_mode, "quantity": o.quantity,
         "total_amount": float(o.total_amount), "status": o.status,
         "status_text": order_service.STATUS_TEXT.get(o.status, o.status),
         "created_time": o.created_time.isoformat()}
        for o in rows.all()
    ])


@router.get("/{order_id}")
async def get_order(order_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, roles = ctx
    order = await db.get(OrderInfo, order_id)
    if not order or order.deleted:
        raise BizError("订单不存在", code=404)
    if "CUSTOMER" in roles and order.buyer_id != user.enterprise_id:
        raise BizError("无权查看", code=403)
    if "FARM" in roles and order.seller_id != user.enterprise_id:
        raise BizError("无权查看", code=403)
    return ok(await order_service.order_detail(db, order))


@router.post("/{order_id}/cancel")
async def cancel(order_id: int, ctx=Depends(require_roles("CUSTOMER")), db: AsyncSession = Depends(get_db)):
    user, _ = ctx
    order = await db.get(OrderInfo, order_id)
    if not order or order.deleted or order.buyer_id != user.enterprise_id:
        raise BizError("订单不存在", code=404)
    await order_service.cancel_order(db, order, user.id)
    await db.commit()
    return ok(message="订单已取消")
