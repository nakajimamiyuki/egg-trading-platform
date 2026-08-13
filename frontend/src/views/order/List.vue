<template>
  <el-card>
    <template #header>{{ title }}</template>
    <el-table :data="list" border @row-click="(r: any) => $router.push(`/order/detail/${r.id}`)" style="cursor: pointer">
      <el-table-column prop="order_no" label="订单号" width="170" />
      <el-table-column label="模式" width="90">
        <template #default="{ row }">{{ { M1: '①蛋库', M2: '②在途', M3: '③账期' }[row.sale_mode as string] }}</template>
      </el-table-column>
      <el-table-column prop="quantity" label="数量(枚)" width="100" />
      <el-table-column prop="total_amount" label="总额(元)" width="110" />
      <el-table-column label="状态" width="170">
        <template #default="{ row }">
          <el-tag :type="ORDER_TAG[row.status] ?? 'info'">{{ row.status_text }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_time" label="创建时间" width="170"
        :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
    </el-table>
    <el-empty v-if="!list.length" description="暂无订单" />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getOrderList } from '../../api/biz'
import type { TagType } from '../../utils/status'

defineProps<{ title: string }>()

const ORDER_TAG: Record<string, TagType> = {
  CREATE: 'info', AUDIT: 'warning', DEPOSIT_PENDING: 'warning', DEPOSIT_PAID: 'warning',
  ADVANCE_PAID: 'warning', VERIFYING: 'warning', OUTBOUND_CONFIRMED: 'warning',
  TAIL_PAID: 'warning', FULL_PAID: 'warning', RELEASED: 'success', FINISHED: 'success',
  CANCEL: 'info', CLOSED: 'info'
}

const list = ref<any[]>([])
onMounted(async () => { list.value = await getOrderList() })
</script>
