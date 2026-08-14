<template>
  <div v-if="order">
    <el-card>
      <template #header>
        <div class="head">
          <span>订单 {{ order.order_no }}
            <el-tag>{{ { M1: '模式①蛋库出库', M2: '模式②在途预付', M3: '模式③渠道账期' }[order.sale_mode as string] }}</el-tag>
          </span>
          <el-tag size="large" type="warning">{{ order.status_text }}</el-tag>
        </div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="买方">{{ order.buyer_name }}</el-descriptions-item>
        <el-descriptions-item label="卖方(养殖户)">{{ order.seller_name }}</el-descriptions-item>
        <el-descriptions-item label="数量">{{ order.quantity }} 枚</el-descriptions-item>
        <el-descriptions-item label="单价">¥{{ order.unit_price }}</el-descriptions-item>
        <el-descriptions-item label="总额">¥{{ order.total_amount }}</el-descriptions-item>
        <el-descriptions-item label="定金(20%)">¥{{ order.deposit_amount }}</el-descriptions-item>
        <el-descriptions-item label="垫资(80%)">¥{{ order.advance_amount }}</el-descriptions-item>
        <el-descriptions-item v-if="order.sale_mode === 'M3'" label="账期">{{ order.credit_days }} 天</el-descriptions-item>
        <el-descriptions-item v-if="order.sale_mode === 'M3'" label="平台分利">¥{{ order.platform_profit }}</el-descriptions-item>
      </el-descriptions>

      <!-- 各角色操作区 -->
      <div class="actions">
        <template v-if="isCustomer">
          <el-button v-if="order.status === 'DEPOSIT_PENDING'" type="primary" @click="onPay('DEPOSIT')">支付定金 ¥{{ order.deposit_amount }}</el-button>
          <el-button v-if="order.status === 'OUTBOUND_CONFIRMED'" type="primary" @click="onPay('TAIL')">支付尾款 ¥{{ order.total_amount - order.deposit_amount }}</el-button>
          <el-button v-if="['AUDIT', 'DEPOSIT_PENDING'].includes(order.status)" type="danger" plain @click="onCancel">取消订单</el-button>
        </template>
        <template v-if="isBusiness">
          <el-button v-if="order.status === 'ADVANCE_PAID'" type="primary" @click="showOutbound = true">开具出库单</el-button>
        </template>
      </div>
    </el-card>

    <!-- 出库单 -->
    <el-card v-if="outbound" class="mt">
      <template #header>出库单 {{ outbound.outbound_no }}
        <el-tag :type="outbound.status === 'RELEASED' ? 'success' : 'warning'" style="margin-left: 8px">{{ outbound.status }}</el-tag>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="数量">{{ outbound.quantity }} 枚</el-descriptions-item>
        <el-descriptions-item label="车牌号">{{ outbound.plate_no }}</el-descriptions-item>
        <el-descriptions-item label="司机">{{ outbound.driver_name }} {{ outbound.driver_phone }}</el-descriptions-item>
      </el-descriptions>
      <div class="confirms">
        <span>三方确认：</span>
        <el-tag :type="outbound.seller_confirmed ? 'success' : 'info'">养殖户{{ outbound.seller_confirmed ? '✓' : '' }}</el-tag>
        <el-tag :type="outbound.buyer_confirmed ? 'success' : 'info'">客户{{ outbound.buyer_confirmed ? '✓' : '' }}</el-tag>
        <el-tag :type="outbound.platform_confirmed ? 'success' : 'info'">平台{{ outbound.platform_confirmed ? '✓' : '' }}</el-tag>
        <template v-if="order.status === 'VERIFYING'">
          <el-button v-if="isFarm && !outbound.seller_confirmed" size="small" type="primary" @click="onConfirm('seller')">养殖户确认</el-button>
          <el-button v-if="isCustomer && !outbound.buyer_confirmed" size="small" type="primary" @click="onConfirm('buyer')">客户确认</el-button>
          <el-button v-if="isBusiness && !outbound.platform_confirmed" size="small" type="primary" @click="onConfirm('platform')">平台确认</el-button>
        </template>
      </div>
      <div class="confirms">
        <span>装车凭证：</span>
        <el-button v-if="canUploadVoucher" size="small" @click="photoInput?.click()">上传照片/视频(自动水印)</el-button>
        <input ref="photoInput" type="file" hidden accept="image/*,video/*" @change="onPhoto" />
        <el-tag v-for="f in outbound.files" :key="f.file_id" size="small" class="file-tag" @click="openFile(f)">
          {{ f.media_type === 'PHOTO' ? '照片' : '视频' }}{{ f.watermarked ? '(已水印)' : '' }} 🔍
        </el-tag>
        <span v-if="!outbound.files?.length" class="tip">暂无</span>
      </div>
    </el-card>

    <!-- 电子提货凭证 -->
    <el-card v-if="voucher" class="mt">
      <template #header>电子提货凭证 {{ voucher.voucher_no }}
        <el-tag :type="voucher.status === 'USED' ? 'success' : 'warning'" style="margin-left: 8px">
          {{ voucher.status === 'USED' ? '已核销' : '待核销' }}
        </el-tag>
      </template>
      <div class="voucher">
        <QrcodeVue :value="voucher.qr_payload" :size="140" />
        <div>
          <p>二维码内容: <code>{{ voucher.qr_payload }}</code></p>
          <p class="tip">养殖户确认收齐全款后, 扫码核验放行 (唯一放行凭证)</p>
          <div v-if="isFarm && voucher.status === 'ACTIVE'" class="scan-box">
            <el-input v-model="scanInput" placeholder="扫码或粘贴二维码内容" style="width: 320px" />
            <el-button type="danger" @click="onVerify">核销放行</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 资金流水 -->
    <el-card v-if="records.length" class="mt">
      <template #header>资金流水</template>
      <el-table :data="records" border size="small">
        <el-table-column prop="pay_no" label="流水号" width="160" />
        <el-table-column label="类型" width="130">
          <template #default="{ row }">{{ { DEPOSIT: '定金(客户)', TAIL: '尾款(客户)', ADVANCE: '垫资80%(平台)', SETTLE: '结算20%(平台)', REFUND: '退款', CHANNEL_PAY: '渠道回款' }[row.pay_type as string] }}</template>
        </el-table-column>
        <el-table-column label="方向" width="70">
          <template #default="{ row }">{{ row.direction === 'IN' ? '收入' : '支出' }}</template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="110" />
        <el-table-column prop="channel" label="通道" width="90" />
        <el-table-column prop="paid_time" label="时间" :formatter="(r: any) => r.paid_time?.slice(0, 16).replace('T', ' ')" />
      </el-table>
    </el-card>

    <!-- 物流 (模式②/③ 在途追踪) -->
    <el-card v-if="logistics || (isBusiness && order.status !== 'CANCEL')" class="mt">
      <template #header>
        <div class="head">
          <span>物流跟踪</span>
          <el-button v-if="isBusiness && !logistics" size="small" type="primary" @click="showLogistics = true">登记运单(叫车)</el-button>
        </div>
      </template>
      <template v-if="logistics">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="运单号">{{ logistics.waybill_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="司机">{{ logistics.driver_name }} {{ logistics.driver_phone }}</el-descriptions-item>
          <el-descriptions-item label="车牌">{{ logistics.plate_no }}</el-descriptions-item>
        </el-descriptions>
        <el-timeline style="margin-top: 12px">
          <el-timeline-item v-for="t in logistics.tracks" :key="t.track_time"
            :timestamp="t.track_time.slice(0, 16).replace('T', ' ')">{{ t.address }}</el-timeline-item>
        </el-timeline>
        <div v-if="isBusiness" class="scan-box">
          <el-input v-model="trackInput" placeholder="录入轨迹点, 如: 到达郑州中转站" style="width: 320px" />
          <el-button @click="onTrack">更新轨迹</el-button>
        </div>
      </template>
      <span v-else class="tip">暂无物流信息（模式①客户自提可不出运单）</span>
    </el-card>

    <!-- 状态时间线 -->
    <el-card class="mt">
      <template #header>流转记录</template>
      <el-timeline>
        <el-timeline-item v-for="e in order.events" :key="e.created_time + e.to_status"
          :timestamp="e.created_time.slice(0, 16).replace('T', ' ')">
          <b>{{ e.to_status_text }}</b> — {{ e.remark }}
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- 开出库单对话框 -->
    <el-dialog v-model="showOutbound" title="开具出库单" width="460px">
      <el-form :model="obForm" label-width="90px">
        <el-form-item label="车牌号" required><el-input v-model="obForm.plate_no" /></el-form-item>
        <el-form-item label="司机姓名" required><el-input v-model="obForm.driver_name" /></el-form-item>
        <el-form-item label="司机电话" required><el-input v-model="obForm.driver_phone" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showOutbound = false">取消</el-button>
        <el-button type="primary" @click="onCreateOutbound">开具</el-button>
      </template>
    </el-dialog>
    <!-- 登记运单对话框 -->
    <el-dialog v-model="showLogistics" title="登记运单（运满满端口就绪前人工录入）" width="460px">
      <el-form label-width="90px">
        <el-form-item label="运单号"><el-input v-model="waybillNo" /></el-form-item>
        <el-form-item label="车牌号" required><el-input v-model="obForm.plate_no" /></el-form-item>
        <el-form-item label="司机姓名" required><el-input v-model="obForm.driver_name" /></el-form-item>
        <el-form-item label="司机电话" required><el-input v-model="obForm.driver_phone" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showLogistics = false">取消</el-button>
        <el-button type="primary" @click="onCreateLogistics">登记</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import QrcodeVue from 'qrcode.vue'
import {
  addOutboundFile, addTrack, cancelOrder, confirmOutbound, createLogistics, createOutbound,
  getLogisticsByOrder, getOrderDetail, getOutboundByOrder, getPayRecords, getVoucher,
  pay, uploadFile, verifyVoucher
} from '../../api/biz'
import { useUserStore } from '../../store/user'

const route = useRoute()
const store = useUserStore()
const orderId = Number(route.params.id)

const order = ref<any>(null)
const outbound = ref<any>(null)
const voucher = ref<any>(null)
const records = ref<any[]>([])
const showOutbound = ref(false)
const showLogistics = ref(false)
const logistics = ref<any>(null)
const trackInput = ref('')
const scanInput = ref('')
const photoInput = ref<HTMLInputElement>()
const obForm = reactive({ plate_no: '', driver_name: '', driver_phone: '' })

const isCustomer = computed(() => store.hasRole('CUSTOMER'))
const isFarm = computed(() => store.hasRole('FARM'))
const isBusiness = computed(() => store.hasRole('BUSINESS'))
// 装车凭证上传: 仅本单三方(养殖户/客户/平台业务), 财务等不显示按钮
const canUploadVoucher = computed(() => isFarm.value || isCustomer.value || isBusiness.value)

async function load() {
  order.value = await getOrderDetail(orderId)
  outbound.value = await getOutboundByOrder(orderId)
  voucher.value = await getVoucher(orderId)
  records.value = await getPayRecords(orderId)
  logistics.value = await getLogisticsByOrder(orderId)
}

async function onPay(type: 'DEPOSIT' | 'TAIL') {
  await ElMessageBox.confirm(`确认支付${type === 'DEPOSIT' ? '定金' : '尾款'}？（模拟支付通道）`, '支付确认')
  const resp: any = await pay(orderId, type)
  ElMessage.success(`支付成功 ¥${resp?.amount}`)
  load()
}

async function onCancel() {
  await ElMessageBox.confirm('确认取消订单？', '提示', { type: 'warning' })
  await cancelOrder(orderId)
  ElMessage.success('订单已取消')
  load()
}

async function onCreateOutbound() {
  await createOutbound({ order_id: orderId, ...obForm })
  ElMessage.success('出库单已开具')
  showOutbound.value = false
  load()
}

async function onConfirm(side: 'seller' | 'buyer' | 'platform') {
  const resp: any = await confirmOutbound(outbound.value.id, side)
  ElMessage.success(resp?.message ?? '确认成功')
  load()
}

function openFile(f: any) {
  if (f.url) window.open(f.url, '_blank')
  else ElMessage.info('文件链接不可用')
}

async function onPhoto(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const resp = (await uploadFile(file, 'OUTBOUND_PHOTO')) as { file_id: number }
  await addOutboundFile(outbound.value.id, resp.file_id, file.type.startsWith('video') ? 'VIDEO' : 'PHOTO')
  ElMessage.success('已上传(自动加水印)')
  load()
}

async function onVerify() {
  if (!scanInput.value) return ElMessage.warning('请输入二维码内容')
  await verifyVoucher(scanInput.value)
  ElMessage.success('核销成功，放行！')
  load()
}

async function onCreateLogistics() {
  await createLogistics({ order_id: orderId, waybill_no: waybillNo.value, ...obForm })
  ElMessage.success('运单已登记')
  showLogistics.value = false
  load()
}

async function onTrack() {
  if (!trackInput.value) return
  await addTrack(logistics.value.id, trackInput.value)
  trackInput.value = ''
  ElMessage.success('轨迹已更新')
  load()
}

const waybillNo = ref('')

onMounted(load)
</script>

<style scoped>
.mt { margin-top: 16px; }
.head { display: flex; justify-content: space-between; align-items: center; }
.actions { margin-top: 16px; }
.confirms { margin-top: 12px; display: flex; gap: 8px; align-items: center; }
.voucher { display: flex; gap: 20px; align-items: flex-start; }
.scan-box { margin-top: 10px; display: flex; gap: 8px; }
.tip { color: #909399; font-size: 13px; }
.file-tag { cursor: pointer; }
</style>
