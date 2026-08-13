import { defineStore } from 'pinia'

interface UserState {
  token: string
  userId: number | null
  realName: string
  roles: string[]
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    token: localStorage.getItem('token') ?? '',
    userId: Number(localStorage.getItem('user_id')) || null,
    realName: localStorage.getItem('real_name') ?? '',
    roles: JSON.parse(localStorage.getItem('roles') ?? '[]')
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    hasRole: (s) => (...roles: string[]) => s.roles.includes('ADMIN') || roles.some((r) => s.roles.includes(r))
  },
  actions: {
    setLogin(token: string, userId: number, realName: string, roles: string[]) {
      this.token = token
      this.userId = userId
      this.realName = realName
      this.roles = roles
      localStorage.setItem('token', token)
      localStorage.setItem('user_id', String(userId))
      localStorage.setItem('real_name', realName)
      localStorage.setItem('roles', JSON.stringify(roles))
    },
    logout() {
      this.$reset()
      ;['token', 'user_id', 'real_name', 'roles'].forEach((k) => localStorage.removeItem(k))
    }
  }
})
