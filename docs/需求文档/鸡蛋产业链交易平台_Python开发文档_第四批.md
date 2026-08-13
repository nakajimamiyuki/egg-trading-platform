# 鸡蛋产业链交易平台 Python开发文档（第四批）

版本：V1.0

## 第一章 数据库设计

### 数据库技术

-   PostgreSQL 15
-   SQLAlchemy 2.x
-   UTF-8

### 公共字段

  字段           类型        说明
  -------------- ----------- ----------
  id             bigserial   主键
  created_time   timestamp   创建时间
  updated_time   timestamp   更新时间
  deleted        boolean     逻辑删除

## 用户权限表

### sys_user

``` sql
CREATE TABLE sys_user (
 id BIGSERIAL PRIMARY KEY,
 username VARCHAR(50),
 password VARCHAR(255),
 phone VARCHAR(20),
 status INT
);
```

### sys_role

角色：

-   养殖企业
-   客户
-   业务人员
-   财务人员
-   管理员

## 企业表 enterprise

字段：

-   id
-   enterprise_name
-   license_no
-   legal_person
-   audit_status

## 订单表 order_info

字段：

-   order_no
-   buyer_id
-   seller_id
-   quantity
-   amount
-   status

订单状态：

CREATE -\> AUDIT -\> CONTRACT -\> DELIVERY -\> FINISHED

# 第二章 FastAPI后端工程设计

## 项目结构

    backend/

    app/

    ├── main.py
    ├── core/
    ├── database/
    ├── modules/
    │   ├── user/
    │   ├── order/
    │   ├── warehouse/
    │   └── finance/
    └── tests/

## requirements.txt

    fastapi
    uvicorn
    sqlalchemy
    asyncpg
    redis
    python-jose
    passlib
    pytest

## FastAPI入口

``` python
from fastapi import FastAPI

app = FastAPI(title="Egg Platform API")

@app.get("/health")
async def health():
    return {"status":"ok"}
```

# 第三章 业务模块设计

## 用户模块

功能：

-   注册
-   登录
-   企业认证
-   权限控制

## 订单模块

功能：

-   创建订单
-   查询订单
-   审批订单
-   状态流转

接口：

    POST /api/v1/orders
    GET /api/v1/orders/{id}

## 仓储模块

功能：

-   仓库管理
-   库存管理
-   交割仓管理

# 第四章 Vue3前端设计

技术：

-   Vue3
-   TypeScript
-   Vite
-   Pinia
-   Vue Router
-   Element Plus

目录：

    src/

    api/
    router/
    store/
    views/
    components/
    utils/

页面：

-   企业认证
-   销售订单
-   采购订单
-   仓库管理
-   审批中心
-   数据看板

# 第五章 Docker环境

服务：

    postgres
    redis
    rabbitmq
    minio
    backend
    frontend
    nginx

# 第六章 API规范

统一：

    /api/v1

返回：

``` json
{
"code":0,
"message":"success",
"data":{}
}
```

# 第七章 测试规范

pytest目录：

    tests/

    test_auth.py
    test_order.py
    test_inventory.py
    test_finance.py

# 第八章 开发启动

环境：

-   Python 3.12
-   Node.js 20
-   PostgreSQL 15

流程：

    git clone

    docker compose up

    初始化数据库

    启动FastAPI

    启动Vue3
