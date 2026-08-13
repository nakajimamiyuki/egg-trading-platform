from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.core.response import ok
from app.database.session import get_db
from app.models import WfInstance
from app.modules.workflow.service import WorkflowService

router = APIRouter()


class HandleRequest(BaseModel):
    action: str  # PASS / REJECT
    opinion: str = ""


@router.get("/todo")
async def todo(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    _, roles = ctx
    return ok(await WorkflowService(db).todo(roles))


@router.post("/tasks/{task_id}/handle")
async def handle(task_id: int, req: HandleRequest, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user, roles = ctx
    if req.action not in ("PASS", "REJECT"):
        from app.core.response import BizError
        raise BizError("action 只能是 PASS 或 REJECT")
    await WorkflowService(db).handle(task_id, user, roles, req.action, req.opinion)
    await db.commit()
    return ok(message="审批完成")


@router.get("/mine")
async def mine(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """我发起的审批"""
    user, _ = ctx
    rows = await db.scalars(
        select(WfInstance).where(WfInstance.initiator_id == user.id).order_by(WfInstance.created_time.desc())
    )
    return ok([
        {"id": i.id, "title": i.title, "biz_type": i.biz_type, "status": i.status,
         "current_seq": i.current_seq, "created_time": i.created_time.isoformat()}
        for i in rows.all()
    ])
