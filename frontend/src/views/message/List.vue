<template>
  <el-card>
    <template #header>
      <div class="head">
        <span>消息中心</span>
        <el-radio-group v-model="tab" size="small" @change="load">
          <el-radio-button :value="false">全部</el-radio-button>
          <el-radio-button :value="true">仅未读</el-radio-button>
        </el-radio-group>
      </div>
    </template>
    <div v-for="m in list" :key="m.id" class="msg" :class="{ unread: !m.read_flag }" @click="onRead(m)">
      <div class="title-row">
        <el-tag size="small" :type="TYPE_TAG[m.type] ?? 'info'">{{ TYPE_TEXT[m.type] ?? m.type }}</el-tag>
        <span class="title">{{ m.title }}</span>
        <span class="time">{{ m.created_time.slice(0, 16).replace('T', ' ') }}</span>
      </div>
      <div class="content">{{ m.content }}</div>
    </div>
    <el-empty v-if="!list.length" description="暂无消息" />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getMessages, markMessageRead } from '../../api/biz'
import type { TagType } from '../../utils/status'

const TYPE_TEXT: Record<string, string> = {
  ADVANCE_PAID: '资金到账', CLOSE_WARNING: '平仓预警', APPROVAL: '审批通知', ORDER_STATUS: '订单状态'
}
const TYPE_TAG: Record<string, TagType> = {
  ADVANCE_PAID: 'success', CLOSE_WARNING: 'danger', APPROVAL: 'warning', ORDER_STATUS: 'info'
}

const list = ref<any[]>([])
const tab = ref(false)

async function load() { list.value = await getMessages(tab.value) }

async function onRead(m: any) {
  if (!m.read_flag) {
    await markMessageRead(m.id)
    m.read_flag = true
  }
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
.msg { padding: 12px 8px; border-bottom: 1px solid #f0f0f0; cursor: pointer; }
.msg.unread { background: #ecf5ff; }
.title-row { display: flex; gap: 8px; align-items: center; }
.title { font-weight: bold; flex: 1; }
.msg.unread .title::after { content: '●'; color: #f56c6c; margin-left: 6px; }
.time { color: #909399; font-size: 12px; }
.content { color: #606266; font-size: 13px; margin-top: 6px; }
</style>
