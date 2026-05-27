export const CATEGORIES = [
  { value: 'operation', label: '运营', icon: 'LineChartOutlined', color: '#3B82F6' },
  { value: 'sales', label: '销售', icon: 'DollarOutlined', color: '#10B981' },
  { value: 'finance', label: '财务', icon: 'WalletOutlined', color: '#F59E0B' },
  { value: 'ops', label: '运维', icon: 'CloudServerOutlined', color: '#8B5CF6' }
];

export const COMPLEXITY = [
  { value: 'simple', label: '简单', color: '#10B981' },
  { value: 'medium', label: '中等', color: '#F59E0B' },
  { value: 'complex', label: '复杂', color: '#EF4444' }
];

export const CHART_TYPES = [
  { value: 'line', label: '折线图', icon: 'LineChartOutlined' },
  { value: 'bar', label: '柱状图', icon: 'BarChartOutlined' },
  { value: 'pie', label: '饼图', icon: 'PieChartOutlined' },
  { value: 'area', label: '面积图', icon: 'AreaChartOutlined' },
  { value: 'gauge', label: '仪表盘', icon: 'DashboardOutlined' }
];

export const COMPONENT_TYPES = [
  { value: 'chart', label: '图表', icon: 'BarChartOutlined' },
  { value: 'metric', label: '指标卡片', icon: 'StockOutlined' },
  { value: 'table', label: '表格', icon: 'TableOutlined' },
  { value: 'text', label: '文本', icon: 'FontSizeOutlined' },
  { value: 'image', label: '图片', icon: 'PictureOutlined' }
];

export const SORT_OPTIONS = [
  { value: 'createdAt', label: '最新发布' },
  { value: 'downloadCount', label: '下载最多' },
  { value: 'rating', label: '评分最高' },
  { value: 'viewCount', label: '浏览最多' }
];
