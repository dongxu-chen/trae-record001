<template>
  <div class="submissions-page">
    <div class="page-header">
      <h2>提交数据</h2>
      <el-button type="primary" @click="exportData">
        <el-icon><Download /></el-icon>
        导出
      </el-button>
    </div>
    
    <el-card>
      <el-table :data="submissions" v-loading="loading">
        <el-table-column prop="form.name" label="表单名称" />
        <el-table-column prop="submitter.name" label="提交人" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <el-dialog v-model="detailVisible" title="提交详情" width="600px">
      <div v-if="currentSubmission">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="表单名称">{{ currentSubmission.form?.name }}</el-descriptions-item>
          <el-descriptions-item label="提交人">{{ currentSubmission.submitter?.name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentSubmission.status)">{{ getStatusText(currentSubmission.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ currentSubmission.created_at }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin: 20px 0 10px">提交数据</h4>
        <el-descriptions :column="1" border>
          <el-descriptions-item v-for="(value, key) in currentSubmission.data" :key="key" :label="key">{{ value }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const loading = ref(false)
const submissions = ref([])
const detailVisible = ref(false)
const currentSubmission = ref(null)

onMounted(() => {
  loadSubmissions()
})

const loadSubmissions = async () => {
  loading.value = true
  try {
    const response = await axios.get('/submissions')
    submissions.value = response.data.data || []
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const getStatusType = (status) => {
  const types = { approved: 'success', rejected: 'danger', pending_approval: 'warning' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { approved: '已通过', rejected: '已拒绝', pending_approval: '审批中' }
  return texts[status] || status
}

const viewDetail = (row) => {
  currentSubmission.value = row
  detailVisible.value = true
}

const exportData = async () => {
  try {
    const response = await axios.post('/submissions/export', { format: 'csv' }, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'submissions.csv')
    document.body.appendChild(link)
    link.click()
    link.remove()
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}
</style>
