"""资金服务 (F6.1/F6.2/F6.4): 统一收付流水 + 账单
当前支付通道为 MOCK(模拟), 真实支付/银企直联通过 channel 适配器切换
"""
import hashlib
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bizconfig import get_config_decimal
from app.core.config import settings
from app.core.response import BizError
from app.models import DeliveryWarehouse, FinanceBill, OrderEvent, OrderInfo, OrderItem, PayRecord, PickupVoucher
from app.modules.order.service import transition


async def _pay_no(db: AsyncSession) -> str:
    today = date.today().strftime("%Y%m%d")
    count = await db.scalar(select(func.count()).select_from(PayRecord).where(PayRecord.pay_no.like(f"PAY{today}%")))
    return f"PAY{today}{count + 1:04d}"


async def _record(db: AsyncSession, order: OrderInfo, direction: str, pay_type: str, amount: Decimal,
                  payer_id: int | None, payee_id: int | None, channel: str = "MOCK",
                  operator_id: int | None = None) -> PayRecord:
    rec = PayRecord(pay_no=await _pay_no(db), order_id=order.id, direction=direction, pay_type=pay_type,
                    amount=amount, payer_id=payer_id, payee_id=payee_id, channel=channel,
                    status="SUCCESS", paid_time=datetime.now(), created_by=operator_id)
    db.add(rec)
    await _update_bill(db, order, direction, amount)
    return rec


async def _update_bill(db: AsyncSession, order: OrderInfo, direction: str, amount: Decimal) -> None:
    """买卖双方账单中心 (F6.4)"""
    for ent_id, field in [(order.buyer_id, "paid"), (order.seller_id, "received")]:
        bill = await db.scalar(select(FinanceBill).where(FinanceBill.order_id == order.id, FinanceBill.enterprise_id == ent_id))
        if not bill:
            today = date.today().strftime("%Y%m%d")
            count = await db.scalar(select(func.count()).select_from(FinanceBill))
            bill = FinanceBill(bill_no=f"BILL{today}{count + 1:04d}", order_id=order.id,
                               enterprise_id=ent_id, amount=order.total_amount)
            db.add(bill)
            await db.flush()
        setattr(bill, field, getattr(bill, field) + amount)


async def buyer_pay(db: AsyncSession, order: OrderInfo, pay_type: str, user) -> PayRecord:
    """客户付款(模拟通道): DEPOSIT 定金20% / TAIL 尾款80%"""
    from app.modules.inventory.service import lock_inventory
    from app.modules.workflow.service import WorkflowService

    if order.buyer_id != user.enterprise_id:
        raise BizError("只能支付本企业订单", code=403)

    if pay_type == "DEPOSIT":
        if order.status != "DEPOSIT_PENDING":
            raise BizError("当前不在待付定金状态")
        rec = await _record(db, order, "IN", "DEPOSIT", order.deposit_amount, order.buyer_id, None, operator_id=user.id)
        item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
        dw = await db.get(DeliveryWarehouse, item.delivery_warehouse_id)
        await lock_inventory(db, dw.warehouse_id, item.product_id, order.quantity, order.id)
        await transition(db, order, "DEPOSIT_PAID", user.id, "客户支付20%定金, 库存已锁定, 发起垫资审批")
        await WorkflowService(db).start("PAYMENT_80", biz_id=order.id,
                                        title=f"垫资审批(80%): {order.order_no} ¥{order.advance_amount}", initiator_id=user.id)
        return rec

    if pay_type == "TAIL":
        if order.status != "OUTBOUND_CONFIRMED":
            raise BizError("出库单三方确认后才能支付尾款")
        tail = order.total_amount - order.deposit_amount
        rec = await _record(db, order, "IN", "TAIL", tail, order.buyer_id, None, operator_id=user.id)
        await transition(db, order, "TAIL_PAID", user.id, "客户支付80%尾款, 发起尾款结算审批")
        await WorkflowService(db).start("PAYMENT_20", biz_id=order.id,
                                        title=f"尾款结算审批(20%): {order.order_no}", initiator_id=user.id)
        return rec

    raise BizError("不支持的支付类型")


async def on_advance_approved(db: AsyncSession, order_id: int) -> None:
    """PAYMENT_80 审批通过 (F6.1): 平台垫资80%给养殖户
    资金通道: MOCK=自动成功 / MANUAL=人工转账兜底(需回单确认, 银企直联就绪前的形态)"""
    from app.core.bizconfig import get_config

    order = await db.get(OrderInfo, order_id)
    if not order or order.status != "DEPOSIT_PAID":
        return
    channel = await get_config(db, "bank_channel", "MOCK")
    if channel == "MANUAL":
        rec = PayRecord(pay_no=await _pay_no(db), order_id=order.id, direction="OUT", pay_type="ADVANCE",
                        amount=order.advance_amount, payer_id=None, payee_id=order.seller_id,
                        channel="MANUAL", status="PENDING")
        db.add(rec)
        await transition(db, order, "ADVANCE_PAID", None, "垫资审批通过, 人工转账中(待回单确认)")
        return
    await _record(db, order, "OUT", "ADVANCE", order.advance_amount, None, order.seller_id)
    await transition(db, order, "ADVANCE_PAID", None, "财务审批通过, 平台垫资80%至养殖户")
    from app.modules.message.router import notify_enterprise
    await notify_enterprise(db, order.seller_id, "ADVANCE_PAID",
                            f"垫资到账: {order.order_no}", f"平台垫资80% ¥{order.advance_amount} 已支付", "ORDER", order.id)


async def on_settle_approved(db: AsyncSession, order_id: int) -> None:
    """PAYMENT_20 审批通过 (F6.2): 结算20%尾款给养殖户, 模式③内扣平台分利"""
    from app.core.bizconfig import get_config

    order = await db.get(OrderInfo, order_id)
    if not order or order.status != "TAIL_PAID":
        return
    settle = order.total_amount - order.advance_amount
    if order.sale_mode == "M3":
        settle = settle - order.platform_profit
    channel = await get_config(db, "bank_channel", "MOCK")
    if channel == "MANUAL":
        rec = PayRecord(pay_no=await _pay_no(db), order_id=order.id, direction="OUT", pay_type="SETTLE",
                        amount=settle, payer_id=None, payee_id=order.seller_id, channel="MANUAL", status="PENDING")
        db.add(rec)
        await transition(db, order, "FULL_PAID", None, "尾款结算审批通过, 人工转账中(待回单确认)")
        return
    await _finish_settle(db, order, settle)


async def _finish_settle(db: AsyncSession, order: OrderInfo, settle: Decimal) -> None:
    """尾款实际付出后: 记账 + 生成核销凭证 + 账单结清"""
    await _record(db, order, "OUT", "SETTLE", settle, None, order.seller_id)
    await transition(db, order, "FULL_PAID", None, f"养殖户已收全款(本笔结算¥{settle}), 生成电子提货凭证")
    await _generate_voucher(db, order)
    bills = await db.scalars(select(FinanceBill).where(FinanceBill.order_id == order.id))
    for b in bills.all():
        b.bill_status = "SETTLED"
    from app.modules.message.router import notify_enterprise
    await notify_enterprise(db, order.seller_id, "ADVANCE_PAID",
                            f"尾款到账: {order.order_no}", f"结算款 ¥{settle} 已支付, 请查收后核销放行", "ORDER", order.id)


async def confirm_manual_payment(db: AsyncSession, record_id: int, voucher_file_id: int, operator_id: int) -> PayRecord:
    """人工转账兜底: 财务上传回单并确认到账 (F9.7 银企直联就绪前)"""
    rec = await db.get(PayRecord, record_id)
    if not rec or rec.status != "PENDING" or rec.channel != "MANUAL":
        raise BizError("流水不存在或不在待确认状态")
    rec.status = "SUCCESS"
    rec.voucher_file_id = voucher_file_id
    rec.paid_time = datetime.now()
    order = await db.get(OrderInfo, rec.order_id)
    await _update_bill(db, order, "OUT", rec.amount)
    if rec.pay_type == "ADVANCE":
        from app.modules.message.router import notify_enterprise
        await notify_enterprise(db, order.seller_id, "ADVANCE_PAID",
                                f"垫资到账: {order.order_no}", f"平台垫资80% ¥{rec.amount} 已支付", "ORDER", order.id)
    elif rec.pay_type == "SETTLE":
        # 人工确认后补生成核销凭证 + 结清账单 (此时订单已是 FULL_PAID 中间态)
        await _generate_voucher(db, order)
        bills = await db.scalars(select(FinanceBill).where(FinanceBill.order_id == order.id))
        for b in bills.all():
            b.bill_status = "SETTLED"
        db.add(OrderEvent(order_id=order.id, from_status=order.status, to_status=order.status,
                          operator_id=operator_id, remark="人工转账回单确认, 电子提货凭证已生成"))
    return rec


async def _generate_voucher(db: AsyncSession, order: OrderInfo) -> PickupVoucher:
    """电子提货凭证 (F5.3): 养殖户收齐全款后生成, 扫码放行唯一凭证"""
    today = date.today().strftime("%Y%m%d")
    count = await db.scalar(select(func.count()).select_from(PickupVoucher))
    voucher_no = f"PV{today}{count + 1:04d}"
    sign = hashlib.sha256(f"{voucher_no}{settings.JWT_SECRET}".encode()).hexdigest()[:16].upper()
    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    outbound_id = None
    from app.models import OutboundOrder
    outbound = await db.scalar(select(OutboundOrder).where(OutboundOrder.order_id == order.id))
    if outbound:
        outbound_id = outbound.id
    v = PickupVoucher(voucher_no=voucher_no, order_id=order.id, outbound_id=outbound_id,
                      qr_payload=f"EGGPICKUP:{voucher_no}:{sign}")
    db.add(v)
    return v
