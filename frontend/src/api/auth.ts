import request from './request'

export interface LoginResp {
  token: string
  user_id: number
  real_name: string
  roles: string[]
}

export const login = (username: string, password: string) =>
  request.post('/auth/login', { username, password }) as Promise<LoginResp>

export const getMe = () => request.get('/auth/me')

export const register = (data: Record<string, unknown>) => request.post('/auth/register', data)
