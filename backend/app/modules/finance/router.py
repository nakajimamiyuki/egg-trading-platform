from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import FinanceBill, OrderInfo, PayRecord
from app.modules.finance import service as finance_service

router = APIRouter()


class PayRequest(BaseModel):
    order_id: int
    pay_type: str  # DEPOSIT / TAIL


@router.post("/pay")
async def mock_pay(req: PayRequest, ctx=Depends(require_roles("CUSTOMER")), db: AsyncSession = Depends(get_db)):
    """客户付款 (模拟支付通道; 真实支付上线时切换 channel)"""
    user, _ = ctx
    order = await db.get(OrderInfo, req.order_id)
    if not order or order.deleted:
        raise BizError("订单不存在", code=404)
    rec = await finance_service.buyer_pay(db, order, req.pay_type, user)
    await db.commit()
    return ok({"pay_no": rec.pay_no, "amount": float(rec.amount)}, message=f"支付成功 ¥{rec.amount}")


@router.get("/records")
async def pay_records(order_id: int | None = None, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """资金流水: 业务/财务看全部, 企业看与本企业相关的"""
    user, roles = ctx
    q = select(PayRecord).where(PayRecord.deleted == False)  # noqa: E712
    if order_id:
        q = q.where(PayRecord.order_id == order_id)
    if "CUSTOMER" in roles:
        q = q.where(PayRecord.payer_id == user.enterprise_id)
    elif "FARM" in roles:
        q = q.where(PayRecord.payee_id == user.enterprise_id)
    rows = await db.scalars(q.order_by(PayRecord.created_time.desc()).limit(200))
    return ok([
        {"id": r.id, "pay_no": r.pay_no, "order_id": r.order_id, "direction": r.direction,
         "pay_type": r.pay_type, "amount": float(r.amount), "channel": r.channel,
         "status": r.status, "paid_time": r.paid_time.isoformat() if r.paid_time else None}
        for r in rows.all()
    ])


class ManualConfirm(BaseModel):
    voucher_file_id: int


@router.post("/records/{record_id}/confirm-manual")
async def confirm_manual(record_id: int, req: ManualConfirm, ctx=Depends(require_roles("FINANCE")),
                         db: AsyncSession = Depends(get_db)):
    """人工转账兜底: 财务上传回单后确认到账 (银企直联就绪前的付款方式)"""
    user, _ = ctx
    rec = await finance_service.confirm_manual_payment(db, record_id, req.voucher_file_id, user.id)
    await db.commit()
    return ok({"pay_no": rec.pay_no}, message="回单已确认, 付款生效")


@router.get("/bills")
async def my_bills(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """账单中心 (F6.4)"""
    user, roles = ctx
    q = select(FinanceBill).where(FinanceBill.deleted == False)  # noqa: E712
    if "FARM" in roles or "CUSTOMER" in roles:
        q = q.where(FinanceBill.enterprise_id == user.enterprise_id)
    rows = await db.scalars(q.order_by(FinanceBill.created_time.desc()))
    return ok([
        {"id": b.id, "bill_no": b.bill_no, "order_id": b.order_id, "amount": float(b.amount),
         "received": float(b.received), "paid": float(b.paid), "bill_status": b.bill_status,
         "created_time": b.created_time.isoformat()}
        for b in rows.all()
    ])
