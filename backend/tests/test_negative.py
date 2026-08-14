"""反向用例: 防资损/防超卖/防越权操作"""
from tests.helpers import (API, approve_todo, auth, create_order, login, register,
                           run_order_to_full_paid, setup_shelf)


async def test_deposit_twice_rejected(client):
    """重复支付定金必须被拒"""
    ctx = await setup_shelf(client, "neg1")
    order_id, order_no = await create_order(client, ctx["buyer"], ctx["shelf_item_id"], 100)
    await approve_todo(client, ctx["biz"], f"订单审核: {order_no}")
    resp1 = await client.post(f"{API}/finance/pay", headers=auth(ctx["buyer"]),
                              json={"order_id": order_id, "pay_type": "DEPOSIT"})
    assert resp1.json()["code"] == 0
    resp2 = await client.post(f"{API}/finance/pay", headers=auth(ctx["buyer"]),
                              json={"order_id": order_id, "pay_type": "DEPOSIT"})
    assert resp2.json()["code"] == 400  # 状态已变, 拒绝


async def test_verify_by_non_seller_rejected(client):
    """非卖方养殖户/客户不能核销"""
    ctx = await setup_shelf(client, "neg2")
    order_id, order_no = await create_order(client, ctx["buyer"], ctx["shelf_item_id"], 100)
    qr = await run_order_to_full_paid(client, order_id, order_no, ctx)
    # 客户扫码 → 403(角色限制)
    resp = await client.post(f"{API}/delivery/verify", headers=auth(ctx["buyer"]), json={"qr_payload": qr})
    assert resp.json()["code"] == 403


async def test_double_verify_rejected(client):
    """重复核销必须被拒(幂等)"""
    ctx = await setup_shelf(client, "neg3")
    order_id, order_no = await create_order(client, ctx["buyer"], ctx["shelf_item_id"], 100)
    qr = await run_order_to_full_paid(client, order_id, order_no, ctx)
    resp1 = await client.post(f"{API}/delivery/verify", headers=auth(ctx["farm"]), json={"qr_payload": qr})
    assert resp1.json()["code"] == 0
    resp2 = await client.post(f"{API}/delivery/verify", headers=auth(ctx["farm"]), json={"qr_payload": qr})
    assert resp2.json()["code"] == 400 and "已核销" in resp2.json()["message"]
    # 库存只扣一次
    resp = await client.get(f"{API}/inventory/list", headers=auth(ctx["biz"]))
    inv = [i for i in resp.json()["data"] if i["warehouse_id"] == ctx["warehouse_id"]][0]
    assert inv["quantity"] == 2900  # 3000 - 100, 只减一次


async def test_oversell_rejected(client):
    """采购数量超过货架库存必须被拒"""
    ctx = await setup_shelf(client, "neg4")
    resp = await client.post(f"{API}/orders/purchase", headers=auth(ctx["buyer"]),
                             json={"shelf_item_id": ctx["shelf_item_id"], "quantity": 99999, "sale_mode": "M1"})
    assert resp.json()["code"] == 400


async def test_dw_apply_without_monitor_rejected(client):
    """监控未确权不能建交割仓 (F2.2 前置)"""
    await register(client, "neg5_farm", "FARM", "未确权养殖场")
    biz = await login(client, "business01")
    farm = await login(client, "neg5_farm")
    await approve_todo(client, biz, "未确权养殖场")
    resp = await client.post(f"{API}/warehouse", headers=auth(farm),
                             json={"name": "未确权仓neg5", "address": "郑州", "capacity": 100})
    wh_id = resp.json()["data"]["id"]
    await client.post(f"{API}/warehouse/{wh_id}/lease-apply", headers=auth(biz), json={"rent_amount": 1000})
    fin = await login(client, "finance01")
    await approve_todo(client, biz, "租赁审批: 未确权仓neg5")
    await approve_todo(client, fin, "租赁审批: 未确权仓neg5")
    resp = await client.post(f"{API}/warehouse/delivery/apply", headers=auth(biz),
                             json={"warehouse_id": wh_id, "quantity": 100, "grade": "A", "spec": "S50", "price": 5})
    assert resp.json()["code"] == 400 and "监控" in resp.json()["message"]


async def test_cancel_restores_shelf(client):
    """取消订单恢复货架数量"""
    ctx = await setup_shelf(client, "neg6")
    order_id, order_no = await create_order(client, ctx["buyer"], ctx["shelf_item_id"], 500)
    await approve_todo(client, ctx["biz"], f"订单审核: {order_no}")
    resp = await client.post(f"{API}/orders/{order_id}/cancel", headers=auth(ctx["buyer"]))
    assert resp.json()["code"] == 0
    resp = await client.get(f"{API}/shelf/list", headers=auth(ctx["buyer"]))
    shelf = [s for s in resp.json()["data"] if s["delivery_warehouse_id"] == ctx["dw_id"]][0]
    assert shelf["quantity"] == 3000  # 恢复


async def test_m3_requires_risk_survey(client):
    """模式③渠道账期: 未尽调的买方被拦截 (F1.3)"""
    ctx = await setup_shelf(client, "neg7")
    resp = await client.post(f"{API}/orders/purchase", headers=auth(ctx["buyer"]),
                             json={"shelf_item_id": ctx["shelf_item_id"], "quantity": 100,
                                   "sale_mode": "M3", "credit_days": 60})
    assert resp.json()["code"] == 400 and "尽调" in resp.json()["message"]


async def test_outbound_file_upload_permission(client):
    """装车凭证上传: 财务等非现场角色被拒, 三方人员可传"""
    import io

    ctx = await setup_shelf(client, "neg8")
    order_id, order_no = await create_order(client, ctx["buyer"], ctx["shelf_item_id"], 100)
    await approve_todo(client, ctx["biz"], f"订单审核: {order_no}")
    await client.post(f"{API}/finance/pay", headers=auth(ctx["buyer"]),
                      json={"order_id": order_id, "pay_type": "DEPOSIT"})
    await approve_todo(client, ctx["fin"], f"垫资审批(80%): {order_no}")
    resp = await client.post(f"{API}/delivery/outbound", headers=auth(ctx["biz"]),
                             json={"order_id": order_id, "plate_no": "豫A00001",
                                   "driver_name": "王五", "driver_phone": "13700000000"})
    ob_id = resp.json()["data"]["id"]

    async def upload_jpg(token):
        resp = await client.post(f"{API}/file/upload?biz_type=OUTBOUND_PHOTO", headers=auth(token),
                                 files={"file": ("p.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")})
        return resp.json()["data"]["file_id"]

    # 财务上传附件 → 403
    fin_file = await upload_jpg(ctx["fin"])
    resp = await client.post(f"{API}/delivery/outbound/{ob_id}/files", headers=auth(ctx["fin"]),
                             json={"file_id": fin_file, "media_type": "PHOTO"})
    assert resp.json()["code"] == 403

    # 养殖户(卖方)上传 → 允许
    farm_file = await upload_jpg(ctx["farm"])
    resp = await client.post(f"{API}/delivery/outbound/{ob_id}/files", headers=auth(ctx["farm"]),
                             json={"file_id": farm_file, "media_type": "PHOTO"})
    assert resp.json()["code"] == 0

    # 附件带回可访问的 url
    resp = await client.get(f"{API}/delivery/outbound/by-order/{order_id}", headers=auth(ctx["farm"]))
    files = resp.json()["data"]["files"]
    assert files and files[0]["url"] and files[0]["url"].startswith("http")
