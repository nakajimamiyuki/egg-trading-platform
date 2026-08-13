from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import CloseApply, CloseOrder, Enterprise, RiskSurvey
from app.modules.risk import service as risk_service

router = APIRouter()


class ApplyCreate(BaseModel):
    delivery_warehouse_id: int
    apply_type: str
    remark: str = ""


class SurveyCreate(BaseModel):
    enterprise_id: int
    report_file_id: int | None = None
    conclusion: str = "WAIT"
    remark: str = ""


# ---------- 平仓预警与申请 (F7.1/F7.2) ----------

@router.post("/check-warnings")
async def check_warnings(ctx=Depends(require_roles("BUSINESS", "ADMIN")), db: AsyncSession = Depends(get_db)):
    """手动触发周转预警检查 (定时任务每日也会自动跑)"""
    count = await risk_service.check_turnover_warnings(db)
    await db.commit()
    return ok({"warned": count}, message=f"检查完成, 新增预警 {count} 条")


@router.post("/apply")
async def create_apply(req: ApplyCreate, ctx=Depends(require_roles("FARM")), db: AsyncSession = Depends(get_db)):
    """养殖端 5 类申请 (F7.2)"""
    user, _ = ctx
    apply = await risk_service.create_apply(db, req.delivery_warehouse_id, req.apply_type, req.remark, user)
    await db.commit()
    return ok({"id": apply.id}, message="申请已提交, 待业务审批")


@router.get("/apply/list")
async def apply_list(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """申请列表: 养殖户看自己的, 业务/财务看全部"""
    from app.models import DeliveryWarehouse

    user, roles = ctx
    rows = await db.scalars(select(CloseApply).where(CloseApply.deleted == False).order_by(CloseApply.created_time.desc()))  # noqa: E712
    result = []
    for a in rows.all():
        dw = await db.get(DeliveryWarehouse, a.delivery_warehouse_id)
        if "FARM" in roles and dw.enterprise_id != user.enterprise_id:
            continue
        result.append({"id": a.id, "dw_no": dw.dw_no, "apply_type": a.apply_type,
                       "apply_type_text": risk_service._apply_text(a.apply_type),
                       "status": a.status, "remark": a.remark, "created_time": a.created_time.isoformat()})
    return ok(result)


# ---------- 强制平仓 (F7.3/F7.4) ----------

@router.post("/force-close/{dw_id}")
async def force_close(dw_id: int, ctx=Depends(require_roles("BUSINESS")), db: AsyncSession = Depends(get_db)):
    """业务端督办: 超期强制平仓 + 折价处置"""
    user, _ = ctx
    co = await risk_service.force_close(db, dw_id, user.id)
    await db.commit()
    return ok({"close_no": co.close_no, "settle_amount": float(co.settle_amount)},
              message="平仓单已创建, 待财务退款审批")


@router.get("/close/list")
async def close_list(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """平仓台账 (F7.4)"""
    from app.models import DeliveryWarehouse
    user, roles = ctx
    rows = await db.scalars(select(CloseOrder).where(CloseOrder.deleted == False).order_by(CloseOrder.created_time.desc()))  # noqa: E712
    result = []
    for c in rows.all():
        dw = await db.get(DeliveryWarehouse, c.delivery_warehouse_id)
        if "FARM" in roles and dw.enterprise_id != user.enterprise_id:
            continue
        result.append({"id": c.id, "close_no": c.close_no, "dw_no": dw.dw_no, "close_type": c.close_type,
                       "quantity": c.quantity, "original_amount": float(c.original_amount),
                       "settle_amount": float(c.settle_amount), "profit_loss": float(c.profit_loss or 0),
                       "discount_ratio": float(c.discount_ratio), "status": c.status,
                       "created_time": c.created_time.isoformat()})
    return ok(result)


# ---------- 渠道风控尽调 (F1.3) ----------

@router.post("/survey")
async def create_survey(req: SurveyCreate, ctx=Depends(require_roles("FINANCE", "BUSINESS")), db: AsyncSession = Depends(get_db)):
    """风控团队登记渠道方尽调结论"""
    user, _ = ctx
    ent = await db.get(Enterprise, req.enterprise_id)
    if not ent or ent.deleted:
        raise BizError("企业不存在", code=404)
    if req.conclusion not in ("WAIT", "PASS", "REJECT"):
        raise BizError("conclusion 必须是 WAIT/PASS/REJECT")
    s = RiskSurvey(enterprise_id=req.enterprise_id, report_file_id=req.report_file_id,
                   conclusion=req.conclusion, remark=req.remark, created_by=user.id)
    db.add(s)
    await db.commit()
    return ok({"id": s.id}, message="尽调结论已登记")


@router.get("/survey/list")
async def survey_list(ctx=Depends(require_roles("FINANCE", "BUSINESS")), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(RiskSurvey).where(RiskSurvey.deleted == False).order_by(RiskSurvey.created_time.desc()))  # noqa: E712
    result = []
    for s in rows.all():
        ent = await db.get(Enterprise, s.enterprise_id)
        result.append({"id": s.id, "enterprise_name": ent.enterprise_name if ent else "",
                       "conclusion": s.conclusion, "remark": s.remark,
                       "report_file_id": s.report_file_id, "created_time": s.created_time.isoformat()})
    return ok(result)
