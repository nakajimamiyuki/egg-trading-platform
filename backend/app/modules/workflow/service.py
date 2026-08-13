"""审批流引擎 (F9.2)
用法:
  await WorkflowService(db).start("ENTERPRISE_AUDIT", biz_id=企业id, title=..., initiator_id=...)
  await WorkflowService(db).handle(task_id, user, roles, action="PASS"/"REJECT", opinion=...)
审批全部通过后自动回写业务状态 (BIZ_CALLBACKS)
"""
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import BizError
from app.models import DeliveryWarehouse, Enterprise, SysUser, Warehouse, WfDefinition, WfInstance, WfNode, WfTask


async def _cb_enterprise_audit(db: AsyncSession, biz_id: int, passed: bool) -> None:
    ent = await db.get(Enterprise, biz_id)
    if ent:
        ent.audit_status = "PASS" if passed else "REJECT"
        if passed:
            ent.coop_evaluation = "准入审批通过，初始合作评价：良好"


async def _cb_warehouse_lease(db: AsyncSession, biz_id: int, passed: bool) -> None:
    """仓库租赁审批 (F2.1): 通过则仓库转为已租赁"""
    wh = await db.get(Warehouse, biz_id)
    if wh:
        wh.lease_status = "LEASED" if passed else "NONE"


async def _cb_delivery_wh_create(db: AsyncSession, biz_id: int, passed: bool) -> None:
    """交割仓建立审批 (F2.3): 通过则建立交割仓 + 库存初始化 + 货架自动上架(F4.1)"""
    from app.models import Product, ShelfItem
    from app.modules.inventory.service import change_inventory, get_or_create_product

    dw = await db.get(DeliveryWarehouse, biz_id)
    if not dw:
        return
    if not passed:
        dw.status = "REJECTED"
        return
    dw.status = "IN_STOCK"
    dw.inbound_date = date.today()
    product = await get_or_create_product(db, dw.grade, dw.spec)
    await change_inventory(db, dw.warehouse_id, product.id, dw.quantity, "INIT", biz_id=dw.id)
    # 实时库存自动上架
    if dw.price:
        db.add(ShelfItem(delivery_warehouse_id=dw.id, product_id=product.id, quantity=dw.quantity,
                         price=dw.price, source_enterprise_id=dw.enterprise_id, status="ON"))


async def _cb_order_audit(db: AsyncSession, biz_id: int, passed: bool) -> None:
    """订单业务审核 (F4.2): 通过则进入待付定金"""
    from app.models import OrderInfo
    from app.modules.order.service import cancel_order, transition

    order = await db.get(OrderInfo, biz_id)
    if not order:
        return
    if passed:
        await transition(db, order, "DEPOSIT_PENDING", None, "业务审核通过, 待客户支付定金")
    else:
        await cancel_order(db, order, None)


async def _cb_payment_80(db: AsyncSession, biz_id: int, passed: bool) -> None:
    if passed:
        from app.modules.finance.service import on_advance_approved
        await on_advance_approved(db, biz_id)


async def _cb_payment_20(db: AsyncSession, biz_id: int, passed: bool) -> None:
    if passed:
        from app.modules.finance.service import on_settle_approved
        await on_settle_approved(db, biz_id)


async def _cb_sale_apply(db: AsyncSession, biz_id: int, passed: bool) -> None:
    """养殖端建单销售申请 (F3.1): 通过则交割仓标记已申请销售"""
    dw = await db.get(DeliveryWarehouse, biz_id)
    if dw and dw.status == "IN_STOCK" and passed:
        dw.status = "APPLYING"


BIZ_CALLBACKS = {
    "ENTERPRISE_AUDIT": _cb_enterprise_audit,
    "WAREHOUSE_LEASE": _cb_warehouse_lease,
    "DELIVERY_WH_CREATE": _cb_delivery_wh_create,
    "ORDER_AUDIT": _cb_order_audit,
    "PAYMENT_80": _cb_payment_80,
    "PAYMENT_20": _cb_payment_20,
    "SALE_APPLY": _cb_sale_apply,
}


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start(self, def_code: str, biz_id: int, title: str, initiator_id: int) -> WfInstance:
        definition = await self.db.scalar(select(WfDefinition).where(WfDefinition.code == def_code, WfDefinition.status == 1))
        if not definition:
            raise BizError(f"审批流定义不存在: {def_code}")
        inst = WfInstance(
            definition_id=definition.id,
            biz_type=definition.biz_type,
            biz_id=biz_id,
            title=title,
            initiator_id=initiator_id,
        )
        self.db.add(inst)
        await self.db.flush()
        await self._create_task(inst, seq=1)
        return inst

    async def _create_task(self, inst: WfInstance, seq: int) -> None:
        node = await self.db.scalar(
            select(WfNode).where(WfNode.definition_id == inst.definition_id, WfNode.seq == seq)
        )
        if not node:
            raise BizError(f"审批流节点缺失: definition={inst.definition_id} seq={seq}")
        self.db.add(WfTask(instance_id=inst.id, node_id=node.id, seq=seq))
        inst.current_seq = seq

    async def handle(self, task_id: int, user: SysUser, roles: list[str], action: str, opinion: str = "") -> None:
        task = await self.db.get(WfTask, task_id)
        if not task or task.status != "TODO":
            raise BizError("任务不存在或已处理")
        node = await self.db.get(WfNode, task.node_id)
        inst = await self.db.get(WfInstance, task.instance_id)
        # 校验处理权限: 节点角色在用户角色中(管理员除外, 管理员不代办业务审批)
        if node.approver_type == "ROLE" and node.approver_ref not in roles:
            raise BizError("无权处理该审批节点", code=403)

        task.assignee_id = user.id
        task.opinion = opinion
        task.done_time = datetime.now()

        if action == "REJECT":
            task.status = "REJECT"
            inst.status = "REJECT"
            await self._finish(inst, passed=False)
            return

        task.status = "PASS"
        max_seq = await self.db.scalar(
            select(func.max(WfNode.seq)).where(WfNode.definition_id == inst.definition_id)
        )
        if task.seq >= (max_seq or 1):
            inst.status = "PASS"
            await self._finish(inst, passed=True)
        else:
            await self._create_task(inst, seq=task.seq + 1)

    async def _finish(self, inst: WfInstance, passed: bool) -> None:
        callback = BIZ_CALLBACKS.get(inst.biz_type)
        if callback:
            await callback(self.db, inst.biz_id, passed)

    async def todo(self, roles: list[str]) -> list[dict]:
        """当前用户角色可见的待办任务"""
        rows = await self.db.execute(
            select(WfTask, WfInstance, WfNode)
            .join(WfInstance, WfInstance.id == WfTask.instance_id)
            .join(WfNode, WfNode.id == WfTask.node_id)
            .where(WfTask.status == "TODO", WfInstance.status == "RUNNING", WfNode.approver_ref.in_(roles))
            .order_by(WfTask.created_time)
        )
        return [
            {
                "task_id": t.id,
                "instance_id": i.id,
                "title": i.title,
                "biz_type": i.biz_type,
                "biz_id": i.biz_id,
                "node_name": n.node_name,
                "seq": t.seq,
                "created_time": t.created_time.isoformat(),
            }
            for t, i, n in rows.all()
        ]
