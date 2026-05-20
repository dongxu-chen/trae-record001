import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const pipelineApi = {
  list: () => api.get('/pipelines'),
  get: (id) => api.get(`/pipelines/${id}`),
  create: (data) => api.post('/pipelines', data),
  update: (id, data) => api.put(`/pipelines/${id}`, data),
  delete: (id) => api.delete(`/pipelines/${id}`),
  run: (id, data = {}) => api.post(`/pipelines/${id}/run`, data),
  validateDag: (id) => api.post(`/pipelines/${id}/validate-dag`),
  configure: (id, config) => api.post(`/pipelines/${id}/configure`, config),
  getExecutions: (id) => api.get(`/pipelines/${id}/executions`),
  getExecutionTasks: (executionId) => api.get(`/pipelines/executions/${executionId}/tasks`),
  getCheckpoint: (executionId) => api.get(`/pipelines/executions/${executionId}/checkpoint`),
  resumeExecution: (executionId) => api.post(`/pipelines/executions/${executionId}/resume`)
}

export const dataQualityApi = {
  listRules: (pipelineId) => api.get('/data-quality/rules', { params: { pipeline_id: pipelineId } }),
  getRule: (id) => api.get(`/data-quality/rules/${id}'),
  createRule: (data) => api.post('/data-quality/rules', data),
  deleteRule: (id) => api.delete(`/data-quality/rules/${id}`),
  listResults: (executionId) => api.get('/data-quality/results', { params: { execution_id: executionId } })
}

// 质量规则模板
export const qualityRuleTemplates = {
  nullCheck: {
    type: 'null_check',
    name: '空值检查',
    description: '检查指定列是否存在空值',
    params: {
      columns: [],
      threshold: 0.0
    }
  },
  duplicateCheck: {
    type: 'duplicate_check',
    name: '重复数据检查',
    description: '检查指定列是否存在重复数据',
    params: {
      columns: []
    }
  },
  rangeCheck: {
    type: 'range_check',
    name: '数值范围检查',
    description: '检查数值是否在指定范围内',
    params: {
      column: '',
      min_value: null,
      max_value: null
    }
  },
  regexCheck: {
    type: 'regex_check',
    name: '正则表达式检查',
    description: '使用正则表达式验证数据格式',
    params: {
      column: '',
      pattern: ''
    }
  },
  uniqueCheck: {
    type: 'unique_check',
    name: '唯一性检查',
    description: '检查列值是否唯一',
    params: {
      column: ''
    }
  },
  sqlValidation: {
    type: 'sql_validation',
    name: 'SQL验证',
    description: '使用SQL查询验证数据',
    params: {
      sql_query: '',
      connection_string: '',
      expected_result: {}
    }
  },
  customCondition: {
    type: 'custom_condition',
    name: '自定义条件',
    description: '使用Pandas表达式自定义验证规则',
    params: {
      condition: ''
    }
  }
}

export default api
