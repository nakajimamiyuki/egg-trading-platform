<template>
  <el-card>
    <template #header>合作激励（满勤赠送机器人）</template>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px"
      title="规则: 持续合作满 6 个月, 且累计发货量达到每满 10 万只鸡规模, 平台赠送一台机器人" />
    <el-table :data="list" border>
      <el-table-column prop="enterprise_name" label="养殖企业" min-width="160" />
      <el-table-column label="合作月数" width="140">
        <template #default="{ row }">{{ row.coop_months }} / {{ row.required_months }} 个月</template>
      </el-table-column>
      <el-table-column label="累计发货" width="160">
        <template #default="{ row }">{{ row.shipped }} / {{ row.required_scale }} 枚</template>
      </el-table-column>
      <el-table-column label="达标" width="90">
        <template #default="{ row }">
          <el-tag :type="row.qualified ? 'success' : 'info'">{{ row.qualified ? '已达标' : '未达标' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'GRANTED' ? 'success' : 'warning'">
            {{ { TRACKING: '跟进中', QUALIFIED: '待赠送', GRANTED: '已赠送' }[row.status as string] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="isBusiness" label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" :disabled="!row.qualified || row.status === 'GRANTED'"
            @click="onGrant(row)">确认赠送</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { getIncentiveList, grantIncentive } from '../../api/biz'
import { useUserStore } from '../../store/user'

const store = useUserStore()
const isBusiness = computed(() => store.hasRole('BUSINESS'))
const list = ref<any[]>([])

async function load() { list.value = await getIncentiveList() }

async function onGrant(row: any) {
  await ElMessageBox.confirm(`确认向「${row.enterprise_name}」赠送机器人一台？`, '激励发放')
  const resp: any = await grantIncentive(row.enterprise_id)
  ElMessage.success(resp?.message ?? '已赠送')
  load()
}

onMounted(load)
</script>
