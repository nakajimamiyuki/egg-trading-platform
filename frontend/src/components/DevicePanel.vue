<template>
  <div>
    <el-dialog :model-value="visible" title="监控设备管理" width="700px" @close="$emit('close')">
      <div class="bar">
        <span>仓库: {{ warehouse?.name }}</span>
        <el-button type="primary" size="small" @click="showAdd = true">登记设备</el-button>
      </div>
      <el-table :data="devices" border size="small">
        <el-table-column prop="device_name" label="设备名称" min-width="140" />
        <el-table-column prop="protocol" label="协议" width="90" />
        <el-table-column prop="stream_url" label="流地址" min-width="180" show-overflow-tooltip />
        <el-table-column label="在线" width="70">
          <template #default="{ row }">
            <el-tag :type="row.online ? 'success' : 'info'">{{ row.online ? '在线' : '离线' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="确权" width="70">
          <template #default="{ row }">
            <el-tag :type="row.confirmed ? 'success' : 'warning'">{{ row.confirmed ? '已确权' : '未确权' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" :disabled="row.online" @click="onCheck(row)">在线检测</el-button>
            <el-button v-if="canConfirm" size="small" type="primary" :disabled="!row.online || row.confirmed" @click="onConfirm(row)">确权</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="point-map">
        <el-button size="small" @click="mapInput?.click()">上传监控点位图</el-button>
        <input ref="mapInput" type="file" hidden @change="onMapFile" />
        <span v-if="warehouse?.point_map_file_id"> ✓ 已上传(file_id: {{ warehouse.point_map_file_id }})</span>
      </div>
    </el-dialog>

    <el-dialog v-model="showAdd" title="登记监控设备" width="480px" append-to-body>
      <el-form :model="addForm" label-width="90px">
        <el-form-item label="设备名称"><el-input v-model="addForm.device_name" /></el-form-item>
        <el-form-item label="协议">
          <el-select v-model="addForm.protocol">
            <el-option label="RTSP" value="RTSP" />
            <el-option label="GB28181" value="GB28181" />
            <el-option label="其他" value="OTHER" />
          </el-select>
        </el-form-item>
        <el-form-item label="流地址"><el-input v-model="addForm.stream_url" placeholder="rtsp://..." /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="onAdd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { checkDevice, confirmDevice, createDevice, getDevices, uploadFile, uploadPointMap } from '../api/biz'

const props = defineProps<{ visible: boolean; warehouse: any; canConfirm: boolean }>()
const emit = defineEmits(['close', 'changed'])

const devices = ref<any[]>([])
const showAdd = ref(false)
const mapInput = ref<HTMLInputElement>()
const addForm = reactive({ device_name: '', protocol: 'RTSP', stream_url: '' })

async function load() {
  if (props.warehouse?.id) devices.value = await getDevices(props.warehouse.id)
}

async function onAdd() {
  await createDevice({ warehouse_id: props.warehouse.id, ...addForm })
  ElMessage.success('设备已登记')
  showAdd.value = false
  Object.assign(addForm, { device_name: '', stream_url: '' })
  load()
}

async function onCheck(row: any) {
  await checkDevice(row.id)
  ElMessage.success('检测完成：设备在线（模拟）')
  load()
}

async function onConfirm(row: any) {
  const resp: any = await confirmDevice(row.id)
  ElMessage.success(resp?.message ?? '确权完成')
  load()
  emit('changed')
}

async function onMapFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const resp = (await uploadFile(file, 'POINT_MAP')) as { file_id: number }
  await uploadPointMap(props.warehouse.id, resp.file_id)
  ElMessage.success('点位图已上传')
  emit('changed')
}

onMounted(load)
</script>

<style scoped>
.bar { display: flex; justify-content: space-between; margin-bottom: 10px; }
.point-map { margin-top: 12px; }
</style>
