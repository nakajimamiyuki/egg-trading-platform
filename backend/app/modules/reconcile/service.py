"""对账中心 (F8.1/F8.2): 单据自动归集匹配 + 差异调账留痕"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import BizError
from app.models import OrderInfo, PayRecord, ReconcileBatch, ReconcileDiff


async def run_batch(db: AsyncSession, scope: str, period_start: date, period_end: date, operator_id: int) -> ReconcileBatch:
    """跑一批对账: 区间内订单 vs 资金流水自动匹配
    匹配规则: 订单总额 = 客户付款(IN) 且 平台付款(OUT) 与订单状态一致
    """
    self_operated = scope == "SELF"
    orders = (await db.scalars(select(OrderInfo).where(
        OrderInfo.deleted == False,  # noqa: E712
        OrderInfo.self_operated == self_operated,
        func.date(OrderInfo.created_time) >= period_start,
        func.date(OrderInfo.created_time) <= period_end,
        OrderInfo.status.notin_(["CREATE", "AUDIT", "CANCEL"]),
    ))).all()

    today = date.today().strftime("%Y%m%d")
    count = await db.scalar(select(func.count()).select_from(ReconcileBatch))
    batch = ReconcileBatch(batch_no=f"REC{today}{count + 1:04d}", scope=scope,
                           period_start=period_start, period_end=period_end, total_count=len(orders))
    db.add(batch)
    await db.flush()

    matched = 0
    for order in orders:
        pays = (await db.scalars(select(PayRecord).where(PayRecord.order_id == order.id, PayRecord.status == "SUCCESS"))).all()
        in_sum = sum((p.amount for p in pays if p.direction == "IN"), Decimal("0"))
        out_sum = sum((p.amount for p in pays if p.direction == "OUT"), Decimal("0"))
        problems = []
        if order.status in ("FINISHED", "RELEASED", "FULL_PAID"):
            if in_sum != order.total_amount:
                problems.append(f"客户实收 ¥{in_sum} ≠ 订单总额 ¥{order.total_amount}")
            expected_out = order.advance_amount + (order.total_amount - order.advance_amount - (order.platform_profit if order.sale_mode == "M3" else Decimal("0")))
            if out_sum != expected_out:
                problems.append(f"平台实付 ¥{out_sum} ≠ 应付 ¥{expected_out}")
        if problems:
            db.add(ReconcileDiff(batch_id=batch.id, biz_type="ORDER", biz_id=order.id, diff_desc="; ".join(problems)))
        else:
            matched += 1

    batch.matched = matched
    batch.diff_count = len(orders) - matched
    return batch


async def adjust_diff(db: AsyncSession, diff_id: int, amount: Decimal, reason: str, operator_id: int) -> ReconcileDiff:
    """人工调账 (F8.1): 留存操作人/时间/原因"""
    diff = await db.get(ReconcileDiff, diff_id)
    if not diff or diff.deleted:
        raise BizError("差异记录不存在", code=404)
    if diff.status != "OPEN":
        raise BizError("该差异已处理")
    if not reason:
        raise BizError("必须填写调账原因(留痕要求)")
    diff.adjust_amount = amount
    diff.adjust_reason = reason
    diff.adjusted_by = operator_id
    diff.adjusted_time = datetime.now()
    diff.status = "ADJUSTED"
    return diff
