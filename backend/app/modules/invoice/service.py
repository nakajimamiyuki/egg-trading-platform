"""电子发票服务 (F6.3/F9.4): 申请 -> 审批 -> 开具 -> 归档/查验
真实税控服务商(百望/航信)接入点预留: file_id + invoice_no 外部回写
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import BizError
from app.models import Invoice, OrderInfo
from app.modules.workflow.service import WorkflowService


async def apply(db: AsyncSession, order: OrderInfo, buyer_title: str, tax_no: str, user) -> Invoice:
    """客户申请开票"""
    if order.buyer_id != user.enterprise_id:
        raise BizError("只能为本企业订单申请发票", code=403)
    if order.status not in ("TAIL_PAID", "FULL_PAID", "RELEASED", "FINISHED"):
        raise BizError("订单完成付款后才能申请发票")
    exists = await db.scalar(select(Invoice).where(Invoice.order_id == order.id, Invoice.deleted == False))  # noqa: E712
    if exists:
        raise BizError("该订单已申请过发票")
    inv = Invoice(order_id=order.id, amount=order.total_amount, buyer_title=buyer_title, tax_no=tax_no)
    db.add(inv)
    await db.flush()
    inv.status = "AUDITING"
    await WorkflowService(db).start("INVOICE_AUDIT", biz_id=inv.id,
                                    title=f"发票审批: {order.order_no} ¥{order.total_amount}", initiator_id=user.id)
    return inv


async def issue(db: AsyncSession, invoice: Invoice) -> None:
    """审批通过后开具 (当前为模拟开具, 接入服务商后替换)"""
    from app.core.docno import next_doc_no
    invoice.invoice_no = await next_doc_no(db, "INV")
    invoice.status = "ISSUED"


async def check(db: AsyncSession, invoice_no: str) -> dict:
    """发票查验 (模拟: 与平台记录核对)"""
    inv = await db.scalar(select(Invoice).where(Invoice.invoice_no == invoice_no, Invoice.deleted == False))  # noqa: E712
    if not inv:
        raise BizError("发票不存在或已作废", code=404)
    return {"invoice_no": inv.invoice_no, "amount": float(inv.amount), "status": inv.status,
            "check_result": "查验一致(模拟)", "buyer_title": inv.buyer_title}
