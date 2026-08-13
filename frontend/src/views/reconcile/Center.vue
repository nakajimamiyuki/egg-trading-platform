<template>
  <div>
    <el-card>
      <template #header>
        <div class="head">
          <span>对账中心</span>
          <el-button v-if="isFinance" type="primary" @click="showRun = true">发起对账</el-button>
        </div>
      </template>
      <el-table :data="batches" border>
        <el-table-column prop="batch_no" label="批次号" width="160" />
        <el-table-column label="范围" width="130">
          <template #default="{ row }">{{ row.scope === 'DELIVERY' ? '交割仓业务' : '自营业务' }}</template>
        </el-table-column>
        <el-table-column prop="period" label="区间" width="200" />
        <el-table-column prop="total_count" label="单据数" width="90" />
        <el-table-column prop="matched" label="匹配" width="80" />
        <el-table-column label="差异" width="90">
          <template #default="{ row }">
            <span :style="{ color: row.diff_count ? '#f56c6c' : '#67c23a' }">{{ row.diff_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ARCHIVED' ? 'success' : 'warning'">
              {{ row.status === 'ARCHIVED' ? '已归档' : '进行中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDiffs(row)">差异明细</el-button>
            <el-button v-if="isFinance && row.status !== 'ARCHIVED'" size="small" @click="onArchive(row)">确认归档</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showRun" title="发起对账" width="480px">
      <el-form :model="runForm" label-width="90px">
        <el-form-item label="业务范围">
          <el-radio-group v-model="runForm.scope">
            <el-radio-button value="DELIVERY">交割仓业务</el-radio-button>
            <el-radio-button value="SELF">自营业务</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="区间" required>
          <el-date-picker v-model="period" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始" end-placeholder="结束" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRun = false">取消</el-button>
        <el-button type="primary" @click="onRun">开始对账</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDiffs" title="差异明细与调账" width="720px">
      <el-table :data="diffs" border size="small">
        <el-table-column prop="biz_id" label="单据ID" width="80" />
        <el-table-column prop="diff_desc" label="差异说明" min-width="240" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ADJUSTED' ? 'success' : 'danger'">
              {{ row.status === 'ADJUSTED' ? '已调账' : '未处理' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="调账信息" min-width="180">
          <template #default="{ row }">
            <span v-if="row.status === 'ADJUSTED'">¥{{ row.adjust_amount }} — {{ row.adjust_reason }}</span>
            <el-button v-else-if="isFinance" size="small" type="primary" @click="onAdjust(row)">调账</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!diffs.length" description="无差异, 全部匹配" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { adjustDiff, archiveReconcileBatch, getReconcileBatches, getReconcileDiffs, runReconcile } from '../../api/biz'
import { useUserStore } from '../../store/user'

const store = useUserStore()
const isFinance = computed(() => store.hasRole('FINANCE'))

const batches = ref<any[]>([])
const diffs = ref<any[]>([])
const showRun = ref(false)
const showDiffs = ref(false)
const period = ref<[string, string] | null>(null)
const runForm = reactive({ scope: 'DELIVERY' })
const currentBatch = ref<any>(null)

async function load() { batches.value = await getReconcileBatches() }

async function onRun() {
  if (!period.value) return ElMessage.warning('请选择对账区间')
  const resp: any = await runReconcile({ scope: runForm.scope, period_start: period.value[0], period_end: period.value[1] })
  ElMessage.success(`对账完成: 共${resp?.total}单, 匹配${resp?.matched}, 差异${resp?.diff}`)
  showRun.value = false
  load()
}

async function openDiffs(row: any) {
  currentBatch.value = row
  diffs.value = await getReconcileDiffs(row.id)
  showDiffs.value = true
}

async function onAdjust(row: any) {
  const { value } = await ElMessageBox.prompt('输入调账金额', '调账', { inputPlaceholder: '如 100.00' })
  const amount = Number(value)
  const reasonResp = await ElMessageBox.prompt('调账原因（必填，留痕）', '调账', { inputPlaceholder: '如: 银行手续费差异' })
  await adjustDiff(row.id, amount, reasonResp.value)
  ElMessage.success('调账完成，已留痕')
  diffs.value = await getReconcileDiffs(currentBatch.value.id)
  load()
}

async function onArchive(row: any) {
  await archiveReconcileBatch(row.id)
  ElMessage.success('已归档')
  load()
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
