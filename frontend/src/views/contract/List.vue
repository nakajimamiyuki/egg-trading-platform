<template>
  <el-card>
    <template #header>合同管理</template>
    <el-table :data="list" border>
      <el-table-column prop="contract_no" label="合同编号" width="160" />
      <el-table-column label="类型" width="110">
        <template #default="{ row }">{{ row.type === 'SETTLE' ? '入驻合同' : '销售合同' }}</template>
      </el-table-column>
      <el-table-column prop="order_id" label="关联订单" width="90">
        <template #default="{ row }">{{ row.order_id ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="签署状态" width="120">
        <template #default="{ row }">
          <el-tag :type="SIGN_TAG[row.sign_status] ?? 'info'">{{ SIGN_TEXT[row.sign_status] ?? row.sign_status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="双方签署" width="140">
        <template #default="{ row }">
          <el-tag size="small" :type="row.party_a_signed ? 'success' : 'info'">平台{{ row.party_a_signed ? '✓' : '' }}</el-tag>
          <el-tag size="small" :type="row.party_b_signed ? 'success' : 'info'" style="margin-left: 4px">企业{{ row.party_b_signed ? '✓' : '' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_time" label="生成时间" width="160"
        :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="onView(row)">查看</el-button>
          <el-button v-if="row.sign_status === 'SIGNING'" size="small" type="primary" @click="onSign(row)">在线签署</el-button>
          <el-button v-if="isPlatform && row.sign_status === 'SIGNED'" size="small" @click="onArchive(row)">归档</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!list.length" description="暂无合同" />
  </el-card>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { archiveContract, getContract, getContractList, signContract } from '../../api/biz'
import { useUserStore } from '../../store/user'
import type { TagType } from '../../utils/status'

const SIGN_TEXT: Record<string, string> = { DRAFT: '待审批', SIGNING: '签署中', SIGNED: '已生效', ARCHIVED: '已归档' }
const SIGN_TAG: Record<string, TagType> = { DRAFT: 'info', SIGNING: 'warning', SIGNED: 'success', ARCHIVED: 'info' }

const store = useUserStore()
const list = ref<any[]>([])
const isPlatform = computed(() => store.hasRole('BUSINESS', 'FINANCE'))

async function load() { list.value = await getContractList() }

async function onView(row: any) {
  const detail: any = await getContract(row.id)
  if (detail?.file_url) window.open(detail.file_url, '_blank')
  else ElMessage.info('合同文件未生成')
}

async function onSign(row: any) {
  await ElMessageBox.confirm('确认在线签署该合同？签署后具有法律效力（存证）。', '合同签署')
  const resp: any = await signContract(row.id)
  ElMessage.success(resp?.message ?? '签署成功')
  load()
}

async function onArchive(row: any) {
  await archiveContract(row.id)
  ElMessage.success('已归档')
  load()
}

onMounted(load)
</script>
