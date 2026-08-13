#!/usr/bin/env python3
"""性能压测脚本: 货架查询 / 下单 / 库存扣减关键路径
用法: python3 scripts/load_test.py [并发数] [每协程请求数]
在宿主机直接跑(打本机容器), 需 pip install httpx
"""
import asyncio
import statistics
import sys
import time

import httpx

BASE = "http://localhost:8000/api/v1"


async def login(client, u, p):
    resp = await client.post(f"{BASE}/auth/login", json={"username": u, "password": p})
    return resp.json()["data"]["token"]


async def bench(name, coro_factory, concurrency: int, per_worker: int):
    latencies = []

    async def worker():
        for _ in range(per_worker):
            start = time.perf_counter()
            resp = await coro_factory()
            latencies.append((time.perf_counter() - start) * 1000)
            assert resp.json()["code"] == 0, f"{name} 请求失败: {resp.text[:200]}"

    start = time.perf_counter()
    await asyncio.gather(*[worker() for _ in range(concurrency)])
    total_time = time.perf_counter() - start
    total = concurrency * per_worker
    print(f"{name}: 并发{concurrency} x {per_worker} = {total} 请求 | "
          f"总耗时 {total_time:.2f}s | RPS {total / total_time:.0f} | "
          f"P50 {statistics.median(latencies):.0f}ms | "
          f"P95 {sorted(latencies)[int(len(latencies) * 0.95)]:.0f}ms | "
          f"最大 {max(latencies):.0f}ms")


async def main():
    concurrency = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    per_worker = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    async with httpx.AsyncClient(timeout=30) as client:
        biz = await login(client, "business01", "123456")
        buyer = await login(client, "buyer001", "123456")
        headers = {"Authorization": f"Bearer {biz}"}
        buyer_headers = {"Authorization": f"Bearer {buyer}"}

        await bench("货架查询(业务端)", lambda: client.get(f"{BASE}/shelf/list", headers=headers), concurrency, per_worker)
        await bench("订单列表(客户端)", lambda: client.get(f"{BASE}/orders/list", headers=buyer_headers), concurrency, per_worker)
        await bench("库存查询", lambda: client.get(f"{BASE}/inventory/list", headers=headers), concurrency, per_worker)
        await bench("数据看板汇总", lambda: client.get(f"{BASE}/dashboard/summary", headers=headers), concurrency, per_worker)


if __name__ == "__main__":
    asyncio.run(main())
