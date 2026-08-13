// 状态字典(前端展示用), 与后端状态机保持一致
export type TagType = 'success' | 'warning' | 'danger' | 'info'

export const AUDIT_STATUS_TEXT: Record<string, string> = { WAIT: '审核中', PASS: '已通过', REJECT: '已驳回' }
export const AUDIT_STATUS_TAG: Record<string, TagType> = { WAIT: 'warning', PASS: 'success', REJECT: 'danger' }

export const INSTANCE_STATUS_TEXT: Record<string, string> = { RUNNING: '审批中', PASS: '已通过', REJECT: '已驳回', CANCEL: '已撤销' }
export const INSTANCE_STATUS_TAG: Record<string, TagType> = { RUNNING: 'warning', PASS: 'success', REJECT: 'danger', CANCEL: 'info' }
