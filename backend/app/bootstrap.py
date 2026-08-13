"""应用启动引导: 种子数据(幂等) + 初始管理员 + 审批流定义 + MinIO bucket"""
import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.database.session import async_session
from app.models import SysConfig, SysDictItem, SysDictType, SysRole, SysUser, SysUserRole, WfDefinition, WfNode
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
    ("CLOSE_APPLY", "养殖端平仓申请审批", "CLOSE_APPLY", [("业务审批", 1, "BUSINESS")]),
    ("INVOICE_AUDIT", "发票审批", "INVOICE_AUDIT", [("财务审批", 1, "FINANCE")]),
]

ROLE_SEEDS = [
    ("FARM", "养殖企业", "养殖端"), ("CUSTOMER", "客户", "采购客户端"),
    ("BUSINESS", "业务人员", "业务端"), ("FINANCE", "财务人员", "财务端"), ("ADMIN", "管理员", "管理后台"),
]

CONFIG_SEEDS = [
    ("deposit_ratio", "0.20", "客户定金比例"),
    ("advance_ratio", "0.80", "平台垫资比例"),
    ("turnover_days", "3", "交割仓周转预警天数"),
    ("close_discount_ratio", "0.80", "超期强制平仓折价比例(按80%计价)"),
    ("platform_profit_per_unit", "1.00", "模式③渠道账期平台分利(元/件)"),
    ("bank_channel", "MOCK", "付款通道: MOCK自动/MANUAL人工回单"),
]

DICT_SEEDS = {
    "EGG_GRADE": ("鸡蛋品级", [("A", "A级"), ("B", "B级"), ("C", "C级")]),
    "EGG_SPEC": ("鸡蛋规格", [("S50", "50kg/件"), ("S45", "45kg/件"), ("S40", "40kg/件")]),
}


async def bootstrap() -> None:
    async with async_session() as db:
        # 单据编号序列(测试库等无SQL初始化脚本的环境)
        from sqlalchemy import text
        await db.execute(text("CREATE SEQUENCE IF NOT EXISTS doc_seq START 1"))

        # 0. 角色/字典/配置种子(幂等, 供无 SQL 初始化脚本的环境使用, 如测试库)
        for code, name, remark in ROLE_SEEDS:
            if not await db.scalar(select(SysRole).where(SysRole.code == code)):
                db.add(SysRole(code=code, name=name, remark=remark))
        for key, value, remark in CONFIG_SEEDS:
            if not await db.scalar(select(SysConfig).where(SysConfig.config_key == key)):
                db.add(SysConfig(config_key=key, config_value=value, remark=remark))
        for type_code, (type_name, items) in DICT_SEEDS.items():
            dtype = await db.scalar(select(SysDictType).where(SysDictType.code == type_code))
            if not dtype:
                dtype = SysDictType(code=type_code, name=type_name)
                db.add(dtype)
                await db.flush()
                for sort, (code, name) in enumerate(items, start=1):
                    db.add(SysDictItem(type_id=dtype.id, code=code, name=name, sort=sort))

        # 1. 平台运营方企业(合同甲方)
        from app.models import Enterprise
        platform = await db.scalar(select(Enterprise).where(Enterprise.type == "PLATFORM"))
        if not platform:
            db.add(Enterprise(enterprise_name="蛋品交易平台运营方", type="PLATFORM", audit_status="PASS"))

        # 2. 初始管理员
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
