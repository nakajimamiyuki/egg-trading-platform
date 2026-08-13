<template>
  <el-card>
    <template #header>交割仓一览</template>
    <el-table :data="list" border>
      <el-table-column prop="dw_no" label="交割仓编号" width="160" />
      <el-table-column prop="warehouse_name" label="仓库" width="130" />
      <el-table-column prop="quantity" label="数量(枚)" width="100" />
      <el-table-column prop="grade" label="品级" width="80" />
      <el-table-column prop="spec" label="规格" width="90" />
      <el-table-column prop="inbound_date" label="入库日期" width="110" />
      <el-table-column label="在库天数" width="110">
        <template #default="{ row }">
          {{ row.days_in_stock }} 天
          <el-tag v-if="row.turnover_warning" type="danger" size="small">周转预警</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="DW_TAG[row.status] ?? 'info'">{{ DW_TEXT[row.status] ?? row.status }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getDwList } from '../../api/biz'
import type { TagType } from '../../utils/status'

const DW_TEXT: Record<string, string> = {
  AUDITING: '审批中', IN_STOCK: '在库', APPLYING: '已申请销售',
  SOLD: '已售', CLOSED: '已平仓', RETURNED: '已退仓', REJECTED: '审批驳回'
}
const DW_TAG: Record<string, TagType> = {
  AUDITING: 'warning', IN_STOCK: 'success', APPLYING: 'warning',
  SOLD: 'info', CLOSED: 'info', RETURNED: 'info', REJECTED: 'danger'
}

const list = ref<any[]>([])
onMounted(async () => { list.value = await getDwList() })
</script>
