<template>
  <div>
    <h2>欢迎，{{ store.realName }}</h2>
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>企业准入状态</template>
          <template v-if="enterprise">
            <el-tag :type="statusType">{{ statusText }}</el-tag>
            <p>{{ enterprise.enterprise_name }}</p>
            <p v-if="enterprise.coop_evaluation" class="eval">{{ enterprise.coop_evaluation }}</p>
          </template>
          <span v-else>平台人员账号，无企业档案</span>
        </el-card>
      </el-col>
      <el-col :span="8" v-if="store.hasRole('BUSINESS', 'FINANCE')">
        <el-card>
          <template #header>待办审批</template>
          <el-badge :value="todoCount" :hidden="!todoCount">
            <el-button @click="$router.push('/approval/todo')">前往审批中心</el-button>
          </el-badge>
        </el-card>
      </el-col>
    </el-row>
    <el-alert class="tip" type="info" :closable="false"
      title="M1 阶段功能：注册建档 / 准入审批 / 权限管理。建仓入库、货架、订单等将在后续里程碑上线。" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getMyEnterprise, getTodoApprovals } from '../api/biz'
import { useUserStore } from '../store/user'
import { AUDIT_STATUS_TAG, AUDIT_STATUS_TEXT } from '../utils/status'

const store = useUserStore()
const enterprise = ref<any>(null)
const todoCount = ref(0)

const statusText = computed(() => AUDIT_STATUS_TEXT[enterprise.value?.audit_status] ?? '-')
const statusType = computed(() => AUDIT_STATUS_TAG[enterprise.value?.audit_status] ?? 'info')

onMounted(async () => {
  if (store.hasRole('FARM', 'CUSTOMER')) {
    try { enterprise.value = await getMyEnterprise() } catch { /* 未关联企业 */ }
  }
  if (store.hasRole('BUSINESS', 'FINANCE')) {
    const todos = (await getTodoApprovals()) as any[]
    todoCount.value = todos.length
  }
})
</script>

<style scoped>
.tip { margin-top: 20px; }
.eval { color: #67c23a; font-size: 13px; }
</style>
