"""物流 (F9.8/F9.9): 叫车 + 轨迹。当前人工兜底(MANUAL), 运满满/GPS 接入后切换 platform=YMM"""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import LogisticsOrder, LogisticsTrack, OrderInfo

router = APIRouter()


class LogisticsCreate(BaseModel):
    order_id: int
    waybill_no: str = ""
    driver_name: str
    driver_phone: str
    plate_no: str


class TrackAdd(BaseModel):
    address: str
    longitude: float | None = None
    latitude: float | None = None


@router.post("/create")
async def create_logistics(req: LogisticsCreate, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    """业务端叫车登记 (运满满端口就绪前为人工录入运单号)"""
    order = await db.get(OrderInfo, req.order_id)
    if not order or order.deleted:
        raise BizError("订单不存在", code=404)
    lo = LogisticsOrder(order_id=req.order_id, platform="MANUAL", waybill_no=req.waybill_no,
                        driver_name=req.driver_name, driver_phone=req.driver_phone, plate_no=req.plate_no)
    db.add(lo)
    await db.commit()
    return ok({"id": lo.id}, message="物流单已创建(人工模式)")


@router.get("/by-order/{order_id}")
async def get_by_order(order_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    lo = await db.scalar(select(LogisticsOrder).where(LogisticsOrder.order_id == order_id, LogisticsOrder.deleted == False))  # noqa: E712
    if not lo:
        return ok(None)
    tracks = await db.scalars(select(LogisticsTrack).where(LogisticsTrack.logistics_id == lo.id).order_by(LogisticsTrack.track_time))
    return ok({"id": lo.id, "platform": lo.platform, "waybill_no": lo.waybill_no,
               "driver_name": lo.driver_name, "driver_phone": lo.driver_phone, "plate_no": lo.plate_no,
               "status": lo.status,
               "tracks": [{"address": t.address, "longitude": float(t.longitude) if t.longitude else None,
                           "latitude": float(t.latitude) if t.latitude else None,
                           "track_time": t.track_time.isoformat()} for t in tracks.all()]})


@router.post("/{logistics_id}/track")
async def add_track(logistics_id: int, req: TrackAdd, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    """录入轨迹点 (GPS 接入后自动回传替代)"""
    lo = await db.get(LogisticsOrder, logistics_id)
    if not lo or lo.deleted:
        raise BizError("物流单不存在", code=404)
    db.add(LogisticsTrack(logistics_id=logistics_id, address=req.address,
                          longitude=req.longitude, latitude=req.latitude, track_time=datetime.now()))
    lo.status = "IN_TRANSIT"
    await db.commit()
    return ok(message="轨迹已更新")


@router.post("/{logistics_id}/status")
async def update_status(logistics_id: int, body: dict, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    lo = await db.get(LogisticsOrder, logistics_id)
    if not lo or lo.deleted:
        raise BizError("物流单不存在", code=404)
    status = body.get("status")
    if status not in ("CALLED", "LOADED", "IN_TRANSIT", "ARRIVED"):
        raise BizError("非法状态")
    lo.status = status
    await db.commit()
    return ok(message="状态已更新")
