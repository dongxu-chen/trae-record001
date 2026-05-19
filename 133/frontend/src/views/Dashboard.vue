<template>
  <div class="dashboard">
    <h2>仪表盘</h2>
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409EFF">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.forms }}</div>
              <div class="stat-label">表单数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67C23A">
              <el-icon><DataLine /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.submissions }}</div>
              <div class="stat-label">提交数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #E6A23C">
              <el-icon><Timer /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pendingApprovals }}</div>
              <div class="stat-label">待审批</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #F56C6C">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.approvalFlows }}</div>
              <div class="stat-label">审批流程</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>最近表单</span>
          </template>
          <el-table :data="recentForms" style="width: 100%">
            <el-table-column prop="name" label="表单名称" />
            <el-table-column prop="created_at" label="创建时间" />
            <el-table-column label="状态">
              <template #default="{ row }">
                <el-tag :type="row.is_published ? 'success' : 'info'">
                  {{ row.is_published ? '已发布' : '草稿' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>待我审批</span>
          </template>
          <el-table :data="pendingApprovals" style="width: 100%">
            <el-table-column prop="submission.form.name" label="表单" />
            <el-table-column prop="submission.submitted_by.name" label="提交人" />
            <el-table-column prop="submission.created_at" label="提交时间" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Document, DataLine, Timer, Connection } from '@element-plus/icons-vue'
import axios from 'axios'

const stats = ref({
  forms: 0,
  submissions: 0,
  pendingApprovals: 0,
  approvalFlows: 0
})

const recentForms = ref([])
const pendingApprovals = ref([])

onMounted(() => {
  loadDashboard()
})

const loadDashboard = async () => {
  try {
    const [formsRes, approvalsRes, flowsRes] = await Promise.all([
      axios.get('/forms'),
      axios.get('/my-approvals'),
      axios.get('/approval-flows')
    ])
    
    recentForms.value = formsRes.data.data?.slice(0, 5) || []
    pendingApprovals.value = approvalsRes.data.data?.filter(a => a.status === 'pending').slice(0, 5) || []
    
    stats.value.forms = formsRes.data.data?.length || 0
    stats.value.pendingApprovals = pendingApprovals.value.length
    stats.value.approvalFlows = flowsRes.data.data?.length || 0
  } catch (error) {
    console.error('加载仪表盘数据失败', error)
  }
}
</script>

<style scoped>
.dashboard h2 {
  margin-bottom: 20px;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}
</style>
