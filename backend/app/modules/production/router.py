from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.core.response import ok
from app.database.session import get_db
from app.models import EggProduction

router = APIRouter()


class ProductionCreate(BaseModel):
    prod_date: date
    quantity: int
    grade: str
    spec: str


def _to_dict(p: EggProduction) -> dict:
    return {"id": p.id, "enterprise_id": p.enterprise_id, "prod_date": p.prod_date.isoformat(),
            "quantity": p.quantity, "grade": p.grade, "spec": p.spec,
            "created_time": p.created_time.isoformat()}


@router.post("")
async def create_production(req: ProductionCreate, ctx=Depends(require_roles("FARM")), db: AsyncSession = Depends(get_db)):
    """养殖端产蛋数据录入 (F2.3)"""
    user, _ = ctx
    p = EggProduction(enterprise_id=user.enterprise_id, prod_date=req.prod_date,
                      quantity=req.quantity, grade=req.grade, spec=req.spec, created_by=user.id)
    db.add(p)
    await db.commit()
    return ok(_to_dict(p), message="产蛋数据已录入")


@router.get("/my")
async def my_production(ctx=Depends(require_roles("FARM")), db: AsyncSession = Depends(get_db)):
    user, _ = ctx
    rows = await db.scalars(select(EggProduction).where(
        EggProduction.enterprise_id == user.enterprise_id, EggProduction.deleted == False  # noqa: E712
    ).order_by(EggProduction.prod_date.desc()))
    return ok([_to_dict(p) for p in rows.all()])


@router.get("/list")
async def list_production(ctx=Depends(require_roles("BUSINESS", "FINANCE")), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(EggProduction).where(EggProduction.deleted == False).order_by(EggProduction.prod_date.desc()))  # noqa: E712
    return ok([_to_dict(p) for p in rows.all()])
