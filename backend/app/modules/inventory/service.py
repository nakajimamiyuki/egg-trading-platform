"""库存服务: 所有库存变更必须写 inventory_log (F2.3/M3 复用)"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import BizError
from app.models import Inventory, InventoryLog, Product


async def get_or_create_product(db: AsyncSession, grade: str, spec: str) -> Product:
    product = await db.scalar(select(Product).where(Product.grade == grade, Product.spec == spec, Product.deleted == False))  # noqa: E712
    if not product:
        product = Product(grade=grade, spec=spec)
        db.add(product)
        await db.flush()
    return product


async def change_inventory(
    db: AsyncSession,
    warehouse_id: int,
    product_id: int,
    change_qty: int,
    biz_type: str,
    biz_id: int | None = None,
    operator_id: int | None = None,
) -> Inventory:
    """库存增减(正入负出), 带乐观锁, 全程写流水"""
    inv = await db.scalar(
        select(Inventory).where(Inventory.warehouse_id == warehouse_id, Inventory.product_id == product_id)
    )
    if not inv:
        if change_qty < 0:
            raise BizError("库存记录不存在, 无法出库")
        inv = Inventory(warehouse_id=warehouse_id, product_id=product_id, quantity=0)
        db.add(inv)
        await db.flush()
    if inv.quantity + change_qty < 0:
        raise BizError(f"库存不足: 当前 {inv.quantity}, 需要 {-change_qty}")
    before = inv.quantity
    inv.quantity += change_qty
    inv.version += 1
    db.add(InventoryLog(
        warehouse_id=warehouse_id, product_id=product_id,
        change_qty=change_qty, before_qty=before, after_qty=inv.quantity,
        biz_type=biz_type, biz_id=biz_id, created_by=operator_id,
    ))
    return inv
