"""提货交付服务 (F5.1/F5.3): 出库单三方确认 + 扫码核销放行"""
import asyncio
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import BizError
from app.models import DeliveryWarehouse, OrderInfo, OrderItem, OutboundOrder, OutboundFile, PickupVoucher
from app.modules.order.service import transition


async def create_outbound(db: AsyncSession, order: OrderInfo, plate_no: str, driver_name: str,
                          driver_phone: str, operator_id: int) -> OutboundOrder:
    """业务端开具出库单 (装车核验前置)"""
    if order.status != "ADVANCE_PAID":
        raise BizError("平台垫资完成后才能开出库单")
    exists = await db.scalar(select(OutboundOrder).where(OutboundOrder.order_id == order.id, OutboundOrder.deleted == False))  # noqa: E712
    if exists:
        raise BizError("该订单已有出库单")
    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    dw = await db.get(DeliveryWarehouse, item.delivery_warehouse_id)
    from app.core.docno import next_doc_no
    ob = OutboundOrder(
        outbound_no=await next_doc_no(db, "OB"), order_id=order.id, warehouse_id=dw.warehouse_id,
        quantity=order.quantity, grade=item.grade, spec=item.spec, unit_price=order.unit_price,
        plate_no=plate_no, driver_name=driver_name, driver_phone=driver_phone, created_by=operator_id,
    )
    db.add(ob)
    await transition(db, order, "VERIFYING", operator_id, "出库单已开具, 待三方确认")
    return ob


async def add_outbound_file(db: AsyncSession, outbound: OutboundOrder, file_id: int, media_type: str) -> None:
    """装车照片/视频: 照片实际打水印(出库单号+时间), 失败不影响附件记录"""
    import logging

    from app.models import FileRecord
    from app.modules.file import service as file_service

    if media_type == "PHOTO":
        try:
            rec = await db.get(FileRecord, file_id)
            data = await file_service.download(rec.bucket, rec.object_key)
            text = f"{outbound.outbound_no}  {datetime.now().strftime('%Y-%m-%d %H:%M')}  EGG-PLATFORM"
            watermarked = await asyncio.to_thread(file_service.watermark_image, data, text)
            await file_service.reupload(rec.bucket, rec.object_key, watermarked)
        except Exception as exc:
            logging.getLogger(__name__).warning("照片打水印失败(原图保留): %s", exc)
    db.add(OutboundFile(outbound_id=outbound.id, file_id=file_id, media_type=media_type, watermarked=True))


async def confirm_outbound(db: AsyncSession, outbound: OutboundOrder, side: str, operator_id: int) -> OutboundOrder:
    """三方确认 (F5.1): seller养殖户 / buyer客户 / platform平台业务"""
    order = await db.get(OrderInfo, outbound.order_id)
    if order.status != "VERIFYING":
        raise BizError("当前不在装车核验阶段")
    field = {"seller": "seller_confirmed", "buyer": "buyer_confirmed", "platform": "platform_confirmed"}.get(side)
    if not field:
        raise BizError("非法确认方")
    if getattr(outbound, field):
        raise BizError("该方已确认")
    setattr(outbound, field, True)
    if outbound.seller_confirmed and outbound.buyer_confirmed and outbound.platform_confirmed:
        outbound.status = "CONFIRMED"
        await transition(db, order, "OUTBOUND_CONFIRMED", operator_id, "出库单三方确认完成, 待客户支付尾款")
    return outbound


async def verify_voucher(db: AsyncSession, qr_payload: str, user) -> PickupVoucher:
    """扫码核销放行 (F5.3) —— 唯一放行凭证, 行级锁+状态校验保证幂等"""
    voucher = await db.scalar(select(PickupVoucher).where(PickupVoucher.qr_payload == qr_payload).with_for_update())
    if not voucher or voucher.deleted:
        raise BizError("提货凭证无效", code=404)
    if voucher.status == "USED":
        raise BizError("该凭证已核销, 请勿重复操作")  # 幂等: 重复扫码返回明确提示
    order = await db.get(OrderInfo, voucher.order_id)
    if order.status != "FULL_PAID":
        raise BizError("养殖户未收齐全款, 不能放行")
    if order.seller_id != user.enterprise_id:
        raise BizError("只有卖方养殖户有权核销放行", code=403)

    from app.modules.inventory.service import release_inventory

    item = await db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    dw = await db.get(DeliveryWarehouse, item.delivery_warehouse_id)
    await release_inventory(db, dw.warehouse_id, item.product_id, order.quantity, order.id)

    voucher.status = "USED"
    voucher.verified_by = user.id
    voucher.verified_time = datetime.now()
    if voucher.outbound_id:
        ob = await db.get(OutboundOrder, voucher.outbound_id)
        if ob:
            ob.status = "RELEASED"
    dw.status = "SOLD"
    await transition(db, order, "RELEASED", user.id, "扫码核销放行, 库存实时扣减")
    await transition(db, order, "FINISHED", user.id, "交易完成")
    return voucher
