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
