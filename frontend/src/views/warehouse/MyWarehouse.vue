<template>
  <el-card>
    <template #header>
      <div class="head">
        <span>我的仓库</span>
        <el-button type="primary" @click="showCreate = true">登记仓库</el-button>
      </div>
    </template>
    <el-table :data="list" border>
      <el-table-column prop="name" label="仓库名称" min-width="140" />
      <el-table-column prop="address" label="地址" min-width="180" />
      <el-table-column prop="capacity" label="容量(件)" width="100" />
      <el-table-column prop="rent_amount" label="租金(元/月)" width="110">
        <template #default="{ row }">{{ row.rent_amount ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="租赁状态" width="110">
        <template #default="{ row }">
          <el-tag :type="LEASE_TAG[row.lease_status]">{{ LEASE_TEXT[row.lease_status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="监控" width="100">
        <template #default="{ row }">
          <el-tag :type="row.monitor_online ? 'success' : 'info'">{{ row.monitor_online ? '已确权' : '未确权' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button size="small" @click="openDevices(row)">监控设备</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="登记仓库" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="仓库名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="地址" required><el-input v-model="form.address" /></el-form-item>
        <el-form-item label="容量(件)"><el-input-number v-model="form.capacity" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="onCreate">提交</el-button>
      </template>
    </el-dialog>

    <DevicePanel :visible="!!current" :warehouse="current" :can-confirm="false" @close="current = null" @changed="load" />
  </el-card>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { createWarehouse, getMyWarehouses } from '../../api/biz'
import DevicePanel from '../../components/DevicePanel.vue'
import type { TagType } from '../../utils/status'

const LEASE_TEXT: Record<string, string> = { NONE: '未租赁', WAIT: '审批中', LEASED: '已租赁' }
const LEASE_TAG: Record<string, TagType> = { NONE: 'info', WAIT: 'warning', LEASED: 'success' }

const list = ref<any[]>([])
const showCreate = ref(false)
const current = ref<any>(null)
const form = reactive({ name: '', address: '', capacity: 1000 })

async function load() { list.value = await getMyWarehouses() }

async function onCreate() {
  if (!form.name || !form.address) return ElMessage.warning('请填写仓库名称和地址')
  await createWarehouse({ ...form })
  ElMessage.success('仓库登记成功，等待平台发起租赁审批')
  showCreate.value = false
  load()
}

function openDevices(row: any) { current.value = row }

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
