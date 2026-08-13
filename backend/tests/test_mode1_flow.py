"""模式① 全流程集成测试 (M3 核心): 下单→审核→定金→垫资→出库三确→尾款→结算→核销→完成"""
from tests.helpers import (API, approve_todo, auth, create_order, run_order_to_full_paid, setup_shelf)


async def test_mode1_full_flow(client):
    ctx = await setup_shelf(client, "m1")
    order_id, order_no = await create_order(client, ctx["buyer"], ctx["shelf_item_id"], 1000)

    # 订单金额校验: 1000枚 x 5.5 = 5500, 定金20%=1100, 垫资80%=4400
    resp = await client.get(f"{API}/orders/{order_id}", headers=auth(ctx["buyer"]))
    order = resp.json()["data"]
    assert order["total_amount"] == 5500.0
    assert order["deposit_amount"] == 1100.0
    assert order["advance_amount"] == 4400.0
    assert order["status"] == "AUDIT"

    qr = await run_order_to_full_paid(client, order_id, order_no, ctx)

    # 核销放行
    resp = await client.post(f"{API}/delivery/verify", headers=auth(ctx["farm"]), json={"qr_payload": qr})
    assert resp.json()["code"] == 0

    # 最终状态
    resp = await client.get(f"{API}/orders/{order_id}", headers=auth(ctx["biz"]))
    assert resp.json()["data"]["status"] == "FINISHED"

    # 库存: 3000 - 1000 = 2000, 锁定 0
    resp = await client.get(f"{API}/inventory/list", headers=auth(ctx["biz"]))
    inv = [i for i in resp.json()["data"] if i["warehouse_id"] == ctx["warehouse_id"]][0]
    assert inv["quantity"] == 2000 and inv["locked_qty"] == 0

    # 资金流水: 收 1100+4400, 付 4400+1100
    resp = await client.get(f"{API}/finance/records", headers=auth(ctx["fin"]), params={"order_id": order_id})
    records = resp.json()["data"]
    in_sum = sum(r["amount"] for r in records if r["direction"] == "IN")
    out_sum = sum(r["amount"] for r in records if r["direction"] == "OUT")
    assert in_sum == 5500.0 and out_sum == 5500.0  # 资金对平

    # 交割仓状态 SOLD
    resp = await client.get(f"{API}/warehouse/delivery/list", headers=auth(ctx["biz"]))
    dw = [d for d in resp.json()["data"] if d["id"] == ctx["dw_id"]][0]
    assert dw["status"] == "SOLD"


async def test_sales_contract_generated(client):
    """订单审核通过后自动生成销售合同 (M4 联动)"""
    ctx = await setup_shelf(client, "m1c")
    order_id, order_no = await create_order(client, ctx["buyer"], ctx["shelf_item_id"], 100)
    await approve_todo(client, ctx["biz"], f"订单审核: {order_no}")
    resp = await client.get(f"{API}/contract/list", headers=auth(ctx["farm"]))
    sale_contracts = [c for c in resp.json()["data"] if c["type"] == "SALE" and c["order_id"] == order_id]
    assert sale_contracts, "订单审核通过应生成销售合同"
