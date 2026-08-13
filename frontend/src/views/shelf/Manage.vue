<template>
  <el-card>
    <template #header>货架管理（定价 / 上下架）</template>
    <el-table :data="list" border>
      <el-table-column prop="dw_no" label="交割仓" width="160" />
      <el-table-column prop="grade" label="品级" width="80" />
      <el-table-column prop="quantity" label="在架数量" width="100" />
      <el-table-column prop="price" label="单价(元/枚)" width="110" />
      <el-table-column prop="source_enterprise" label="来源养殖户" min-width="150" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'ON' ? 'success' : 'info'">{{ row.status === 'ON' ? '在售' : '下架' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="onPrice(row)">改价</el-button>
          <el-button size="small" :type="row.status === 'ON' ? 'warning' : 'success'" @click="onToggle(row)">
            {{ row.status === 'ON' ? '下架' : '上架' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { getShelfManage, setShelfPrice, setShelfStatus } from '../../api/biz'

const list = ref<any[]>([])
async function load() { list.value = await getShelfManage() }

async function onPrice(row: any) {
  const { value } = await ElMessageBox.prompt('输入新单价(元/枚)', '改价', { inputValue: String(row.price) })
  await setShelfPrice(row.id, Number(value))
  ElMessage.success('价格已更新')
  load()
}

async function onToggle(row: any) {
  await setShelfStatus(row.id, row.status === 'ON' ? 'OFF' : 'ON')
  load()
}

onMounted(load)
</script>
