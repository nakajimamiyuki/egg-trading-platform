<template>
  <div>
    <el-card>
      <template #header>
        <div class="head">
          <span>交割仓预警（在库 ≥ 周转天数）</span>
          <el-button v-if="isBusiness" @click="onCheck">手动触发预警检查</el-button>
        </div>
      </template>
      <el-table :data="warnings" border>
        <el-table-column prop="dw_no" label="交割仓" width="160" />
        <el-table-column prop="warehouse_name" label="仓库" width="120" />
        <el-table-column prop="quantity" label="数量" width="90" />
        <el-table-column prop="days_in_stock" label="在库天数" width="100" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="DW_TAG[row.status] ?? 'info'">{{ DW_TEXT[row.status] ?? row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260">
          <template #default="{ row }">
            <template v-if="isFarm && ['IN_STOCK', 'APPLYING'].includes(row.status)">
              <el-button size="small" @click="openApply(row)">发起申请</el-button>
            </template>
            <el-button v-if="isBusiness && ['IN_STOCK', 'APPLYING'].includes(row.status)"
              size="small" type="danger" @click="onForceClose(row)">强制平仓</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!warnings.length" description="暂无预警交割仓" />
    </el-card>

    <el-card class="mt">
      <template #header>我的申请 / 申请记录</template>
      <el-table :data="applies" border size="small">
        <el-table-column prop="dw_no" label="交割仓" width="150" />
        <el-table-column prop="apply_type_text" label="申请类型" width="200" />
        <el-table-column prop="remark" label="说明" min-width="140" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="APPLY_TAG[row.status] ?? 'info'">{{ APPLY_TEXT[row.status] ?? row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_time" label="时间" width="160"
          :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
      </el-table>
    </el-card>

    <el-card class="mt">
      <template #header>平仓台账</template>
      <el-table :data="closes" border size="small">
        <el-table-column prop="close_no" label="平仓单号" width="150" />
        <el-table-column prop="dw_no" label="交割仓" width="150" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="original_amount" label="原价(元)" width="100" />
        <el-table-column prop="settle_amount" label="折价结算(元)" width="110" />
        <el-table-column prop="profit_loss" label="盈亏(元)" width="100">
          <template #default="{ row }"><span style="color:#f56c6c">-{{ row.profit_loss }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'REFUNDED' ? 'success' : 'warning'">
              {{ { PENDING: '退款审批中', CONFIRMED: '已确认', REFUNDED: '已退款' }[row.status as string] }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showApply" title="发起申请" width="480px">
      <el-form label-width="100px">
        <el-form-item label="申请类型" required>
          <el-select v-model="applyType" style="width: 100%">
            <el-option label="申请退仓（退回货物退还预付款）" value="RETURN" />
            <el-option label="平台自行销售（指定客户）" value="SELF_SALE_DESIGNATED" />
            <el-option label="平台自行销售（非指定客户）" value="SELF_SALE_OPEN" />
            <el-option label="销售给平台" value="SALE_TO_PLATFORM" />
            <el-option label="超期平台订单处理" value="OVERDUE_HANDLE" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="applyRemark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApply = false">取消</el-button>
        <el-button type="primary" @click="onApply">提交（待业务审批）</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { checkWarnings, createCloseApply, forceClose, getCloseApplies, getCloseList, getDwList } from '../../api/biz'
import { useUserStore } from '../../store/user'
import type { TagType } from '../../utils/status'

const DW_TEXT: Record<string, string> = { IN_STOCK: '在库', APPLYING: '已申请销售', SOLD: '已售', CLOSED: '已平仓', RETURNED: '已退仓' }
const DW_TAG: Record<string, TagType> = { IN_STOCK: 'success', APPLYING: 'warning', SOLD: 'info', CLOSED: 'info', RETURNED: 'info' }
const APPLY_TEXT: Record<string, string> = { WAIT: '待审批', PASS: '已通过', REJECT: '已驳回', DONE: '已完成' }
const APPLY_TAG: Record<string, TagType> = { WAIT: 'warning', PASS: 'success', REJECT: 'danger', DONE: 'success' }

const store = useUserStore()
const isFarm = computed(() => store.hasRole('FARM'))
const isBusiness = computed(() => store.hasRole('BUSINESS'))

const dwList = ref<any[]>([])
const applies = ref<any[]>([])
const closes = ref<any[]>([])
const showApply = ref(false)
const applyType = ref('RETURN')
const applyRemark = ref('')
const currentDw = ref<any>(null)

const warnings = computed(() => dwList.value.filter((d) => d.turnover_warning || ['IN_STOCK', 'APPLYING'].includes(d.status)))

async function load() {
  dwList.value = await getDwList()
  applies.value = await getCloseApplies()
  closes.value = await getCloseList()
}

async function onCheck() {
  const resp: any = await checkWarnings()
  ElMessage.success(resp?.message ?? '检查完成')
  load()
}

function openApply(row: any) { currentDw.value = row; showApply.value = true }

async function onApply() {
  await createCloseApply({ delivery_warehouse_id: currentDw.value.id, apply_type: applyType.value, remark: applyRemark.value })
  ElMessage.success('申请已提交，待业务审批')
  showApply.value = false
  load()
}

async function onForceClose(row: any) {
  await ElMessageBox.confirm(
    `确认对 ${row.dw_no} 强制平仓？将按折价比例结算（默认 80%），货物折价出库。`, '强制平仓', { type: 'warning' })
  const resp: any = await forceClose(row.id)
  ElMessage.success(`${resp?.message}，折价结算 ¥${resp?.settle_amount}`)
  load()
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
.mt { margin-top: 16px; }
</style>
