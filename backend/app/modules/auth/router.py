from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.response import BizError, ok
from app.core.security import create_token, hash_password, verify_password
from app.database.session import get_db
from app.models import Enterprise, EnterpriseFile, SysRole, SysUser, SysUserRole
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.modules.workflow.service import WorkflowService

router = APIRouter()

ROLE_MAP = {"FARM": "FARM", "BUYER": "CUSTOMER"}


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """自助注册: 创建账号 + 企业档案(待审核) + 自动发起准入审批"""
    exists = await db.scalar(select(SysUser).where(SysUser.username == req.username))
    if exists:
        raise BizError("用户名已存在")

    user = SysUser(
        username=req.username,
        password=hash_password(req.password),
        real_name=req.real_name,
        phone=req.phone,
    )
    db.add(user)
    await db.flush()

    ent = Enterprise(
        enterprise_name=req.enterprise_name,
        type=req.enterprise_type,
        license_no=req.license_no,
        legal_person=req.legal_person,
        contact_phone=req.contact_phone or req.phone,
        address=req.address,
        breed=req.breed,
        stock_qty=req.stock_qty,
        day_age=req.day_age,
        daily_egg_qty=req.daily_egg_qty,
        created_by=user.id,
    )
    db.add(ent)
    await db.flush()
    user.enterprise_id = ent.id

    for f in req.files:
        db.add(EnterpriseFile(enterprise_id=ent.id, file_type=f.get("file_type", "OTHER"), file_id=f["file_id"]))

    role = await db.scalar(select(SysRole).where(SysRole.code == ROLE_MAP[req.enterprise_type]))
    db.add(SysUserRole(user_id=user.id, role_id=role.id))

    await WorkflowService(db).start(
        "ENTERPRISE_AUDIT",
        biz_id=ent.id,
        title=f"企业准入审批: {req.enterprise_name}",
        initiator_id=user.id,
    )
    await db.commit()
    return ok({"user_id": user.id, "enterprise_id": ent.id}, message="注册成功, 待平台审核")


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(SysUser).where(SysUser.username == req.username, SysUser.deleted == False))  # noqa: E712
    if not user or not verify_password(req.password, user.password):
        raise BizError("用户名或密码错误")
    if user.status != 1:
        raise BizError("账号已禁用")
    rows = await db.execute(
        select(SysRole.code).join(SysUserRole, SysUserRole.role_id == SysRole.id).where(SysUserRole.user_id == user.id)
    )
    roles = [r[0] for r in rows.all()]
    main_role = roles[0] if roles else ""
    return ok({"token": create_token(user.id, main_role), "user_id": user.id, "real_name": user.real_name, "roles": roles})


@router.get("/me")
async def me(ctx=Depends(get_current_user)):
    user, roles = ctx
    return ok({"user_id": user.id, "username": user.username, "real_name": user.real_name, "roles": roles, "enterprise_id": user.enterprise_id})
