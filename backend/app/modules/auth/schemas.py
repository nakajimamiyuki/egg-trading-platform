from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """自助注册 (F1.1/F1.2): 账号 + 企业信息, 证照 file_id 列表"""
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=50)
    real_name: str = Field(max_length=50)
    phone: str = Field(max_length=20)
    enterprise_name: str = Field(max_length=100)
    enterprise_type: str = Field(pattern="^(FARM|BUYER)$")  # FARM养殖/BUYER采购商
    license_no: str | None = None
    legal_person: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    # 养殖企业专属
    breed: str | None = None
    stock_qty: int | None = None
    day_age: int | None = None
    daily_egg_qty: int | None = None
    # 证照: [{"file_type":"LICENSE","file_id":1}, ...]
    files: list[dict] = []


class LoginRequest(BaseModel):
    username: str
    password: str
