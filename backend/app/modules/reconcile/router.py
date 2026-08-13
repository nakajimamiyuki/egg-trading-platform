from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import ReconcileBatch, ReconcileDiff
from app.modules.reconcile import service as reconcile_service

router = APIRouter()


class RunBatch(BaseModel):
    scope: str = "DELIVERY"  # DELIVERY交割仓业务 / SELF自营业务
    period_start: date
    period_end: date


class Adjust(BaseModel):
    amount: float
    reason: str


@router.post("/run")
async def run(req: RunBatch, ctx=Depends(require_roles("FINANCE")), db: AsyncSession = Depends(get_db)):
    """发起对账 (F8.1/F8.2)"""
    user, _ = ctx
    if req.scope not in ("DELIVERY", "SELF"):
        raise BizError("scope 必须是 DELIVERY/SELF")
    batch = await reconcile_service.run_batch(db, req.scope, req.period_start, req.period_end, user.id)
    await db.commit()
    return ok({"batch_no": batch.batch_no, "total": batch.total_count,
               "matched": batch.matched, "diff": batch.diff_count}, message="对账完成")


@router.get("/batches")
async def batches(ctx=Depends(require_roles("FINANCE", "BUSINESS")), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(ReconcileBatch).where(ReconcileBatch.deleted == False).order_by(ReconcileBatch.created_time.desc()))  # noqa: E712
    return ok([{"id": b.id, "batch_no": b.batch_no, "scope": b.scope,
                "period": f"{b.period_start} ~ {b.period_end}", "total_count": b.total_count,
                "matched": b.matched, "diff_count": b.diff_count, "status": b.status,
                "created_time": b.created_time.isoformat()} for b in rows.all()])


@router.get("/diffs")
async def diffs(batch_id: int, ctx=Depends(require_roles("FINANCE", "BUSINESS")), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(ReconcileDiff).where(ReconcileDiff.batch_id == batch_id, ReconcileDiff.deleted == False))  # noqa: E712
    return ok([{"id": d.id, "biz_type": d.biz_type, "biz_id": d.biz_id, "diff_desc": d.diff_desc,
                "status": d.status, "adjust_amount": float(d.adjust_amount) if d.adjust_amount else None,
                "adjust_reason": d.adjust_reason,
                "adjusted_time": d.adjusted_time.isoformat() if d.adjusted_time else None} for d in rows.all()])


@router.post("/diffs/{diff_id}/adjust")
async def adjust(diff_id: int, req: Adjust, ctx=Depends(require_roles("FINANCE")), db: AsyncSession = Depends(get_db)):
    """人工调账 (留痕: 操作人/时间/原因)"""
    user, _ = ctx
    await reconcile_service.adjust_diff(db, diff_id, Decimal(str(req.amount)), req.reason, user.id)
    await db.commit()
    return ok(message="调账完成, 已留痕")


@router.post("/batches/{batch_id}/archive")
async def archive(batch_id: int, ctx=Depends(require_roles("FINANCE")), db: AsyncSession = Depends(get_db)):
    """对账确认归档 (F8.1): 有未处理差异时不允许归档"""
    batch = await db.get(ReconcileBatch, batch_id)
    if not batch or batch.deleted:
        raise BizError("批次不存在", code=404)
    open_diffs = await db.scalar(select(ReconcileDiff).where(ReconcileDiff.batch_id == batch_id, ReconcileDiff.status == "OPEN"))
    if open_diffs:
        raise BizError("存在未处理差异, 不能归档")
    batch.status = "ARCHIVED"
    await db.commit()
    return ok(message="对账批次已归档")
