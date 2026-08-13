import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '../store/user'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { public: true, title: '登录' } },
  { path: '/register', name: 'Register', component: () => import('../views/Register.vue'), meta: { public: true, title: '注册' } },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '首页' } },
      { path: 'enterprise/my', component: () => import('../views/enterprise/MyEnterprise.vue'), meta: { title: '我的企业', roles: ['FARM', 'CUSTOMER'] } },
      { path: 'enterprise/list', component: () => import('../views/enterprise/List.vue'), meta: { title: '合作方管理', roles: ['BUSINESS'] } },
      { path: 'approval/todo', component: () => import('../views/approval/Todo.vue'), meta: { title: '审批中心', roles: ['BUSINESS', 'FINANCE'] } },
      { path: 'approval/mine', component: () => import('../views/approval/Mine.vue'), meta: { title: '我的申请' } },
      { path: 'system/config', component: () => import('../views/system/Config.vue'), meta: { title: '参数配置', roles: ['ADMIN'] } }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  document.title = `蛋品交易平台${to.meta.title ? ' - ' + String(to.meta.title) : ''}`
  const store = useUserStore()
  if (to.meta.public) return true
  if (!store.isLoggedIn) return { path: '/login', query: { redirect: to.fullPath } }
  const need = to.meta.roles as string[] | undefined
  if (need && !store.hasRole(...need)) return { path: '/dashboard' }
  return true
})

export default router
