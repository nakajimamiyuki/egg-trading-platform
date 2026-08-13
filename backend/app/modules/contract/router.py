from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.response import BizError, ok
from app.database.session import get_db
from app.models import Contract
from app.modules.contract import service as contract_service
from app.modules.file import service as file_service
from app.modules.file.service import presigned_url
from app.models import FileRecord

router = APIRouter()


def _to_dict(c: Contract) -> dict:
    return {
        "id": c.id, "contract_no": c.contract_no, "type": c.type, "order_id": c.order_id,
        "party_a_id": c.party_a_id, "party_b_id": c.party_b_id,
        "sign_status": c.sign_status, "party_a_signed": c.party_a_signed,
        "party_b_signed": c.party_b_signed, "file_id": c.file_id,
        "signed_time": c.signed_time.isoformat() if c.signed_time else None,
        "created_time": c.created_time.isoformat(),
    }


@router.get("/list")
async def list_contracts(ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """合同列表: 企业看自己的(乙方), 平台人员看全部"""
    user, roles = ctx
    q = select(Contract).where(Contract.deleted == False)  # noqa: E712
    if user.enterprise_id:
        q = q.where(Contract.party_b_id == user.enterprise_id)
    rows = await db.scalars(q.order_by(Contract.created_time.desc()))
    return ok([_to_dict(c) for c in rows.all()])


@router.get("/{contract_id}")
async def get_contract(contract_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """合同详情 + 文件预览地址"""
    user, _ = ctx
    c = await db.get(Contract, contract_id)
    if not c or c.deleted:
        raise BizError("合同不存在", code=404)
    if user.enterprise_id and c.party_b_id != user.enterprise_id:
        raise BizError("无权查看", code=403)
    data = _to_dict(c)
    if c.file_id:
        rec = await db.get(FileRecord, c.file_id)
        if rec:
            data["file_url"] = await presigned_url(rec.bucket, rec.object_key)
    return ok(data)


@router.post("/{contract_id}/sign")
async def sign_contract(contract_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """在线签署 (甲方=平台人员, 乙方=企业用户)"""
    user, _ = ctx
    c = await db.get(Contract, contract_id)
    if not c or c.deleted:
        raise BizError("合同不存在", code=404)
    await contract_service.sign(db, c, user)
    await db.commit()
    msg = "双方签署完成, 合同生效并存证" if c.sign_status == "SIGNED" else "签署成功, 待另一方签署"
    return ok(_to_dict(c), message=msg)


@router.post("/{contract_id}/archive")
async def archive_contract(contract_id: int, ctx=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """归档 (平台人员)"""
    user, _ = ctx
    if user.enterprise_id:
        raise BizError("仅平台人员可归档", code=403)
    c = await db.get(Contract, contract_id)
    if not c or c.deleted:
        raise BizError("合同不存在", code=404)
    if c.sign_status != "SIGNED":
        raise BizError("合同未签署完成, 不能归档")
    c.sign_status = "ARCHIVED"
    await db.commit()
    return ok(message="合同已归档")
