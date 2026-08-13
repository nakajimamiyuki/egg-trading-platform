from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import DeliveryWarehouse, Enterprise, Product, ShelfItem

router = APIRouter()


def _shelf_dict(s: ShelfItem, dw: DeliveryWarehouse, p: Product, ent_name: str) -> dict:
    return {
        "id": s.id, "delivery_warehouse_id": s.delivery_warehouse_id, "dw_no": dw.dw_no,
        "grade": p.grade, "spec": p.spec, "quantity": s.quantity,
        "price": float(s.price), "source_enterprise": ent_name,
        "designated": s.designated, "status": s.status,
        "created_time": s.created_time.isoformat(),
    }


async def _query(db: AsyncSession, designated: bool | None, grade: str | None, only_on: bool):
    q = (select(ShelfItem, DeliveryWarehouse, Product, Enterprise.enterprise_name)
         .join(DeliveryWarehouse, DeliveryWarehouse.id == ShelfItem.delivery_warehouse_id)
         .join(Product, Product.id == ShelfItem.product_id)
         .join(Enterprise, Enterprise.id == ShelfItem.source_enterprise_id)
         .where(ShelfItem.deleted == False))  # noqa: E712
    if only_on:
        q = q.where(ShelfItem.status == "ON", ShelfItem.quantity > 0)
    if designated is not None:
        q = q.where(ShelfItem.designated == designated)
    if grade:
        q = q.where(Product.grade == grade)
    return (await db.execute(q.order_by(ShelfItem.created_time.desc()))).all()


@router.get("/list")
async def shelf_list(designated: bool | None = None, grade: str | None = None,
                     ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """产区现货货架 (F4.1): 客户端选购, 支持指定/非指定养殖户筛选"""
    rows = await _query(db, designated, grade, only_on=True)
    return ok([_shelf_dict(s, d, p, n) for s, d, p, n in rows])


@router.get("/manage")
async def shelf_manage(ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    """货架管理(业务端): 含下架项, 用于定价与上下架"""
    rows = await _query(db, None, None, only_on=False)
    return ok([_shelf_dict(s, d, p, n) for s, d, p, n in rows])


@router.put("/{shelf_id}/price")
async def set_price(shelf_id: int, body: dict, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    shelf = await db.get(ShelfItem, shelf_id)
    if not shelf or shelf.deleted:
        raise BizError("货架项不存在", code=404)
    shelf.price = body["price"]
    await db.commit()
    return ok(message="价格已更新")


@router.put("/{shelf_id}/status")
async def set_status(shelf_id: int, body: dict, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    shelf = await db.get(ShelfItem, shelf_id)
    if not shelf or shelf.deleted:
        raise BizError("货架项不存在", code=404)
    status = body.get("status")
    if status not in ("ON", "OFF"):
        raise BizError("status 只能是 ON/OFF")
    shelf.status = status
    await db.commit()
    return ok(message="已上架" if status == "ON" else "已下架")
