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
