# 蛋品交易平台 演示数据初始化（Windows PowerShell 版）
# 用法: 在仓库根目录执行  powershell -ExecutionPolicy Bypass -File scripts\demo_seed.ps1
# 前置: docker compose up -d 已启动且后端健康

$B = "http://localhost:8000/api/v1"

function Login($u, $p) {
    $resp = Invoke-RestMethod -Method Post -Uri "$B/auth/login" -ContentType "application/json" -Body (@{username=$u; password=$p} | ConvertTo-Json)
    return $resp.data.token
}

function Approve($token, $keyword, $opinion) {
    $todo = Invoke-RestMethod -Uri "$B/workflow/todo" -Headers @{Authorization="Bearer $token"}
    $task = $todo.data | Where-Object { $_.title -like "*$keyword*" } | Select-Object -First 1
    if ($task) {
        $resp = Invoke-RestMethod -Method Post -Uri "$B/workflow/tasks/$($task.task_id)/handle" -ContentType "application/json" -Headers @{Authorization="Bearer $token"} -Body (@{action="PASS"; opinion=$opinion} | ConvertTo-Json)
        Write-Host $resp.message
    }
}

Write-Host "== 注册养殖户 =="
Invoke-RestMethod -Method Post -Uri "$B/auth/register" -ContentType "application/json" -Body (@{
    username="farm001"; password="123456"; real_name="张三"; phone="13800000001"
    enterprise_name="绿源蛋鸡养殖场"; enterprise_type="FARM"; license_no="91410100MA9XXXX01"
    legal_person="张三"; address="河南省郑州市中牟县"; breed="海兰褐"; stock_qty=100000; day_age=180; daily_egg_qty=95000
} | ConvertTo-Json) | ForEach-Object { Write-Host $_.message }

Write-Host "== 注册采购商 =="
Invoke-RestMethod -Method Post -Uri "$B/auth/register" -ContentType "application/json" -Body (@{
    username="buyer001"; password="123456"; real_name="李四"; phone="13900000002"
    enterprise_name="中原蛋品批发公司"; enterprise_type="BUYER"; license_no="91410100MA9XXXX02"; legal_person="李四"
} | ConvertTo-Json) | ForEach-Object { Write-Host $_.message }

$BIZ = Login business01 123456
$FIN = Login finance01 123456
$FARM = Login farm001 123456

Write-Host "== 准入审批 =="
Approve $BIZ "绿源" "资质齐全"
Approve $BIZ "中原" "资质齐全"

Write-Host "== 建仓库 + 租赁审批(业务→财务) =="
Invoke-RestMethod -Method Post -Uri "$B/warehouse" -ContentType "application/json" -Headers @{Authorization="Bearer $FARM"} -Body (@{name="绿源1号仓"; address="郑州市中牟县"; capacity=5000} | ConvertTo-Json) | Out-Null
Invoke-RestMethod -Method Post -Uri "$B/warehouse/1/lease-apply" -ContentType "application/json" -Headers @{Authorization="Bearer $BIZ"} -Body (@{rent_amount=8000} | ConvertTo-Json) | ForEach-Object { Write-Host $_.message }
Approve $BIZ "租赁" "条款无误"
Approve $FIN "租赁" "租金合理"

Write-Host "== 监控设备登记+检测+确权 =="
Invoke-RestMethod -Method Post -Uri "$B/iot/devices" -ContentType "application/json" -Headers @{Authorization="Bearer $FARM"} -Body (@{warehouse_id=1; device_name="1号仓东门摄像头"; protocol="RTSP"; stream_url="rtsp://192.168.1.100:554/stream1"} | ConvertTo-Json) | Out-Null
Invoke-RestMethod -Method Post -Uri "$B/iot/devices/1/check" -Headers @{Authorization="Bearer $FARM"} | Out-Null
Invoke-RestMethod -Method Post -Uri "$B/iot/devices/1/confirm" -Headers @{Authorization="Bearer $BIZ"} | ForEach-Object { Write-Host $_.message }

Write-Host "== 产蛋录入 + 交割仓审批 =="
Invoke-RestMethod -Method Post -Uri "$B/production" -ContentType "application/json" -Headers @{Authorization="Bearer $FARM"} -Body (@{prod_date="2026-08-13"; quantity=3000; grade="A"; spec="S50"} | ConvertTo-Json) | Out-Null
Invoke-RestMethod -Method Post -Uri "$B/warehouse/delivery/apply" -ContentType "application/json" -Headers @{Authorization="Bearer $BIZ"} -Body (@{warehouse_id=1; quantity=3000; grade="A"; spec="S50"; price=5.5} | ConvertTo-Json) | ForEach-Object { Write-Host $_.message }
Approve $BIZ "交割仓" "同意建仓"

Write-Host "== 结果验证 =="
$dw = Invoke-RestMethod -Uri "$B/warehouse/delivery/list" -Headers @{Authorization="Bearer $BIZ"}
$dw.data | ForEach-Object { Write-Host "$($_.dw_no) $($_.status) $($_.quantity)枚" }
$inv = Invoke-RestMethod -Uri "$B/inventory/list" -Headers @{Authorization="Bearer $BIZ"}
$inv.data | ForEach-Object { Write-Host "库存: $($_.warehouse_name) $($_.grade)级 $($_.quantity)枚" }
$shelf = Invoke-RestMethod -Uri "$B/shelf/list" -Headers @{Authorization="Bearer $BIZ"}
$shelf.data | ForEach-Object { Write-Host "货架: $($_.dw_no) $($_.grade)级 $($_.quantity)枚 ¥$($_.price) $($_.source_enterprise)" }

Write-Host "演示数据初始化完成 ✅"
Write-Host "账号: farm001/buyer001/business01/finance01 密码均为123456, admin/admin123"
