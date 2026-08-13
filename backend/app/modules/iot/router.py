from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import IotDevice, Warehouse

router = APIRouter()


class DeviceCreate(BaseModel):
    warehouse_id: int
    device_name: str
    protocol: str = "RTSP"
    stream_url: str


def _to_dict(d: IotDevice) -> dict:
    return {"id": d.id, "warehouse_id": d.warehouse_id, "device_name": d.device_name,
            "device_type": d.device_type, "protocol": d.protocol, "stream_url": d.stream_url,
            "online": d.online, "confirmed": d.confirmed, "created_time": d.created_time.isoformat()}


@router.post("/devices")
async def create_device(req: DeviceCreate, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """登记监控设备 (养殖户登记自己仓库, 业务端可代办)"""
    user, roles = ctx
    wh = await db.get(Warehouse, req.warehouse_id)
    if not wh or wh.deleted:
        raise BizError("仓库不存在", code=404)
    if "FARM" in roles and wh.enterprise_id != user.enterprise_id:
        raise BizError("只能登记自己企业的仓库设备", code=403)
    d = IotDevice(warehouse_id=wh.id, device_name=req.device_name, protocol=req.protocol, stream_url=req.stream_url)
    db.add(d)
    await db.commit()
    return ok(_to_dict(d), message="设备已登记")


@router.get("/devices")
async def list_devices(warehouse_id: int | None = None, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, roles = ctx
    q = select(IotDevice).where(IotDevice.deleted == False)  # noqa: E712
    if warehouse_id:
        q = q.where(IotDevice.warehouse_id == warehouse_id)
    if "FARM" in roles:
        q = q.join(Warehouse, Warehouse.id == IotDevice.warehouse_id).where(Warehouse.enterprise_id == user.enterprise_id)
    rows = await db.scalars(q.order_by(IotDevice.created_time.desc()))
    return ok([_to_dict(d) for d in rows.all()])


@router.post("/devices/{device_id}/check")
async def check_online(device_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """监控在线检测。当前为模拟实现, M4 阶段接入真实 RTSP/GB28181 探测"""
    d = await db.get(IotDevice, device_id)
    if not d or d.deleted:
        raise BizError("设备不存在", code=404)
    d.online = True
    await db.commit()
    return ok(_to_dict(d), message="检测完成: 设备在线(模拟)")


@router.post("/devices/{device_id}/confirm")
async def confirm_device(device_id: int, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    """业务端监控确权 (F2.2)。仓库下所有设备确权后, 仓库标记监控在线"""
    d = await db.get(IotDevice, device_id)
    if not d or d.deleted:
        raise BizError("设备不存在", code=404)
    if not d.online:
        raise BizError("设备未通过在线检测, 不能确权")
    d.confirmed = True
    remaining = await db.scalar(
        select(IotDevice).where(IotDevice.warehouse_id == d.warehouse_id,
                                IotDevice.deleted == False, IotDevice.confirmed == False, IotDevice.id != d.id)  # noqa: E712
    )
    wh = await db.get(Warehouse, d.warehouse_id)
    if wh and not remaining:
        wh.monitor_online = True
    await db.commit()
    return ok(_to_dict(d), message="确权完成" + (", 仓库监控已标记在线" if wh and wh.monitor_online else ""))


class PointMapRequest(BaseModel):
    file_id: int


@router.post("/warehouses/{warehouse_id}/point-map")
async def upload_point_map(warehouse_id: int, req: PointMapRequest, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """上传监控点位图 (F2.2)"""
    wh = await db.get(Warehouse, warehouse_id)
    if not wh or wh.deleted:
        raise BizError("仓库不存在", code=404)
    wh.point_map_file_id = req.file_id
    await db.commit()
    return ok(message="点位图已上传")
