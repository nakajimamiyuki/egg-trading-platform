<template>
  <el-card>
    <template #header>
      <div class="head">
        <span>发票管理</span>
        <div>
          <el-button v-if="isCustomer" type="primary" @click="showApply = true">申请开票</el-button>
          <el-button @click="showCheck = true">发票查验</el-button>
        </div>
      </div>
    </template>
    <el-table :data="list" border>
      <el-table-column prop="invoice_no" label="发票号码" width="160">
        <template #default="{ row }">{{ row.invoice_no ?? '未开具' }}</template>
      </el-table-column>
      <el-table-column prop="order_id" label="订单ID" width="80" />
      <el-table-column prop="buyer_title" label="抬头" min-width="160" />
      <el-table-column prop="amount" label="金额" width="110" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="INV_TAG[row.status] ?? 'info'">{{ INV_TEXT[row.status] ?? row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_time" label="申请时间" width="160"
        :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
      <el-table-column v-if="isFinance" label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'ISSUED'" size="small" @click="onArchive(row)">归档</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!list.length" description="暂无发票" />

    <el-dialog v-model="showApply" title="申请开票" width="480px">
      <el-form :model="applyForm" label-width="100px">
        <el-form-item label="订单" required>
          <el-select v-model="applyForm.order_id" placeholder="选择已完成订单" style="width: 100%">
            <el-option v-for="o in finishedOrders" :key="o.id" :label="`${o.order_no} (¥${o.total_amount})`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="发票抬头" required><el-input v-model="applyForm.buyer_title" /></el-form-item>
        <el-form-item label="税号" required><el-input v-model="applyForm.tax_no" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApply = false">取消</el-button>
        <el-button type="primary" @click="onApply">提交申请</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCheck" title="发票查验" width="440px">
      <el-input v-model="checkNo" placeholder="输入发票号码, 如 INV202608130001" />
      <el-button type="primary" style="margin-top: 10px" @click="onCheck">查验</el-button>
      <el-alert v-if="checkResult" style="margin-top: 12px" type="success" :closable="false"
        :title="checkResult.check_result" :description="`金额: ¥${checkResult.amount} 抬头: ${checkResult.buyer_title}`" />
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { applyInvoice, archiveInvoice, checkInvoice, getInvoiceList, getOrderList } from '../../api/biz'
import { useUserStore } from '../../store/user'
import type { TagType } from '../../utils/status'

const INV_TEXT: Record<string, string> = { APPLY: '已申请', AUDITING: '审批中', ISSUED: '已开具', ARCHIVED: '已归档' }
const INV_TAG: Record<string, TagType> = { APPLY: 'info', AUDITING: 'warning', ISSUED: 'success', ARCHIVED: 'info' }

const store = useUserStore()
const list = ref<any[]>([])
const finishedOrders = ref<any[]>([])
const showApply = ref(false)
const showCheck = ref(false)
const checkNo = ref('')
const checkResult = ref<any>(null)
const applyForm = reactive({ order_id: null as number | null, buyer_title: '', tax_no: '' })

const isCustomer = computed(() => store.hasRole('CUSTOMER'))
const isFinance = computed(() => store.hasRole('FINANCE'))

async function load() {
  list.value = await getInvoiceList()
  if (isCustomer.value) {
    const orders: any[] = await getOrderList()
    finishedOrders.value = orders.filter((o) => ['TAIL_PAID', 'FULL_PAID', 'RELEASED', 'FINISHED'].includes(o.status))
  }
}

async function onApply() {
  if (!applyForm.order_id || !applyForm.buyer_title || !applyForm.tax_no) return ElMessage.warning('请完整填写')
  await applyInvoice({ order_id: applyForm.order_id, buyer_title: applyForm.buyer_title, tax_no: applyForm.tax_no })
  ElMessage.success('发票申请已提交，待财务审批')
  showApply.value = false
  load()
}

async function onArchive(row: any) {
  await archiveInvoice(row.id)
  ElMessage.success('已归档')
  load()
}

async function onCheck() {
  if (!checkNo.value) return
  checkResult.value = await checkInvoice(checkNo.value)
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
