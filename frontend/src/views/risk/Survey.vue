<template>
  <el-card>
    <template #header>
      <div class="head">
        <span>渠道风控尽调（F1.3）</span>
        <el-button type="primary" @click="showCreate = true">登记尽调结论</el-button>
      </div>
    </template>
    <el-alert type="info" :closable="false" style="margin-bottom: 12px"
      title="渠道方(如京东)须尽调通过后才能启用渠道账期模式(模式③)" />
    <el-table :data="list" border>
      <el-table-column prop="enterprise_name" label="渠道方" min-width="160" />
      <el-table-column label="结论" width="100">
        <template #default="{ row }">
          <el-tag :type="{ WAIT: 'warning', PASS: 'success', REJECT: 'danger' }[row.conclusion as string] as any">
            {{ { WAIT: '尽调中', PASS: '通过', REJECT: '不通过' }[row.conclusion as string] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="200" />
      <el-table-column prop="created_time" label="时间" width="160"
        :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
    </el-table>

    <el-dialog v-model="showCreate" title="登记尽调结论" width="480px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="渠道方企业" required>
          <el-select v-model="form.enterprise_id" style="width: 100%">
            <el-option v-for="e in buyers" :key="e.id" :label="e.enterprise_name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="尽调结论" required>
          <el-radio-group v-model="form.conclusion">
            <el-radio-button value="PASS">通过</el-radio-button>
            <el-radio-button value="REJECT">不通过</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="评价报告">
          <input type="file" @change="onReportFile" />
          <span v-if="form.report_file_id" style="color:#67c23a"> ✓ 已上传</span>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="onCreate">提交</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { createSurvey, getEnterpriseList, getSurveyList, uploadFile } from '../../api/biz'

const list = ref<any[]>([])
const buyers = ref<any[]>([])
const showCreate = ref(false)
const form = reactive({ enterprise_id: null as number | null, conclusion: 'PASS', remark: '', report_file_id: undefined as number | undefined })

async function load() {
  list.value = await getSurveyList()
  const ents: any[] = await getEnterpriseList({ type: 'BUYER' })
  buyers.value = ents
}

async function onReportFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const resp = (await uploadFile(file, 'RISK_REPORT')) as { file_id: number }
  form.report_file_id = resp.file_id
}

async function onCreate() {
  if (!form.enterprise_id) return ElMessage.warning('请选择渠道方企业')
  await createSurvey({ enterprise_id: form.enterprise_id, conclusion: form.conclusion, remark: form.remark, report_file_id: form.report_file_id })
  ElMessage.success('尽调结论已登记')
  showCreate.value = false
  load()
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
