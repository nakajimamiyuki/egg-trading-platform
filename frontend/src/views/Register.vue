<template>
  <div class="register-page">
    <el-card class="box">
      <h2>企业自助注册</h2>
      <el-form :model="form" label-width="110px">
        <el-form-item label="企业类型" required>
          <el-radio-group v-model="form.enterprise_type">
            <el-radio-button value="FARM">养殖企业</el-radio-button>
            <el-radio-button value="BUYER">采购商</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-divider content-position="left">账号信息</el-divider>
        <el-form-item label="用户名" required><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="密码" required><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item label="联系人" required><el-input v-model="form.real_name" /></el-form-item>
        <el-form-item label="手机号" required><el-input v-model="form.phone" /></el-form-item>
        <el-divider content-position="left">企业信息</el-divider>
        <el-form-item label="企业名称" required><el-input v-model="form.enterprise_name" /></el-form-item>
        <el-form-item label="信用代码"><el-input v-model="form.license_no" placeholder="统一社会信用代码" /></el-form-item>
        <el-form-item label="法人代表"><el-input v-model="form.legal_person" /></el-form-item>
        <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
        <template v-if="form.enterprise_type === 'FARM'">
          <el-divider content-position="left">养殖信息</el-divider>
          <el-form-item label="养殖品种"><el-input v-model="form.breed" placeholder="如: 海兰褐" /></el-form-item>
          <el-form-item label="存栏量(只)"><el-input-number v-model="form.stock_qty" :min="0" /></el-form-item>
          <el-form-item label="日龄(天)"><el-input-number v-model="form.day_age" :min="0" /></el-form-item>
          <el-form-item label="日均产蛋(枚)"><el-input-number v-model="form.daily_egg_qty" :min="0" /></el-form-item>
        </template>
        <el-divider content-position="left">证照上传（扫描件加盖公章）</el-divider>
        <el-form-item v-for="ft in fileTypes" :key="ft.value" :label="ft.label">
          <input type="file" @change="(e) => onFileChange(e, ft.value)" />
          <span v-if="uploaded[ft.value]" class="ok"> ✓ 已上传</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onSubmit">提交注册（待平台审核）</el-button>
          <el-button @click="$router.push('/login')">返回登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { register } from '../api/auth'
import { uploadFile } from '../api/biz'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  enterprise_type: 'FARM', username: '', password: '', real_name: '', phone: '',
  enterprise_name: '', license_no: '', legal_person: '', address: '',
  breed: '', stock_qty: 0, day_age: 0, daily_egg_qty: 0
})
const uploaded = reactive<Record<string, number>>({})

const fileTypes = computed(() =>
  form.enterprise_type === 'FARM'
    ? [
        { value: 'LICENSE', label: '营业执照' },
        { value: 'ID_CARD', label: '法人身份证' },
        { value: 'BREEDING_PERMIT', label: '养殖许可证' },
        { value: 'PROVENANCE', label: '引种证明' }
      ]
    : [
        { value: 'LICENSE', label: '营业执照' },
        { value: 'ID_CARD', label: '法人身份证' }
      ]
)

async function onFileChange(e: Event, fileType: string) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const resp = (await uploadFile(file, 'ENTERPRISE_FILE')) as { file_id: number }
  uploaded[fileType] = resp.file_id
  ElMessage.success('上传成功')
}

async function onSubmit() {
  if (!form.username || !form.password || !form.enterprise_name || !form.real_name || !form.phone) {
    return ElMessage.warning('请填写带 * 的必填项')
  }
  loading.value = true
  try {
    const files = Object.entries(uploaded).map(([file_type, file_id]) => ({ file_type, file_id }))
    await register({ ...form, files })
    ElMessage.success('注册成功，请等待平台审核')
    router.push('/login')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page { display: flex; justify-content: center; padding: 40px 0; }
.box { width: 640px; }
h2 { text-align: center; margin-top: 0; }
.ok { color: #67c23a; }
</style>
