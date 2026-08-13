<template>
  <el-card>
    <template #header>我的申请</template>
    <el-table :data="list" border>
      <el-table-column prop="title" label="申请事项" min-width="200" />
      <el-table-column prop="biz_type" label="业务类型" width="160" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="INSTANCE_STATUS_TAG[row.status]">{{ INSTANCE_STATUS_TEXT[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_time" label="发起时间" width="170"
        :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getMyApprovals } from '../../api/biz'
import { INSTANCE_STATUS_TAG, INSTANCE_STATUS_TEXT } from '../../utils/status'

const list = ref<any[]>([])
onMounted(async () => { list.value = await getMyApprovals() })
</script>
