"""RBAC 与安全 (F9.1): 未登录/越权/角色隔离"""
from tests.helpers import API, auth, login, register, setup_shelf


async def test_no_token_401(client):
    resp = await client.get(f"{API}/enterprise/list")
    assert resp.json()["code"] == 401


async def test_farm_cannot_access_business_apis(client):
    await register(client, "sec_farm", "FARM", "安全测试养殖场")
    farm = await login(client, "sec_farm")
    # 合作方管理(业务端)
    resp = await client.get(f"{API}/enterprise/list", headers=auth(farm))
    assert resp.json()["code"] == 403
    # 发起交割仓审批(业务端)
    resp = await client.post(f"{API}/warehouse/delivery/apply", headers=auth(farm),
                             json={"warehouse_id": 1, "quantity": 1, "grade": "A", "spec": "S50", "price": 1})
    assert resp.json()["code"] == 403
    # 强制平仓(业务端)
    resp = await client.post(f"{API}/risk/force-close/1", headers=auth(farm))
    assert resp.json()["code"] == 403


async def test_customer_data_isolation(client):
    """客户只能看到本企业订单"""
    ctx1 = await setup_shelf(client, "iso1")
    ctx2 = await setup_shelf(client, "iso2")
    resp = await client.post(f"{API}/orders/purchase", headers=auth(ctx1["buyer"]),
                             json={"shelf_item_id": ctx1["shelf_item_id"], "quantity": 10, "sale_mode": "M1"})
    order_id = resp.json()["data"]["id"]
    # buyer2 查看 buyer1 的订单 → 403
    resp = await client.get(f"{API}/orders/{order_id}", headers=auth(ctx2["buyer"]))
    assert resp.json()["code"] == 403
    # buyer2 的订单列表不含该订单
    resp = await client.get(f"{API}/orders/list", headers=auth(ctx2["buyer"]))
    assert all(o["id"] != order_id for o in resp.json()["data"])
