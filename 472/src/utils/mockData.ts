import type { Project, Annotation, DataPoint, User } from '../types';

export const generateTimeSeriesData = (count: number): DataPoint[] => {
  const data: DataPoint[] = [];
  const now = new Date();
  for (let i = 0; i < count; i++) {
    const date = new Date(now);
    date.setDate(date.getDate() - count + i);
    data.push({
      x: date.toISOString().split('T')[0],
      y: Math.random() * 100 + 50 + Math.sin(i / 5) * 30,
    });
  }
  return data;
};

export const generateScatterData = (count: number): DataPoint[] => {
  return Array.from({ length: count }, () => ({
    x: Math.random() * 100,
    y: Math.random() * 100,
  }));
};

export const generateBarData = (count: number): DataPoint[] => {
  return Array.from({ length: count }, (_, i) => ({
    x: `Category ${i + 1}`,
    y: Math.floor(Math.random() * 100 + 20),
  }));
};

export const mockProjects: Project[] = [
  {
    id: 'proj-1',
    name: '销售数据时序分析',
    description: '对过去一年的销售数据进行时序标注',
    chartType: 'timeSeries',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    dataPoints: generateTimeSeriesData(365),
    dataFileName: 'sales_2024.csv',
  },
  {
    id: 'proj-2',
    name: '用户行为散点分析',
    description: '分析用户活跃度与消费的关系',
    chartType: 'scatter',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    dataPoints: generateScatterData(200),
    dataFileName: 'user_behavior.csv',
  },
  {
    id: 'proj-3',
    name: '月度营收柱状图',
    description: '各月度营收对比分析',
    chartType: 'bar',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    dataPoints: generateBarData(12),
    dataFileName: 'monthly_revenue.csv',
  },
];

export const mockAnnotations: Annotation[] = [
  {
    id: 'ann-1',
    projectId: 'proj-1',
    type: 'classification',
    dataPointIndex: 50,
    label: '正常波动',
    description: '属于正常的销售波动范围',
    color: '#3b82f6',
    createdBy: '用户_123',
    createdAt: new Date().toISOString(),
  },
  {
    id: 'ann-2',
    projectId: 'proj-1',
    type: 'anomaly',
    dataPointIndex: 100,
    label: '异常峰值',
    description: '销量突然激增，需要进一步分析',
    color: '#ef4444',
    createdBy: '用户_456',
    createdAt: new Date().toISOString(),
  },
  {
    id: 'ann-3',
    projectId: 'proj-1',
    type: 'trend',
    dataPointIndex: 200,
    label: '上升趋势',
    description: '开始进入销售旺季',
    color: '#22c55e',
    createdBy: '用户_123',
    createdAt: new Date().toISOString(),
  },
];

export const mockUsers: User[] = [
  { id: 'user-1', name: '张三', color: '#3b82f6' },
  { id: 'user-2', name: '李四', color: '#10b981' },
  { id: 'user-3', name: '王五', color: '#f59e0b' },
];
