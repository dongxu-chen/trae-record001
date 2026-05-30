const API_BASE = '/api'

async function request(url, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error(`API请求失败 ${url}:`, error)
    throw error
  }
}

export const api = {
  health: async () => {
    return await request('/health', { method: 'GET' })
  },

  analyzeColumn: async (columnData, columnName) => {
    return await request('/analyze', {
      method: 'POST',
      body: JSON.stringify({ columnData, columnName })
    })
  },

  analyzeAll: async (data) => {
    return await request('/analyze/batch', {
      method: 'POST',
      body: JSON.stringify({ data })
    })
  },

  recommendRules: async (analysis) => {
    return await request('/rules/recommend', {
      method: 'POST',
      body: JSON.stringify({ analysis })
    })
  },

  executeFill: async (rule, columnData, config, fullData, colIndex) => {
    return await request('/fill/execute', {
      method: 'POST',
      body: JSON.stringify({ rule, columnData, config, fullData, colIndex })
    })
  },

  batchFill: async (data, rules) => {
    return await request('/fill/batch', {
      method: 'POST',
      body: JSON.stringify({ data, rules })
    })
  },

  getAllRules: async () => {
    return await request('/rules', { method: 'GET' })
  },

  importCSV: async (csv) => {
    return await request('/import/csv', {
      method: 'POST',
      body: JSON.stringify({ csv })
    })
  }
}

export default api
