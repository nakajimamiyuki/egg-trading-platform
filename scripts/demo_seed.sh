#!/bin/bash
# 演示数据一键初始化: 注册→审批→建仓→入库全链路 (开发/演示用)
# 用法: ./scripts/demo_seed.sh   (需服务已启动, 数据库为空或允许重复报错)
set -e
B=http://localhost:8000/api/v1
J='Content-Type: application/json'

login() { curl -s -X POST $B/auth/login -H "$J" -d "{\"username\":\"$1\",\"password\":\"$2\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])"; }

echo "== 注册养殖户 =="
curl -s -X POST $B/auth/register -H "$J" -d '{"username":"farm001","password":"123456","real_name":"张三","phone":"13800000001","enterprise_name":"绿源蛋鸡养殖场","enterprise_type":"FARM","license_no":"91410100MA9XXXX01","legal_person":"张三","address":"河南省郑州市中牟县","breed":"海兰褐","stock_qty":100000,"day_age":180,"daily_egg_qty":95000}' | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

echo "== 注册采购商 =="
curl -s -X POST $B/auth/register -H "$J" -d '{"username":"buyer001","password":"123456","real_name":"李四","phone":"13900000002","enterprise_name":"中原蛋品批发公司","enterprise_type":"BUYER","license_no":"91410100MA9XXXX02","legal_person":"李四","address":"郑州市金水区"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

BIZ=$(login business01 123456)
FIN=$(login finance01 123456)
FARM=$(login farm001 123456)

approve() { # $1=token $2=标题关键词 $3=意见
  local T=$(curl -s $B/workflow/todo -H "Authorization: Bearer $1" | python3 -c "import sys,json;d=[t['task_id'] for t in json.load(sys.stdin)['data'] if '$2' in t['title']];print(d[0] if d else '')")
  [ -n "$T" ] && curl -s -X POST $B/workflow/tasks/$T/handle -H "Authorization: Bearer $1" -H "$J" -d "{\"action\":\"PASS\",\"opinion\":\"$3\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"
}

echo "== 准入审批 =="
approve "$BIZ" "绿源" "资质齐全"
approve "$BIZ" "中原" "资质齐全"

echo "== 建仓库+租赁审批(业务→财务) =="
curl -s -X POST $B/warehouse -H "Authorization: Bearer $FARM" -H "$J" -d '{"name":"绿源1号仓","address":"郑州市中牟县","capacity":5000}' > /dev/null
curl -s -X POST $B/warehouse/1/lease-apply -H "Authorization: Bearer $BIZ" -H "$J" -d '{"rent_amount":8000}' | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"
approve "$BIZ" "租赁" "条款无误"
approve "$FIN" "租赁" "租金合理"

echo "== 监控设备登记+检测+确权 =="
curl -s -X POST $B/iot/devices -H "Authorization: Bearer $FARM" -H "$J" -d '{"warehouse_id":1,"device_name":"1号仓东门摄像头","protocol":"RTSP","stream_url":"rtsp://192.168.1.100:554/stream1"}' > /dev/null
curl -s -X POST $B/iot/devices/1/check -H "Authorization: Bearer $FARM" > /dev/null
curl -s -X POST $B/iot/devices/1/confirm -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"

echo "== 产蛋录入+交割仓审批 =="
curl -s -X POST $B/production -H "Authorization: Bearer $FARM" -H "$J" -d '{"prod_date":"2026-08-13","quantity":3000,"grade":"A","spec":"S50"}' > /dev/null
curl -s -X POST $B/warehouse/delivery/apply -H "Authorization: Bearer $BIZ" -H "$J" -d '{"warehouse_id":1,"quantity":3000,"grade":"A","spec":"S50","price":5.5}' | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"
approve "$BIZ" "交割仓" "同意建仓"

echo "== 结果验证 =="
curl -s $B/warehouse/delivery/list -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;[print(d['dw_no'],d['status'],d['quantity'],'枚') for d in json.load(sys.stdin)['data']]"
curl -s $B/inventory/list -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;[print('库存:',i['warehouse_name'],i['grade'],'级',i['quantity'],'枚') for i in json.load(sys.stdin)['data']]"
echo "== 货架(自动上架) =="
curl -s $B/shelf/list -H "Authorization: Bearer $BIZ" | python3 -c "import sys,json;[print('货架:',s['dw_no'],s['grade'],'级',s['quantity'],'枚 ¥'+str(s['price']),s['source_enterprise']) for s in json.load(sys.stdin)['data']]"
echo "演示数据初始化完成 ✅"
