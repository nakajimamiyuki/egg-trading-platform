"""平仓风控服务 (F7.1-F7.4)
- 周转预警: 定时任务, 在库天数 >= 周转天数即预警(站内信)
- 5 类申请 (F7.2): 退仓/平台自销(指定/非指定)/销售给平台/超期处理
- 强制平仓 (F7.3): 超期货品按折价比例处置, 发起平仓退款审批
- 退款执行 (F7.4): 审批通过后退款 + 库存出库 + 平仓台账(盈亏核算)
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bizconfig import get_config_decimal, get_config_int
from app.core.response import BizError
from app.models import CloseApply, CloseOrder, DeliveryWarehouse, Inventory, OrderInfo
from app.modules.workflow.service import WorkflowService


async def check_turnover_warnings(db: AsyncSession) -> int:
    """周转预警 (F7.1): 在库超期未售 → 通知业务端与养殖户。返回预警数量"""
    from app.modules.message.router import notify_enterprise, notify_role

    turnover_days = await get_config_int(db, "turnover_days", 3)
    rows = await db.scalars(select(DeliveryWarehouse).where(
        DeliveryWarehouse.deleted == False,  # noqa: E712
        DeliveryWarehouse.status.in_(["IN_STOCK", "APPLYING"]),
        DeliveryWarehouse.inbound_date.isnot(None),
    ))
    count = 0
    for dw in rows.all():
        days = (date.today() - dw.inbound_date).days
        if days >= turnover_days:
            count += 1
            title = f"平仓预警: {dw.dw_no} 已在库 {days} 天"
            await notify_role(db, "BUSINESS", "CLOSE_WARNING", title, f"{dw.grade}级 {dw.quantity}枚, 请督办处理", "DELIVERY_WH", dw.id)
            await notify_enterprise(db, dw.enterprise_id, "CLOSE_WARNING", title,
                                    "周转期已到, 可申请退仓/自行销售, 超期将强制平仓折价处置", "DELIVERY_WH", dw.id)
    return count


async def create_apply(db: AsyncSession, dw_id: int, apply_type: str, remark: str, user) -> CloseApply:
    """养殖端 5 类申请 (F7.2)"""
    dw = await db.get(DeliveryWarehouse, dw_id)
    if not dw or dw.deleted or dw.enterprise_id != user.enterprise_id:
        raise BizError("交割仓不存在", code=404)
    valid = ("RETURN", "SELF_SALE_DESIGNATED", "SELF_SALE_OPEN", "SALE_TO_PLATFORM", "OVERDUE_HANDLE")
    if apply_type not in valid:
        raise BizError(f"申请类型必须是: {'/'.join(valid)}")
    apply = CloseApply(delivery_warehouse_id=dw_id, apply_type=apply_type, remark=remark, created_by=user.id)
    db.add(apply)
    await db.flush()
    await WorkflowService(db).start("CLOSE_APPLY", biz_id=apply.id,
                                    title=f"养殖端申请[{_apply_text(apply_type)}]: {dw.dw_no}", initiator_id=user.id)
    return apply


def _apply_text(t: str) -> str:
    return {"RETURN": "申请退仓", "SELF_SALE_DESIGNATED": "平台自行销售(指定客户)",
            "SELF_SALE_OPEN": "平台自行销售(非指定客户)", "SALE_TO_PLATFORM": "销售给平台",
            "OVERDUE_HANDLE": "超期订单处理"}.get(t, t)


async def on_apply_approved(db: AsyncSession, apply_id: int) -> None:
    """申请审批通过后的处置"""
    apply = await db.get(CloseApply, apply_id)
    if not apply or apply.status != "WAIT":
        return
    dw = await db.get(DeliveryWarehouse, apply.delivery_warehouse_id)
    apply.status = "PASS"
    if apply.apply_type == "RETURN":
        # 退仓: 库存退回, 交割仓关闭
        from app.modules.inventory.service import change_inventory, get_or_create_product
        product = await get_or_create_product(db, dw.grade, dw.spec)
        await change_inventory(db, dw.warehouse_id, product.id, -dw.quantity, "OUT", biz_id=dw.id)
        dw.status = "RETURNED"
        apply.status = "DONE"
    elif apply.apply_type in ("SELF_SALE_DESIGNATED", "SELF_SALE_OPEN", "SALE_TO_PLATFORM"):
        dw.status = "APPLYING"  # 转入平台销售流程


async def force_close(db: AsyncSession, dw_id: int, operator_id: int) -> CloseOrder:
    """超期强制平仓 (F7.3): 按折价比例处置, 发起平仓退款审批 (F7.4)"""
    dw = await db.get(DeliveryWarehouse, dw_id)
    if not dw or dw.deleted:
        raise BizError("交割仓不存在", code=404)
    if dw.status not in ("IN_STOCK", "APPLYING"):
        raise BizError(f"当前状态({dw.status})不能平仓")
    exists = await db.scalar(select(CloseOrder).where(CloseOrder.delivery_warehouse_id == dw_id, CloseOrder.status != "REFUNDED"))
    if exists:
        raise BizError("该交割仓已有进行中的平仓单")

    ratio = await get_config_decimal(db, "close_discount_ratio", "0.80")
    original = (Decimal(dw.quantity) * (dw.price or Decimal("0"))).quantize(Decimal("0.01"))
    settle = (original * ratio).quantize(Decimal("0.01"))
    today = date.today().strftime("%Y%m%d")
    count = await db.scalar(select(func.count()).select_from(CloseOrder))
    co = CloseOrder(
        close_no=f"PC{today}{count + 1:04d}", delivery_warehouse_id=dw_id, close_type="FORCE",
        discount_ratio=ratio, quantity=dw.quantity, original_amount=original, settle_amount=settle,
        profit_loss=original - settle, created_by=operator_id,
    )
    db.add(co)
    await db.flush()
    await WorkflowService(db).start("CLOSE_REFUND", biz_id=co.id,
                                    title=f"平仓退款审批: {dw.dw_no} 折价结算¥{settle}", initiator_id=operator_id)
    return co


async def on_close_refund_approved(db: AsyncSession, close_order_id: int) -> None:
    """平仓退款审批通过 (F7.4): 退款给养殖户 + 滞销品出库 + 台账核算"""
    from app.modules.inventory.service import change_inventory, get_or_create_product
    from app.modules.message.router import notify_enterprise

    co = await db.get(CloseOrder, close_order_id)
    if not co or co.status != "PENDING":
        return
    dw = await db.get(DeliveryWarehouse, co.delivery_warehouse_id)
    co.status = "CONFIRMED"
    # 退款流水 (人工/直联通道沿用 finance 的设计, 此处直接记账)
    from app.models import PayRecord
    today = date.today().strftime("%Y%m%d")
    count = await db.scalar(select(func.count()).select_from(PayRecord))
    db.add(PayRecord(pay_no=f"PAY{today}{count + 1:04d}", order_id=None, direction="OUT", pay_type="REFUND",
                     amount=co.settle_amount, payer_id=None, payee_id=dw.enterprise_id,
                     channel="MOCK", status="SUCCESS", paid_time=datetime.now()))
    # 滞销品出库
    product = await get_or_create_product(db, dw.grade, dw.spec)
    await change_inventory(db, dw.warehouse_id, product.id, -dw.quantity, "CLOSE_OUT", biz_id=co.id)
    dw.status = "CLOSED"
    co.status = "REFUNDED"
    await notify_enterprise(db, dw.enterprise_id, "CLOSE_WARNING",
                            f"平仓完成: {dw.dw_no}", f"折价结算 ¥{co.settle_amount} 已退款(原价¥{co.original_amount}, 折价{int(co.discount_ratio * 100)}%)",
                            "CLOSE_ORDER", co.id)
