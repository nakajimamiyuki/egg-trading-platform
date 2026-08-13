#!/bin/bash
# M3 模式①全流程自动化测试: 采购→审核→定金→垫资→出库三确→尾款→结算→二维码→扫码放行
# 前置: demo_seed.sh 已执行
set -e
B=http://localhost:8000/api/v1
J='Content-Type: application/json'

login() { curl -s -X POST $B/auth/login -H "$J" -d "{\"username\":\"$1\",\"password\":\"$2\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])"; }
approve() {
  local T=$(curl -s $B/workflow/todo -H "Authorization: Bearer $1" | python3 -c "import sys,json;d=[t['task_id'] for t in json.load(sys.stdin)['data'] if '$2' in t['title']];print(d[0] if d else '')")
  [ -n "$T" ] && curl -s -X POST $B/workflow/tasks/$T/handle -H "Authorization: Bearer $1" -H "$J" -d "{\"action\":\"PASS\",\"opinion\":\"$3\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"
}

BIZ=$(login business01 123456); FIN=$(login finance01 123456)
FARM=$(login farm001 123456); BUYER=$(login buyer001 123456)

echo "== 1. 采购商下单(模式①, 1000枚) =="
ORDER=$(curl -s -X POST $B/orders/purchase -H "Authorization: Bearer $BUYER" -H "$J" -d '{"shelf_item_id":1,"quantity":1000,"sale_mode":"M1"}')
echo "$ORDER" | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];print('订单:',d['order_no'],'总额:',d['total_amount'],'定金:',d['deposit_amount'],'垫资:',d['advance_amount'])"
OID=$(echo "$ORDER" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['id'])")

echo "== 2. 业务审核订单 =="
approve "$BIZ" "订单审核" "信息无误"

echo "== 3. 客户付20%定金 =="
curl -s -X POST $B/finance/pay -H "Authorization: Bearer $BUYER" -H "$J" -d "{\"order_id\":$OID,\"pay_type\":\"DEPOSIT\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

echo "== 4. 财务垫资审批(80%给养殖户) =="
approve "$FIN" "垫资" "同意垫资"

echo "== 5. 业务开出库单 =="
OB=$(curl -s -X POST $B/delivery/outbound -H "Authorization: Bearer $BIZ" -H "$J" -d "{\"order_id\":$OID,\"plate_no\":\"豫A12345\",\"driver_name\":\"王五\",\"driver_phone\":\"13700000003\"}")
echo "$OB" | python3 -c "import sys,json;print('出库单:',json.load(sys.stdin)['data']['outbound_no'])"
OBID=$(echo "$OB" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['id'])")

echo "== 6. 三方确认(养殖户/客户/平台) =="
curl -s -X POST $B/delivery/outbound/$OBID/confirm/seller -H "Authorization: Bearer $FARM" | python3 -c "import sys,json;print('养殖户:',json.load(sys.stdin)['message'])"
curl -s -X POST $B/delivery/outbound/$OBID/confirm/buyer -H "Authorization: Bearer $BUYER" | python3 -c "import sys,json;print('客户:',json.load(sys.stdin)['message'])"
curl -s -X POST $B/delivery/outbound/$OBID/confirm/platform -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;print('平台:',json.load(sys.stdin)['message'])"

echo "== 7. 客户付80%尾款 =="
curl -s -X POST $B/finance/pay -H "Authorization: Bearer $BUYER" -H "$J" -d "{\"order_id\":$OID,\"pay_type\":\"TAIL\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

echo "== 8. 财务尾款结算审批(20%给养殖户) =="
approve "$FIN" "尾款结算" "货款到账已查收"

echo "== 9. 电子提货凭证 =="
QR=$(curl -s $B/delivery/voucher/by-order/$OID -H "Authorization: Bearer $FARM" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['qr_payload'])")
echo "二维码内容: $QR"

echo "== 10. 越权核销测试(客户扫码, 应被拒) =="
curl -s -X POST $B/delivery/verify -H "Authorization: Bearer $BUYER" -H "$J" -d "{\"qr_payload\":\"$QR\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

echo "== 11. 养殖户扫码核销放行 =="
curl -s -X POST $B/delivery/verify -H "Authorization: Bearer $FARM" -H "$J" -d "{\"qr_payload\":\"$QR\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

echo "== 12. 重复扫码测试(应提示已核销) =="
curl -s -X POST $B/delivery/verify -H "Authorization: Bearer $FARM" -H "$J" -d "{\"qr_payload\":\"$QR\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

echo "== 13. 最终状态验证 =="
curl -s $B/orders/$OID -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];print('订单状态:',d['status_text']);[print('  ',e['to_status_text'],'-',e['remark']) for e in d['events']]"
curl -s $B/inventory/list -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;[print('库存:',i['quantity'],'枚, 锁定',i['locked_qty']) for i in json.load(sys.stdin)['data']]"
echo "== 资金流水 =="
curl -s "$B/finance/records?order_id=$OID" -H "Authorization: Bearer $FIN" | python3 -c "import sys,json;[print(r['pay_type'],r['direction'],'¥'+str(r['amount']),r['status']) for r in json.load(sys.stdin)['data']]"
echo "M3 模式①全流程测试完成 ✅"
