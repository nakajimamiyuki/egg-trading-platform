<template>
  <div class="login-page">
    <el-card class="box">
      <h2>🥚 蛋品交易平台</h2>
      <el-form :model="form" @keyup.enter="onLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="onLogin">登 录</el-button>
        <div class="links">
          <router-link to="/register">没有账号？企业自助注册</router-link>
        </div>
      </el-form>
      <el-divider />
      <div class="demo">
        演示账号：admin/admin123（管理员）· business01/123456（业务）· finance01/123456（财务）
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api/auth'
import { useUserStore } from '../store/user'

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const router = useRouter()
const route = useRoute()
const store = useUserStore()

async function onLogin() {
  if (!form.username || !form.password) return ElMessage.warning('请输入用户名和密码')
  loading.value = true
  try {
    const resp = await login(form.username, form.password)
    store.setLogin(resp.token, resp.user_id, resp.real_name, resp.roles)
    ElMessage.success('登录成功')
    router.push((route.query.redirect as string) || '/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { display: flex; justify-content: center; padding-top: 120px; }
.box { width: 400px; }
h2 { text-align: center; margin-top: 0; }
.links { text-align: right; margin-top: 12px; }
.demo { font-size: 12px; color: #909399; text-align: center; }
</style>
