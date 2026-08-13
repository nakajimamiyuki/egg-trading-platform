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
      { path: 'warehouse/my', component: () => import('../views/warehouse/MyWarehouse.vue'), meta: { title: '我的仓库', roles: ['FARM'] } },
      { path: 'warehouse/production', component: () => import('../views/warehouse/Production.vue'), meta: { title: '产蛋录入', roles: ['FARM'] } },
      { path: 'warehouse/list', component: () => import('../views/warehouse/WarehouseList.vue'), meta: { title: '仓库管理', roles: ['BUSINESS'] } },
      { path: 'warehouse/delivery', component: () => import('../views/warehouse/DeliveryList.vue'), meta: { title: '交割仓一览', roles: ['FARM', 'BUSINESS', 'FINANCE'] } },
      { path: 'warehouse/inventory', component: () => import('../views/warehouse/InventoryList.vue'), meta: { title: '库存查询', roles: ['FARM', 'BUSINESS', 'FINANCE'] } },
      { path: 'shelf/hall', component: () => import('../views/shelf/Hall.vue'), meta: { title: '商品大厅', roles: ['CUSTOMER', 'BUSINESS'] } },
      { path: 'shelf/manage', component: () => import('../views/shelf/Manage.vue'), meta: { title: '货架管理', roles: ['BUSINESS'] } },
      { path: 'order/list', component: () => import('../views/order/List.vue'), meta: { title: '订单管理' } },
      { path: 'order/detail/:id', component: () => import('../views/order/Detail.vue'), meta: { title: '订单详情' } },
      { path: 'finance/bills', component: () => import('../views/finance/Bills.vue'), meta: { title: '账单中心' } },
      { path: 'finance/invoices', component: () => import('../views/finance/Invoices.vue'), meta: { title: '发票管理', roles: ['CUSTOMER', 'FINANCE'] } },
      { path: 'finance/manual-pay', component: () => import('../views/finance/ManualPay.vue'), meta: { title: '付款执行', roles: ['FINANCE'] } },
      { path: 'contract/list', component: () => import('../views/contract/List.vue'), meta: { title: '合同管理' } },
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
