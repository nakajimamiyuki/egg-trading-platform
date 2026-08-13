-- =============================================================
-- 蛋品交易平台 PostgreSQL 初始化脚本
-- 版本: V1.0  日期: 2026-08-13
-- 依据: 需求清单 F1.1-F10.4 / 平台架构图 / 开发文档第三、四批
-- 说明: 本脚本仅在 postgres 容器首次启动(空数据卷)时执行
--       金额一律 numeric(14,2), 状态字段一律 varchar + 注释枚举值
-- =============================================================

SET client_encoding = 'UTF8';

-- -------------------------------------------------------------
-- 一、系统与权限 (F9.1)
-- -------------------------------------------------------------
CREATE TABLE sys_role (
    id           BIGSERIAL PRIMARY KEY,
    code         VARCHAR(50)  NOT NULL UNIQUE,      -- FARM/CUSTOMER/BUSINESS/FINANCE/ADMIN
    name         VARCHAR(50)  NOT NULL,             -- 养殖企业/客户/业务人员/财务人员/管理员
    remark       VARCHAR(255),
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE sys_permission (
    id           BIGSERIAL PRIMARY KEY,
    code         VARCHAR(100) NOT NULL UNIQUE,      -- 如 order:create / approval:finance
    name         VARCHAR(100) NOT NULL,
    type         VARCHAR(20)  NOT NULL DEFAULT 'API', -- MENU/API/ACTION
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE sys_user (
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password      VARCHAR(255) NOT NULL,            -- bcrypt
    real_name     VARCHAR(50),
    phone         VARCHAR(20),
    enterprise_id BIGINT,                           -- 所属企业(平台人员为空)
    status        INT          NOT NULL DEFAULT 1,  -- 1正常 0禁用
    created_time  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time  TIMESTAMP    NOT NULL DEFAULT now(),
    created_by    BIGINT,
    deleted       BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE sys_user_role (
    user_id BIGINT NOT NULL REFERENCES sys_user(id),
    role_id BIGINT NOT NULL REFERENCES sys_role(id),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE sys_role_permission (
    role_id       BIGINT NOT NULL REFERENCES sys_role(id),
    permission_id BIGINT NOT NULL REFERENCES sys_permission(id),
    PRIMARY KEY (role_id, permission_id)
);

-- -------------------------------------------------------------
-- 二、企业建档与准入 (F1.1/F1.2/F1.4)
-- -------------------------------------------------------------
CREATE TABLE enterprise (
    id              BIGSERIAL PRIMARY KEY,
    enterprise_name VARCHAR(100) NOT NULL,
    type            VARCHAR(20)  NOT NULL,          -- FARM养殖户 BUYER采购商 CHANNEL渠道方
    license_no      VARCHAR(50),                    -- 统一社会信用代码
    legal_person    VARCHAR(50),                    -- 法人
    auth_rep        VARCHAR(50),                    -- 授权代表
    id_card_no      VARCHAR(30),                    -- 法人/授权代表身份证号(加密存储)
    real_name_verified BOOLEAN   NOT NULL DEFAULT FALSE, -- 实名认证结果
    contact_phone   VARCHAR(20),
    address         VARCHAR(255),
    -- 养殖企业专属字段 (F1.1)
    breed           VARCHAR(50),                    -- 养殖品种
    stock_qty       INT,                            -- 存栏量(只)
    day_age         INT,                            -- 日龄(天)
    daily_egg_qty   INT,                            -- 日均产蛋量(枚)
    -- 准入审批
    audit_status    VARCHAR(10)  NOT NULL DEFAULT 'WAIT', -- WAIT/PASS/REJECT
    audit_remark    VARCHAR(500),
    coop_evaluation VARCHAR(500),                   -- 系统生成的合作评价
    created_time    TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time    TIMESTAMP    NOT NULL DEFAULT now(),
    created_by      BIGINT,
    deleted         BOOLEAN      NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_enterprise_type ON enterprise(type);

CREATE TABLE enterprise_file (
    id            BIGSERIAL PRIMARY KEY,
    enterprise_id BIGINT       NOT NULL REFERENCES enterprise(id),
    file_type     VARCHAR(30)  NOT NULL,  -- LICENSE营业执照/ID_CARD法人身份证/BREEDING_PERMIT养殖许可/PROVENANCE引种证明/OTHER
    file_id       BIGINT       NOT NULL,  -- -> file_record.id
    created_time  TIMESTAMP    NOT NULL DEFAULT now(),
    deleted       BOOLEAN      NOT NULL DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 三、字典(品级/规格等) + 系统参数配置(业务方确认: 关键参数后台可配置)
-- -------------------------------------------------------------
CREATE TABLE sys_config (
    id           BIGSERIAL PRIMARY KEY,
    config_key   VARCHAR(50)  NOT NULL UNIQUE,
    config_value VARCHAR(255) NOT NULL,
    remark       VARCHAR(255),
    updated_time TIMESTAMP    NOT NULL DEFAULT now()
);

INSERT INTO sys_config (config_key, config_value, remark) VALUES
    ('deposit_ratio',        '0.20', '客户定金比例'),
    ('advance_ratio',        '0.80', '平台垫资比例'),
    ('turnover_days',        '3',    '交割仓周转预警天数'),
    ('close_discount_ratio', '0.80', '超期强制平仓折价比例(按80%计价)'),
    ('platform_profit_per_unit', '1.00', '模式③渠道账期平台分利(元/件)');

CREATE TABLE sys_dict_type (
    id   BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,   -- EGG_GRADE / EGG_SPEC / SALE_MODE
    name VARCHAR(50) NOT NULL
);

CREATE TABLE sys_dict_item (
    id       BIGSERIAL PRIMARY KEY,
    type_id  BIGINT      NOT NULL REFERENCES sys_dict_type(id),
    code     VARCHAR(50) NOT NULL,
    name     VARCHAR(50) NOT NULL,
    sort     INT         NOT NULL DEFAULT 0,
    UNIQUE (type_id, code)
);

-- -------------------------------------------------------------
-- 四、审批流引擎 (F9.2) —— 全平台所有审批复用
-- -------------------------------------------------------------
CREATE TABLE wf_definition (
    id           BIGSERIAL PRIMARY KEY,
    code         VARCHAR(50)  NOT NULL UNIQUE,  -- ENTERPRISE_AUDIT/WAREHOUSE_LEASE/DELIVERY_WH_CREATE/ORDER_AUDIT/CONTRACT_SIGN/PAYMENT_80/PAYMENT_20/CLOSE_REFUND/INVOICE_AUDIT/CHANNEL_RISK...
    name         VARCHAR(100) NOT NULL,
    biz_type     VARCHAR(50)  NOT NULL,         -- 业务类型
    status       INT          NOT NULL DEFAULT 1,
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE wf_node (
    id            BIGSERIAL PRIMARY KEY,
    definition_id BIGINT      NOT NULL REFERENCES wf_definition(id),
    node_name     VARCHAR(50) NOT NULL,
    seq           INT         NOT NULL,         -- 节点顺序
    approver_type VARCHAR(20) NOT NULL DEFAULT 'ROLE', -- ROLE/USER
    approver_ref  VARCHAR(50) NOT NULL,         -- 角色code或user_id
    created_time  TIMESTAMP   NOT NULL DEFAULT now(),
    deleted       BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE TABLE wf_instance (
    id            BIGSERIAL PRIMARY KEY,
    definition_id BIGINT      NOT NULL REFERENCES wf_definition(id),
    biz_type      VARCHAR(50) NOT NULL,         -- 冗余,便于查询
    biz_id        BIGINT      NOT NULL,         -- 业务单据id
    title         VARCHAR(200) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'RUNNING', -- RUNNING/PASS/REJECT/CANCEL
    current_seq   INT         NOT NULL DEFAULT 1,
    initiator_id  BIGINT      NOT NULL REFERENCES sys_user(id),
    created_time  TIMESTAMP   NOT NULL DEFAULT now(),
    updated_time  TIMESTAMP   NOT NULL DEFAULT now(),
    deleted       BOOLEAN     NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_wf_instance_biz ON wf_instance(biz_type, biz_id);

CREATE TABLE wf_task (
    id          BIGSERIAL PRIMARY KEY,
    instance_id BIGINT      NOT NULL REFERENCES wf_instance(id),
    node_id     BIGINT      NOT NULL REFERENCES wf_node(id),
    seq         INT         NOT NULL,
    assignee_id BIGINT      REFERENCES sys_user(id),  -- 实际处理人(领取后)
    status      VARCHAR(20) NOT NULL DEFAULT 'TODO',  -- TODO/PASS/REJECT/SKIP
    opinion     VARCHAR(500),
    done_time   TIMESTAMP,
    created_time TIMESTAMP  NOT NULL DEFAULT now(),
    updated_time TIMESTAMP  NOT NULL DEFAULT now(),
    deleted     BOOLEAN     NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_wf_task_instance ON wf_task(instance_id);

-- -------------------------------------------------------------
-- 五、文件存储 (MinIO 对象索引)
-- -------------------------------------------------------------
CREATE TABLE file_record (
    id           BIGSERIAL PRIMARY KEY,
    bucket       VARCHAR(50)  NOT NULL,
    object_key   VARCHAR(255) NOT NULL,
    file_name    VARCHAR(255),
    file_size    BIGINT,
    content_type VARCHAR(100),
    biz_type     VARCHAR(50),           -- ENTERPRISE_FILE/OUTBOUND_PHOTO/CONTRACT/INVOICE/POINT_MAP...
    biz_id       BIGINT,
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    created_by   BIGINT,
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 六、仓库与库存 (F2.1/F2.3)
-- -------------------------------------------------------------
CREATE TABLE warehouse (
    id             BIGSERIAL PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    enterprise_id  BIGINT       REFERENCES enterprise(id), -- 所属养殖户
    address        VARCHAR(255) NOT NULL,
    capacity       INT,                                    -- 容量(件)
    rent_amount    NUMERIC(14,2),                          -- 租金
    lease_status   VARCHAR(10)  NOT NULL DEFAULT 'NONE',   -- NONE无/WAIT审批中/LEASED已租赁
    monitor_online BOOLEAN      NOT NULL DEFAULT FALSE,    -- 监控在线确权 (F2.2)
    point_map_file_id BIGINT,                              -- 监控点位图 -> file_record
    created_time   TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time   TIMESTAMP    NOT NULL DEFAULT now(),
    created_by     BIGINT,
    deleted        BOOLEAN      NOT NULL DEFAULT FALSE
);

-- 产蛋数据录入 (F2.3)
CREATE TABLE egg_production (
    id            BIGSERIAL PRIMARY KEY,
    enterprise_id BIGINT      NOT NULL REFERENCES enterprise(id),
    prod_date     DATE        NOT NULL,
    quantity      INT         NOT NULL,   -- 数量(枚)
    grade         VARCHAR(20) NOT NULL,   -- 品级 -> 字典 EGG_GRADE
    spec          VARCHAR(20) NOT NULL,   -- 规格 -> 字典 EGG_SPEC
    created_time  TIMESTAMP   NOT NULL DEFAULT now(),
    created_by    BIGINT,
    deleted       BOOLEAN     NOT NULL DEFAULT FALSE
);

-- 交割仓 (业务端审批通过后建立, 库存初始化)
CREATE TABLE delivery_warehouse (
    id               BIGSERIAL PRIMARY KEY,
    dw_no            VARCHAR(32)  NOT NULL UNIQUE,   -- 交割仓编号
    warehouse_id     BIGINT       NOT NULL REFERENCES warehouse(id),
    enterprise_id    BIGINT       NOT NULL REFERENCES enterprise(id), -- 货主养殖户
    quantity         INT          NOT NULL,          -- 初始入库数量
    grade            VARCHAR(20)  NOT NULL,
    spec             VARCHAR(20)  NOT NULL,
    price            NUMERIC(14,2),                    -- 上架单价(业务端定价)
    inbound_date     DATE,                                   -- 审批通过建仓时写入
    turnover_days    INT          NOT NULL DEFAULT 3,        -- 周转天数(预警用, F7.1)
    status           VARCHAR(20)  NOT NULL DEFAULT 'AUDITING', -- AUDITING审批中/IN_STOCK在库/APPLYING/SOLD/CLOSED/RETURNED/REJECTED
    created_time     TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time     TIMESTAMP    NOT NULL DEFAULT now(),
    deleted          BOOLEAN      NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_dw_status ON delivery_warehouse(status);

CREATE TABLE inventory (
    id             BIGSERIAL PRIMARY KEY,
    warehouse_id   BIGINT NOT NULL REFERENCES warehouse(id),
    product_id     BIGINT NOT NULL,                        -- -> product.id
    quantity       INT    NOT NULL DEFAULT 0,
    locked_qty     INT    NOT NULL DEFAULT 0,              -- 定金锁定数量 (F4.2)
    version        INT    NOT NULL DEFAULT 0,              -- 乐观锁
    updated_time   TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (warehouse_id, product_id)
);

CREATE TABLE inventory_log (
    id            BIGSERIAL PRIMARY KEY,
    warehouse_id  BIGINT      NOT NULL,
    product_id    BIGINT      NOT NULL,
    change_qty    INT         NOT NULL,     -- 正入负出
    before_qty    INT         NOT NULL,
    after_qty     INT         NOT NULL,
    biz_type      VARCHAR(30) NOT NULL,     -- INIT/IN/OUT/LOCK/UNLOCK/CLOSE_OUT
    biz_id        BIGINT,
    created_time  TIMESTAMP   NOT NULL DEFAULT now(),
    created_by    BIGINT
);

-- -------------------------------------------------------------
-- 七、IoT 监控设备 (F2.2/F9.6)
-- -------------------------------------------------------------
CREATE TABLE iot_device (
    id            BIGSERIAL PRIMARY KEY,
    warehouse_id  BIGINT      NOT NULL REFERENCES warehouse(id),
    device_name   VARCHAR(100),
    device_type   VARCHAR(30) NOT NULL DEFAULT 'CAMERA',
    protocol      VARCHAR(20) NOT NULL DEFAULT 'RTSP',  -- RTSP/GB28181/OTHER
    stream_url    VARCHAR(500),
    online        BOOLEAN     NOT NULL DEFAULT FALSE,
    confirmed     BOOLEAN     NOT NULL DEFAULT FALSE,   -- 确权
    created_time  TIMESTAMP   NOT NULL DEFAULT now(),
    updated_time  TIMESTAMP   NOT NULL DEFAULT now(),
    deleted       BOOLEAN     NOT NULL DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 八、产品与货架 (F4.1)
-- -------------------------------------------------------------
CREATE TABLE product (
    id           BIGSERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL DEFAULT '鸡蛋',
    category     VARCHAR(50),
    grade        VARCHAR(20)  NOT NULL,
    spec         VARCHAR(20)  NOT NULL,
    unit         VARCHAR(10)  NOT NULL DEFAULT '件',
    price        NUMERIC(14,2),          -- 参考单价
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

-- 货架: 交割仓库存自动上架
CREATE TABLE shelf_item (
    id                   BIGSERIAL PRIMARY KEY,
    delivery_warehouse_id BIGINT NOT NULL REFERENCES delivery_warehouse(id),
    product_id           BIGINT       NOT NULL REFERENCES product(id),
    quantity             INT          NOT NULL,
    price                NUMERIC(14,2) NOT NULL,
    source_enterprise_id BIGINT       NOT NULL,   -- 来源养殖户(支持指定/非指定筛选)
    designated           BOOLEAN      NOT NULL DEFAULT FALSE, -- 是否指定客户可见
    status               VARCHAR(10)  NOT NULL DEFAULT 'ON',  -- ON上架/OFF下架
    created_time         TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time         TIMESTAMP    NOT NULL DEFAULT now(),
    deleted              BOOLEAN      NOT NULL DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 九、订单 (F3.1/F4.2/F4.3, 三种模式 F10.1-F10.3)
-- 状态机: CREATE->AUDIT->DEPOSIT_PAID->ADVANCE_PAID->DELIVERING
--         ->TAIL_PAID->RELEASED->FINISHED  (另: CANCEL/CLOSED)
-- -------------------------------------------------------------
CREATE TABLE order_info (
    id               BIGSERIAL PRIMARY KEY,
    order_no         VARCHAR(32)  NOT NULL UNIQUE,
    sale_mode        VARCHAR(10)  NOT NULL,     -- M1蛋库出库标准/M2在途预付/M3渠道账期
    buyer_id         BIGINT       NOT NULL REFERENCES enterprise(id),
    seller_id        BIGINT       NOT NULL REFERENCES enterprise(id),
    self_operated    BOOLEAN      NOT NULL DEFAULT FALSE, -- 是否平台自营单
    designated       BOOLEAN      NOT NULL DEFAULT FALSE, -- 指定/非指定养殖户
    quantity         INT          NOT NULL,
    unit_price       NUMERIC(14,2) NOT NULL,
    total_amount     NUMERIC(14,2) NOT NULL,
    deposit_ratio    NUMERIC(5,4)  NOT NULL DEFAULT 0.20,  -- 定金比例
    deposit_amount   NUMERIC(14,2) NOT NULL,
    advance_ratio    NUMERIC(5,4)  NOT NULL DEFAULT 0.80,  -- 平台垫资比例
    advance_amount   NUMERIC(14,2) NOT NULL,
    platform_profit  NUMERIC(14,2) NOT NULL DEFAULT 0,     -- 模式③内扣分利(如1元/件*数量)
    credit_days      INT,                                   -- 模式③账期天数(如60)
    credit_due_date  DATE,                                  -- 账期到期日
    status           VARCHAR(20)  NOT NULL DEFAULT 'CREATE',
    remark           VARCHAR(500),
    created_time     TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time     TIMESTAMP    NOT NULL DEFAULT now(),
    created_by       BIGINT,
    deleted          BOOLEAN      NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_order_status ON order_info(status);
CREATE INDEX idx_order_buyer  ON order_info(buyer_id);
CREATE INDEX idx_order_seller ON order_info(seller_id);

CREATE TABLE order_item (
    id            BIGSERIAL PRIMARY KEY,
    order_id      BIGINT       NOT NULL REFERENCES order_info(id),
    product_id    BIGINT       NOT NULL REFERENCES product(id),
    delivery_warehouse_id BIGINT REFERENCES delivery_warehouse(id),
    quantity      INT          NOT NULL,
    grade         VARCHAR(20),
    spec          VARCHAR(20),
    unit_price    NUMERIC(14,2) NOT NULL,
    amount        NUMERIC(14,2) NOT NULL,
    created_time  TIMESTAMP    NOT NULL DEFAULT now(),
    deleted       BOOLEAN      NOT NULL DEFAULT FALSE
);

-- 订单状态流转日志
CREATE TABLE order_event (
    id           BIGSERIAL PRIMARY KEY,
    order_id     BIGINT      NOT NULL REFERENCES order_info(id),
    from_status  VARCHAR(20),
    to_status    VARCHAR(20) NOT NULL,
    operator_id  BIGINT,
    remark       VARCHAR(500),
    created_time TIMESTAMP   NOT NULL DEFAULT now()
);

-- -------------------------------------------------------------
-- 十、资金结算 (F6.1/F6.2/F6.4)
-- -------------------------------------------------------------
-- 统一资金流水: 收/付全在这里, 银企直联与人工兜底共用
CREATE TABLE pay_record (
    id            BIGSERIAL PRIMARY KEY,
    pay_no        VARCHAR(32)  NOT NULL UNIQUE,
    order_id      BIGINT       REFERENCES order_info(id),  -- 平仓退款等无订单场景为空
    direction     VARCHAR(10)  NOT NULL,   -- IN收款(客户->平台) / OUT付款(平台->养殖户/退款)
    pay_type      VARCHAR(20)  NOT NULL,   -- DEPOSIT定金/TAIL尾款/ADVANCE垫资80%/SETTLE尾款20%/REFUND退款/CHANNEL_PAY渠道回款
    amount        NUMERIC(14,2) NOT NULL,
    payer_id      BIGINT,                  -- 付款方(企业id, 平台为空)
    payee_id      BIGINT,                  -- 收款方
    channel       VARCHAR(20)  NOT NULL DEFAULT 'MOCK', -- MOCK模拟/WECHAT/ALIPAY/BANK直连/MANUAL人工转账
    status        VARCHAR(20)  NOT NULL DEFAULT 'PENDING', -- PENDING/SUCCESS/FAILED
    voucher_file_id BIGINT,                -- 人工转账回单 -> file_record
    external_no   VARCHAR(64),             -- 第三方/银行流水号
    paid_time     TIMESTAMP,
    created_time  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time  TIMESTAMP    NOT NULL DEFAULT now(),
    created_by    BIGINT,
    deleted       BOOLEAN      NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_pay_order ON pay_record(order_id);

-- 账单中心: 每单一账单, 汇总资金状态
CREATE TABLE finance_bill (
    id            BIGSERIAL PRIMARY KEY,
    bill_no       VARCHAR(32)  NOT NULL UNIQUE,
    order_id      BIGINT       NOT NULL REFERENCES order_info(id),
    enterprise_id BIGINT       NOT NULL,   -- 账单归属方
    amount        NUMERIC(14,2) NOT NULL,
    received      NUMERIC(14,2) NOT NULL DEFAULT 0,
    paid          NUMERIC(14,2) NOT NULL DEFAULT 0,
    bill_status   VARCHAR(20)   NOT NULL DEFAULT 'OPEN', -- OPEN/SETTLING/SETTLED
    created_time  TIMESTAMP     NOT NULL DEFAULT now(),
    updated_time  TIMESTAMP     NOT NULL DEFAULT now(),
    deleted       BOOLEAN       NOT NULL DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 十一、提货交付 (F5.1/F5.2/F5.3)
-- -------------------------------------------------------------
CREATE TABLE outbound_order (
    id            BIGSERIAL PRIMARY KEY,
    outbound_no   VARCHAR(32)  NOT NULL UNIQUE,
    order_id      BIGINT       NOT NULL REFERENCES order_info(id),
    warehouse_id  BIGINT       NOT NULL,
    quantity      INT          NOT NULL,
    grade         VARCHAR(20),
    spec          VARCHAR(20),
    unit_price    NUMERIC(14,2),
    plate_no      VARCHAR(20),             -- 车牌号
    driver_name   VARCHAR(50),
    driver_phone  VARCHAR(20),
    -- 三方确认 (F5.1)
    seller_confirmed   BOOLEAN NOT NULL DEFAULT FALSE,
    buyer_confirmed    BOOLEAN NOT NULL DEFAULT FALSE,
    platform_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    status        VARCHAR(20)  NOT NULL DEFAULT 'DRAFT', -- DRAFT/CONFIRMED/RELEASED
    created_time  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time  TIMESTAMP    NOT NULL DEFAULT now(),
    created_by    BIGINT,
    deleted       BOOLEAN      NOT NULL DEFAULT FALSE
);

-- 出库单附件: 装车照片/视频(带水印)
CREATE TABLE outbound_file (
    id           BIGSERIAL PRIMARY KEY,
    outbound_id  BIGINT      NOT NULL REFERENCES outbound_order(id),
    file_id      BIGINT      NOT NULL REFERENCES file_record(id),
    media_type   VARCHAR(10) NOT NULL,     -- PHOTO/VIDEO
    watermarked  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_time TIMESTAMP   NOT NULL DEFAULT now(),
    deleted      BOOLEAN     NOT NULL DEFAULT FALSE
);

-- 电子提货凭证(核销二维码) —— 出库放行唯一凭证 (F5.3)
CREATE TABLE pickup_voucher (
    id           BIGSERIAL PRIMARY KEY,
    voucher_no   VARCHAR(32)  NOT NULL UNIQUE,
    order_id     BIGINT       NOT NULL REFERENCES order_info(id),
    outbound_id  BIGINT       REFERENCES outbound_order(id),
    qr_payload   VARCHAR(255) NOT NULL,    -- 二维码内容(签名防伪造)
    status       VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE', -- ACTIVE/USED/EXPIRED
    verified_by  BIGINT,                   -- 核销人(养殖户)
    verified_time TIMESTAMP,
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 十二、电子合同与发票 (F1.5/F3.2/F6.3/F9.3/F9.4)
-- -------------------------------------------------------------
CREATE TABLE contract_template (
    id           BIGSERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    type         VARCHAR(30)  NOT NULL,   -- SETTLE入驻合同/SALE销售合同
    file_id      BIGINT,                  -- 模板文件
    status       INT          NOT NULL DEFAULT 1,
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE contract (
    id           BIGSERIAL PRIMARY KEY,
    contract_no  VARCHAR(32)  NOT NULL UNIQUE,
    type         VARCHAR(30)  NOT NULL,   -- SETTLE(仅首次入驻)/SALE
    order_id     BIGINT,                  -- 销售合同关联订单
    party_a_id   BIGINT       NOT NULL,   -- 甲方(企业id)
    party_b_id   BIGINT       NOT NULL,
    file_id      BIGINT,                  -- 已签章文件 -> file_record
    sign_status  VARCHAR(20)  NOT NULL DEFAULT 'DRAFT', -- DRAFT/SIGNING/SIGNED/ARCHIVED
    party_a_signed BOOLEAN    NOT NULL DEFAULT FALSE,
    party_a_time  TIMESTAMP,
    party_b_signed BOOLEAN    NOT NULL DEFAULT FALSE,
    party_b_time  TIMESTAMP,
    esign_flow_id VARCHAR(64),            -- 第三方签署流程号(接入e签宝后使用)
    signed_time  TIMESTAMP,
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE invoice (
    id           BIGSERIAL PRIMARY KEY,
    invoice_no   VARCHAR(50),
    order_id     BIGINT       NOT NULL,
    bill_id      BIGINT,
    type         VARCHAR(20)  NOT NULL DEFAULT 'VAT', -- VAT增值税专/普票
    amount       NUMERIC(14,2) NOT NULL,
    buyer_title  VARCHAR(100),            -- 抬头
    tax_no       VARCHAR(30),
    status       VARCHAR(20)  NOT NULL DEFAULT 'APPLY', -- APPLY申请/AUDITING审批/ISSUED已开/ARCHIVED归档
    file_id      BIGINT,
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 十三、风控与平仓 (F1.3/F7.1-F7.4)
-- -------------------------------------------------------------
-- 渠道方风控尽调 (F1.3)
CREATE TABLE risk_survey (
    id            BIGSERIAL PRIMARY KEY,
    enterprise_id BIGINT       NOT NULL REFERENCES enterprise(id), -- 渠道方
    report_file_id BIGINT,                 -- 《企业基本信息表及评价报告》
    conclusion    VARCHAR(10)  NOT NULL DEFAULT 'WAIT', -- WAIT/PASS/REJECT
    remark        VARCHAR(500),
    created_time  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time  TIMESTAMP    NOT NULL DEFAULT now(),
    created_by    BIGINT,
    deleted       BOOLEAN      NOT NULL DEFAULT FALSE
);

-- 养殖端5类申请 (F7.2)
CREATE TABLE close_apply (
    id                   BIGSERIAL PRIMARY KEY,
    delivery_warehouse_id BIGINT      NOT NULL REFERENCES delivery_warehouse(id),
    apply_type           VARCHAR(30)  NOT NULL,  -- RETURN退仓/SELF_SALE_DESIGNATED平台自销指定/SELF_SALE_OPEN平台自销非指定/SALE_TO_PLATFORM销售给平台/OVERDUE_HANDLE超期处理
    status               VARCHAR(20)  NOT NULL DEFAULT 'WAIT', -- WAIT/PASS/REJECT/DONE
    remark               VARCHAR(500),
    created_time         TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time         TIMESTAMP    NOT NULL DEFAULT now(),
    created_by           BIGINT,
    deleted              BOOLEAN      NOT NULL DEFAULT FALSE
);

-- 强制平仓与折价处置 (F7.3)
CREATE TABLE close_order (
    id                   BIGSERIAL PRIMARY KEY,
    close_no             VARCHAR(32)   NOT NULL UNIQUE,
    delivery_warehouse_id BIGINT       NOT NULL REFERENCES delivery_warehouse(id),
    close_type           VARCHAR(20)   NOT NULL,  -- FORCE强制平仓/APPLY申请平仓
    discount_ratio       NUMERIC(5,4)  NOT NULL DEFAULT 0.80, -- 折价处置(20%折价=按80%计价)
    quantity             INT           NOT NULL,
    original_amount      NUMERIC(14,2) NOT NULL,
    settle_amount        NUMERIC(14,2) NOT NULL,  -- 折价后结算金额
    profit_loss          NUMERIC(14,2),           -- 平仓盈亏(系统自动核算, F7.4)
    status               VARCHAR(20)   NOT NULL DEFAULT 'PENDING', -- PENDING/CONFIRMED/REFUNDED
    created_time         TIMESTAMP     NOT NULL DEFAULT now(),
    updated_time         TIMESTAMP     NOT NULL DEFAULT now(),
    created_by           BIGINT,
    deleted              BOOLEAN       NOT NULL DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 十四、对账中心 (F8.1/F8.2)
-- -------------------------------------------------------------
CREATE TABLE reconcile_batch (
    id           BIGSERIAL PRIMARY KEY,
    batch_no     VARCHAR(32)  NOT NULL UNIQUE,
    scope        VARCHAR(20)  NOT NULL,      -- DELIVERY交割仓业务/SELF自营业务
    period_start DATE         NOT NULL,
    period_end   DATE         NOT NULL,
    total_count  INT          NOT NULL DEFAULT 0,
    matched      INT          NOT NULL DEFAULT 0,
    diff_count   INT          NOT NULL DEFAULT 0,
    status       VARCHAR(20)  NOT NULL DEFAULT 'RUNNING', -- RUNNING/CONFIRMED/ARCHIVED
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE reconcile_diff (
    id            BIGSERIAL PRIMARY KEY,
    batch_id      BIGINT       NOT NULL REFERENCES reconcile_batch(id),
    biz_type      VARCHAR(30)  NOT NULL,     -- ORDER/PAY/OUTBOUND/BILL/BANK_FLOW
    biz_id        BIGINT       NOT NULL,
    diff_desc     VARCHAR(500) NOT NULL,
    adjust_amount NUMERIC(14,2),             -- 调账金额
    adjust_reason VARCHAR(500),              -- 调账原因(留痕, F8.1)
    adjusted_by   BIGINT,
    adjusted_time TIMESTAMP,
    status        VARCHAR(20)  NOT NULL DEFAULT 'OPEN', -- OPEN/ADJUSTED
    created_time  TIMESTAMP    NOT NULL DEFAULT now(),
    deleted       BOOLEAN      NOT NULL DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 十五、物流 (F9.8/F9.9)
-- -------------------------------------------------------------
CREATE TABLE logistics_order (
    id            BIGSERIAL PRIMARY KEY,
    order_id      BIGINT       NOT NULL REFERENCES order_info(id),
    platform      VARCHAR(20)  NOT NULL DEFAULT 'YMM',  -- YMM运满满/MANUAL人工
    waybill_no    VARCHAR(64),                          -- 运单号
    driver_name   VARCHAR(50),
    driver_phone  VARCHAR(20),
    plate_no      VARCHAR(20),
    status        VARCHAR(20)  NOT NULL DEFAULT 'CALLED', -- CALLED已叫车/LOADED已装车/IN_TRANSIT在途/ARRIVED已到达
    created_time  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time  TIMESTAMP    NOT NULL DEFAULT now(),
    deleted       BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE logistics_track (
    id           BIGSERIAL PRIMARY KEY,
    logistics_id BIGINT        NOT NULL REFERENCES logistics_order(id),
    longitude    NUMERIC(10,6),
    latitude     NUMERIC(10,6),
    address      VARCHAR(255),
    track_time   TIMESTAMP     NOT NULL,
    created_time TIMESTAMP     NOT NULL DEFAULT now()
);

-- -------------------------------------------------------------
-- 十六、消息通知 (F9.5)
-- -------------------------------------------------------------
CREATE TABLE message (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT       NOT NULL,     -- 接收人
    type         VARCHAR(30)  NOT NULL,     -- ADVANCE_PAID垫资到账/CLOSE_WARNING平仓预警/APPROVAL审批/ORDER_STATUS订单状态
    title        VARCHAR(200) NOT NULL,
    content      TEXT,
    biz_type     VARCHAR(50),
    biz_id       BIGINT,
    read_flag    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_time TIMESTAMP    NOT NULL DEFAULT now(),
    deleted      BOOLEAN      NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_message_user ON message(user_id, read_flag);

-- -------------------------------------------------------------
-- 十七、激励规则 (F10.4)
-- -------------------------------------------------------------
CREATE TABLE incentive_record (
    id            BIGSERIAL PRIMARY KEY,
    enterprise_id BIGINT       NOT NULL REFERENCES enterprise(id),
    rule_desc     VARCHAR(255) NOT NULL DEFAULT '合作满6个月且发货量达每满10万只鸡规模',
    coop_months   INT          NOT NULL DEFAULT 0,
    chicken_scale INT          NOT NULL DEFAULT 0,   -- 累计发货对应鸡规模(万只)
    qualified     BOOLEAN      NOT NULL DEFAULT FALSE,
    promise_file_id BIGINT,                          -- 平台承诺书
    status        VARCHAR(20)  NOT NULL DEFAULT 'TRACKING', -- TRACKING/QUALIFIED/GRANTED已赠送
    created_time  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_time  TIMESTAMP    NOT NULL DEFAULT now(),
    deleted       BOOLEAN      NOT NULL DEFAULT FALSE
);

-- =============================================================
-- 种子数据: 角色 / 字典
-- (管理员账号由后端首次启动时创建, 见 backend 启动逻辑)
-- =============================================================
INSERT INTO sys_role (code, name, remark) VALUES
    ('FARM',     '养殖企业', '养殖端'),
    ('CUSTOMER', '客户',     '采购客户端'),
    ('BUSINESS', '业务人员', '业务端'),
    ('FINANCE',  '财务人员', '财务端'),
    ('ADMIN',    '管理员',   '管理后台');

INSERT INTO sys_dict_type (code, name) VALUES
    ('EGG_GRADE', '鸡蛋品级'),
    ('EGG_SPEC',  '鸡蛋规格');

INSERT INTO sys_dict_item (type_id, code, name, sort)
SELECT t.id, v.code, v.name, v.sort
FROM sys_dict_type t
JOIN (VALUES
    ('EGG_GRADE', 'A',  'A级', 1),
    ('EGG_GRADE', 'B',  'B级', 2),
    ('EGG_GRADE', 'C',  'C级', 3),
    ('EGG_SPEC',  'S50', '50kg/件', 1),
    ('EGG_SPEC',  'S45', '45kg/件', 2),
    ('EGG_SPEC',  'S40', '40kg/件', 3)
) AS v(tcode, code, name, sort) ON t.code = v.tcode;
