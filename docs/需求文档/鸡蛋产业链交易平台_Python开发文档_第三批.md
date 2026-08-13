# 鸡蛋产业链交易平台 Python开发文档（第三批）

版本：V1.0

目标： 本批文档用于进入正式研发阶段，重点覆盖：

-   数据库详细设计
-   REST API设计规范
-   FastAPI代码工程规范
-   Vue3前端工程规范
-   开发环境规范

# 第一部分 数据库详细设计文档

# 1. 数据库总体设计

数据库：

PostgreSQL 15

字符集：

UTF-8

ORM：

SQLAlchemy 2.x

数据库分层：

    业务表

    基础表

    日志表

    配置表

    字典表

------------------------------------------------------------------------

# 2. 公共字段设计

所有业务表包含：

  字段           类型        说明
  -------------- ----------- ----------
  id             bigint      主键
  created_time   timestamp   创建时间
  updated_time   timestamp   更新时间
  created_by     bigint      创建人
  deleted        boolean     逻辑删除

------------------------------------------------------------------------

# 3. 用户权限数据库

## sys_user 用户表

字段：

  字段       类型      说明
  ---------- --------- --------
  id         bigint    用户ID
  username   varchar   账号
  password   varchar   密码
  phone      varchar   手机号
  role_id    bigint    角色

## sys_role 角色表

角色：

-   养殖企业
-   客户
-   业务人员
-   财务人员
-   管理员

## sys_permission 权限表

保存：

-   菜单权限
-   API权限
-   操作权限

------------------------------------------------------------------------

# 4. 企业管理数据库

## enterprise 企业信息表

字段：

-   id
-   enterprise_name
-   license_no
-   legal_person
-   contact_phone
-   audit_status

状态：

    WAIT

    PASS

    REJECT

------------------------------------------------------------------------

# 5. 产品数据表

## product 产品表

字段：

-   id
-   product_name
-   category
-   grade
-   specification
-   price

示例：

    鸡蛋

    A级

    50kg

------------------------------------------------------------------------

# 6. 订单数据库

## order_info订单主表

字段：

  字段        说明
  ----------- ----------
  order_no    订单编号
  buyer_id    采购方
  seller_id   销售方
  quantity    数量
  amount      金额
  status      状态

## order_item订单明细

保存：

-   商品
-   数量
-   品级
-   价格

------------------------------------------------------------------------

# 7. 仓储数据库

## warehouse仓库表

字段：

-   id
-   name
-   address
-   capacity
-   monitor_url

## inventory库存表

字段：

-   warehouse_id
-   product_id
-   quantity

库存变更必须记录：

inventory_log

------------------------------------------------------------------------

# 8. 财务数据库

## finance_bill账单表

字段：

-   order_id
-   amount
-   bill_status

## invoice发票表

字段：

-   invoice_no
-   amount
-   status

------------------------------------------------------------------------

# 第二部分 REST API设计文档

# 1. API规范

基础地址：

    /api/v1

返回格式：

``` json
{
"code":0,
"message":"success",
"data":{}
}
```

------------------------------------------------------------------------

# 2. 用户接口

## 用户登录

POST

    /api/v1/auth/login

请求：

``` json
{
"username":"admin",
"password":"123456"
}
```

返回：

``` json
{
"token":"xxxxx"
}
```

------------------------------------------------------------------------

# 3. 企业接口

创建企业：

POST

    /enterprise/create

参数：

-   企业名称
-   法人
-   营业执照

------------------------------------------------------------------------

# 4. 订单接口

创建销售订单：

POST

    /orders/sale/create

查询订单：

GET

    /orders/{id}

------------------------------------------------------------------------

# 5. 仓库接口

创建仓库：

POST

    /warehouse/create

库存查询：

GET

    /inventory/list

------------------------------------------------------------------------

# 第三部分 FastAPI代码工程规范

# 1. 服务结构

    order_service/


    app/

    ├── main.py

    ├── api/

    ├── models/

    ├── schemas/

    ├── services/

    ├── repository/

    ├── core/

    └── tests/

------------------------------------------------------------------------

# 2. 分层设计

Controller层：

负责HTTP接口

Service层：

负责业务逻辑

Repository层：

负责数据库访问

Model层：

数据库模型

Schema：

请求响应模型

------------------------------------------------------------------------

# 3. Pydantic模型

示例：

``` python
from pydantic import BaseModel


class OrderCreate(BaseModel):

    quantity:int

    price:float
```

------------------------------------------------------------------------

# 4. Service示例

``` python
class OrderService:


    async def create(self,data):

        order=create_order(data)

        return order
```

------------------------------------------------------------------------

# 第四部分 Vue3前端开发设计

# 1. 技术栈

-   Vue3
-   TypeScript
-   Vite
-   Pinia
-   Vue Router
-   Axios
-   Element Plus

------------------------------------------------------------------------

# 2. 工程目录

    src/


    api/

    components/

    views/

    router/

    store/

    utils/

    hooks/

    permission/

------------------------------------------------------------------------

# 3. 页面模块

## 养殖端

页面：

-   企业认证
-   产蛋录入
-   销售管理
-   仓库管理
-   财务中心

## 客户端

页面：

-   商品大厅
-   采购订单
-   合同中心

## 管理后台

页面：

-   用户管理
-   审批中心
-   数据看板

------------------------------------------------------------------------

# 4. Axios封装

功能：

-   Token自动注入
-   错误处理
-   请求重试

------------------------------------------------------------------------

# 第五部分 开发环境设计

# Docker Compose开发环境

服务：

    postgres

    redis

    rabbitmq

    minio

    backend

    frontend

------------------------------------------------------------------------

# 第六部分 Git开发规范

分支：

    main

    develop

    feature/order

    feature/payment

    bugfix/*

提交：

    feat:

    fix:

    docs:

    refactor:

------------------------------------------------------------------------

# 第七部分 后续开发文档

下一阶段继续生成：

1.  完整PostgreSQL SQL建库脚本
2.  FastAPI完整源码模板
3.  Vue3完整源码模板
4.  Docker Compose文件
5.  Kubernetes生产部署文件
6.  Swagger接口完整定义
7.  自动化测试代码
