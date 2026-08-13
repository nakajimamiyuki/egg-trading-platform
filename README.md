# 蛋品交易平台 (Egg Platform)

鸡蛋产业链 B2B 交易平台：养殖端 / 客户端 / 业务端 / 财务端 + 基础模块。
技术栈：FastAPI + PostgreSQL 15 + Redis + RabbitMQ + MinIO ｜ Vue3 + TypeScript + Element Plus

## 快速开始

前置：已安装并启动 Docker Desktop（内存配额 ≥ 6GB）

```bash
# 启动全部服务（首次会自动执行建库 SQL 和种子数据）
docker compose up -d --build

# 查看后端日志
docker compose logs -f backend

# 停止
docker compose down

# 停止并清空所有数据（重置数据库时用，谨慎！）
docker compose down -v
```

启动后访问：

| 入口 | 地址 | 说明 |
|---|---|---|
| 前端 | http://localhost:8080 | 四端统一入口（M0 为骨架验证页） |
| 后端 API 文档 | http://localhost:8000/docs | Swagger UI |
| 健康检查 | http://localhost:8000/api/v1/health/db | 应返回种子角色数 = 5 |
| RabbitMQ 管理台 | http://localhost:15672 | egg / egg_dev_2026 |
| MinIO 控制台 | http://localhost:9001 | egg / egg_dev_2026 |

## 目录结构

```
trading_platform/
├── docker-compose.yml          # 一键开发环境
├── docker/postgres/init/       # 建库 SQL（首次启动自动执行）
│   └── 01_schema.sql           #   全部表结构 + 角色/字典种子数据
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py             # 入口
│   │   ├── core/               # 配置/统一返回/异常/JWT
│   │   ├── database/           # 异步会话
│   │   ├── api/                # 路由聚合
│   │   └── modules/            # 业务模块(M1起逐步填充)
│   │       ├── auth/ user/ enterprise/ workflow/ ...
│   └── tests/
└── frontend/                   # Vue3 前端
    └── src/
        ├── api/request.ts      # Axios 封装(Token 注入/错误处理)
        ├── router/  store/  views/  layouts/
        └── main.ts
```

## 开发约定

- API 统一前缀 `/api/v1`，统一返回 `{"code":0,"message":"success","data":{}}`
- 业务异常抛 `BizError(message)`，全局异常处理器自动转统一格式
- 数据库表：snake_case，公共字段 id/created_time/updated_time/deleted
- 金额一律 `numeric(14,2)`；状态字段 varchar + 注释枚举值（见 01_schema.sql）
- 后端源码已挂载进容器，改代码 uvicorn 自动热更新，无需重启
- 数据库结构变更：修改 `01_schema.sql` 后执行 `docker compose down -v && docker compose up -d` 重置（仅开发期）

## 里程碑

- [x] M0 环境与骨架（当前）
- [ ] M1 用户权限 + 审批流引擎
- [ ] M2 建仓入库 + IoT 监控
- [ ] M3 交易核心（三种销售模式 + 扫码核销）
- [ ] M4 资金结算 + 合同发票
- [ ] M5 风控平仓 + 对账看板 + 物流
- [ ] M6 上线
