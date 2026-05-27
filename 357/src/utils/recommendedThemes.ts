import type { RecommendedTheme, ChartTheme } from '@/types/theme';

const baseDarkTheme: Partial<ChartTheme> = {
  backgroundColor: '#141414',
  textStyle: {
    color: '#e8e8e8',
  },
  title: {
    textStyle: {
      color: '#e8e8e8',
    },
    subtextStyle: {
      color: '#bfbfbf',
    },
  },
  legend: {
    textStyle: {
      color: '#e8e8e8',
    },
  },
  categoryAxis: {
    axisLine: {
      lineStyle: {
        color: '#8c8c8c',
      },
    },
    axisTick: {
      lineStyle: {
        color: '#8c8c8c',
      },
    },
    axisLabel: {
      color: '#bfbfbf',
    },
    splitLine: {
      lineStyle: {
        color: '#434343',
      },
    },
  },
  valueAxis: {
    axisLabel: {
      color: '#bfbfbf',
    },
    splitLine: {
      lineStyle: {
        color: '#434343',
      },
    },
  },
  tooltip: {
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    textStyle: {
      color: '#333333',
    },
  },
  grid: {
    borderColor: '#434343',
  },
};

const baseLightTheme: Partial<ChartTheme> = {
  backgroundColor: '#ffffff',
  textStyle: {
    color: '#333333',
  },
  title: {
    textStyle: {
      color: '#333333',
    },
    subtextStyle: {
      color: '#666666',
    },
  },
  legend: {
    textStyle: {
      color: '#333333',
    },
  },
  categoryAxis: {
    axisLine: {
      lineStyle: {
        color: '#666666',
      },
    },
    axisTick: {
      lineStyle: {
        color: '#666666',
      },
    },
    axisLabel: {
      color: '#666666',
    },
    splitLine: {
      lineStyle: {
        color: '#e0e0e0',
      },
    },
  },
  valueAxis: {
    axisLabel: {
      color: '#666666',
    },
    splitLine: {
      lineStyle: {
        color: '#e0e0e0',
      },
    },
  },
  tooltip: {
    backgroundColor: 'rgba(50, 50, 50, 0.9)',
    textStyle: {
      color: '#ffffff',
    },
  },
  grid: {
    borderColor: '#e0e0e0',
  },
};

export const recommendedThemes: RecommendedTheme[] = [
  {
    id: 'dashboard-cyber',
    name: '科技大屏',
    description: '深色科技感，适合数据大屏、监控驾驶舱',
    category: 'dashboard',
    categoryName: '数据大屏',
    previewColors: ['#00d4ff', '#00ff88', '#ffd700', '#ff6b6b', '#a855f7'],
    theme: {
      ...baseDarkTheme,
      color: ['#00d4ff', '#00ff88', '#ffd700', '#ff6b6b', '#a855f7', '#f472b6', '#22d3ee', '#84cc16', '#fb923c'],
    },
  },
  {
    id: 'dashboard-neon',
    name: '霓虹都市',
    description: '赛博朋克风格，高饱和度霓虹配色',
    category: 'dashboard',
    categoryName: '数据大屏',
    previewColors: ['#ff00ff', '#00ffff', '#ffd700', '#ff1493', '#7fff00'],
    theme: {
      ...baseDarkTheme,
      color: ['#ff00ff', '#00ffff', '#ffd700', '#ff1493', '#7fff00', '#ff6347', '#00fa9a', '#ff69b4', '#9370db'],
    },
  },
  {
    id: 'dashboard-ocean',
    name: '深海探索',
    description: '蓝绿色调，沉稳大气的商务大屏',
    category: 'dashboard',
    categoryName: '数据大屏',
    previewColors: ['#0077b6', '#00b4d8', '#90e0ef', '#023e8a', '#48cae4'],
    theme: {
      ...baseDarkTheme,
      color: ['#0077b6', '#00b4d8', '#90e0ef', '#023e8a', '#48cae4', '#0096c7', '#00b4d8', '#03045e', '#caf0f8'],
    },
  },
  {
    id: 'report-professional',
    name: '商务专业',
    description: '低饱和度灰蓝，适合正式工作报告',
    category: 'report',
    categoryName: '工作报告',
    previewColors: ['#2c3e50', '#34495e', '#7f8c8d', '#95a5a6', '#bdc3c7'],
    theme: {
      ...baseLightTheme,
      color: ['#2c3e50', '#34495e', '#7f8c8d', '#95a5a6', '#bdc3c7', '#3498db', '#2980b9', '#1abc9c', '#16a085'],
    },
  },
  {
    id: 'report-elegant',
    name: '简约典雅',
    description: '莫兰迪色系，优雅内敛的汇报风格',
    category: 'report',
    categoryName: '工作报告',
    previewColors: ['#84a59d', '#f28482', '#f5cac3', '#f7ede2', '#f6bd60'],
    theme: {
      ...baseLightTheme,
      color: ['#84a59d', '#f28482', '#f5cac3', '#f6bd60', '#9a8c98', '#c9ada7', '#4a4e69', '#22223b', '#f2e9e4'],
    },
  },
  {
    id: 'report-classic',
    name: '经典蓝调',
    description: '经典商务蓝，稳重大气的年度报告',
    category: 'report',
    categoryName: '工作报告',
    previewColors: ['#1a365d', '#2a4365', '#2b6cb0', '#3182ce', '#4299e1'],
    theme: {
      ...baseLightTheme,
      color: ['#1a365d', '#2a4365', '#2b6cb0', '#3182ce', '#4299e1', '#63b3ed', '#90cdf4', '#2c5282', '#2c7a7b'],
    },
  },
  {
    id: 'finance-stock',
    name: '股市行情',
    description: '绿涨红跌，专业金融数据配色',
    category: 'finance',
    categoryName: '财务分析',
    previewColors: ['#ef4444', '#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6'],
    theme: {
      ...baseLightTheme,
      color: ['#ef4444', '#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316'],
    },
  },
  {
    id: 'finance-audit',
    name: '审计严谨',
    description: '灰黑为主，专业严谨的审计报表',
    category: 'finance',
    categoryName: '财务分析',
    previewColors: ['#1f2937', '#4b5563', '#6b7280', '#9ca3af', '#d1d5db'],
    theme: {
      ...baseLightTheme,
      color: ['#1f2937', '#4b5563', '#6b7280', '#9ca3af', '#d1d5db', '#374151', '#111827', '#60a5fa', '#34d399'],
    },
  },
  {
    id: 'finance-revenue',
    name: '营收分析',
    description: '金色点缀，突出营收增长主题',
    category: 'finance',
    categoryName: '财务分析',
    previewColors: ['#b45309', '#d97706', '#f59e0b', '#fbbf24', '#fcd34d'],
    theme: {
      ...baseLightTheme,
      color: ['#b45309', '#d97706', '#f59e0b', '#fbbf24', '#fcd34d', '#1e40af', '#1d4ed8', '#2563eb', '#dc2626'],
    },
  },
  {
    id: 'marketing-vibrant',
    name: '活力营销',
    description: '高饱和度亮色，吸引眼球的活动报表',
    category: 'marketing',
    categoryName: '营销报表',
    previewColors: ['#f43f5e', '#ec4899', '#8b5cf6', '#06b6d4', '#84cc16'],
    theme: {
      ...baseLightTheme,
      color: ['#f43f5e', '#ec4899', '#8b5cf6', '#06b6d4', '#84cc16', '#f59e0b', '#ef4444', '#14b8a6', '#a855f7'],
    },
  },
  {
    id: 'marketing-growth',
    name: '增长黑客',
    description: '绿橙对比，突出用户增长主题',
    category: 'marketing',
    categoryName: '营销报表',
    previewColors: ['#10b981', '#059669', '#047857', '#f97316', '#ea580c'],
    theme: {
      ...baseLightTheme,
      color: ['#10b981', '#059669', '#047857', '#f97316', '#ea580c', '#06b6d4', '#8b5cf6', '#f43f5e', '#eab308'],
    },
  },
  {
    id: 'marketing-social',
    name: '社交媒体',
    description: '粉色系为主，适合社交平台数据分析',
    category: 'marketing',
    categoryName: '营销报表',
    previewColors: ['#ec4899', '#f472b6', '#f9a8d4', '#a855f7', '#c084fc'],
    theme: {
      ...baseLightTheme,
      color: ['#ec4899', '#f472b6', '#f9a8d4', '#a855f7', '#c084fc', '#06b6d4', '#f59e0b', '#84cc16', '#3b82f6'],
    },
  },
  {
    id: 'tech-minimal',
    name: '极简科技',
    description: '蓝紫渐变，极客风格的技术分享',
    category: 'tech',
    categoryName: '科技风格',
    previewColors: ['#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef'],
    theme: {
      ...baseLightTheme,
      color: ['#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#06b6d4', '#14b8a6', '#f59e0b', '#84cc16'],
    },
  },
  {
    id: 'tech-dark',
    name: '暗夜代码',
    description: '深色背景+亮色高亮，适合技术产品演示',
    category: 'tech',
    categoryName: '科技风格',
    previewColors: ['#61afef', '#98c379', '#e5c07b', '#e06c75', '#c678dd'],
    theme: {
      ...baseDarkTheme,
      color: ['#61afef', '#98c379', '#e5c07b', '#e06c75', '#c678dd', '#56b6c2', '#d19a66', '#abb2bf', '#282c34'],
    },
  },
  {
    id: 'tech-startup',
    name: '创业活力',
    description: '清新活泼，适合创业公司产品数据',
    category: 'tech',
    categoryName: '科技风格',
    previewColors: ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
    theme: {
      ...baseLightTheme,
      color: ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316'],
    },
  },
];

export const themeCategories = [
  { value: 'all', label: '全部' },
  { value: 'dashboard', label: '数据大屏' },
  { value: 'report', label: '工作报告' },
  { value: 'finance', label: '财务分析' },
  { value: 'marketing', label: '营销报表' },
  { value: 'tech', label: '科技风格' },
];
