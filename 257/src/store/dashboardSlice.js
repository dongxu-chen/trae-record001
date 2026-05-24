import { createSlice, nanoid } from '@reduxjs/toolkit'
import { mockSalesData, mockUserGrowthData, mockRevenueData, mockTableData } from '../data/mockData'

const currentUser = {
  id: 'user-' + nanoid(6),
  name: '用户' + Math.floor(Math.random() * 1000),
  color: `hsl(${Math.random() * 360}, 70%, 50%)`,
  avatar: '👤',
}

const initialState = {
  components: [],
  filters: {},
  templates: [
    {
      id: 'template-sales',
      name: '销售数据看板',
      description: '包含销售额、订单量、客户增长等核心指标',
      components: [
        { id: 'metric-1', type: 'metric', title: '总销售额', config: { value: '¥1,234,567', trend: '+12.5%', trendUp: true }, position: { col: 0, row: 0, width: 3, height: 2 } },
        { id: 'metric-2', type: 'metric', title: '订单数量', config: { value: '8,456', trend: '+8.2%', trendUp: true }, position: { col: 3, row: 0, width: 3, height: 2 } },
        { id: 'metric-3', type: 'metric', title: '活跃用户', config: { value: '23,456', trend: '+15.3%', trendUp: true }, position: { col: 6, row: 0, width: 3, height: 2 } },
        { id: 'metric-4', type: 'metric', title: '转化率', config: { value: '3.45%', trend: '-0.2%', trendUp: false }, position: { col: 9, row: 0, width: 3, height: 2 } },
        { id: 'chart-1', type: 'chart', title: '月度销售趋势', config: { chartType: 'line', dataKey: 'sales' }, position: { col: 0, row: 2, width: 6, height: 4 } },
        { id: 'chart-2', type: 'chart', title: '产品类别分布', config: { chartType: 'pie', dataKey: 'category' }, position: { col: 6, row: 2, width: 6, height: 4 } },
      ]
    },
    {
      id: 'template-user',
      name: '用户分析看板',
      description: '用户增长、留存、行为分析',
      components: [
        { id: 'metric-1', type: 'metric', title: '新增用户', config: { value: '1,234', trend: '+20.1%', trendUp: true }, position: { col: 0, row: 0, width: 4, height: 2 } },
        { id: 'metric-2', type: 'metric', title: '留存率', config: { value: '68.5%', trend: '+2.3%', trendUp: true }, position: { col: 4, row: 0, width: 4, height: 2 } },
        { id: 'metric-3', type: 'metric', title: '平均停留时长', config: { value: '12分30秒', trend: '+5.0%', trendUp: true }, position: { col: 8, row: 0, width: 4, height: 2 } },
        { id: 'chart-1', type: 'chart', title: '用户增长曲线', config: { chartType: 'bar', dataKey: 'users' }, position: { col: 0, row: 2, width: 12, height: 4 } },
      ]
    }
  ],
  lastUpdated: null,
  isRefreshing: false,
  currentUser,
  marketComponents: [
    {
      id: 'market-1',
      type: 'custom',
      name: 'KPI进度环',
      description: '环形进度展示组件，支持目标值对比',
      author: '张三',
      authorAvatar: '👨‍💼',
      downloads: 1234,
      rating: 4.8,
      tags: ['指标', '可视化'],
      preview: '📊',
      config: {
        value: 75,
        target: 100,
        color: '#52c41a',
      }
    },
    {
      id: 'market-2',
      type: 'custom',
      name: '迷你趋势图',
      description: '小巧的趋势折线图，适合嵌入指标卡',
      author: '李四',
      authorAvatar: '👩‍💻',
      downloads: 892,
      rating: 4.6,
      tags: ['图表', '趋势'],
      preview: '📈',
      config: {
        data: [10, 20, 15, 25, 30, 28, 35],
        color: '#1890ff',
      }
    },
    {
      id: 'market-3',
      type: 'custom',
      name: '热力地图',
      description: '矩阵热力图，展示二维数据分布',
      author: '王五',
      authorAvatar: '🧑‍🎨',
      downloads: 567,
      rating: 4.9,
      tags: ['图表', '热力'],
      preview: '🔥',
      config: {
        rows: ['周一', '周二', '周三'],
        cols: ['上午', '下午', '晚上'],
        data: [[10, 20, 30], [15, 25, 35], [20, 30, 40]],
      }
    },
    {
      id: 'market-4',
      type: 'custom',
      name: '仪表盘',
      description: '经典仪表盘样式，适合展示百分比',
      author: '赵六',
      authorAvatar: '👨‍🔬',
      downloads: 2341,
      rating: 4.7,
      tags: ['指标', '可视化'],
      preview: '🎯',
      config: {
        value: 65,
        min: 0,
        max: 100,
        unit: '%',
      }
    },
  ],
  uploadedComponents: [],
  collaboration: {
    isConnected: false,
    users: [currentUser],
    cursors: {},
    isCollaborating: false,
  },
  alerts: [
    {
      id: 'alert-1',
      componentId: null,
      metricName: '总销售额',
      condition: 'below',
      threshold: 1000000,
      severity: 'warning',
      isActive: false,
      enabled: true,
    },
    {
      id: 'alert-2',
      componentId: null,
      metricName: '转化率',
      condition: 'below',
      threshold: 3,
      severity: 'danger',
      isActive: true,
      enabled: true,
    }
  ],
}

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    addComponent: (state, action) => {
      const { type, position } = action.payload
      const id = `component-${nanoid(8)}`
      const newComponent = {
        id,
        type,
        title: getDefaultTitle(type),
        config: getDefaultConfig(type),
        position,
      }
      state.components.push(newComponent)
    },
    removeComponent: (state, action) => {
      state.components = state.components.filter(c => c.id !== action.payload)
    },
    updateComponentPosition: (state, action) => {
      const { id, position } = action.payload
      const component = state.components.find(c => c.id === id)
      if (component) {
        component.position = position
      }
    },
    updateComponentConfig: (state, action) => {
      const { id, config } = action.payload
      const component = state.components.find(c => c.id === id)
      if (component) {
        component.config = { ...component.config, ...config }
      }
    },
    updateComponentTitle: (state, action) => {
      const { id, title } = action.payload
      const component = state.components.find(c => c.id === id)
      if (component) {
        component.title = title
      }
    },
    setFilter: (state, action) => {
      const { key, value } = action.payload
      state.filters[key] = value
    },
    clearFilters: (state) => {
      state.filters = {}
    },
    applyTemplate: (state, action) => {
      const template = state.templates.find(t => t.id === action.payload)
      if (template) {
        state.components = JSON.parse(JSON.stringify(template.components)).map(c => ({
          ...c,
          id: `${c.type}-${nanoid(8)}`
        }))
        state.filters = {}
      }
    },
    refreshData: (state) => {
      state.isRefreshing = true
      state.components.forEach(component => {
        if (component.type === 'metric') {
          const change = (Math.random() - 0.5) * 10
          const trendUp = change > 0
          component.config = {
            ...component.config,
            value: generateRandomValue(component.title),
            trend: `${trendUp ? '+' : ''}${change.toFixed(1)}%`,
            trendUp
          }
        }
      })
      state.lastUpdated = new Date().toISOString()
      state.isRefreshing = false
      state.alerts.forEach(alert => {
        if (alert.enabled) {
          const randomTrigger = Math.random() > 0.7
          alert.isActive = randomTrigger
        }
      })
    },
    saveLayout: (state) => {
      const layout = {
        components: state.components,
        savedAt: new Date().toISOString()
      }
      localStorage.setItem('dashboard-layout', JSON.stringify(layout))
    },
    loadLayout: (state) => {
      const saved = localStorage.getItem('dashboard-layout')
      if (saved) {
        const layout = JSON.parse(saved)
        state.components = layout.components
      }
    },
    clearLayout: (state) => {
      state.components = []
      state.filters = {}
      localStorage.removeItem('dashboard-layout')
    },
    reorderComponents: (state, action) => {
      const { activeId, overId } = action.payload
      const oldIndex = state.components.findIndex(c => c.id === activeId)
      const newIndex = state.components.findIndex(c => c.id === overId)
      if (oldIndex !== -1 && newIndex !== -1) {
        const [removed] = state.components.splice(oldIndex, 1)
        state.components.splice(newIndex, 0, removed)
      }
    },
    addMarketComponent: (state, action) => {
      const { marketComponent, position } = action.payload
      const id = `component-${nanoid(8)}`
      const newComponent = {
        id,
        type: 'custom',
        title: marketComponent.name,
        config: { ...marketComponent.config, marketId: marketComponent.id },
        position,
      }
      state.components.push(newComponent)
    },
    uploadComponent: (state, action) => {
      const { name, description, tags, preview, config } = action.payload
      const newComponent = {
        id: 'market-' + nanoid(8),
        type: 'custom',
        name,
        description,
        author: state.currentUser.name,
        authorAvatar: state.currentUser.avatar,
        downloads: 0,
        rating: 5.0,
        tags,
        preview,
        config,
      }
      state.marketComponents.push(newComponent)
      state.uploadedComponents.push(newComponent.id)
    },
    startCollaboration: (state) => {
      state.collaboration.isConnected = true
      state.collaboration.isCollaborating = true
      const mockUsers = [
        { id: 'user-1', name: '张三', color: '#f5222d', avatar: '👨‍💼' },
        { id: 'user-2', name: '李四', color: '#fa8c16', avatar: '👩‍💻' },
        { id: 'user-3', name: '王五', color: '#52c41a', avatar: '🧑‍🎨' },
      ].filter(() => Math.random() > 0.3)
      state.collaboration.users = [state.currentUser, ...mockUsers]
    },
    stopCollaboration: (state) => {
      state.collaboration.isConnected = false
      state.collaboration.isCollaborating = false
      state.collaboration.users = [state.currentUser]
      state.collaboration.cursors = {}
    },
    updateCursor: (state, action) => {
      const { userId, x, y, componentId } = action.payload
      state.collaboration.cursors[userId] = { x, y, componentId, updatedAt: Date.now() }
    },
    addAlert: (state, action) => {
      const alert = {
        id: 'alert-' + nanoid(8),
        ...action.payload,
        isActive: false,
      }
      state.alerts.push(alert)
    },
    updateAlert: (state, action) => {
      const { id, ...updates } = action.payload
      const alert = state.alerts.find(a => a.id === id)
      if (alert) {
        Object.assign(alert, updates)
      }
    },
    deleteAlert: (state, action) => {
      state.alerts = state.alerts.filter(a => a.id !== action.payload)
    },
    toggleAlert: (state, action) => {
      const alert = state.alerts.find(a => a.id === action.payload)
      if (alert) {
        alert.enabled = !alert.enabled
      }
    },
  },
})

function getDefaultTitle(type) {
  const titles = {
    chart: '新建图表',
    metric: '指标卡',
    table: '数据表格',
    filter: '筛选器',
    custom: '自定义组件',
  }
  return titles[type] || '组件'
}

function getDefaultConfig(type) {
  switch (type) {
    case 'chart':
      return {
        chartType: 'line',
        dataKey: 'sales',
      }
    case 'metric':
      return {
        value: '0',
        trend: '+0%',
        trendUp: true,
      }
    case 'table':
      return {
        columns: ['名称', '数值', '状态'],
        data: mockTableData,
      }
    case 'filter':
      return {
        filterKey: 'category',
        options: ['全部', '电子产品', '服装', '食品', '家居'],
        value: '全部',
      }
    default:
      return {}
  }
}

function generateRandomValue(title) {
  if (title.includes('销售额') || title.includes('收入')) {
    return `¥${(Math.random() * 2000000 + 500000).toLocaleString().split('.')[0]}`
  }
  if (title.includes('用户') || title.includes('订单')) {
    return (Math.random() * 50000 + 5000).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  }
  if (title.includes('率') || title.includes('百分比')) {
    return `${(Math.random() * 50 + 10).toFixed(2)}%`
  }
  return (Math.random() * 10000).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

export const {
  addComponent,
  removeComponent,
  updateComponentPosition,
  updateComponentConfig,
  updateComponentTitle,
  setFilter,
  clearFilters,
  applyTemplate,
  refreshData,
  saveLayout,
  loadLayout,
  clearLayout,
  reorderComponents,
  addMarketComponent,
  uploadComponent,
  startCollaboration,
  stopCollaboration,
  updateCursor,
  addAlert,
  updateAlert,
  deleteAlert,
  toggleAlert,
} = dashboardSlice.actions

export default dashboardSlice.reducer
