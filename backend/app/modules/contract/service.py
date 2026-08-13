"""电子合同服务 (F1.5/F3.2/F9.3)
生成 -> 合同签署审批 -> 双方在线签署 -> 归档存证
真实电子签(e签宝/法大大)接入点已预留: esign_flow_id + 签名字段
"""
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import BizError
from app.models import Contract, Enterprise, FileRecord, OrderInfo
from app.modules.file import service as file_service

SETTLE_TEMPLATE = """
<h2>交割仓入驻电子合同</h2>
<p>合同编号: {contract_no}</p>
<p>甲方(平台): {party_a}</p>
<p>乙方(入驻企业): {party_b}</p>
<p>统一社会信用代码: {license_no}</p>
<hr/>
<p>一、乙方自愿入驻甲方蛋品交易平台, 使用交割仓服务进行蛋品销售。</p>
<p>二、乙方承诺所供蛋品符合国家食品安全标准, 产蛋数据真实有效。</p>
<p>三、双方确认平台交易规则: 客户定金20%, 平台垫资80%, 养殖户收齐全款后方可放行。</p>
<p>四、交割仓周转期为 {turnover_days} 天, 超期未售出甲方有权按 {discount}% 折价强制平仓。</p>
<p>五、本合同仅首次入驻签署一次, 日常业务不再重复签署。</p>
<p>签署日期: {today}</p>
"""

SALE_TEMPLATE = """
<h2>交割仓销售合同</h2>
<p>合同编号: {contract_no}　关联订单: {order_no}</p>
<p>甲方(平台): {party_a}</p>
<p>乙方(卖方): {party_b}</p>
<p>买方: {buyer}</p>
<hr/>
<p>标的物: 鸡蛋 {grade}级 {spec}, 数量 {quantity} 枚, 单价 ¥{unit_price}, 总额 ¥{total_amount}</p>
<p>销售模式: {sale_mode_text}</p>
<p>结算方式: 买方支付20%定金, 平台垫资80%; 出库三方确认后买方支付80%尾款, 平台结算20%尾款。</p>
<p>签署日期: {today}</p>
"""

MODE_TEXT = {"M1": "模式①蛋库出库标准", "M2": "模式②在途货物预付", "M3": "模式③渠道账期"}


async def _next_no(db: AsyncSession) -> str:
    today = date.today().strftime("%Y%m%d")
    count = await db.scalar(select(func.count()).select_from(Contract))
    return f"HT{today}{count + 1:04d}"


async def _platform(db: AsyncSession) -> Enterprise:
    ent = await db.scalar(select(Enterprise).where(Enterprise.type == "PLATFORM"))
    if not ent:
        raise BizError("平台运营方企业未初始化")
    return ent


async def _save_file(db: AsyncSession, contract_no: str, html: str) -> int:
    content = f"<html><head><meta charset='utf-8'></head><body>{html}</body></html>"
    bucket, key = await file_service.upload(content.encode("utf-8"), f"{contract_no}.html", "text/html")
    rec = FileRecord(bucket=bucket, object_key=key, file_name=f"{contract_no}.html",
                     file_size=len(content), content_type="text/html", biz_type="CONTRACT")
    db.add(rec)
    await db.flush()
    return rec.id


async def generate_settle_contract(db: AsyncSession, enterprise: Enterprise, initiator_id: int) -> Contract:
    """入驻合同 (仅首次入驻时签署, F3.2)"""
    from app.core.bizconfig import get_config_decimal, get_config_int
    from app.modules.workflow.service import WorkflowService

    platform = await _platform(db)
    contract_no = await _next_no(db)
    discount = await get_config_decimal(db, "close_discount_ratio", "0.80")
    html = SETTLE_TEMPLATE.format(
        contract_no=contract_no, party_a=platform.enterprise_name, party_b=enterprise.enterprise_name,
        license_no=enterprise.license_no or "-",
        turnover_days=await get_config_int(db, "turnover_days", 3),
        discount=int(discount * 100),
        today=date.today().isoformat(),
    )
    contract = Contract(contract_no=contract_no, type="SETTLE", party_a_id=platform.id,
                        party_b_id=enterprise.id, file_id=await _save_file(db, contract_no, html))
    db.add(contract)
    await db.flush()
    await WorkflowService(db).start("CONTRACT_SIGN", biz_id=contract.id,
                                    title=f"合同签署审批: 入驻合同 {enterprise.enterprise_name}", initiator_id=initiator_id)
    return contract


async def generate_sale_contract(db: AsyncSession, order: OrderInfo, initiator_id: int) -> Contract:
    """销售合同 (随订单生成)"""
    from app.modules.workflow.service import WorkflowService

    platform = await _platform(db)
    seller = await db.get(Enterprise, order.seller_id)
    buyer = await db.get(Enterprise, order.buyer_id)
    from app.models import OrderItem
    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    contract_no = await _next_no(db)
    html = SALE_TEMPLATE.format(
        contract_no=contract_no, order_no=order.order_no, party_a=platform.enterprise_name,
        party_b=seller.enterprise_name if seller else "-", buyer=buyer.enterprise_name if buyer else "-",
        grade=item.grade if item else "", spec=item.spec if item else "",
        quantity=order.quantity, unit_price=order.unit_price, total_amount=order.total_amount,
        sale_mode_text=MODE_TEXT.get(order.sale_mode, order.sale_mode), today=date.today().isoformat(),
    )
    contract = Contract(contract_no=contract_no, type="SALE", order_id=order.id, party_a_id=platform.id,
                        party_b_id=order.seller_id, file_id=await _save_file(db, contract_no, html))
    db.add(contract)
    await db.flush()
    await WorkflowService(db).start("CONTRACT_SIGN", biz_id=contract.id,
                                    title=f"合同签署审批: 销售合同 {order.order_no}", initiator_id=initiator_id)
    return contract


async def sign(db: AsyncSession, contract: Contract, user) -> Contract:
    """在线签署: 甲方=平台人员(业务/财务/管理员), 乙方=企业用户"""
    if contract.sign_status != "SIGNING":
        raise BizError("合同未到可签署状态(需签署审批通过)")
    is_platform_side = user.enterprise_id is None
    if is_platform_side and not contract.party_a_signed:
        contract.party_a_signed = True
        contract.party_a_time = datetime.now()
    elif user.enterprise_id == contract.party_b_id and not contract.party_b_signed:
        contract.party_b_signed = True
        contract.party_b_time = datetime.now()
    else:
        raise BizError("你不是该合同的签署方或已签署", code=403)
    if contract.party_a_signed and contract.party_b_signed:
        contract.sign_status = "SIGNED"
        contract.signed_time = datetime.now()
    return contract
