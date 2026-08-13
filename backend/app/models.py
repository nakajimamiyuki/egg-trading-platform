"""SQLAlchemy 2.0 模型 —— 与 docker/postgres/init/01_schema.sql 对应
M1 范围: 系统权限 / 企业 / 审批流 / 文件 / 消息 / 字典 / 配置
后续阶段的模型(订单/库存/资金等)在对应里程碑补充
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------- 系统权限 ----------------

class SysRole(Base):
    __tablename__ = "sys_role"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(String(255))
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class SysUser(Base):
    __tablename__ = "sys_user"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    real_name: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))
    enterprise_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[int] = mapped_column(Integer, default=1)
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class SysUserRole(Base):
    __tablename__ = "sys_user_role"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_role.id"), primary_key=True)


# ---------------- 企业与准入 ----------------

class Enterprise(Base, TimestampMixin):
    __tablename__ = "enterprise"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    enterprise_name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20))  # FARM/BUYER/CHANNEL
    license_no: Mapped[str | None] = mapped_column(String(50))
    legal_person: Mapped[str | None] = mapped_column(String(50))
    auth_rep: Mapped[str | None] = mapped_column(String(50))
    id_card_no: Mapped[str | None] = mapped_column(String(30))
    real_name_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(255))
    breed: Mapped[str | None] = mapped_column(String(50))
    stock_qty: Mapped[int | None] = mapped_column(Integer)
    day_age: Mapped[int | None] = mapped_column(Integer)
    daily_egg_qty: Mapped[int | None] = mapped_column(Integer)
    audit_status: Mapped[str] = mapped_column(String(10), default="WAIT")  # WAIT/PASS/REJECT
    audit_remark: Mapped[str | None] = mapped_column(String(500))
    coop_evaluation: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(BigInteger)


class EnterpriseFile(Base):
    __tablename__ = "enterprise_file"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    enterprise_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("enterprise.id"))
    file_type: Mapped[str] = mapped_column(String(30))
    file_id: Mapped[int] = mapped_column(BigInteger)
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------- 文件 ----------------

class FileRecord(Base):
    __tablename__ = "file_record"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bucket: Mapped[str] = mapped_column(String(50))
    object_key: Mapped[str] = mapped_column(String(255))
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    content_type: Mapped[str | None] = mapped_column(String(100))
    biz_type: Mapped[str | None] = mapped_column(String(50))
    biz_id: Mapped[int | None] = mapped_column(BigInteger)
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------- 审批流 ----------------

class WfDefinition(Base, TimestampMixin):
    __tablename__ = "wf_definition"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    biz_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[int] = mapped_column(Integer, default=1)


class WfNode(Base):
    __tablename__ = "wf_node"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    definition_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("wf_definition.id"))
    node_name: Mapped[str] = mapped_column(String(50))
    seq: Mapped[int] = mapped_column(Integer)
    approver_type: Mapped[str] = mapped_column(String(20), default="ROLE")
    approver_ref: Mapped[str] = mapped_column(String(50))
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class WfInstance(Base):
    __tablename__ = "wf_instance"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    definition_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("wf_definition.id"))
    biz_type: Mapped[str] = mapped_column(String(50))
    biz_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    current_seq: Mapped[int] = mapped_column(Integer, default=1)
    initiator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"))
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class WfTask(Base):
    __tablename__ = "wf_task"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instance_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("wf_instance.id"))
    node_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("wf_node.id"))
    seq: Mapped[int] = mapped_column(Integer)
    assignee_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sys_user.id"))
    status: Mapped[str] = mapped_column(String(20), default="TODO")
    opinion: Mapped[str | None] = mapped_column(String(500))
    done_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------- 消息 ----------------

class Message(Base):
    __tablename__ = "message"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str | None] = mapped_column(Text)
    biz_type: Mapped[str | None] = mapped_column(String(50))
    biz_id: Mapped[int | None] = mapped_column(BigInteger)
    read_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------- 字典与配置 ----------------

class SysDictType(Base):
    __tablename__ = "sys_dict_type"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(50))


class SysDictItem(Base):
    __tablename__ = "sys_dict_item"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    type_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_dict_type.id"))
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(50))
    sort: Mapped[int] = mapped_column(Integer, default=0)


class SysConfig(Base):
    __tablename__ = "sys_config"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    config_key: Mapped[str] = mapped_column(String(50), unique=True)
    config_value: Mapped[str] = mapped_column(String(255))
    remark: Mapped[str | None] = mapped_column(String(255))
    updated_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------- 仓储与库存 (M2) ----------------

class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouse"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    enterprise_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("enterprise.id"))
    address: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[int | None] = mapped_column(Integer)
    rent_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    lease_status: Mapped[str] = mapped_column(String(10), default="NONE")  # NONE/WAIT/LEASED
    monitor_online: Mapped[bool] = mapped_column(Boolean, default=False)
    point_map_file_id: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[int | None] = mapped_column(BigInteger)


class EggProduction(Base):
    __tablename__ = "egg_production"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    enterprise_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("enterprise.id"))
    prod_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[int] = mapped_column(Integer)
    grade: Mapped[str] = mapped_column(String(20))
    spec: Mapped[str] = mapped_column(String(20))
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class DeliveryWarehouse(Base, TimestampMixin):
    __tablename__ = "delivery_warehouse"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dw_no: Mapped[str] = mapped_column(String(32), unique=True)
    warehouse_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("warehouse.id"))
    enterprise_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("enterprise.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    grade: Mapped[str] = mapped_column(String(20))
    spec: Mapped[str] = mapped_column(String(20))
    inbound_date: Mapped[date | None] = mapped_column(Date)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))  # 上架单价(业务端定价)
    turnover_days: Mapped[int] = mapped_column(Integer, default=3)
    # AUDITING审批中/IN_STOCK在库/APPLYING已申请销售/SOLD已售/CLOSED已平仓/RETURNED已退仓/REJECTED审批驳回
    status: Mapped[str] = mapped_column(String(20), default="AUDITING")


class Product(Base, TimestampMixin):
    __tablename__ = "product"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_name: Mapped[str] = mapped_column(String(100), default="鸡蛋")
    category: Mapped[str | None] = mapped_column(String(50))
    grade: Mapped[str] = mapped_column(String(20))
    spec: Mapped[str] = mapped_column(String(20))
    unit: Mapped[str] = mapped_column(String(10), default="件")
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))


class Inventory(Base):
    __tablename__ = "inventory"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("warehouse.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    locked_qty: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)
    updated_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InventoryLog(Base):
    __tablename__ = "inventory_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(BigInteger)
    product_id: Mapped[int] = mapped_column(BigInteger)
    change_qty: Mapped[int] = mapped_column(Integer)
    before_qty: Mapped[int] = mapped_column(Integer)
    after_qty: Mapped[int] = mapped_column(Integer)
    biz_type: Mapped[str] = mapped_column(String(30))
    biz_id: Mapped[int | None] = mapped_column(BigInteger)
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[int | None] = mapped_column(BigInteger)


class IotDevice(Base, TimestampMixin):
    __tablename__ = "iot_device"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("warehouse.id"))
    device_name: Mapped[str | None] = mapped_column(String(100))
    device_type: Mapped[str] = mapped_column(String(30), default="CAMERA")
    protocol: Mapped[str] = mapped_column(String(20), default="RTSP")
    stream_url: Mapped[str | None] = mapped_column(String(500))
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------- 交易核心 (M3) ----------------

class ShelfItem(Base, TimestampMixin):
    __tablename__ = "shelf_item"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_warehouse_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("delivery_warehouse.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    source_enterprise_id: Mapped[int] = mapped_column(BigInteger)
    designated: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(10), default="ON")  # ON/OFF


class OrderInfo(Base, TimestampMixin):
    __tablename__ = "order_info"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True)
    sale_mode: Mapped[str] = mapped_column(String(10))  # M1/M2/M3
    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("enterprise.id"))
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("enterprise.id"))
    self_operated: Mapped[bool] = mapped_column(Boolean, default=False)
    designated: Mapped[bool] = mapped_column(Boolean, default=False)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    deposit_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.20"))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    advance_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.80"))
    advance_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    platform_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    credit_days: Mapped[int | None] = mapped_column(Integer)
    credit_due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="CREATE")
    remark: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int | None] = mapped_column(BigInteger)


class OrderItem(Base):
    __tablename__ = "order_item"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_info.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"))
    delivery_warehouse_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("delivery_warehouse.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    grade: Mapped[str | None] = mapped_column(String(20))
    spec: Mapped[str | None] = mapped_column(String(20))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class OrderEvent(Base):
    __tablename__ = "order_event"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_info.id"))
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    operator_id: Mapped[int | None] = mapped_column(BigInteger)
    remark: Mapped[str | None] = mapped_column(String(500))
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PayRecord(Base, TimestampMixin):
    __tablename__ = "pay_record"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pay_no: Mapped[str] = mapped_column(String(32), unique=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_info.id"))
    direction: Mapped[str] = mapped_column(String(10))  # IN/OUT
    pay_type: Mapped[str] = mapped_column(String(20))   # DEPOSIT/TAIL/ADVANCE/SETTLE/REFUND/CHANNEL_PAY
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payer_id: Mapped[int | None] = mapped_column(BigInteger)
    payee_id: Mapped[int | None] = mapped_column(BigInteger)
    channel: Mapped[str] = mapped_column(String(20), default="MOCK")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    voucher_file_id: Mapped[int | None] = mapped_column(BigInteger)
    external_no: Mapped[str | None] = mapped_column(String(64))
    paid_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[int | None] = mapped_column(BigInteger)


class FinanceBill(Base, TimestampMixin):
    __tablename__ = "finance_bill"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    bill_no: Mapped[str] = mapped_column(String(32), unique=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_info.id"))
    enterprise_id: Mapped[int] = mapped_column(BigInteger)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    received: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    bill_status: Mapped[str] = mapped_column(String(20), default="OPEN")


class OutboundOrder(Base, TimestampMixin):
    __tablename__ = "outbound_order"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    outbound_no: Mapped[str] = mapped_column(String(32), unique=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_info.id"))
    warehouse_id: Mapped[int] = mapped_column(BigInteger)
    quantity: Mapped[int] = mapped_column(Integer)
    grade: Mapped[str | None] = mapped_column(String(20))
    spec: Mapped[str | None] = mapped_column(String(20))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    plate_no: Mapped[str | None] = mapped_column(String(20))
    driver_name: Mapped[str | None] = mapped_column(String(50))
    driver_phone: Mapped[str | None] = mapped_column(String(20))
    seller_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    buyer_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    platform_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")  # DRAFT/CONFIRMED/RELEASED
    created_by: Mapped[int | None] = mapped_column(BigInteger)


class OutboundFile(Base):
    __tablename__ = "outbound_file"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    outbound_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("outbound_order.id"))
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("file_record.id"))
    media_type: Mapped[str] = mapped_column(String(10))
    watermarked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class PickupVoucher(Base):
    __tablename__ = "pickup_voucher"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    voucher_no: Mapped[str] = mapped_column(String(32), unique=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_info.id"))
    outbound_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("outbound_order.id"))
    qr_payload: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/USED/EXPIRED
    verified_by: Mapped[int | None] = mapped_column(BigInteger)
    verified_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
