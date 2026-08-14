import request from './request'

export const getTodoApprovals = () => request.get('/workflow/todo')
export const handleApproval = (taskId: number, action: 'PASS' | 'REJECT', opinion: string) =>
  request.post(`/workflow/tasks/${taskId}/handle`, { action, opinion })
export const getMyApprovals = () => request.get('/workflow/mine')

export const getMyEnterprise = () => request.get('/enterprise/my')
export const getEnterpriseList = (params?: Record<string, string>) =>
  request.get('/enterprise/list', { params })

export const getDict = (typeCode: string) => request.get(`/common/dict/${typeCode}`)
export const getConfigs = () => request.get('/common/config')
export const updateConfig = (key: string, value: string) => request.put(`/common/config/${key}`, { value })

export const uploadFile = (file: File, bizType: string, token?: string) => {
  const form = new FormData()
  form.append('file', file)
  return request.post(`/file/upload?biz_type=${bizType}`, form, {
    headers: { 'Content-Type': 'multipart/form-data', ...(token ? { Authorization: `Bearer ${token}` } : {}) }
  })
}

// ---------- M2: 仓库 / 产蛋 / 交割仓 / IoT / 库存 ----------
export const createWarehouse = (data: { name: string; address: string; capacity?: number }) =>
  request.post('/warehouse', data)
export const getMyWarehouses = () => request.get('/warehouse/my')
export const getWarehouseList = () => request.get('/warehouse/list')
export const leaseApply = (warehouseId: number, rent_amount: number) =>
  request.post(`/warehouse/${warehouseId}/lease-apply`, { rent_amount })

export const createProduction = (data: { prod_date: string; quantity: number; grade: string; spec: string }) =>
  request.post('/production', data)
export const getMyProduction = () => request.get('/production/my')
export const getProductionList = () => request.get('/production/list')

export const dwApply = (data: { warehouse_id: number; quantity: number; grade: string; spec: string }) =>
  request.post('/warehouse/delivery/apply', data)
export const getDwList = () => request.get('/warehouse/delivery/list')

export const createDevice = (data: { warehouse_id: number; device_name: string; protocol: string; stream_url: string }) =>
  request.post('/iot/devices', data)
export const getDevices = (warehouseId?: number) =>
  request.get('/iot/devices', { params: warehouseId ? { warehouse_id: warehouseId } : {} })
export const checkDevice = (deviceId: number) => request.post(`/iot/devices/${deviceId}/check`)
export const confirmDevice = (deviceId: number) => request.post(`/iot/devices/${deviceId}/confirm`)
export const uploadPointMap = (warehouseId: number, fileId: number) =>
  request.post(`/iot/warehouses/${warehouseId}/point-map`, { file_id: fileId })

export const getInventoryList = () => request.get('/inventory/list')

// ---------- M3: 货架 / 订单 / 资金 / 交付 ----------
export const getShelfList = (params?: Record<string, unknown>) => request.get('/shelf/list', { params })
export const getShelfManage = () => request.get('/shelf/manage')
export const setShelfPrice = (id: number, price: number) => request.put(`/shelf/${id}/price`, { price })
export const setShelfStatus = (id: number, status: 'ON' | 'OFF') => request.put(`/shelf/${id}/status`, { status })

export const createPurchase = (data: { shelf_item_id: number; quantity: number; sale_mode: string; credit_days?: number; designated?: boolean }) =>
  request.post('/orders/purchase', data)
export const getOrderList = (status?: string) => request.get('/orders/list', { params: status ? { status } : {} })
export const getOrderDetail = (id: number) => request.get(`/orders/${id}`)
export const cancelOrder = (id: number) => request.post(`/orders/${id}/cancel`)
export const dwSaleApply = (dwId: number) => request.post(`/warehouse/delivery/${dwId}/sale-apply`)

export const pay = (orderId: number, payType: 'DEPOSIT' | 'TAIL') => request.post('/finance/pay', { order_id: orderId, pay_type: payType })
export const getPayRecords = (orderId?: number) => request.get('/finance/records', { params: orderId ? { order_id: orderId } : {} })
export const getBills = () => request.get('/finance/bills')

export const createOutbound = (data: { order_id: number; plate_no: string; driver_name: string; driver_phone: string }) =>
  request.post('/delivery/outbound', data)
export const getOutboundByOrder = (orderId: number) => request.get(`/delivery/outbound/by-order/${orderId}`)
export const addOutboundFile = (outboundId: number, fileId: number, mediaType: 'PHOTO' | 'VIDEO') =>
  request.post(`/delivery/outbound/${outboundId}/files`, { file_id: fileId, media_type: mediaType })
export const confirmOutbound = (outboundId: number, side: 'seller' | 'buyer' | 'platform') =>
  request.post(`/delivery/outbound/${outboundId}/confirm/${side}`)
export const getVoucher = (orderId: number) => request.get(`/delivery/voucher/by-order/${orderId}`)
export const verifyVoucher = (qrPayload: string) => request.post('/delivery/verify', { qr_payload: qrPayload })

// ---------- M4: 合同 / 发票 / 人工付款 ----------
export const getContractList = () => request.get('/contract/list')
export const getContract = (id: number) => request.get(`/contract/${id}`)
export const signContract = (id: number) => request.post(`/contract/${id}/sign`)
export const archiveContract = (id: number) => request.post(`/contract/${id}/archive`)

export const applyInvoice = (data: { order_id: number; buyer_title: string; tax_no: string }) =>
  request.post('/invoice/apply', data)
export const getInvoiceList = () => request.get('/invoice/list')
export const archiveInvoice = (id: number) => request.post(`/invoice/${id}/archive`)
export const checkInvoice = (invoiceNo: string) => request.get(`/invoice/check/${invoiceNo}`)

export const confirmManualPay = (recordId: number, voucherFileId: number) =>
  request.post(`/finance/records/${recordId}/confirm-manual`, { voucher_file_id: voucherFileId })

// ---------- M5: 风控 / 对账 / 看板 / 物流 / 激励 ----------
export const checkWarnings = () => request.post('/risk/check-warnings')
export const createCloseApply = (data: { delivery_warehouse_id: number; apply_type: string; remark: string }) =>
  request.post('/risk/apply', data)
export const getCloseApplies = () => request.get('/risk/apply/list')
export const forceClose = (dwId: number) => request.post(`/risk/force-close/${dwId}`)
export const getCloseList = () => request.get('/risk/close/list')
export const createSurvey = (data: { enterprise_id: number; conclusion: string; remark: string; report_file_id?: number }) =>
  request.post('/risk/survey', data)
export const getSurveyList = () => request.get('/risk/survey/list')

export const runReconcile = (data: { scope: string; period_start: string; period_end: string }) =>
  request.post('/reconcile/run', data)
export const getReconcileBatches = () => request.get('/reconcile/batches')
export const getReconcileDiffs = (batchId: number) => request.get('/reconcile/diffs', { params: { batch_id: batchId } })
export const adjustDiff = (diffId: number, amount: number, reason: string) =>
  request.post(`/reconcile/diffs/${diffId}/adjust`, { amount, reason })
export const archiveReconcileBatch = (batchId: number) => request.post(`/reconcile/batches/${batchId}/archive`)

export const getDashboardSummary = () => request.get('/dashboard/summary')
export const exportReport = () => request.get('/dashboard/export', { responseType: 'blob' })

export const createLogistics = (data: { order_id: number; waybill_no: string; driver_name: string; driver_phone: string; plate_no: string }) =>
  request.post('/logistics/create', data)
export const getLogisticsByOrder = (orderId: number) => request.get(`/logistics/by-order/${orderId}`)
export const addTrack = (logisticsId: number, address: string) =>
  request.post(`/logistics/${logisticsId}/track`, { address })

export const getIncentiveList = () => request.get('/incentive/list')
export const grantIncentive = (enterpriseId: number, promiseFileId?: number) =>
  request.post('/incentive/grant', { enterprise_id: enterpriseId, promise_file_id: promiseFileId })

// ---------- 站内信 ----------
export const getMessages = (unreadOnly = false) =>
  request.get('/message/list', { params: unreadOnly ? { unread_only: true } : {} })
export const getUnreadCount = () => request.get('/message/unread-count')
export const markMessageRead = (id: number) => request.post(`/message/${id}/read`)
