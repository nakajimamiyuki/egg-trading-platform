<template>
  <el-card>
    <template #header>账单中心</template>
    <el-table :data="list" border>
      <el-table-column prop="bill_no" label="账单号" width="160" />
      <el-table-column prop="order_id" label="订单ID" width="90" />
      <el-table-column prop="amount" label="订单金额" width="110" />
      <el-table-column prop="received" label="已收" width="110" />
      <el-table-column prop="paid" label="已付" width="110" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.bill_status === 'SETTLED' ? 'success' : 'warning'">
            {{ { OPEN: '待结算', SETTLING: '结算中', SETTLED: '已结清' }[row.bill_status as string] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_time" label="创建时间" width="170"
        :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
    </el-table>
    <el-empty v-if="!list.length" description="暂无账单" />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getBills } from '../../api/biz'

const list = ref<any[]>([])
onMounted(async () => { list.value = await getBills() })
</script>
