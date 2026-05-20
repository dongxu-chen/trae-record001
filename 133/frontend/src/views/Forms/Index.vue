<template>
  <div class="forms-page">
    <div class="page-header">
      <h2>表单管理</h2>
      <el-button type="primary" @click="$router.push('/forms/create')">
        <el-icon><Plus /></el-icon>
        新建表单
      </el-button>
    </div>
    
    <el-card>
      <el-table :data="forms" v-loading="loading">
        <el-table-column prop="name" label="表单名称" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="creator.name" label="创建人" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag :type="row.is_published ? 'success' : 'info'">
              {{ row.is_published ? '已发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewForm(row)">查看</el-button>
            <el-button link type="primary" @click="editForm(row)">编辑</el-button>
            <el-button link type="success" @click="publishForm(row)" v-if="!row.is_published">发布</el-button>
            <el-button link type="danger" @click="deleteForm(row)">删除</el-button>
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
const forms = ref([])

onMounted(() => {
  loadForms()
})

const loadForms = async () => {
  loading.value = true
  try {
    const response = await axios.get('/forms')
    forms.value = response.data.data || []
  } catch (error) {
    ElMessage.error('加载表单失败')
  } finally {
    loading.value = false
  }
}

const viewForm = (row) => {
  router.push(`/forms/${row.id}`)
}

const editForm = (row) => {
  router.push(`/forms/${row.id}/edit`)
}

const publishForm = async (row) => {
  try {
    await axios.post(`/forms/${row.id}/publish`)
    ElMessage.success('发布成功')
    loadForms()
  } catch (error) {
    ElMessage.error('发布失败')
  }
}

const deleteForm = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个表单吗？', '提示')
    await axios.delete(`/forms/${row.id}`)
    ElMessage.success('删除成功')
    loadForms()
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
