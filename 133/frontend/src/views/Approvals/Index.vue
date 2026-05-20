<template>
  <div class="approvals-page">
    <h2>我的审批</h2>
    
    <el-card style="margin-top: 20px">
      <el-table :data="approvals" v-loading="loading">
        <el-table-column prop="submission.form.name" label="表单名称" />
        <el-table-column prop="submission.submitter.name" label="提交人" />
        <el-table-column prop="step_order" label="审批步骤" width="100">
          <template #default="{ row }">第 {{ row.step_order }} 步</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">查看</el-button>
            <el-button link type="success" @click="approve(row)" v-if="row.status === 'pending'">通过</el-button>
            <el-button link type="danger" @click="reject(row)" v-if="row.status === 'pending'">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <el-dialog v-model="detailVisible" title="审批详情" width="600px">
      <div v-if="currentApproval">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="表单名称">{{ currentApproval.submission?.form?.name }}</el-descriptions-item>
          <el-descriptions-item label="提交人">{{ currentApproval.submission?.submitter?.name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentApproval.status)">{{ getStatusText(currentApproval.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="审批时间">{{ currentApproval.approved_at || '-' }}</el-descriptions-item>
        </el-descriptions>
        <el-descriptions v-if="currentApproval.comment" :column="1" border style="margin-top: 20px">
          <el-descriptions-item label="审批意见">{{ currentApproval.comment }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin: 20px 0 10px">提交数据</h4>
        <el-descriptions :column="1" border>
          <el-descriptions-item v-for="(value, key) in currentApproval.submission?.data" :key="key" :label="key">{{ value }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
    
    <el-dialog v-model="rejectVisible" title="拒绝审批" width="500px">
      <el-form label-width="80px">
        <el-form-item label="拒绝理由">
          <el-input v-model="rejectComment" type="textarea" :rows="4" placeholder="请输入拒绝理由" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmReject" :loading="processing">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const loading = ref(false)
const processing = ref(false)
const approvals = ref([])
const detailVisible = ref(false)
const rejectVisible = ref(false)
const currentApproval = ref(null)
const rejectComment = ref('')

onMounted(() => {
  loadApprovals()
})

const loadApprovals = async () => {
  loading.value = true
  try {
    const response = await axios.get('/my-approvals')
    approvals.value = response.data.data || []
  } catch (error) {
    ElMessage.error('加载审批失败')
  } finally {
    loading.value = false
  }
}

const getStatusType = (status) => {
  const types = { approved: 'success', rejected: 'danger', pending: 'warning', waiting: 'info', cancelled: 'info' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { approved: '已通过', rejected: '已拒绝', pending: '待处理', waiting: '等待中', cancelled: '已取消' }
  return texts[status] || status
}

const viewDetail = (row) => {
  currentApproval.value = row
  detailVisible.value = true
}

const approve = async (row) => {
  try {
    await ElMessageBox.confirm('确定要通过这个审批吗？', '提示')
    processing.value = true
    await axios.post(`/approvals/${row.id}/approve`)
    ElMessage.success('审批成功')
    loadApprovals()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  } finally {
    processing.value = false
  }
}

const reject = (row) => {
  currentApproval.value = row
  rejectComment.value = ''
  rejectVisible.value = true
}

const confirmReject = async () => {
  if (!rejectComment.value.trim()) {
    ElMessage.warning('请输入拒绝理由')
    return
  }
  processing.value = true
  try {
    await axios.post(`/approvals/${currentApproval.value.id}/reject`, { comment: rejectComment.value })
    ElMessage.success('已拒绝')
    rejectVisible.value = false
    loadApprovals()
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    processing.value = false
  }
}
</script>

<style scoped>
h2 {
  margin-bottom: 20px;
}
</style>
