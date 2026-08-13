#!/bin/bash
# M5 功能自动化测试: 强制平仓/对账/尽调拦截/看板/物流/激励
# 前置: demo_seed.sh + test_m3_flow.sh 已执行
set -e
B=http://localhost:8000/api/v1
J='Content-Type: application/json'
login() { curl -s -X POST $B/auth/login -H "$J" -d "{\"username\":\"$1\",\"password\":\"$2\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])"; }
approve() {
  local T=$(curl -s $B/workflow/todo -H "Authorization: Bearer $1" | python3 -c "import sys,json;d=[t['task_id'] for t in json.load(sys.stdin)['data'] if '$2' in t['title']];print(d[0] if d else '')")
  [ -n "$T" ] && curl -s -X POST $B/workflow/tasks/$T/handle -H "Authorization: Bearer $1" -H "$J" -d "{\"action\":\"PASS\",\"opinion\":\"$3\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"
}
BIZ=$(login business01 123456); FIN=$(login finance01 123456); FARM=$(login farm001 123456); BUYER=$(login buyer001 123456)

echo "== 1. 周转预警手动触发 =="
curl -s -X POST $B/risk/check-warnings -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

echo "== 2. 养殖端退仓申请(先建第二个交割仓) =="
curl -s -X POST $B/warehouse/delivery/apply -H "Authorization: Bearer $BIZ" -H "$J" -d '{"warehouse_id":1,"quantity":2000,"grade":"B","spec":"S45","price":5.0}' > /dev/null
approve "$BIZ" "交割仓" "同意建仓"
DW2=$(curl -s $B/warehouse/delivery/list -H "Authorization: Bearer $FARM" | python3 -c "import sys,json;print([d['id'] for d in json.load(sys.stdin)['data'] if d['status']=='IN_STOCK'][0])")
curl -s -X POST $B/risk/apply -H "Authorization: Bearer $FARM" -H "$J" -d "{\"delivery_warehouse_id\":$DW2,\"apply_type\":\"RETURN\",\"remark\":\"行情不好,申请退仓\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"
approve "$BIZ" "退仓" "同意退仓"
curl -s $B/warehouse/delivery/list -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;[print(' ',d['dw_no'],d['status']) for d in json.load(sys.stdin)['data']]"

echo "== 3. 强制平仓+折价处置(先再造一个交割仓) =="
curl -s -X POST $B/warehouse/delivery/apply -H "Authorization: Bearer $BIZ" -H "$J" -d '{"warehouse_id":1,"quantity":1500,"grade":"C","spec":"S40","price":4.5}' > /dev/null
approve "$BIZ" "交割仓" "同意"
DW3=$(curl -s $B/warehouse/delivery/list -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;print([d['id'] for d in json.load(sys.stdin)['data'] if d['status']=='IN_STOCK'][0])")
curl -s -X POST $B/risk/force-close/$DW3 -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['message'],d['data'])"
approve "$FIN" "平仓退款" "按80%折价结算"
curl -s $B/risk/close/list -H "Authorization: Bearer $FIN" | python3 -c "import sys,json;[print('  平仓单:',c['close_no'],'原价',c['original_amount'],'结算',c['settle_amount'],'盈亏',c['profit_loss'],c['status']) for c in json.load(sys.stdin)['data']]"
curl -s $B/inventory/list -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;[print('  库存:',i['grade'],'级',i['quantity'],'枚') for i in json.load(sys.stdin)['data']]"

echo "== 4. 对账中心 =="
curl -s -X POST $B/reconcile/run -H "Authorization: Bearer $FIN" -H "$J" -d '{"scope":"DELIVERY","period_start":"2026-08-01","period_end":"2026-08-31"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data'])"
BID=$(curl -s $B/reconcile/batches -H "Authorization: Bearer $FIN" | python3 -c "import sys,json;print(json.load(sys.stdin)['data'][0]['id'])")
curl -s -X POST $B/reconcile/batches/$BID/archive -H "Authorization: Bearer $FIN" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

echo "== 5. 渠道账期模式尽调拦截(F1.3) =="
SHELF=$(curl -s $B/shelf/list -H "Authorization: Bearer $BUYER" | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];print(d[0]['id'] if d else '')")
if [ -n "$SHELF" ]; then
  curl -s -X POST $B/orders/purchase -H "Authorization: Bearer $BUYER" -H "$J" -d "{\"shelf_item_id\":$SHELF,\"quantity\":100,\"sale_mode\":\"M3\",\"credit_days\":60}" | python3 -c "import sys,json;print('  未尽调下单M3:',json.load(sys.stdin)['message'])"
  curl -s -X POST $B/risk/survey -H "Authorization: Bearer $FIN" -H "$J" -d '{"enterprise_id":2,"conclusion":"PASS","remark":"京东渠道资质合规"}' | python3 -c "import sys,json;print('  尽调登记:',json.load(sys.stdin)['message'])"
  curl -s -X POST $B/orders/purchase -H "Authorization: Bearer $BUYER" -H "$J" -d "{\"shelf_item_id\":$SHELF,\"quantity\":100,\"sale_mode\":\"M3\",\"credit_days\":60}" | python3 -c "import sys,json;d=json.load(sys.stdin);print('  尽调后下单M3:',d['message'],'分利:',d['data']['platform_profit'] if d.get('data') else '-')"
fi

echo "== 6. 数据看板 =="
curl -s $B/dashboard/summary -H "Authorization: Bearer $FIN" | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];print('  订单分布:',d['order_by_mode']);print('  收款:',d['total_received'],'付款:',d['total_paid'],'退款:',d['total_refund']);print('  库存:',d['inventory'],'交割仓:',d['dw_by_status'])"
curl -s -o /tmp/report.xlsx -w "  Excel导出: %{http_code} " $B/dashboard/export -H "Authorization: Bearer $FIN" && ls -la /tmp/report.xlsx | awk '{print "大小:",$5,"字节"}'

echo "== 7. 物流(M3模式①订单的运单) =="
curl -s -X POST $B/logistics/create -H "Authorization: Bearer $BIZ" -H "$J" -d '{"order_id":1,"waybill_no":"YMM20260813001","driver_name":"王五","driver_phone":"13700000003","plate_no":"豫A12345"}' | python3 -c "import sys,json;print(' ',json.load(sys.stdin)['message'])"
curl -s -X POST $B/logistics/1/track -H "Authorization: Bearer $BIZ" -H "$J" -d '{"address":"郑州市中牟县装货完成","longitude":113.97,"latitude":34.72}' | python3 -c "import sys,json;print(' ',json.load(sys.stdin)['message'])"
curl -s $B/logistics/by-order/1 -H "Authorization: Bearer $BUYER" | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];print('  物流状态:',d['status'],'轨迹点:',len(d['tracks']))"

echo "== 8. 激励名单(F10.4) =="
curl -s $B/incentive/list -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;[print(' ',i['enterprise_name'],'合作',i['coop_months'],'月 发货',i['shipped'],'枚 达标:',i['qualified']) for i in json.load(sys.stdin)['data']]"
echo "M5 全部测试完成 ✅"
