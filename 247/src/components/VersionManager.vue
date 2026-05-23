<template>
  <div class="version-manager">
    <div class="version-header">
      <h3>版本管理</h3>
      <button class="btn btn-primary btn-small" @click="publishVersion">发布新版本</button>
    </div>

    <div v-if="versions.length === 0" class="empty-tip">
      暂无版本记录
    </div>

    <div v-else class="version-list">
      <div
        v-for="version in versions"
        :key="version.id"
        class="version-item"
        :class="{ active: currentVersion === version.version }"
      >
        <div class="version-info">
          <span class="version-tag">v{{ version.version }}</span>
          <span class="version-date">{{ formatDate(version.createdAt) }}</span>
        </div>
        <div class="version-desc">{{ version.description || '无描述' }}</div>
        <div class="version-actions">
          <button class="btn btn-default btn-small" @click="restoreVersion(version)">恢复此版本</button>
          <button class="btn btn-default btn-small" @click="viewSchema(version)">查看Schema</button>
        </div>
      </div>
    </div>

    <div v-if="showPublishModal" class="modal-mask" @click.self="showPublishModal = false">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">发布新版本</span>
          <button class="modal-close" @click="showPublishModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="config-item">
            <label class="config-label">版本号</label>
            <input
              type="number"
              class="config-input"
              v-model.number="newVersion"
              :min="1"
              :step="0.1"
            />
          </div>
          <div class="config-item">
            <label class="config-label">版本描述</label>
            <textarea
              class="config-input"
              v-model="versionDescription"
              rows="3"
              placeholder="描述此版本的变更内容..."
            ></textarea>
          </div>
          <div class="config-item">
            <label class="config-label">字段映射（数据迁移）</label>
            <div class="mapping-hint">
              当字段名称变更时，配置旧字段到新字段的映射关系，用于迁移已有数据
            </div>
            <div v-for="(mapping, index) in fieldMappings" :key="index" class="mapping-row">
              <select class="config-input" v-model="mapping.oldField">
                <option value="">旧字段</option>
                <option v-for="field in allFields" :key="field" :value="field">{{ field }}</option>
              </select>
              <span class="mapping-arrow">→</span>
              <select class="config-input" v-model="mapping.newField">
                <option value="">新字段</option>
                <option v-for="field in currentFields" :key="field" :value="field">{{ field }}</option>
              </select>
              <button class="btn btn-default btn-small" @click="removeMapping(index)">删除</button>
            </div>
            <button class="btn btn-default btn-small" @click="addMapping">+ 添加映射</button>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-default" @click="showPublishModal = false">取消</button>
          <button class="btn btn-primary" @click="confirmPublish">发布</button>
        </div>
      </div>
    </div>

    <div v-if="showSchemaModal" class="modal-mask" @click.self="showSchemaModal = false">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">Schema 详情</span>
          <button class="modal-close" @click="showSchemaModal = false">×</button>
        </div>
        <div class="modal-body">
          <pre class="code-block">{{ JSON.stringify(selectedSchema, null, 2) }}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn btn-default" @click="showSchemaModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { VersionManager as VM, FormDataStorage } from '../utils/IndexedDB.js'

const props = defineProps({
  formId: {
    type: String,
    default: 'default_form'
  },
  formItems: {
    type: Array,
    default: () => []
  },
  currentVersion: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['versionChange', 'restoreVersion'])

const versions = ref([])
const showPublishModal = ref(false)
const showSchemaModal = ref(false)
const newVersion = ref(1)
const versionDescription = ref('')
const fieldMappings = ref([])
const selectedSchema = ref(null)

const currentFields = computed(() => {
  return props.formItems.map(item => item.field)
})

const allFields = computed(() => {
  const fields = new Set(currentFields.value)
  versions.value.forEach(v => {
    if (v.schema?.properties) {
      Object.keys(v.schema.properties).forEach(f => fields.add(f))
    }
  })
  return Array.from(fields)
})

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadVersions = async () => {
  versions.value = await VM.getVersions(props.formId)
  if (versions.value.length > 0) {
    newVersion.value = versions.value[0].version + 1
  }
}

const publishVersion = () => {
  showPublishModal.value = true
  fieldMappings.value = []
}

const addMapping = () => {
  fieldMappings.value.push({ oldField: '', newField: '' })
}

const removeMapping = (index) => {
  fieldMappings.value.splice(index, 1)
}

const confirmPublish = async () => {
  const schema = {
    type: 'object',
    properties: {},
    required: []
  }

  props.formItems.forEach(item => {
    schema.properties[item.field] = {
      type: item.type === 'number' ? 'number' : 'string',
      title: item.label
    }
    if (item.required) {
      schema.required.push(item.field)
    }
  })

  const mapping = {}
  fieldMappings.value.forEach(m => {
    if (m.oldField && m.newField) {
      mapping[m.oldField] = m.newField
    }
  })

  const version = await VM.createVersion(
    props.formId,
    newVersion.value,
    schema,
    versionDescription.value
  )

  if (Object.keys(mapping).length > 0) {
    await VM.setFieldMapping(props.formId, newVersion.value, mapping)
  }

  const latestData = await FormDataStorage.getLatestFormData(props.formId)
  if (latestData) {
    const newSchema = { ...schema, fieldMapping: mapping }
    const migratedData = await VM.migrateData(
      latestData.data,
      latestData.version,
      newSchema
    )
    await FormDataStorage.saveFormData(props.formId, newVersion.value, migratedData)
  }

  await loadVersions()
  showPublishModal.value = false
  emit('versionChange', newVersion.value)
  newVersion.value++
}

const restoreVersion = (version) => {
  emit('restoreVersion', version)
}

const viewSchema = (version) => {
  selectedSchema.value = version.schema
  showSchemaModal.value = true
}

onMounted(() => {
  loadVersions()
})
</script>

<style scoped>
.version-manager {
  padding: 16px;
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.version-header h3 {
  margin: 0;
  font-size: 16px;
}

.version-list {
  max-height: 400px;
  overflow-y: auto;
}

.version-item {
  padding: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  margin-bottom: 8px;
  background: #fafafa;
}

.version-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.version-info {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.version-tag {
  padding: 2px 8px;
  background: #409eff;
  color: #fff;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.version-date {
  font-size: 12px;
  color: #909399;
}

.version-desc {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.version-actions {
  display: flex;
  gap: 8px;
}

.mapping-hint {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.mapping-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.mapping-arrow {
  color: #909399;
}

.mapping-row .config-input {
  flex: 1;
}
</style>
