<template>
  <el-card>
    <template #header>业务参数配置（管理员）</template>
    <el-table :data="list" border>
      <el-table-column prop="key" label="参数键" width="220" />
      <el-table-column prop="remark" label="说明" min-width="200" />
      <el-table-column prop="value" label="当前值" width="120" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="onEdit(row)">修改</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getConfigs, updateConfig } from '../../api/biz'

const list = ref<any[]>([])

async function load() { list.value = (await getConfigs()) as any[] }

async function onEdit(row: any) {
  const { value } = await ElMessageBox.prompt(`修改「${row.remark}」`, row.key, { inputValue: row.value })
  await updateConfig(row.key, value)
  ElMessage.success('已更新')
  load()
}

onMounted(load)
</script>
