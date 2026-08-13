import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'

// 统一封装: Token 自动注入 + 统一错误处理 (对应开发文档要求)
const instance = axios.create({
  baseURL: '/api/v1',
  timeout: 15000
})

instance.interceptors.request.use((config) => {
  const store = useUserStore()
  if (store.token) {
    config.headers.Authorization = `Bearer ${store.token}`
  }
  return config
})

instance.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      ElMessage.error(body.message ?? '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return body
  },
  (error) => {
    ElMessage.error(error.message ?? '网络异常')
    return Promise.reject(error)
  }
)

// 响应拦截器已解包统一返回格式, 这里用宽松类型导出避免 AxiosResponse 类型噪音
const request = instance as unknown as {
  get<T = any>(url: string, config?: any): Promise<T>
  post<T = any>(url: string, data?: any, config?: any): Promise<T>
  put<T = any>(url: string, data?: any, config?: any): Promise<T>
  delete<T = any>(url: string, config?: any): Promise<T>
}

export default request
