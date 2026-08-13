from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import Invoice, OrderInfo
from app.modules.invoice import service as invoice_service

router = APIRouter()


class InvoiceApply(BaseModel):
    order_id: int
    buyer_title: str
    tax_no: str


def _to_dict(i: Invoice) -> dict:
    return {"id": i.id, "invoice_no": i.invoice_no, "order_id": i.order_id, "type": i.type,
            "amount": float(i.amount), "buyer_title": i.buyer_title, "tax_no": i.tax_no,
            "status": i.status, "created_time": i.created_time.isoformat()}


@router.post("/apply")
async def apply_invoice(req: InvoiceApply, ctx=Depends(require_roles("CUSTOMER")), db: AsyncSession = Depends(get_db)):
    user, _ = ctx
    order = await db.get(OrderInfo, req.order_id)
    if not order or order.deleted:
        raise BizError("订单不存在", code=404)
    inv = await invoice_service.apply(db, order, req.buyer_title, req.tax_no, user)
    await db.commit()
    return ok(_to_dict(inv), message="发票申请已提交, 待财务审批")


@router.get("/list")
async def list_invoices(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, roles = ctx
    q = select(Invoice, OrderInfo.buyer_id).join(OrderInfo, OrderInfo.id == Invoice.order_id).where(Invoice.deleted == False)  # noqa: E712
    rows = (await db.execute(q.order_by(Invoice.created_time.desc()))).all()
    if "CUSTOMER" in roles:
        rows = [r for r in rows if r[1] == user.enterprise_id]
    return ok([_to_dict(i) for i, _ in rows])


@router.post("/{invoice_id}/archive")
async def archive(invoice_id: int, ctx=Depends(require_roles("FINANCE")), db: AsyncSession = Depends(get_db)):
    """财务归档 (F6.3)"""
    inv = await db.get(Invoice, invoice_id)
    if not inv or inv.deleted:
        raise BizError("发票不存在", code=404)
    if inv.status != "ISSUED":
        raise BizError("仅已开具的发票可归档")
    inv.status = "ARCHIVED"
    await db.commit()
    return ok(message="发票已归档")


@router.get("/check/{invoice_no}")
async def check_invoice(invoice_no: str, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """发票查验"""
    return ok(await invoice_service.check(db, invoice_no))
