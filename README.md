# 蛋品交易平台 (Egg Trading Platform)

鸡蛋产业链 B2B 交易平台：养殖端 / 客户端 / 业务端 / 财务端 + 基础模块。
核心业务为"交割仓 + 平台垫资"模式，支持三种销售模式：

- **模式①** 蛋库出库标准模式：客户付 20% 定金 → 平台垫 80% → 装车核验三方确认 → 尾款 → 扫码核销放行
- **模式②** 在途货物预付模式：远端客户，平台叫车，养殖户收齐全款才放行，GPS 在途追踪
- **模式③** 渠道账期服务模式：渠道客户（如京东 60 天账期），风控尽调前置，尾款内扣平台分利

**技术栈**：FastAPI + PostgreSQL 15 + Redis + RabbitMQ + MinIO ｜ Vue3 + TypeScript + Element Plus + ECharts ｜ Docker Compose

**开发进度**：M0–M5 全部完成（需求清单 F1.1–F10.4 全功能实现），M6（测试加固与上云）进行中。

---

## 快速开始

整条链路已容器化，Windows / Linux / macOS 通用，一条命令拉起全部服务。

### 环境要求

| 项目 | 要求 |
|---|---|
| 软件 | **Docker**（Windows 用 Docker Desktop + WSL2；Linux 用 Docker Engine）+ Git |
| 硬件 | CPU 4 核+、内存 ≥8GB（建议 16GB，Docker 内存配额调至 6GB+）、磁盘 ≥20GB |

### 启动

```bash
git clone https://github.com/nakajimamiyuki/egg-trading-platform.git
cd egg-trading-platform
git checkout develop
docker compose up -d --build      # 首次构建约 5–10 分钟
```

启动后访问：

| 入口 | 地址 | 账号 |
|---|---|---|
| **平台页面** | http://localhost:8080 | 见下方演示账号 |
| API 文档 (Swagger) | http://localhost:8000/docs | — |
| RabbitMQ 管理台 | http://localhost:15672 | egg / egg_dev_2026 |
| MinIO 文件控制台 | http://localhost:9001 | egg / egg_dev_2026 |

演示账号：`admin/admin123`（管理员）｜ `business01/123456`（业务）｜ `finance01/123456`（财务）｜ `farm001/123456`（养殖）｜ `buyer001/123456`（客户）

### 初始化演示数据（可选）

```bash
# Linux / macOS / Git Bash
bash scripts/demo_seed.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts\demo_seed.ps1
```

造出：已入驻的养殖户+采购商 → 已租赁+监控确权仓库 → 在库交割仓 → 已上架货架。

### 自动化验收脚本

```bash
bash scripts/test_m3_flow.sh   # 模式①交易全流程(下单→定金→垫资→出库三确→尾款→结算→扫码放行)
bash scripts/test_m5_flow.sh   # 平仓/对账/尽调/看板/物流/激励
```

---

## 部署说明

### Windows

1. 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（`winget install Docker.DockerDesktop`），按引导启用 WSL2
2. 若报虚拟化错误：BIOS 开启 VT-x/AMD-V；管理员 PowerShell 执行 `wsl --install` 后重启
3. Docker Desktop → Settings → Resources → **内存调到 6GB+**
4. `git clone` → `docker compose up -d --build`
5. 端口冲突（8080/8000/5432 被占）时改 `docker-compose.yml` 的端口映射

### Linux（云服务器/本地服务器）

```bash
curl -fsSL https://get.docker.com | bash        # Ubuntu/Debian 一键装 Docker
systemctl enable --now docker
git clone <仓库地址> && cd egg-trading-platform && git checkout develop
docker compose up -d --build
```

- 局域网/公网访问：`http://服务器IP:8080`，防火墙/安全组放行 **8080**（页面）和 **9000**（文件预览）
- ⚠️ **文件链接（合同/证照/照片）要在其他电脑打开**，必须把 `docker-compose.yml` 中 backend 的 `MINIO_PUBLIC_ENDPOINT` 从 `localhost:9000` 改为服务器 IP（如 `192.168.1.50:9000`）或文件域名，然后 `docker compose up -d backend`

### 生产化清单（正式上线前）

1. 更换 `docker-compose.yml` 中所有默认密码与 `JWT_SECRET`
2. 各服务加 `restart: always`（或迁移 K8s）
3. 前置 Nginx/网关 + 域名 HTTPS（支付回调等要求）
4. 定期备份：`docker exec egg-postgres pg_dump -U egg egg_platform > backup.sql` + MinIO 卷
5. 云服务器需**弹性公网 IP**（银企直联银行白名单要求固定 IP）
6. 数据库/缓存/文件可换云托管（RDS / 云 Redis / OSS）

### 端口一览

| 端口 | 服务 | 对外 |
|---|---|---|
| 8080 | 前端页面（含 /api 反代） | ✅ 唯一必须 |
| 9000 | MinIO 文件访问 | 需要文件预览时 |
| 8000 | 后端 API / Swagger | 可选（调试用） |
| 5432 / 6379 / 5672 / 15672 / 9001 | 数据库/缓存/队列/控制台 | ❌ 不要对外 |

---

## 日常运维

```bash
docker compose up -d                 # 启动
docker compose down                  # 停止（数据保留）
docker compose down -v               # 停止并清空数据（重置演示环境）
docker compose logs -f backend       # 后端日志（backend/app/ 源码热更新，改即生效）
git pull && docker compose up -d --build   # 更新代码并重建
```

## 项目结构

```
├── docker-compose.yml          # 一键环境（6 容器）
├── docker/postgres/init/       # 建库 SQL（43 表 + 种子数据，首次启动自动执行）
├── backend/                    # FastAPI 后端
│   ├── app/core/               # 配置/统一返回/异常/JWT/RBAC/参数配置
│   ├── app/modules/            # 24 个业务模块(auth/order/finance/workflow/risk/...)
│   └── app/bootstrap.py        # 启动引导(管理员/演示账号/11类审批流定义)
├── frontend/                   # Vue3 + Element Plus（四端按角色出菜单）
└── scripts/                    # 演示数据与自动化验收脚本（bash + PowerShell）
```

## 开发约定

- API 前缀 `/api/v1`，统一返回 `{"code":0,"message":"success","data":{}}`
- 表命名 snake_case，公共字段 id/created_time/updated_time/deleted；金额 numeric(14,2)
- 所有审批走统一审批流引擎（wf_definition 配置化）；所有资金走统一 pay_record 流水
- 第三方依赖（支付/电子签/发票/银企直联/运满满）全部适配器 + 人工兜底，接口到位热切换

## 里程碑

- [x] M0 环境与骨架（43 表建库 + 双端骨架 + 一键环境）
- [x] M1 用户权限 + 审批流引擎 + 建档准入
- [x] M2 建仓入库 + IoT 监控确权
- [x] M3 交易核心（三种模式状态机 + 出库三方确认 + 扫码核销）
- [x] M4 资金结算 + 电子合同/发票 + 银企直联兜底
- [x] M5 平仓风控 + 对账中心 + 数据看板 + 物流 + 激励
- [ ] M6 测试加固与上云（进行中）
