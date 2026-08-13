<template>
  <el-container class="layout">
    <el-aside width="220px">
      <div class="logo">🥚 蛋品交易平台</div>
      <el-menu :default-active="$route.path" router background-color="#001529" text-color="#ffffffa6" active-text-color="#fff">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">{{ m.title }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>{{ roleLabel }}端</span>
        <el-dropdown @command="(c: string) => c === 'logout' && onLogout()">
          <span class="user">{{ store.realName }} ▾</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'

const store = useUserStore()
const router = useRouter()

const ALL_MENUS = [
  { path: '/dashboard', title: '首页', roles: ['FARM', 'CUSTOMER', 'BUSINESS', 'FINANCE', 'ADMIN'] },
  { path: '/enterprise/my', title: '我的企业', roles: ['FARM', 'CUSTOMER'] },
  { path: '/shelf/hall', title: '商品大厅', roles: ['CUSTOMER', 'BUSINESS'] },
  { path: '/order/list', title: '订单管理', roles: ['FARM', 'CUSTOMER', 'BUSINESS', 'FINANCE'] },
  { path: '/finance/bills', title: '账单中心', roles: ['FARM', 'CUSTOMER', 'BUSINESS', 'FINANCE'] },
  { path: '/contract/list', title: '合同管理', roles: ['FARM', 'CUSTOMER', 'BUSINESS', 'FINANCE', 'ADMIN'] },
  { path: '/finance/invoices', title: '发票管理', roles: ['CUSTOMER', 'FINANCE'] },
  { path: '/finance/manual-pay', title: '付款执行', roles: ['FINANCE'] },
  { path: '/risk/center', title: '平仓风控', roles: ['FARM', 'BUSINESS', 'FINANCE'] },
  { path: '/risk/survey', title: '渠道尽调', roles: ['BUSINESS', 'FINANCE'] },
  { path: '/reconcile/center', title: '对账中心', roles: ['BUSINESS', 'FINANCE'] },
  { path: '/dashboard/board', title: '数据看板', roles: ['BUSINESS', 'FINANCE'] },
  { path: '/incentive/list', title: '合作激励', roles: ['FARM', 'BUSINESS'] },
  { path: '/warehouse/my', title: '我的仓库', roles: ['FARM'] },
  { path: '/warehouse/production', title: '产蛋录入', roles: ['FARM'] },
  { path: '/warehouse/delivery', title: '交割仓一览', roles: ['FARM', 'BUSINESS', 'FINANCE'] },
  { path: '/warehouse/inventory', title: '库存查询', roles: ['FARM', 'BUSINESS', 'FINANCE'] },
  { path: '/approval/mine', title: '我的申请', roles: ['FARM', 'CUSTOMER', 'BUSINESS'] },
  { path: '/approval/todo', title: '审批中心', roles: ['BUSINESS', 'FINANCE'] },
  { path: '/enterprise/list', title: '合作方管理', roles: ['BUSINESS'] },
  { path: '/shelf/manage', title: '货架管理', roles: ['BUSINESS'] },
  { path: '/warehouse/list', title: '仓库管理', roles: ['BUSINESS'] },
  { path: '/system/config', title: '参数配置', roles: ['ADMIN'] }
]

const menus = computed(() => ALL_MENUS.filter((m) => store.hasRole(...m.roles)))

const roleLabel = computed(() => {
  const map: Record<string, string> = { FARM: '养殖', CUSTOMER: '客户', BUSINESS: '业务', FINANCE: '财务', ADMIN: '管理' }
  return map[store.roles[0]] ?? ''
})

function onLogout() {
  store.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout { height: 100vh; }
.el-aside { background: #001529; }
.logo { color: #fff; text-align: center; padding: 18px 0; font-weight: bold; }
.el-menu { border-right: none; }
.header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; }
.user { cursor: pointer; color: #409eff; }
</style>
