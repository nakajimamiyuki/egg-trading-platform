"""测试辅助: 常用业务流的封装"""

API = "/api/v1"


async def login(client, username: str, password: str = "123456") -> str:
    resp = await client.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert resp.json()["code"] == 0, f"登录失败: {resp.json()}"
    return resp.json()["data"]["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def register(client, username: str, ent_type: str, name: str) -> int:
    """注册企业, 返回 enterprise_id"""
    body = {
        "username": username, "password": "123456", "real_name": "测试", "phone": "13800000000",
        "enterprise_name": name, "enterprise_type": ent_type, "license_no": f"LIC-{username}",
        "legal_person": "测试法人", "address": "郑州市",
    }
    if ent_type == "FARM":
        body.update({"breed": "海兰褐", "stock_qty": 100000, "day_age": 180, "daily_egg_qty": 95000})
    resp = await client.post(f"{API}/auth/register", json=body)
    assert resp.json()["code"] == 0, f"注册失败: {resp.json()}"
    return resp.json()["data"]["enterprise_id"]


async def approve_todo(client, token: str, keyword: str, opinion: str = "同意") -> None:
    """在待办里按标题关键词找到任务并通过。关键词必须唯一(用企业名/仓库名/单号)"""
    resp = await client.get(f"{API}/workflow/todo", headers=auth(token))
    tasks = [t for t in resp.json()["data"] if keyword in t["title"]]
    assert tasks, f"待办中没有含[{keyword}]的任务"
    task_id = tasks[0]["task_id"]
    resp = await client.post(f"{API}/workflow/tasks/{task_id}/handle", headers=auth(token),
                             json={"action": "PASS", "opinion": opinion})
    assert resp.json()["code"] == 0, f"审批失败: {resp.json()}"


async def setup_shelf(client, tag: str) -> dict:
    """完整前置: 注册并审批养殖户+采购商 -> 建仓 -> 租赁 -> 监控确权 -> 交割仓 -> 上架
    返回各方 token 与关键 id。所有审批关键词均用 tag 唯一化, 可并行多组"""
    farm_name = f"测试养殖场{tag}"
    buyer_name = f"测试采购商{tag}"
    wh_name = f"仓库{tag}"
    await register(client, f"farm_{tag}", "FARM", farm_name)
    await register(client, f"buyer_{tag}", "BUYER", buyer_name)

    biz = await login(client, "business01")
    fin = await login(client, "finance01")
    farm = await login(client, f"farm_{tag}")
    buyer = await login(client, f"buyer_{tag}")

    await approve_todo(client, biz, farm_name)
    await approve_todo(client, biz, buyer_name)

    resp = await client.post(f"{API}/warehouse", headers=auth(farm),
                             json={"name": wh_name, "address": "郑州", "capacity": 5000})
    wh_id = resp.json()["data"]["id"]

    await client.post(f"{API}/warehouse/{wh_id}/lease-apply", headers=auth(biz), json={"rent_amount": 8000})
    await approve_todo(client, biz, f"租赁审批: {wh_name}")
    await approve_todo(client, fin, f"租赁审批: {wh_name}")

    resp = await client.post(f"{API}/iot/devices", headers=auth(farm),
                             json={"warehouse_id": wh_id, "device_name": "摄像头", "protocol": "RTSP",
                                   "stream_url": "rtsp://x/1"})
    dev_id = resp.json()["data"]["id"]
    await client.post(f"{API}/iot/devices/{dev_id}/check", headers=auth(farm))
    await client.post(f"{API}/iot/devices/{dev_id}/confirm", headers=auth(biz))

    resp = await client.post(f"{API}/warehouse/delivery/apply", headers=auth(biz),
                             json={"warehouse_id": wh_id, "quantity": 3000, "grade": "A", "spec": "S50", "price": 5.5})
    dw_id = resp.json()["data"]["id"]
    await approve_todo(client, biz, f"交割仓建立审批: {wh_name}")

    resp = await client.get(f"{API}/shelf/list", headers=auth(buyer))
    shelf = [s for s in resp.json()["data"] if s["delivery_warehouse_id"] == dw_id]
    assert shelf, "交割仓审批通过后应自动上架"

    return {"farm": farm, "buyer": buyer, "biz": biz, "fin": fin,
            "warehouse_id": wh_id, "dw_id": dw_id, "shelf_item_id": shelf[0]["id"]}


async def create_order(client, buyer: str, shelf_item_id: int, quantity: int) -> tuple[int, str]:
    """下单, 返回 (order_id, order_no)"""
    resp = await client.post(f"{API}/orders/purchase", headers=auth(buyer),
                             json={"shelf_item_id": shelf_item_id, "quantity": quantity, "sale_mode": "M1"})
    assert resp.json()["code"] == 0, f"下单失败: {resp.json()}"
    return resp.json()["data"]["id"], resp.json()["data"]["order_no"]


async def run_order_to_full_paid(client, order_id: int, order_no: str, ctx: dict) -> str:
    """把订单推进到 FULL_PAID(生成提货凭证), 返回 qr_payload。审批用单号定位, 不串单"""
    await approve_todo(client, ctx["biz"], f"订单审核: {order_no}")
    resp = await client.post(f"{API}/finance/pay", headers=auth(ctx["buyer"]),
                             json={"order_id": order_id, "pay_type": "DEPOSIT"})
    assert resp.json()["code"] == 0
    await approve_todo(client, ctx["fin"], f"垫资审批(80%): {order_no}")

    resp = await client.post(f"{API}/delivery/outbound", headers=auth(ctx["biz"]),
                             json={"order_id": order_id, "plate_no": "豫A00001",
                                   "driver_name": "王五", "driver_phone": "13700000000"})
    ob_id = resp.json()["data"]["id"]
    await client.post(f"{API}/delivery/outbound/{ob_id}/confirm/seller", headers=auth(ctx["farm"]))
    await client.post(f"{API}/delivery/outbound/{ob_id}/confirm/buyer", headers=auth(ctx["buyer"]))
    await client.post(f"{API}/delivery/outbound/{ob_id}/confirm/platform", headers=auth(ctx["biz"]))

    resp = await client.post(f"{API}/finance/pay", headers=auth(ctx["buyer"]),
                             json={"order_id": order_id, "pay_type": "TAIL"})
    assert resp.json()["code"] == 0
    await approve_todo(client, ctx["fin"], f"尾款结算审批(20%): {order_no}")

    resp = await client.get(f"{API}/delivery/voucher/by-order/{order_id}", headers=auth(ctx["farm"]))
    voucher = resp.json()["data"]
    assert voucher and voucher["status"] == "ACTIVE"
    return voucher["qr_payload"]
