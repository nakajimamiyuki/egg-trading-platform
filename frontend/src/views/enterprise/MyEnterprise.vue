<template>
  <el-card>
    <template #header>我的企业</template>
    <el-descriptions v-if="ent" :column="2" border>
      <el-descriptions-item label="企业名称">{{ ent.enterprise_name }}</el-descriptions-item>
      <el-descriptions-item label="类型">{{ ent.type === 'FARM' ? '养殖企业' : '采购商' }}</el-descriptions-item>
      <el-descriptions-item label="信用代码">{{ ent.license_no }}</el-descriptions-item>
      <el-descriptions-item label="法人代表">{{ ent.legal_person }}</el-descriptions-item>
      <el-descriptions-item label="联系电话">{{ ent.contact_phone }}</el-descriptions-item>
      <el-descriptions-item label="地址">{{ ent.address }}</el-descriptions-item>
      <template v-if="ent.type === 'FARM'">
        <el-descriptions-item label="养殖品种">{{ ent.breed }}</el-descriptions-item>
        <el-descriptions-item label="存栏量">{{ ent.stock_qty }} 只</el-descriptions-item>
        <el-descriptions-item label="日龄">{{ ent.day_age }} 天</el-descriptions-item>
        <el-descriptions-item label="日均产蛋">{{ ent.daily_egg_qty }} 枚</el-descriptions-item>
      </template>
      <el-descriptions-item label="准入状态">
        <el-tag :type="AUDIT_STATUS_TAG[ent.audit_status]">{{ AUDIT_STATUS_TEXT[ent.audit_status] }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="合作评价">{{ ent.coop_evaluation ?? '-' }}</el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getMyEnterprise } from '../../api/biz'
import { AUDIT_STATUS_TAG, AUDIT_STATUS_TEXT } from '../../utils/status'

const ent = ref<any>(null)
onMounted(async () => { ent.value = await getMyEnterprise() })
</script>
