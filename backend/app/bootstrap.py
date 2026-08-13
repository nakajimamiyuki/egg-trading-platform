"""应用启动引导: 创建初始管理员 + 种子审批流定义 + MinIO bucket"""
import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.database.session import async_session
from app.models import SysRole, SysUser, SysUserRole, WfDefinition, WfNode
from app.modules.file.service import ensure_bucket

logger = logging.getLogger(__name__)

# 审批流种子: (code, name, biz_type, [(节点名, 顺序, 审批角色)])
WF_SEEDS = [
    ("ENTERPRISE_AUDIT", "企业准入审批", "ENTERPRISE_AUDIT", [("业务员审核", 1, "BUSINESS")]),
    ("WAREHOUSE_LEASE", "仓库租赁审批", "WAREHOUSE_LEASE", [("业务审批", 1, "BUSINESS"), ("财务审批", 2, "FINANCE")]),
    ("DELIVERY_WH_CREATE", "交割仓建立审批", "DELIVERY_WH_CREATE", [("业务审批", 1, "BUSINESS")]),
    ("ORDER_AUDIT", "订单业务审核", "ORDER_AUDIT", [("业务审核", 1, "BUSINESS")]),
    ("SALE_APPLY", "交割仓销售申请审批", "SALE_APPLY", [("业务审核", 1, "BUSINESS")]),
    ("CONTRACT_SIGN", "合同签署审批", "CONTRACT_SIGN", [("业务审批", 1, "BUSINESS"), ("财务审批", 2, "FINANCE")]),
    ("PAYMENT_80", "交割仓付款审批(80%垫资)", "PAYMENT_80", [("财务审批", 1, "FINANCE")]),
    ("PAYMENT_20", "交割仓尾款审批(20%结算)", "PAYMENT_20", [("财务审批", 1, "FINANCE")]),
    ("CLOSE_REFUND", "平仓退款审批", "CLOSE_REFUND", [("财务审批", 1, "FINANCE")]),
    ("INVOICE_AUDIT", "发票审批", "INVOICE_AUDIT", [("财务审批", 1, "FINANCE")]),
]


async def bootstrap() -> None:
    async with async_session() as db:
        # 0. 平台运营方企业(合同甲方)
        from app.models import Enterprise
        platform = await db.scalar(select(Enterprise).where(Enterprise.type == "PLATFORM"))
        if not platform:
            db.add(Enterprise(enterprise_name="蛋品交易平台运营方", type="PLATFORM", audit_status="PASS"))

        # 1. 初始管理员
        admin = await db.scalar(select(SysUser).where(SysUser.username == settings.ADMIN_USERNAME))
        if not admin:
            admin = SysUser(
                username=settings.ADMIN_USERNAME,
                password=hash_password(settings.ADMIN_PASSWORD),
                real_name="系统管理员",
            )
            db.add(admin)
            await db.flush()
            role = await db.scalar(select(SysRole).where(SysRole.code == "ADMIN"))
            db.add(SysUserRole(user_id=admin.id, role_id=role.id))
            logger.info("初始管理员已创建: %s", settings.ADMIN_USERNAME)

        # 2. 演示用业务/财务账号 (开发环境)
        for username, name, role_code in [("business01", "业务员一", "BUSINESS"), ("finance01", "财务一", "FINANCE")]:
            if not await db.scalar(select(SysUser).where(SysUser.username == username)):
                u = SysUser(username=username, password=hash_password("123456"), real_name=name)
                db.add(u)
                await db.flush()
                role = await db.scalar(select(SysRole).where(SysRole.code == role_code))
                db.add(SysUserRole(user_id=u.id, role_id=role.id))

        # 3. 审批流定义种子
        for code, name, biz_type, nodes in WF_SEEDS:
            definition = await db.scalar(select(WfDefinition).where(WfDefinition.code == code))
            if not definition:
                definition = WfDefinition(code=code, name=name, biz_type=biz_type)
                db.add(definition)
                await db.flush()
                for node_name, seq, role_code in nodes:
                    db.add(WfNode(definition_id=definition.id, node_name=node_name, seq=seq,
                                  approver_type="ROLE", approver_ref=role_code))

        await db.commit()

    # 4. MinIO bucket
    try:
        await ensure_bucket()
    except Exception as exc:  # MinIO 未就绪不阻塞启动
        logger.warning("MinIO bucket 初始化失败(可稍后重试): %s", exc)
