"""满勤合作激励 (F10.4): 合作满6个月 + 发货量达每满10万只鸡规模 → 赠送机器人"""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import Enterprise, IncentiveRecord, OrderInfo

router = APIRouter()

REQUIRED_MONTHS = 6
REQUIRED_SCALE = 100000  # 10万只鸡规模(按累计发货枚数折算)


async def _compute(db: AsyncSession, ent: Enterprise) -> tuple[int, int]:
    """返回 (合作月数, 累计发货量)"""
    months = (date.today().year - ent.created_time.year) * 12 + (date.today().month - ent.created_time.month)
    shipped = await db.scalar(select(func.coalesce(func.sum(OrderInfo.quantity), 0)).where(
        OrderInfo.seller_id == ent.id, OrderInfo.status == "FINISHED", OrderInfo.deleted == False))  # noqa: E712
    return max(months, 0), int(shipped or 0)


@router.get("/list")
async def list_incentives(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """激励名单: 业务端看全部养殖户, 养殖户看自己"""
    user, roles = ctx
    q = select(Enterprise).where(Enterprise.type == "FARM", Enterprise.audit_status == "PASS", Enterprise.deleted == False)  # noqa: E712
    if "FARM" in roles:
        q = q.where(Enterprise.id == user.enterprise_id)
    farms = (await db.scalars(q)).all()
    result = []
    for ent in farms:
        months, shipped = await _compute(db, ent)
        qualified = months >= REQUIRED_MONTHS and shipped >= REQUIRED_SCALE
        rec = await db.scalar(select(IncentiveRecord).where(IncentiveRecord.enterprise_id == ent.id, IncentiveRecord.deleted == False))  # noqa: E712
        result.append({
            "enterprise_id": ent.id, "enterprise_name": ent.enterprise_name,
            "coop_months": months, "shipped": shipped,
            "required_months": REQUIRED_MONTHS, "required_scale": REQUIRED_SCALE,
            "qualified": qualified, "status": rec.status if rec else "TRACKING",
            "promise_file_id": rec.promise_file_id if rec else None,
            "record_id": rec.id if rec else None,
        })
    return ok(result)


class GrantRequest(BaseModel):
    enterprise_id: int
    promise_file_id: int | None = None


@router.post("/grant")
async def grant(req: GrantRequest, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    """确认赠送机器人 (可附承诺书文件)"""
    user, _ = ctx
    ent = await db.get(Enterprise, req.enterprise_id)
    if not ent or ent.deleted:
        raise BizError("企业不存在", code=404)
    months, shipped = await _compute(db, ent)
    if not (months >= REQUIRED_MONTHS and shipped >= REQUIRED_SCALE):
        raise BizError(f"未达标: 合作 {months}/6 个月, 发货 {shipped}/100000")
    rec = await db.scalar(select(IncentiveRecord).where(IncentiveRecord.enterprise_id == ent.id, IncentiveRecord.deleted == False))  # noqa: E712
    if not rec:
        rec = IncentiveRecord(enterprise_id=ent.id)
        db.add(rec)
    rec.coop_months = months
    rec.chicken_scale = shipped
    rec.qualified = True
    rec.promise_file_id = req.promise_file_id
    rec.status = "GRANTED"
    await db.commit()
    return ok(message=f"已确认向 {ent.enterprise_name} 赠送机器人一台")
