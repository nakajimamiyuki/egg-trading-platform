<template>
  <el-card>
    <template #header>
      <div class="head">
        <span>产蛋数据录入</span>
        <el-button type="primary" @click="showCreate = true">录入产蛋数据</el-button>
      </div>
    </template>
    <el-table :data="list" border>
      <el-table-column prop="prod_date" label="日期" width="120" />
      <el-table-column prop="quantity" label="数量(枚)" width="120" />
      <el-table-column prop="grade" label="品级" width="100" />
      <el-table-column prop="spec" label="规格" width="120" />
      <el-table-column prop="created_time" label="录入时间"
        :formatter="(r: any) => r.created_time.slice(0, 16).replace('T', ' ')" />
    </el-table>

    <el-dialog v-model="showCreate" title="录入产蛋数据" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="日期" required>
          <el-date-picker v-model="form.prod_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="数量(枚)" required><el-input-number v-model="form.quantity" :min="1" /></el-form-item>
        <el-form-item label="品级" required>
          <el-select v-model="form.grade">
            <el-option v-for="g in grades" :key="g.code" :label="g.name" :value="g.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="规格" required>
          <el-select v-model="form.spec">
            <el-option v-for="s in specs" :key="s.code" :label="s.name" :value="s.code" />
          </el-select>
        </el-form-item>
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
import { createProduction, getDict, getMyProduction } from '../../api/biz'

const list = ref<any[]>([])
const showCreate = ref(false)
const grades = ref<any[]>([])
const specs = ref<any[]>([])
const form = reactive({ prod_date: new Date().toISOString().slice(0, 10), quantity: 1000, grade: 'A', spec: 'S50' })

async function load() { list.value = await getMyProduction() }

async function onCreate() {
  await createProduction({ ...form })
  ElMessage.success('产蛋数据已录入')
  showCreate.value = false
  load()
}

onMounted(async () => {
  load()
  grades.value = await getDict('EGG_GRADE')
  specs.value = await getDict('EGG_SPEC')
})
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
</style>
