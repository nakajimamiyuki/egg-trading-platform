from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import ok
from app.database.session import get_db
from app.models import Inventory, Product, Warehouse

router = APIRouter()


@router.get("/list")
async def list_inventory(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """库存查询: 养殖户看自己仓库, 业务/财务/管理员看全部"""
    user, roles = ctx
    q = (select(Inventory, Warehouse.name, Warehouse.enterprise_id, Product.grade, Product.spec, Product.unit)
         .join(Warehouse, Warehouse.id == Inventory.warehouse_id)
         .join(Product, Product.id == Inventory.product_id))
    if "FARM" in roles:
        q = q.where(Warehouse.enterprise_id == user.enterprise_id)
    rows = await db.execute(q.order_by(Inventory.updated_time.desc()))
    return ok([
        {"warehouse_id": inv.warehouse_id, "warehouse_name": wh_name, "product_id": inv.product_id,
         "grade": grade, "spec": spec, "unit": unit,
         "quantity": inv.quantity, "locked_qty": inv.locked_qty, "available": inv.quantity - inv.locked_qty,
         "updated_time": inv.updated_time.isoformat()}
        for inv, wh_name, _ent, grade, spec, unit in rows.all()
    ])
