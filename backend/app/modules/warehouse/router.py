from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bizconfig import get_config_int
from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import DeliveryWarehouse, Warehouse
from app.modules.workflow.service import WorkflowService

router = APIRouter()


class WarehouseCreate(BaseModel):
    name: str
    address: str
    capacity: int | None = None


class LeaseApply(BaseModel):
    rent_amount: float


class DwApply(BaseModel):
    warehouse_id: int
    quantity: int
    grade: str
    spec: str


def _wh_dict(w: Warehouse) -> dict:
    return {
        "id": w.id, "name": w.name, "address": w.address, "capacity": w.capacity,
        "enterprise_id": w.enterprise_id, "rent_amount": float(w.rent_amount) if w.rent_amount else None,
        "lease_status": w.lease_status, "monitor_online": w.monitor_online,
        "point_map_file_id": w.point_map_file_id,
        "created_time": w.created_time.isoformat(),
    }


def _dw_dict(d: DeliveryWarehouse, wh_name: str = "") -> dict:
    days_in_stock = (date.today() - d.inbound_date).days if d.inbound_date else 0
    return {
        "id": d.id, "dw_no": d.dw_no, "warehouse_id": d.warehouse_id, "warehouse_name": wh_name,
        "enterprise_id": d.enterprise_id, "quantity": d.quantity, "grade": d.grade, "spec": d.spec,
        "inbound_date": d.inbound_date.isoformat() if d.inbound_date else None,
        "turnover_days": d.turnover_days, "days_in_stock": days_in_stock,
        "turnover_warning": d.status == "IN_STOCK" and days_in_stock >= d.turnover_days,
        "status": d.status, "created_time": d.created_time.isoformat(),
    }


# ---------- 仓库 (F2.1) ----------

@router.post("")
async def create_warehouse(req: WarehouseCreate, ctx=Depends(require_roles("FARM")), db: AsyncSession = Depends(get_db)):
    """养殖端仓库登记"""
    user, _ = ctx
    if not user.enterprise_id:
        raise BizError("当前账号未关联企业")
    wh = Warehouse(name=req.name, address=req.address, capacity=req.capacity,
                   enterprise_id=user.enterprise_id, created_by=user.id)
    db.add(wh)
    await db.commit()
    return ok(_wh_dict(wh), message="仓库登记成功, 等待平台发起租赁审批")


@router.get("/my")
async def my_warehouses(ctx=Depends(require_roles("FARM")), db: AsyncSession = Depends(get_db)):
    user, _ = ctx
    rows = await db.scalars(select(Warehouse).where(Warehouse.enterprise_id == user.enterprise_id, Warehouse.deleted == False))  # noqa: E712
    return ok([_wh_dict(w) for w in rows.all()])


@router.get("/list")
async def list_warehouses(ctx=Depends(require_roles("BUSINESS", "FINANCE")), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(Warehouse).where(Warehouse.deleted == False).order_by(Warehouse.created_time.desc()))  # noqa: E712
    return ok([_wh_dict(w) for w in rows.all()])


@router.post("/{warehouse_id}/lease-apply")
async def lease_apply(warehouse_id: int, req: LeaseApply, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    """业务端发起仓库租赁审批 (确认位置/容量/租金条款)"""
    user, _ = ctx
    wh = await db.get(Warehouse, warehouse_id)
    if not wh or wh.deleted:
        raise BizError("仓库不存在", code=404)
    if wh.lease_status != "NONE":
        raise BizError("该仓库已在租赁流程中或已租赁")
    wh.rent_amount = req.rent_amount
    wh.lease_status = "WAIT"
    await WorkflowService(db).start("WAREHOUSE_LEASE", biz_id=wh.id,
                                    title=f"仓库租赁审批: {wh.name} (租金{req.rent_amount}元)", initiator_id=user.id)
    await db.commit()
    return ok(message="租赁审批已发起(业务→财务两级审批)")


# ---------- 交割仓 (F2.3) ----------

@router.post("/delivery/apply")
async def dw_apply(req: DwApply, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    """业务端发起交割仓建立审批: 前置条件=仓库已租赁+监控已确权"""
    user, _ = ctx
    wh = await db.get(Warehouse, req.warehouse_id)
    if not wh or wh.deleted:
        raise BizError("仓库不存在", code=404)
    if wh.lease_status != "LEASED":
        raise BizError("仓库未完成租赁审批, 不能建交割仓")
    if not wh.monitor_online:
        raise BizError("仓库监控未接入确权 (F2.2), 不能建交割仓")

    today = date.today().strftime("%Y%m%d")
    count = await db.scalar(select(func.count()).select_from(DeliveryWarehouse).where(DeliveryWarehouse.dw_no.like(f"DW{today}%")))
    dw_no = f"DW{today}{count + 1:04d}"
    turnover_days = await get_config_int(db, "turnover_days", 3)

    dw = DeliveryWarehouse(dw_no=dw_no, warehouse_id=wh.id, enterprise_id=wh.enterprise_id,
                           quantity=req.quantity, grade=req.grade, spec=req.spec, turnover_days=turnover_days)
    db.add(dw)
    await db.flush()
    await WorkflowService(db).start("DELIVERY_WH_CREATE", biz_id=dw.id,
                                    title=f"交割仓建立审批: {wh.name} {req.grade}级 {req.quantity}枚", initiator_id=user.id)
    await db.commit()
    return ok(_dw_dict(dw), message="交割仓审批已发起")


@router.get("/delivery/list")
async def dw_list(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """交割仓一览: 养殖户看自己的, 业务/财务/管理员看全部 (F7.1 预警字段一并返回)"""
    user, roles = ctx
    q = select(DeliveryWarehouse, Warehouse.name).join(Warehouse, Warehouse.id == DeliveryWarehouse.warehouse_id)
    if "FARM" in roles:
        q = q.where(DeliveryWarehouse.enterprise_id == user.enterprise_id)
    rows = await db.execute(q.where(DeliveryWarehouse.deleted == False).order_by(DeliveryWarehouse.created_time.desc()))  # noqa: E712
    return ok([_dw_dict(d, wh_name) for d, wh_name in rows.all()])
