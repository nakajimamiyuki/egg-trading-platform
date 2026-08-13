<template>
  <el-card>
    <template #header>审批中心（待办）</template>
    <el-table :data="list" border v-loading="loading">
      <el-table-column prop="title" label="审批事项" min-width="200" />
      <el-table-column prop="node_name" label="当前节点" width="120" />
      <el-table-column prop="biz_type" label="业务类型" width="160" />
      <el-table-column prop="created_time" label="发起时间" width="170"
        :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="success" size="small" @click="onHandle(row, 'PASS')">通过</el-button>
          <el-button type="danger" size="small" @click="onHandle(row, 'REJECT')">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !list.length" description="暂无待办审批" />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTodoApprovals, handleApproval } from '../../api/biz'

const list = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    list.value = (await getTodoApprovals()) as any[]
  } finally {
    loading.value = false
  }
}

async function onHandle(row: any, action: 'PASS' | 'REJECT') {
  const { value } = await ElMessageBox.prompt(
    `确认${action === 'PASS' ? '通过' : '驳回'}「${row.title}」？`, '审批意见',
    { inputPlaceholder: '请输入审批意见（选填）', confirmButtonText: '确认', cancelButtonText: '取消' }
  )
  await handleApproval(row.task_id, action, value || '')
  ElMessage.success('审批完成')
  load()
}

onMounted(load)
</script>
