# 蛋品交易平台 部署说明（Windows / Linux 通用）

版本：V1.0 ｜ 日期：2026-08-13 ｜ 适用代码：`develop` 分支（M5 Feature Complete）

> 整个平台已容器化：一条 `docker compose up -d` 命令拉起全部服务（前端、后端、PostgreSQL、Redis、RabbitMQ、MinIO），**代码零改动**，Windows / Linux / macOS 通用。

---

## 0. 部署后你会得到什么

| 入口 | 地址 | 说明 |
|---|---|---|
| 平台页面（四端统一入口） | http://localhost:8080 | 演示/使用主入口 |
| 后端 API 文档 | http://localhost:8000/docs | Swagger 接口文档 |
| RabbitMQ 管理台 | http://localhost:15672 | egg / egg_dev_2026 |
| MinIO 文件控制台 | http://localhost:9001 | egg / egg_dev_2026 |

演示账号：`admin/admin123`（管理员）、`business01/123456`（业务）、`finance01/123456`（财务）、`farm001/123456`（养殖）、`buyer001/123456`（客户）。

---

# 第一部分：Windows 部署

## 1. 环境要求

| 项目 | 要求 |
|---|---|
| 系统 | Windows 10 64位（22H2+）/ Windows 11，家庭版/专业版均可 |
| 硬件 | CPU 4 核+、内存 ≥8GB（建议 16GB）、磁盘 ≥20GB 可用 |
| 虚拟化 | BIOS 需开启 CPU 虚拟化（VT-x/AMD-V，大多数电脑默认已开） |
| 软件 | Docker Desktop for Windows、Git for Windows |

## 2. 安装步骤

### 2.1 安装 Docker Desktop

```powershell
# 方式一: winget 命令行安装
winget install Docker.DockerDesktop

# 方式二: 官网下载安装包
# https://www.docker.com/products/docker-desktop/
```

- 安装过程会引导启用 **WSL2**（如提示 `wsl --install`，照做并重启电脑）
- 安装后启动 Docker Desktop，等任务栏鲸鱼图标变绿
- **调内存配额**：Docker Desktop → ⚙️ Settings → Resources → Memory 调到 **6GB 以上** → Apply & Restart

### 2.2 安装 Git 并拉取代码

```powershell
winget install Git.Git

# 拉代码（GitHub 私有仓库, 需先登录: gh auth login, 或用账号密码/token）
git clone https://github.com/nakajimamiyuki/egg-trading-platform.git
cd egg-trading-platform
git checkout develop
```

### 2.3 一键启动

```powershell
docker compose up -d --build
```

首次构建约 5–10 分钟（下载镜像 + 安装依赖），之后启动只要几秒。

### 2.4 初始化演示数据（可选）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo_seed.ps1
```

> 仓库里同时提供 `scripts/demo_seed.sh`（Linux/Mac/Git Bash 用）和 `demo_seed.ps1`（Windows 用），效果相同：造出已入驻的养殖户+采购商+已租赁确权仓库+在架交割仓。

### 2.5 验证

浏览器打开 http://localhost:8080 → 看到登录页即成功。用 `business01/123456` 登录，左侧有完整菜单。

## 3. Windows 常见问题

| 问题 | 解决 |
|---|---|
| 启动报 WSL2 错误 | 管理员 PowerShell 执行 `wsl --install` 后重启 |
| 报虚拟化未开启 | 进 BIOS 开启 VT-x/AMD-V |
| 端口被占用（如 8080） | 改 `docker-compose.yml` 里对应服务的端口映射（如 `"8081:80"`） |
| 构建时网络慢/超时 | Docker Desktop → Settings → Docker Engine，配置国内镜像加速器后重启 |
| 页面能开但合同/文件链接打不开 | 见第四部分"局域网/服务器访问"说明 |

---

# 第二部分：Linux 部署（云服务器/本地服务器）

## 1. 环境要求

| 项目 | 要求 |
|---|---|
| 系统 | Ubuntu 22.04+ / Debian 12+ / CentOS Stream 9+（其他发行版同理） |
| 硬件 | 最低 2核4G（测试），**生产建议 4核8G+**，磁盘 ≥50GB |
| 软件 | Docker Engine + Docker Compose 插件 |

## 2. 安装步骤（以 Ubuntu 为例）

```bash
# 2.1 安装 Docker（官方一键脚本）
curl -fsSL https://get.docker.com | bash
systemctl enable --now docker

# 2.2 拉代码
git clone https://github.com/nakajimamiyuki/egg-trading-platform.git
cd egg-trading-platform
git checkout develop

# 2.3 启动
docker compose up -d --build

# 2.4 初始化演示数据（可选）
bash scripts/demo_seed.sh
```

## 3. 服务器访问方式

- 本机访问：http://localhost:8080
- **局域网/公网访问**：http://服务器IP:8080
  - 云服务器需在安全组/防火墙放行端口：`8080`（页面）、`8000`（API，可选）、`9000`（MinIO 文件，合同/证照预览需要）
  - ⚠️ 给别人访问前，必须修改一个环境变量（见第四部分）

## 4. 生产化建议（正式上线前）

1. **改密码**：`docker-compose.yml` 里的数据库/Redis/RabbitMQ/MinIO 密码和 `JWT_SECRET` 全部换成强密码
2. **加自启动**：给 compose 各服务加 `restart: always`
3. **HTTPS**：前置 Nginx/网关 + 域名证书（真实支付回调、微信登录等都要求 HTTPS）
4. **数据备份**：定期备份 PostgreSQL 数据卷和 MinIO 数据卷（见第五部分）
5. **云托管中间件**：正式环境建议数据库用云 RDS、文件用 OSS，比容器自建更稳

---

# 第三部分：日常运维操作（两个系统通用）

```bash
docker compose up -d          # 启动
docker compose down           # 停止（数据保留）
docker compose down -v        # 停止并清空全部数据（重置演示环境）
docker compose logs -f backend   # 看后端日志
docker compose ps             # 查看容器状态
docker compose restart backend   # 重启后端

# 更新代码（拉新版后重建）
git pull && docker compose up -d --build

# 完全重置演示环境（清库+重建+造数）
docker compose down -v && docker compose up -d --build
# Windows: powershell -ExecutionPolicy Bypass -File scripts\demo_seed.ps1
# Linux:   bash scripts/demo_seed.sh
```

修改后端代码：容器挂载了源码，`backend/app/` 下的改动保存即热更新，无需重启。

---

# 第四部分：局域网/服务器访问的重要配置

平台里合同、证照、装车照片等文件链接（MinIO 预签名 URL）默认生成的是 `localhost:9000`——**只有部署机自己能打开**。要让局域网其他电脑或公网用户能预览文件：

编辑 `docker-compose.yml` 中 backend 的环境变量：

```yaml
backend:
  environment:
    MINIO_PUBLIC_ENDPOINT: localhost:9000     # 改这里
```

改为部署机的实际地址，例如：

```yaml
    MINIO_PUBLIC_ENDPOINT: 192.168.1.50:9000      # 局域网演示
    # 或 MINIO_PUBLIC_ENDPOINT: files.yourdomain.com   # 正式域名
```

然后 `docker compose up -d backend` 重启后端即可（代码不用改）。

> 页面本身（8080）和 API（由前端 nginx 反代 `/api`）无需任何修改即可被局域网访问，只有文件预览链接涉及这个变量。

---

# 第五部分：数据与备份

| 数据 | 位置（Docker 卷） | 备份方式 |
|---|---|---|
| 业务数据库 | `egg-platform_pg_data` | `docker exec egg-postgres pg_dump -U egg egg_platform > backup.sql` |
| 文件（证照/合同/照片） | `egg-platform_minio_data` | 直接打卷快照或 MinIO 控制台导出 |
| 队列/缓存 | rabbitmq/redis 卷 | 非关键数据，可不备 |

恢复：`cat backup.sql | docker exec -i egg-postgres psql -U egg egg_platform`

---

# 第六部分：端口一览

| 端口 | 服务 | 必须对外 |
|---|---|---|
| 8080 | 前端页面（含 /api 反代） | ✅ 唯一必须 |
| 8000 | 后端 API（Swagger） | 可选（调试/对接用） |
| 9000 | MinIO 文件访问 | 需要文件预览时 ✅ |
| 9001 | MinIO 控制台 | 仅管理员 |
| 5432 | PostgreSQL | ❌ 不建议对外 |
| 6379 | Redis | ❌ 不要对外 |
| 5672/15672 | RabbitMQ | ❌ 不要对外 |

---

# 第七部分：上线到云（M6 计划事项速查）

1. 云服务器（4核8G）+ **弹性公网 IP**（银企直联固定 IP 白名单需要）
2. 域名 + 备案 + HTTPS 证书
3. 数据库/Redis/对象存储可换云托管（RDS/Redis/OSS）
4. 真实支付（微信/支付宝商户号）回调联调——替换模拟支付通道
5. 银企直联签约后切换 `bank_channel`，去掉人工回单环节
