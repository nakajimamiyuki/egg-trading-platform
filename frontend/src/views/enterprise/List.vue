<template>
  <el-card>
    <template #header>
      <div class="head">
        <span>合作方管理</span>
        <div>
          <el-select v-model="filterType" clearable placeholder="类型" style="width: 130px; margin-right: 8px" @change="load">
            <el-option label="养殖企业" value="FARM" />
            <el-option label="采购商" value="BUYER" />
          </el-select>
          <el-select v-model="filterStatus" clearable placeholder="状态" style="width: 130px" @change="load">
            <el-option label="审核中" value="WAIT" />
            <el-option label="已通过" value="PASS" />
            <el-option label="已驳回" value="REJECT" />
          </el-select>
        </div>
      </div>
    </template>
    <el-table :data="list" border>
      <el-table-column prop="enterprise_name" label="企业名称" min-width="160" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">{{ row.type === 'FARM' ? '养殖企业' : '采购商' }}</template>
      </el-table-column>
      <el-table-column prop="legal_person" label="法人" width="100" />
      <el-table-column prop="contact_phone" label="电话" width="130" />
      <el-table-column prop="stock_qty" label="存栏量" width="100" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="AUDIT_STATUS_TAG[row.audit_status]">{{ AUDIT_STATUS_TEXT[row.audit_status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_time" label="注册时间" width="170" :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getEnterpriseList } from '../../api/biz'
import { AUDIT_STATUS_TAG, AUDIT_STATUS_TEXT } from '../../utils/status'

const list = ref<any[]>([])
const filterType = ref('')
const filterStatus = ref('')

async function load() {
  const params: Record<string, string> = {}
  if (filterType.value) params.type = filterType.value
  if (filterStatus.value) params.audit_status = filterStatus.value
  list.value = await getEnterpriseList(params)
}
onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
