<template>
  <el-card>
    <template #header>仓库管理（业务端）</template>
    <el-table :data="list" border v-loading="loading">
      <el-table-column prop="name" label="仓库名称" min-width="130" />
      <el-table-column prop="address" label="地址" min-width="150" />
      <el-table-column prop="capacity" label="容量" width="80" />
      <el-table-column prop="rent_amount" label="租金" width="90">
        <template #default="{ row }">{{ row.rent_amount ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="租赁" width="90">
        <template #default="{ row }">
          <el-tag :type="LEASE_TAG[row.lease_status]">{{ LEASE_TEXT[row.lease_status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="监控" width="90">
        <template #default="{ row }">
          <el-tag :type="row.monitor_online ? 'success' : 'info'">{{ row.monitor_online ? '已确权' : '未确权' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" :disabled="row.lease_status !== 'NONE'" @click="openLease(row)">发起租赁审批</el-button>
          <el-button size="small" @click="openDevices(row)">设备管理</el-button>
          <el-button size="small" type="primary" :disabled="row.lease_status !== 'LEASED' || !row.monitor_online" @click="openDw(row)">建交割仓</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showLease" title="发起仓库租赁审批" width="440px">
      <p>{{ current?.name }}（{{ current?.address }}，容量 {{ current?.capacity }} 件）</p>
      <el-form label-width="110px">
        <el-form-item label="租金(元/月)" required><el-input-number v-model="rentAmount" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showLease = false">取消</el-button>
        <el-button type="primary" @click="onLease">发起审批</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDw" title="发起交割仓建立审批" width="480px">
      <p>{{ current?.name }} —— 需产蛋数据支持，审批通过后自动建立交割仓并初始化库存</p>
      <el-form :model="dwForm" label-width="90px">
        <el-form-item label="数量(枚)" required><el-input-number v-model="dwForm.quantity" :min="1" /></el-form-item>
        <el-form-item label="品级" required>
          <el-select v-model="dwForm.grade">
            <el-option v-for="g in grades" :key="g.code" :label="g.name" :value="g.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="规格" required>
          <el-select v-model="dwForm.spec">
            <el-option v-for="s in specs" :key="s.code" :label="s.name" :value="s.code" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDw = false">取消</el-button>
        <el-button type="primary" @click="onDw">发起审批</el-button>
      </template>
    </el-dialog>

    <DevicePanel :visible="!!deviceTarget" :warehouse="deviceTarget" :can-confirm="true" @close="deviceTarget = null" @changed="load" />
  </el-card>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { dwApply, getDict, getWarehouseList, leaseApply } from '../../api/biz'
import DevicePanel from '../../components/DevicePanel.vue'
import type { TagType } from '../../utils/status'

const LEASE_TEXT: Record<string, string> = { NONE: '未租赁', WAIT: '审批中', LEASED: '已租赁' }
const LEASE_TAG: Record<string, TagType> = { NONE: 'info', WAIT: 'warning', LEASED: 'success' }

const list = ref<any[]>([])
const loading = ref(false)
const showLease = ref(false)
const showDw = ref(false)
const current = ref<any>(null)
const deviceTarget = ref<any>(null)
const rentAmount = ref(8000)
const dwForm = reactive({ quantity: 1000, grade: 'A', spec: 'S50' })
const grades = ref<any[]>([])
const specs = ref<any[]>([])

async function load() {
  loading.value = true
  try { list.value = await getWarehouseList() } finally { loading.value = false }
}

function openLease(row: any) { current.value = row; showLease.value = true }
function openDevices(row: any) { deviceTarget.value = row }
function openDw(row: any) { current.value = row; showDw.value = true }

async function onLease() {
  await leaseApply(current.value.id, rentAmount.value)
  ElMessage.success('租赁审批已发起（业务→财务两级审批）')
  showLease.value = false
  load()
}

async function onDw() {
  await dwApply({ warehouse_id: current.value.id, ...dwForm })
  ElMessage.success('交割仓审批已发起')
  showDw.value = false
  load()
}

onMounted(async () => {
  load()
  grades.value = await getDict('EGG_GRADE')
  specs.value = await getDict('EGG_SPEC')
})
</script>
