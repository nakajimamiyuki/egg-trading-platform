"""并发测试: 防并发资损 (重复支付/重复核销/超卖)
真正模拟多请求同时到达, 验证行级锁与状态机防护
"""
import asyncio

from tests.helpers import (API, approve_todo, auth, create_order, run_order_to_full_paid, setup_shelf)


async def test_concurrent_deposit_only_one_succeeds(client):
    """5 个并发定金支付, 只能成功 1 个, 流水只有 1 笔 DEPOSIT"""
    ctx = await setup_shelf(client, "cc1")
    order_id, order_no = await create_order(client, ctx["buyer"], ctx["shelf_item_id"], 100)
    await approve_todo(client, ctx["biz"], f"订单审核: {order_no}")

    results = await asyncio.gather(*[
        client.post(f"{API}/finance/pay", headers=auth(ctx["buyer"]),
                    json={"order_id": order_id, "pay_type": "DEPOSIT"})
        for _ in range(5)
    ])
    codes = [r.json()["code"] for r in results]
    assert codes.count(0) == 1, f"并发支付应只有1笔成功, 实际: {codes}"

    resp = await client.get(f"{API}/finance/records", headers=auth(ctx["biz"]), params={"order_id": order_id})
    deposits = [r for r in resp.json()["data"] if r["pay_type"] == "DEPOSIT"]
    assert len(deposits) == 1, "定金流水必须只有1笔"


async def test_concurrent_verify_only_one_succeeds(client):
    """5 个并发核销, 只能成功 1 个, 库存只扣一次"""
    ctx = await setup_shelf(client, "cc2")
    order_id, order_no = await create_order(client, ctx["buyer"], ctx["shelf_item_id"], 100)
    qr = await run_order_to_full_paid(client, order_id, order_no, ctx)

    results = await asyncio.gather(*[
        client.post(f"{API}/delivery/verify", headers=auth(ctx["farm"]), json={"qr_payload": qr})
        for _ in range(5)
    ])
    codes = [r.json()["code"] for r in results]
    assert codes.count(0) == 1, f"并发核销应只有1个成功, 实际: {codes}"

    resp = await client.get(f"{API}/inventory/list", headers=auth(ctx["biz"]))
    inv = [i for i in resp.json()["data"] if i["warehouse_id"] == ctx["warehouse_id"]][0]
    assert inv["quantity"] == 2900, "库存只能扣减一次"


async def test_concurrent_purchase_no_oversell(client):
    """货架3000枚, 6个并发各买1000, 成交总量不得超过库存"""
    ctx = await setup_shelf(client, "cc3")
    results = await asyncio.gather(*[
        client.post(f"{API}/orders/purchase", headers=auth(ctx["buyer"]),
                    json={"shelf_item_id": ctx["shelf_item_id"], "quantity": 1000, "sale_mode": "M1"})
        for _ in range(6)
    ])
    success = sum(1 for r in results if r.json()["code"] == 0)
    assert success <= 3, f"最多只能成交3单(3000枚), 实际成交 {success}"

    resp = await client.get(f"{API}/shelf/list", headers=auth(ctx["buyer"]))
    shelf = [s for s in resp.json()["data"] if s["delivery_warehouse_id"] == ctx["dw_id"]]
    remaining = shelf[0]["quantity"] if shelf else 0
    assert remaining == 3000 - success * 1000
    assert remaining >= 0
