"""认证与注册 (M1)"""
from tests.helpers import API, login, register


async def test_register_and_login(client):
    ent_id = await register(client, "auth_farm1", "FARM", "认证测试养殖场")
    assert ent_id > 0
    token = await login(client, "auth_farm1")
    resp = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.json()["data"]["roles"] == ["FARM"]


async def test_duplicate_username_rejected(client):
    await register(client, "auth_dup", "BUYER", "重复名测试公司")
    resp = await client.post(f"{API}/auth/register", json={
        "username": "auth_dup", "password": "123456", "real_name": "x", "phone": "1",
        "enterprise_name": "另一家公司", "enterprise_type": "BUYER"})
    assert resp.json()["code"] == 400


async def test_wrong_password_rejected(client):
    resp = await client.post(f"{API}/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.json()["code"] == 400
