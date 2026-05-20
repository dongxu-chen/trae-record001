<template>
  <div class="flows-page">
    <div class="page-header">
      <h2>审批流程</h2>
      <el-button type="primary" @click="$router.push('/approval-flows/create')">
        <el-icon><Plus /></el-icon>
        新建流程
      </el-button>
    </div>
    
    <el-card>
      <el-table :data="flows" v-loading="loading">
        <el-table-column prop="name" label="流程名称" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="editFlow(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteFlow(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const loading = ref(false)
const flows = ref([])

onMounted(() => {
  loadFlows()
})

const loadFlows = async () => {
  loading.value = true
  try {
    const response = await axios.get('/approval-flows')
    flows.value = response.data.data || []
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const editFlow = (row) => {
  router.push(`/approval-flows/${row.id}/edit`)
}

const deleteFlow = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个流程吗？', '提示')
    await axios.delete(`/approval-flows/${row.id}`)
    ElMessage.success('删除成功')
    loadFlows()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
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
