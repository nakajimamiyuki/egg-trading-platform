"""数据看板 (F8.3) + 报表导出 (F8.4)"""
import io
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.core.response import ok
from app.database.session import get_db
from app.models import DeliveryWarehouse, Inventory, OrderInfo, PayRecord

router = APIRouter()


@router.get("/summary")
async def summary(ctx=Depends(require_roles("FINANCE", "BUSINESS")), db: AsyncSession = Depends(get_db)):
    """交易规模/付款/退款/结算/库存 汇总 (F8.3)"""

    async def sum_pay(direction: str | None, pay_type: str | None = None):
        q = select(func.coalesce(func.sum(PayRecord.amount), 0)).where(PayRecord.status == "SUCCESS")
        if direction:
            q = q.where(PayRecord.direction == direction)
        if pay_type:
            q = q.where(PayRecord.pay_type == pay_type)
        return float(await db.scalar(q) or 0)

    order_stats = await db.execute(
        select(OrderInfo.sale_mode, func.count(), func.coalesce(func.sum(OrderInfo.total_amount), 0))
        .where(OrderInfo.deleted == False, OrderInfo.status.notin_(["CANCEL"]))  # noqa: E712
        .group_by(OrderInfo.sale_mode)
    )
    by_mode = {m: {"count": c, "amount": float(a)} for m, c, a in order_stats.all()}

    total_qty = await db.scalar(select(func.coalesce(func.sum(Inventory.quantity), 0)))
    locked_qty = await db.scalar(select(func.coalesce(func.sum(Inventory.locked_qty), 0)))
    dw_stats = await db.execute(
        select(DeliveryWarehouse.status, func.count()).where(DeliveryWarehouse.deleted == False).group_by(DeliveryWarehouse.status))  # noqa: E712

    # 近7天每日成交额
    daily = await db.execute(
        select(func.date(OrderInfo.created_time), func.count(), func.coalesce(func.sum(OrderInfo.total_amount), 0))
        .where(OrderInfo.deleted == False, OrderInfo.status.notin_(["CANCEL"]))  # noqa: E712
        .group_by(func.date(OrderInfo.created_time)).order_by(func.date(OrderInfo.created_time))
    )

    return ok({
        "order_by_mode": by_mode,
        "total_received": await sum_pay("IN"),
        "total_paid": await sum_pay("OUT"),
        "total_refund": await sum_pay("OUT", "REFUND"),
        "inventory": {"total": int(total_qty or 0), "locked": int(locked_qty or 0)},
        "dw_by_status": {s: c for s, c in dw_stats.all()},
        "daily": [{"date": str(d), "count": c, "amount": float(a)} for d, c, a in daily.all()],
    })


@router.get("/export")
async def export_excel(ctx=Depends(require_roles("FINANCE", "BUSINESS")), db: AsyncSession = Depends(get_db)):
    """交易报表导出 Excel (F8.3/F8.4)"""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "交易报表"
    ws.append(["订单号", "模式", "数量", "总额", "定金", "垫资", "状态", "创建时间"])
    orders = await db.scalars(select(OrderInfo).where(OrderInfo.deleted == False).order_by(OrderInfo.created_time.desc()))  # noqa: E712
    for o in orders.all():
        ws.append([o.order_no, o.sale_mode, o.quantity, float(o.total_amount),
                   float(o.deposit_amount), float(o.advance_amount), o.status,
                   o.created_time.strftime("%Y-%m-%d %H:%M")])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"trade_report_{date.today().isoformat()}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})
