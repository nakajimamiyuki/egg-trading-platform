<template>
  <div v-if="data">
    <el-row :gutter="16">
      <el-col :span="6"><el-card><div class="stat">¥{{ data.total_received }}</div><div class="label">累计收款</div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat">¥{{ data.total_paid }}</div><div class="label">累计付款(含垫资)</div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat" style="color:#f56c6c">¥{{ data.total_refund }}</div><div class="label">平仓退款</div></el-card></el-col>
      <el-col :span="6"><el-card><div class="stat">{{ data.inventory.total }}</div><div class="label">库存总量(枚) / 锁定 {{ data.inventory.locked }}</div></el-card></el-col>
    </el-row>

    <el-row :gutter="16" class="mt">
      <el-col :span="12"><el-card><div ref="dailyChart" style="height: 300px" /></el-card></el-col>
      <el-col :span="12"><el-card><div ref="modeChart" style="height: 300px" /></el-card></el-col>
    </el-row>

    <el-card class="mt">
      <template #header>
        <div class="head">
          <span>报表导出</span>
          <el-button type="primary" @click="onExport">导出 Excel 交易报表</el-button>
        </div>
      </template>
      <span class="tip">含全部订单的编号/模式/金额/状态明细; 月度台账归档在此导出的报表基础上按月执行</span>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { onMounted, ref } from 'vue'
import { exportReport, getDashboardSummary } from '../../api/biz'

const data = ref<any>(null)
const dailyChart = ref<HTMLElement>()
const modeChart = ref<HTMLElement>()

const MODE_NAME: Record<string, string> = { M1: '模式①蛋库出库', M2: '模式②在途预付', M3: '模式③渠道账期' }

async function onExport() {
  const blob = (await exportReport()) as Blob
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `交易报表_${new Date().toISOString().slice(0, 10)}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('报表已导出')
}

onMounted(async () => {
  data.value = await getDashboardSummary()
  const daily = data.value.daily ?? []
  echarts.init(dailyChart.value!).setOption({
    title: { text: '每日交易额' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: daily.map((d: any) => d.date) },
    yAxis: { type: 'value' },
    series: [{ type: 'line', smooth: true, areaStyle: {}, data: daily.map((d: any) => d.amount), name: '交易额(元)' }]
  })
  const modes = data.value.order_by_mode ?? {}
  echarts.init(modeChart.value!).setOption({
    title: { text: '订单模式分布' },
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: '60%',
      data: Object.entries(modes).map(([k, v]: [string, any]) => ({ name: MODE_NAME[k] ?? k, value: v.amount }))
    }]
  })
})
</script>

<style scoped>
.stat { font-size: 24px; font-weight: bold; color: #409eff; }
.label { color: #909399; margin-top: 6px; }
.mt { margin-top: 16px; }
.head { display: flex; justify-content: space-between; align-items: center; }
.tip { color: #909399; font-size: 13px; }
</style>
