<template>
  <el-card>
    <template #header>付款执行（人工转账兜底 / 银企直联就绪前）</template>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px"
      title="当参数配置 bank_channel=MANUAL 时, 垫资/尾款审批通过后在此上传银行回单确认到账; MOCK 模式下无待办。" />
    <el-table :data="pending" border>
      <el-table-column prop="pay_no" label="流水号" width="160" />
      <el-table-column label="款项" width="120">
        <template #default="{ row }">{{ { ADVANCE: '垫资80%', SETTLE: '尾款结算20%' }[row.pay_type as string] ?? row.pay_type }}</template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="110" />
      <el-table-column prop="order_id" label="订单ID" width="90" />
      <el-table-column label="回单" min-width="180">
        <template #default="{ row }">
          <input type="file" :id="`v-${row.id}`" @change="(e) => onVoucherFile(e, row.id)" />
          <span v-if="vouchers[row.id]" style="color: #67c23a"> ✓ 已上传</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button type="primary" size="small" :disabled="!vouchers[row.id]" @click="onConfirm(row)">确认到账</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!pending.length" description="暂无待确认付款" />
  </el-card>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { confirmManualPay, getPayRecords, uploadFile } from '../../api/biz'

const records = ref<any[]>([])
const pending = ref<any[]>([])
const vouchers = ref<Record<number, number>>({})

async function load() {
  records.value = await getPayRecords()
  pending.value = records.value.filter((r) => r.channel === 'MANUAL' && r.status === 'PENDING')
}

async function onVoucherFile(e: Event, recordId: number) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const resp = (await uploadFile(file, 'PAY_VOUCHER')) as { file_id: number }
  vouchers.value[recordId] = resp.file_id
}

async function onConfirm(row: any) {
  await confirmManualPay(row.id, vouchers.value[row.id])
  ElMessage.success('回单已确认，付款生效')
  load()
}

onMounted(load)
</script>
