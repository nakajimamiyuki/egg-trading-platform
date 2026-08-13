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
