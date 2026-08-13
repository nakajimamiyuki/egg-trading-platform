<template>
  <el-card>
    <template #header>库存查询</template>
    <el-table :data="list" border>
      <el-table-column prop="warehouse_name" label="仓库" min-width="140" />
      <el-table-column prop="grade" label="品级" width="90" />
      <el-table-column prop="spec" label="规格" width="110" />
      <el-table-column prop="quantity" label="总库存" width="100" />
      <el-table-column prop="locked_qty" label="锁定" width="100" />
      <el-table-column prop="available" label="可用" width="100">
        <template #default="{ row }">
          <span :style="{ color: row.available > 0 ? '#67c23a' : '#f56c6c' }">{{ row.available }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="updated_time" label="更新时间" width="170"
        :formatter="(r: any) => r.updated_time.slice(0, 16).replace('T', ' ')" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getInventoryList } from '../../api/biz'

const list = ref<any[]>([])
onMounted(async () => { list.value = await getInventoryList() })
</script>
