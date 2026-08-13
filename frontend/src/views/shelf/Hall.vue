<template>
  <div>
    <div class="filters">
      <el-select v-model="filters.designated" clearable placeholder="养殖户类型" style="width: 160px" @change="load">
        <el-option label="指定养殖户" :value="true" />
        <el-option label="非指定养殖户" :value="false" />
      </el-select>
      <el-select v-model="filters.grade" clearable placeholder="品级" style="width: 120px; margin-left: 8px" @change="load">
        <el-option v-for="g in grades" :key="g.code" :label="g.name" :value="g.code" />
      </el-select>
    </div>
    <el-row :gutter="16">
      <el-col v-for="item in list" :key="item.id" :span="8">
        <el-card class="goods" shadow="hover">
          <div class="title">鸡蛋 {{ item.grade }}级 · {{ specName(item.spec) }}</div>
          <div class="price">¥{{ item.price }} <span class="unit">/ 枚</span></div>
          <div class="meta">库存 {{ item.quantity }} 枚 ｜ 来源: {{ item.source_enterprise }}</div>
          <div class="meta">交割仓: {{ item.dw_no }}</div>
          <el-button type="primary" style="width: 100%; margin-top: 10px" @click="openBuy(item)">采购</el-button>
        </el-card>
      </el-col>
    </el-row>
    <el-empty v-if="!list.length" description="暂无在售现货" />

    <el-dialog v-model="showBuy" title="建单采购" width="480px">
      <template v-if="current">
        <p>{{ current.grade }}级 / {{ specName(current.spec) }}，单价 ¥{{ current.price }}，库存 {{ current.quantity }}</p>
        <el-form :model="buyForm" label-width="110px">
          <el-form-item label="采购数量(枚)" required>
            <el-input-number v-model="buyForm.quantity" :min="1" :max="current.quantity" />
          </el-form-item>
          <el-form-item label="销售模式" required>
            <el-radio-group v-model="buyForm.sale_mode">
              <el-radio-button value="M1">①蛋库出库标准</el-radio-button>
              <el-radio-button value="M2">②在途货物预付</el-radio-button>
              <el-radio-button value="M3">③渠道账期</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="buyForm.sale_mode === 'M3'" label="账期天数" required>
            <el-input-number v-model="buyForm.credit_days" :min="1" :max="180" />
          </el-form-item>
          <el-form-item label="预估总额">
            <span class="total">¥{{ (buyForm.quantity * current.price).toFixed(2) }}</span>
            <span class="tip">（定金 20% = ¥{{ (buyForm.quantity * current.price * 0.2).toFixed(2) }}）</span>
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="showBuy = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onBuy">提交采购订单</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createPurchase, getDict, getShelfList } from '../../api/biz'

const router = useRouter()
const list = ref<any[]>([])
const grades = ref<any[]>([])
const specs = ref<any[]>([])
const filters = reactive<{ designated: boolean | '' ; grade: string }>({ designated: '', grade: '' })
const showBuy = ref(false)
const submitting = ref(false)
const current = ref<any>(null)
const buyForm = reactive({ quantity: 100, sale_mode: 'M1', credit_days: 60 })

const specName = (code: string) => specs.value.find((s) => s.code === code)?.name ?? code

async function load() {
  const params: Record<string, unknown> = {}
  if (filters.designated !== '') params.designated = filters.designated
  if (filters.grade) params.grade = filters.grade
  list.value = await getShelfList(params)
}

function openBuy(item: any) {
  current.value = item
  buyForm.quantity = Math.min(100, item.quantity)
  showBuy.value = true
}

async function onBuy() {
  submitting.value = true
  try {
    const resp: any = await createPurchase({
      shelf_item_id: current.value.id,
      quantity: buyForm.quantity,
      sale_mode: buyForm.sale_mode,
      ...(buyForm.sale_mode === 'M3' ? { credit_days: buyForm.credit_days } : {})
    })
    ElMessage.success('采购订单已提交，待业务审核')
    showBuy.value = false
    router.push(`/order/detail/${resp?.id ?? ''}`)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  load()
  grades.value = await getDict('EGG_GRADE')
  specs.value = await getDict('EGG_SPEC')
})
</script>

<style scoped>
.filters { margin-bottom: 16px; }
.goods { margin-bottom: 16px; }
.title { font-weight: bold; }
.price { color: #f56c6c; font-size: 24px; font-weight: bold; margin: 8px 0; }
.unit { font-size: 13px; color: #909399; }
.meta { color: #606266; font-size: 13px; margin-top: 4px; }
.total { color: #f56c6c; font-weight: bold; }
.tip { color: #909399; font-size: 12px; }
</style>
