"""订单服务: 三种销售模式状态机 (F3.1/F4.2/F4.3/F10.1-F10.3)

状态机:
  CREATE -> AUDIT -> DEPOSIT_PENDING -> DEPOSIT_PAID -> ADVANCE_PAID
  -> VERIFYING -> OUTBOUND_CONFIRMED -> TAIL_PAID -> FULL_PAID
  -> RELEASED -> FINISHED        (分支: CANCEL / CLOSED)
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bizconfig import get_config_decimal
from app.core.response import BizError
from app.models import DeliveryWarehouse, OrderEvent, OrderInfo, OrderItem, ShelfItem

STATUS_TEXT = {
    "CREATE": "已创建", "AUDIT": "业务审核中", "DEPOSIT_PENDING": "待付定金",
    "DEPOSIT_PAID": "定金已付(垫资审批中)", "ADVANCE_PAID": "平台已垫资80%",
    "VERIFYING": "装车核验中", "OUTBOUND_CONFIRMED": "出库单已确认",
    "TAIL_PAID": "尾款已付(结算审批中)", "FULL_PAID": "养殖户已收全款(待放行)",
    "RELEASED": "已核销放行", "FINISHED": "已完成",
    "CANCEL": "已取消", "CLOSED": "已平仓",
}

# 允许的主动流转(非审批/支付驱动的流转在这里声明)
ALLOWED = {"FINISHED": {"RELEASED"}}


async def transition(db: AsyncSession, order: OrderInfo, to: str, operator_id: int | None = None, remark: str = "") -> None:
    db.add(OrderEvent(order_id=order.id, from_status=order.status, to_status=to, operator_id=operator_id, remark=remark))
    order.status = to


async def _next_no(db: AsyncSession, prefix: str) -> str:
    today = date.today().strftime("%Y%m%d")
    count = await db.scalar(select(func.count()).select_from(OrderInfo).where(OrderInfo.order_no.like(f"{prefix}{today}%")))
    return f"{prefix}{today}{count + 1:04d}"


async def create_purchase_order(
    db: AsyncSession, buyer_user, shelf_item_id: int, quantity: int, sale_mode: str = "M1",
    credit_days: int | None = None, designated: bool = False,
) -> OrderInfo:
    """客户端建单采购 (F4.2): 校验货架 -> 计算金额 -> 创建订单 -> 发起业务审核"""
    from app.modules.workflow.service import WorkflowService

    shelf = await db.get(ShelfItem, shelf_item_id)
    if not shelf or shelf.deleted or shelf.status != "ON":
        raise BizError("货架商品不存在或已下架")
    if quantity <= 0 or quantity > shelf.quantity:
        raise BizError(f"采购数量须为 1~{shelf.quantity}")

    dw = await db.get(DeliveryWarehouse, shelf.delivery_warehouse_id)
    deposit_ratio = await get_config_decimal(db, "deposit_ratio", "0.20")
    advance_ratio = await get_config_decimal(db, "advance_ratio", "0.80")

    total = Decimal(quantity) * shelf.price
    deposit = (total * deposit_ratio).quantize(Decimal("0.01"))
    advance = (total * advance_ratio).quantize(Decimal("0.01"))
    platform_profit = Decimal("0")
    if sale_mode == "M3":
        if not credit_days:
            raise BizError("渠道账期模式必须填写账期天数")
        # F1.3: 渠道方须先通过风控尽调
        from app.models import RiskSurvey
        survey = await db.scalar(select(RiskSurvey).where(
            RiskSurvey.enterprise_id == buyer_user.enterprise_id,
            RiskSurvey.conclusion == "PASS", RiskSurvey.deleted == False))  # noqa: E712
        if not survey:
            raise BizError("渠道账期模式要求买方已通过风控尽调 (F1.3), 请联系平台风控团队")
        profit_per = await get_config_decimal(db, "platform_profit_per_unit", "1.00")
        platform_profit = (profit_per * quantity).quantize(Decimal("0.01"))

    order = OrderInfo(
        order_no=await _next_no(db, "SO"), sale_mode=sale_mode,
        buyer_id=buyer_user.enterprise_id, seller_id=shelf.source_enterprise_id,
        designated=designated, quantity=quantity, unit_price=shelf.price,
        total_amount=total, deposit_ratio=deposit_ratio, deposit_amount=deposit,
        advance_ratio=advance_ratio, advance_amount=advance,
        platform_profit=platform_profit, credit_days=credit_days,
        created_by=buyer_user.id,
    )
    db.add(order)
    await db.flush()
    db.add(OrderItem(order_id=order.id, product_id=shelf.product_id,
                     delivery_warehouse_id=shelf.delivery_warehouse_id,
                     quantity=quantity, grade=dw.grade, spec=dw.spec,
                     unit_price=shelf.price, amount=total))
    await transition(db, order, "AUDIT", buyer_user.id, "采购订单提交, 待业务审核")
    # 货架扣减(审核期间先占用展示量, 定金后正式锁库存)
    shelf.quantity -= quantity
    if dw:
        dw.status = "APPLYING"
    await WorkflowService(db).start("ORDER_AUDIT", biz_id=order.id,
                                    title=f"订单审核: {order.order_no} 数量{quantity}", initiator_id=buyer_user.id)
    return order


async def cancel_order(db: AsyncSession, order: OrderInfo, operator_id: int) -> None:
    """取消订单: 仅审核前/待付定金阶段允许; 恢复货架"""
    if order.status not in ("CREATE", "AUDIT", "DEPOSIT_PENDING"):
        raise BizError(f"当前状态({STATUS_TEXT.get(order.status)})不允许取消")
    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    if item and item.delivery_warehouse_id:
        shelf = await db.scalar(select(ShelfItem).where(ShelfItem.delivery_warehouse_id == item.delivery_warehouse_id))
        if shelf:
            shelf.quantity += item.quantity
        dw = await db.get(DeliveryWarehouse, item.delivery_warehouse_id)
        if dw and dw.status == "APPLYING":
            dw.status = "IN_STOCK"
    await transition(db, order, "CANCEL", operator_id, "订单取消")


async def order_detail(db: AsyncSession, order: OrderInfo) -> dict:
    items = await db.scalars(select(OrderItem).where(OrderItem.order_id == order.id))
    events = await db.scalars(select(OrderEvent).where(OrderEvent.order_id == order.id).order_by(OrderEvent.created_time))
    from app.models import Enterprise
    buyer = await db.get(Enterprise, order.buyer_id)
    seller = await db.get(Enterprise, order.seller_id)
    return {
        "id": order.id, "order_no": order.order_no, "sale_mode": order.sale_mode,
        "buyer_name": buyer.enterprise_name if buyer else "", "seller_name": seller.enterprise_name if seller else "",
        "quantity": order.quantity, "unit_price": float(order.unit_price),
        "total_amount": float(order.total_amount), "deposit_amount": float(order.deposit_amount),
        "advance_amount": float(order.advance_amount), "platform_profit": float(order.platform_profit),
        "credit_days": order.credit_days,
        "credit_due_date": order.credit_due_date.isoformat() if order.credit_due_date else None,
        "status": order.status, "status_text": STATUS_TEXT.get(order.status, order.status),
        "remark": order.remark, "created_time": order.created_time.isoformat(),
        "items": [{"product_id": i.product_id, "delivery_warehouse_id": i.delivery_warehouse_id,
                   "quantity": i.quantity, "grade": i.grade, "spec": i.spec,
                   "unit_price": float(i.unit_price), "amount": float(i.amount)} for i in items.all()],
        "events": [{"from_status": e.from_status, "to_status": e.to_status,
                    "to_status_text": STATUS_TEXT.get(e.to_status, e.to_status),
                    "remark": e.remark, "created_time": e.created_time.isoformat()} for e in events.all()],
    }
