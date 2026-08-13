from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import OrderInfo, OutboundFile, OutboundOrder, PickupVoucher
from app.modules.delivery import service as delivery_service

router = APIRouter()


class OutboundCreate(BaseModel):
    order_id: int
    plate_no: str
    driver_name: str
    driver_phone: str


class OutboundFileAdd(BaseModel):
    file_id: int
    media_type: str  # PHOTO/VIDEO


class VerifyRequest(BaseModel):
    qr_payload: str


def _ob_dict(ob: OutboundOrder, files: list) -> dict:
    return {
        "id": ob.id, "outbound_no": ob.outbound_no, "order_id": ob.order_id,
        "quantity": ob.quantity, "grade": ob.grade, "spec": ob.spec,
        "unit_price": float(ob.unit_price) if ob.unit_price else None,
        "plate_no": ob.plate_no, "driver_name": ob.driver_name, "driver_phone": ob.driver_phone,
        "seller_confirmed": ob.seller_confirmed, "buyer_confirmed": ob.buyer_confirmed,
        "platform_confirmed": ob.platform_confirmed, "status": ob.status,
        "files": files, "created_time": ob.created_time.isoformat(),
    }


@router.post("/outbound")
async def create_outbound(req: OutboundCreate, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    """业务端开具出库单 (F5.1)"""
    user, _ = ctx
    order = await db.get(OrderInfo, req.order_id)
    if not order or order.deleted:
        raise BizError("订单不存在", code=404)
    ob = await delivery_service.create_outbound(db, order, req.plate_no, req.driver_name, req.driver_phone, user.id)
    await db.commit()
    return ok(_ob_dict(ob, []), message="出库单已开具, 待三方确认")


@router.get("/outbound/by-order/{order_id}")
async def get_outbound(order_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ob = await db.scalar(select(OutboundOrder).where(OutboundOrder.order_id == order_id, OutboundOrder.deleted == False))  # noqa: E712
    if not ob:
        return ok(None)
    files = await db.scalars(select(OutboundFile).where(OutboundFile.outbound_id == ob.id, OutboundFile.deleted == False))  # noqa: E712
    return ok(_ob_dict(ob, [{"file_id": f.file_id, "media_type": f.media_type, "watermarked": f.watermarked} for f in files.all()]))


@router.post("/outbound/{outbound_id}/files")
async def add_file(outbound_id: int, req: OutboundFileAdd, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """上传装车照片/视频 (带水印)"""
    ob = await db.get(OutboundOrder, outbound_id)
    if not ob or ob.deleted:
        raise BizError("出库单不存在", code=404)
    await delivery_service.add_outbound_file(db, ob, req.file_id, req.media_type)
    await db.commit()
    return ok(message="附件已添加(已加水印)")


@router.post("/outbound/{outbound_id}/confirm/{side}")
async def confirm(outbound_id: int, side: str, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """三方确认: seller(养殖户) / buyer(客户) / platform(业务)"""
    user, roles = ctx
    allowed = {"seller": "FARM", "buyer": "CUSTOMER", "platform": "BUSINESS"}
    if side not in allowed or allowed[side] not in roles and "ADMIN" not in roles:
        raise BizError("你的角色不能以该方身份确认", code=403)
    ob = await db.get(OutboundOrder, outbound_id)
    if not ob or ob.deleted:
        raise BizError("出库单不存在", code=404)
    await delivery_service.confirm_outbound(db, ob, side, user.id)
    await db.commit()
    return ok(message=f"{'已三方确认' if ob.status == 'CONFIRMED' else '确认成功, 待其他方确认'}")


@router.get("/voucher/by-order/{order_id}")
async def get_voucher(order_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    v = await db.scalar(select(PickupVoucher).where(PickupVoucher.order_id == order_id, PickupVoucher.deleted == False))  # noqa: E712
    if not v:
        return ok(None)
    return ok({"voucher_no": v.voucher_no, "qr_payload": v.qr_payload, "status": v.status,
               "verified_time": v.verified_time.isoformat() if v.verified_time else None})


@router.post("/verify")
async def verify(req: VerifyRequest, ctx=Depends(require_roles("FARM")), db: AsyncSession = Depends(get_db)):
    """养殖户扫码核销放行 (F5.3, 唯一放行凭证)"""
    user, _ = ctx
    v = await delivery_service.verify_voucher(db, req.qr_payload, user)
    await db.commit()
    return ok({"voucher_no": v.voucher_no}, message="核销成功, 放行!")
