"""安全测试: token 伪造/篡改、IDOR 越权、注入探测、文件上传限制"""
import io

from app.core.security import create_token
from tests.helpers import API, auth, login, register, setup_shelf


async def test_invalid_token_rejected(client):
    resp = await client.get(f"{API}/auth/me", headers={"Authorization": "Bearer fake-token-123"})
    assert resp.json()["code"] == 401


async def test_tampered_token_rejected(client):
    """伪造 user_id 的 token(签名不对)必须被拒"""
    forged = create_token(1, "ADMIN") + "tampered"
    resp = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert resp.json()["code"] == 401


async def test_sql_injection_login_failed(client):
    """SQL 注入探测: 登录口注入不能绕过认证"""
    for payload in ["admin' OR '1'='1", "admin'--", "' OR 1=1 --", "admin'; DROP TABLE sys_user;--"]:
        resp = await client.post(f"{API}/auth/login", json={"username": payload, "password": payload})
        assert resp.json()["code"] != 0, f"注入 payload 不应成功: {payload}"
    # 确认注入后正常账号仍可用(表没被删)
    assert (await client.post(f"{API}/auth/login", json={"username": "admin", "password": "admin123"})).json()["code"] == 0


async def test_upload_executable_rejected(client):
    """可执行文件上传必须被拒"""
    token = await login(client, "admin", "admin123")
    for name in ["evil.exe", "shell.php", "hack.sh", "virus.bat", "x.js"]:
        resp = await client.post(f"{API}/file/upload?biz_type=OTHER", headers=auth(token),
                                 files={"file": (name, io.BytesIO(b"malicious"), "application/octet-stream")})
        assert resp.json()["code"] == 400, f"应拒绝: {name}"


async def test_upload_image_allowed(client):
    token = await login(client, "admin", "admin123")
    resp = await client.post(f"{API}/file/upload?biz_type=OTHER", headers=auth(token),
                             files={"file": ("photo.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")})
    assert resp.json()["code"] == 0


async def test_idor_warehouse_isolation(client):
    """IDOR: 养殖户A不能读取养殖户B的仓库/给B的仓库登记设备"""
    ctx_a = await setup_shelf(client, "idorA")
    await register(client, "idorB_farm", "FARM", "隔离测试养殖场B")
    biz = await login(client, "business01")
    await approve_todo_from(client, biz, "隔离测试养殖场B")
    farm_b = await login(client, "idorB_farm")

    # B 的仓库列表不含 A 的仓库
    resp = await client.get(f"{API}/warehouse/my", headers=auth(farm_b))
    assert all(w["id"] != ctx_a["warehouse_id"] for w in resp.json()["data"])
    # B 给 A 的仓库登记设备 → 403
    resp = await client.post(f"{API}/iot/devices", headers=auth(farm_b),
                             json={"warehouse_id": ctx_a["warehouse_id"], "device_name": "x",
                                   "protocol": "RTSP", "stream_url": "rtsp://x"})
    assert resp.json()["code"] == 403


async def test_idor_contract_isolation(client):
    """IDOR: 企业不能查看其他企业的合同"""
    ctx_a = await setup_shelf(client, "idorC")
    await register(client, "idorD_farm", "FARM", "隔离测试养殖场D")
    biz = await login(client, "business01")
    await approve_todo_from(client, biz, "隔离测试养殖场D")
    farm_d = await login(client, "idorD_farm")
    # D 的合同列表里不能有 A 的入驻合同
    resp = await client.get(f"{API}/contract/list", headers=auth(farm_d))
    assert len(resp.json()["data"]) == 1  # 只有 D 自己的入驻合同


async def approve_todo_from(client, token, keyword):
    from tests.helpers import approve_todo
    await approve_todo(client, token, keyword)
