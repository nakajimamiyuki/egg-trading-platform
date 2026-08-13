from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import Enterprise, EnterpriseFile

router = APIRouter()


def _to_dict(e: Enterprise) -> dict:
    return {
        "id": e.id, "enterprise_name": e.enterprise_name, "type": e.type,
        "license_no": e.license_no, "legal_person": e.legal_person,
        "contact_phone": e.contact_phone, "address": e.address,
        "breed": e.breed, "stock_qty": e.stock_qty, "day_age": e.day_age,
        "daily_egg_qty": e.daily_egg_qty, "audit_status": e.audit_status,
        "audit_remark": e.audit_remark, "coop_evaluation": e.coop_evaluation,
        "created_time": e.created_time.isoformat(),
    }


@router.get("/my")
async def my_enterprise(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """当前用户的企业档案与准入状态"""
    user, _ = ctx
    if not user.enterprise_id:
        raise BizError("当前账号未关联企业")
    ent = await db.get(Enterprise, user.enterprise_id)
    files = await db.scalars(select(EnterpriseFile).where(EnterpriseFile.enterprise_id == ent.id))
    data = _to_dict(ent)
    data["files"] = [{"file_type": f.file_type, "file_id": f.file_id} for f in files.all()]
    return ok(data)


@router.get("/list")
async def list_enterprises(type: str | None = None, audit_status: str | None = None,
                           ctx=Depends(require_roles("BUSINESS", "FINANCE")), db: AsyncSession = Depends(get_db)):
    """合作方管理 (F1.4): 业务/财务端查看"""
    q = select(Enterprise).where(Enterprise.deleted == False)  # noqa: E712
    if type:
        q = q.where(Enterprise.type == type)
    if audit_status:
        q = q.where(Enterprise.audit_status == audit_status)
    rows = await db.scalars(q.order_by(Enterprise.created_time.desc()))
    return ok([_to_dict(e) for e in rows.all()])
