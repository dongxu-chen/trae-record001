import { RelativePoint } from '../../shared/types';

export interface DataPoint {
  x: number | string;
  y: number;
  index: number;
}

export interface AnomalyPoint {
  point: DataPoint;
  position: RelativePoint;
  score: number;
  type: 'spike' | 'drop' | 'outlier';
  description: string;
  suggestion: string;
}

export interface TrendPoint {
  startPoint: DataPoint;
  endPoint: DataPoint;
  position: RelativePoint;
  endPosition: RelativePoint;
  trend: 'up' | 'down' | 'stable';
  changePercent: number;
  duration: number;
  description: string;
  suggestion: string;
}

export interface AIRecommendation {
  id: string;
  type: 'anomaly' | 'trend' | 'insight';
  position: RelativePoint;
  endPosition?: RelativePoint;
  annotationType: 'text' | 'arrow' | 'highlight';
  content: string;
  color: string;
  confidence: number;
  category: string;
}

export const calculateZScore = (values: number[]): number[] => {
  const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
  const stdDev = Math.sqrt(
    values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length
  );
  
  if (stdDev === 0) return values.map(() => 0);
  
  return values.map(v => (v - mean) / stdDev);
};

export const detectAnomalies = (
  dataPoints: DataPoint[],
  threshold: number = 2.0
): AnomalyPoint[] => {
  if (dataPoints.length < 3) return [];

  const values = dataPoints.map(d => d.y);
  const zScores = calculateZScore(values);
  const anomalies: AnomalyPoint[] = [];

  for (let i = 0; i < dataPoints.length; i++) {
    const absZ = Math.abs(zScores[i]);
    if (absZ >= threshold) {
      const point = dataPoints[i];
      const prevValue = i > 0 ? values[i - 1] : values[i];
      const change = ((point.y - prevValue) / Math.abs(prevValue)) * 100;
      
      let type: 'spike' | 'drop' | 'outlier';
      let description: string;
      let suggestion: string;

      if (change > 20) {
        type = 'spike';
        description = `数据突增 ${change.toFixed(1)}%`;
        suggestion = '这个数据点明显高于平均值，建议检查是否有特殊事件导致增长';
      } else if (change < -20) {
        type = 'drop';
        description = `数据骤降 ${Math.abs(change).toFixed(1)}%`;
        suggestion = '这个数据点明显低于平均值，建议分析下降原因';
      } else {
        type = 'outlier';
        description = `异常值 (Z-score: ${absZ.toFixed(2)})`;
        suggestion = '这是一个统计异常点，值得关注和分析';
      }

      const position: RelativePoint = {
        x: (i + 0.5) / dataPoints.length,
        y: 0.3 + Math.random() * 0.4,
      };

      anomalies.push({
        point,
        position,
        score: absZ,
        type,
        description,
        suggestion,
      });
    }
  }

  return anomalies.sort((a, b) => b.score - a.score);
};

export const detectTrends = (
  dataPoints: DataPoint[],
  minDuration: number = 2,
  minChangePercent: number = 15
): TrendPoint[] => {
  if (dataPoints.length < minDuration + 1) return [];

  const trends: TrendPoint[] = [];
  const values = dataPoints.map(d => d.y);

  let i = 0;
  while (i < dataPoints.length - 1) {
    const startValue = values[i];
    let j = i + 1;
    let currentDirection = values[j] > startValue ? 'up' : values[j] < startValue ? 'down' : 'stable';

    while (
      j < dataPoints.length &&
      (values[j] - values[j - 1]) * (currentDirection === 'up' ? 1 : currentDirection === 'down' ? -1 : 0) >= 0
    ) {
      j++;
    }

    const duration = j - i;
    if (duration >= minDuration) {
      const endValue = values[j - 1];
      const changePercent = ((endValue - startValue) / Math.abs(startValue)) * 100;
      
      if (Math.abs(changePercent) >= minChangePercent) {
        const trend = changePercent > 0 ? 'up' : 'down';
        
        const startPoint = dataPoints[i];
        const endPoint = dataPoints[j - 1];
        
        const position: RelativePoint = {
          x: (i + 0.5) / dataPoints.length,
          y: 0.5,
        };
        
        const endPosition: RelativePoint = {
          x: (j - 0.5) / dataPoints.length,
          y: 0.5,
        };

        let description: string;
        let suggestion: string;

        if (trend === 'up') {
          description = `持续增长 ${changePercent.toFixed(1)}%`;
          suggestion = `这是一个持续${duration}个周期的上升趋势，增长显著，值得关注`;
        } else {
          description = `持续下降 ${Math.abs(changePercent).toFixed(1)}%`;
          suggestion = `这是一个持续${duration}个周期的下降趋势，建议分析原因并采取措施`;
        }

        trends.push({
          startPoint,
          endPoint,
          position,
          endPosition,
          trend,
          changePercent,
          duration,
          description,
          suggestion,
        });
      }
    }

    i = Math.max(i + 1, j - 1);
  }

  return trends.sort((a, b) => Math.abs(b.changePercent) - Math.abs(a.changePercent));
};

export const generateInsights = (dataPoints: DataPoint[]): AIRecommendation[] => {
  if (dataPoints.length === 0) return [];

  const values = dataPoints.map(d => d.y);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const avg = values.reduce((sum, v) => sum + v, 0) / values.length;
  const maxIndex = values.indexOf(max);
  const minIndex = values.indexOf(min);

  const recommendations: AIRecommendation[] = [];

  recommendations.push({
    id: 'insight-max',
    type: 'insight',
    position: { x: (maxIndex + 0.5) / dataPoints.length, y: 0.2 },
    annotationType: 'text',
    content: `📈 最高点: ${max}`,
    color: '#22c55e',
    confidence: 0.95,
    category: '统计信息',
  });

  recommendations.push({
    id: 'insight-min',
    type: 'insight',
    position: { x: (minIndex + 0.5) / dataPoints.length, y: 0.8 },
    annotationType: 'text',
    content: `📉 最低点: ${min}`,
    color: '#ef4444',
    confidence: 0.95,
    category: '统计信息',
  });

  recommendations.push({
    id: 'insight-avg',
    type: 'insight',
    position: { x: 0.5, y: 0.5 },
    annotationType: 'text',
    content: `📊 平均值: ${avg.toFixed(1)}`,
    color: '#3b82f6',
    confidence: 0.95,
    category: '统计信息',
  });

  const volatility = Math.sqrt(
    values.reduce((sum, v) => sum + Math.pow(v - avg, 2), 0) / values.length
  ) / avg * 100;

  if (volatility > 30) {
    recommendations.push({
      id: 'insight-volatility',
      type: 'insight',
      position: { x: 0.1, y: 0.1 },
      annotationType: 'highlight',
      content: `高波动性 (${volatility.toFixed(1)}%)`,
      color: '#f59e0b',
      confidence: 0.85,
      category: '风险提示',
    });
  }

  return recommendations;
};

export const analyzeChartData = (
  chartData: any
): { anomalies: AnomalyPoint[]; trends: TrendPoint[]; recommendations: AIRecommendation[] } => {
  const dataPoints: DataPoint[] = [];
  
  if (chartData?.series?.[0]?.data) {
    const series = chartData.series[0];
    const xData = chartData.xAxis?.data || [];
    
    series.data.forEach((value: number, index: number) => {
      dataPoints.push({
        x: xData[index] ?? index,
        y: value,
        index,
      });
    });
  }

  const anomalies = detectAnomalies(dataPoints);
  const trends = detectTrends(dataPoints);
  const insights = generateInsights(dataPoints);

  const anomalyRecommendations: AIRecommendation[] = anomalies.map((a, idx) => ({
    id: `anomaly-${idx}`,
    type: 'anomaly' as const,
    position: a.position,
    annotationType: 'text' as const,
    content: `⚠️ ${a.description}`,
    color: a.type === 'spike' ? '#22c55e' : a.type === 'drop' ? '#ef4444' : '#f59e0b',
    confidence: Math.min(0.95, 0.7 + a.score * 0.1),
    category: '异常检测',
  }));

  const trendRecommendations: AIRecommendation[] = trends.map((t, idx) => ({
    id: `trend-${idx}`,
    type: 'trend' as const,
    position: t.position,
    endPosition: t.endPosition,
    annotationType: 'arrow' as const,
    content: `📊 ${t.description}`,
    color: t.trend === 'up' ? '#22c55e' : '#ef4444',
    confidence: Math.min(0.95, 0.7 + Math.abs(t.changePercent) * 0.005),
    category: '趋势分析',
  }));

  return {
    anomalies,
    trends,
    recommendations: [...anomalyRecommendations, ...trendRecommendations, ...insights],
  };
};

export const annotationTemplates = [
  {
    id: 'tpl-1',
    category: '通用',
    content: '这里数据很重要',
    color: '#3b82f6',
    icon: '💡',
  },
  {
    id: 'tpl-2',
    category: '通用',
    content: '需要进一步分析',
    color: '#f59e0b',
    icon: '🔍',
  },
  {
    id: 'tpl-3',
    category: '通用',
    content: '待确认',
    color: '#6b7280',
    icon: '❓',
  },
  {
    id: 'tpl-4',
    category: '异常',
    content: '数据异常，请检查',
    color: '#ef4444',
    icon: '⚠️',
  },
  {
    id: 'tpl-5',
    category: '异常',
    content: '突增点，值得关注',
    color: '#22c55e',
    icon: '📈',
  },
  {
    id: 'tpl-6',
    category: '异常',
    content: '骤降点，需要分析',
    color: '#ef4444',
    icon: '📉',
  },
  {
    id: 'tpl-7',
    category: '趋势',
    content: '持续上升趋势',
    color: '#22c55e',
    icon: '↗️',
  },
  {
    id: 'tpl-8',
    category: '趋势',
    content: '持续下降趋势',
    color: '#ef4444',
    icon: '↘️',
  },
  {
    id: 'tpl-9',
    category: '趋势',
    content: '趋于稳定',
    color: '#06b6d4',
    icon: '➡️',
  },
  {
    id: 'tpl-10',
    category: '业务',
    content: 'Q4旺季预期',
    color: '#8b5cf6',
    icon: '🎯',
  },
  {
    id: 'tpl-11',
    category: '业务',
    content: '促销活动影响',
    color: '#ec4899',
    icon: '🎁',
  },
  {
    id: 'tpl-12',
    category: '业务',
    content: '新品发布带动',
    color: '#14b8a6',
    icon: '🚀',
  },
  {
    id: 'tpl-13',
    category: '问题',
    content: '此处有bug',
    color: '#ef4444',
    icon: '🐛',
  },
  {
    id: 'tpl-14',
    category: '问题',
    content: '数据缺失',
    color: '#f97316',
    icon: '❌',
  },
  {
    id: 'tpl-15',
    category: '其他',
    content: '好！',
    color: '#22c55e',
    icon: '👍',
  },
  {
    id: 'tpl-16',
    category: '其他',
    content: '关注此处',
    color: '#f59e0b',
    icon: '👀',
  },
];

export const searchAnnotations = (
  annotations: any[],
  query: string,
  options: {
    searchContent?: boolean;
    searchAuthor?: boolean;
    searchType?: boolean;
    positionFilter?: { xRange?: [number, number]; yRange?: [number, number] };
  } = {}
): any[] => {
  const {
    searchContent = true,
    searchAuthor = true,
    searchType = true,
    positionFilter,
  } = options;

  if (!query && !positionFilter) return annotations;

  const lowerQuery = query.toLowerCase();

  return annotations.filter(annotation => {
    let matches = true;

    if (query) {
      let textMatch = false;

      if (searchContent && annotation.content) {
        textMatch = textMatch || annotation.content.toLowerCase().includes(lowerQuery);
      }

      if (searchAuthor && annotation.authorName) {
        textMatch = textMatch || annotation.authorName.toLowerCase().includes(lowerQuery);
      }

      if (searchType && annotation.type) {
        const typeNames: Record<string, string> = {
          text: '文本',
          arrow: '箭头',
          highlight: '高亮',
        };
        textMatch = textMatch || 
          annotation.type.toLowerCase().includes(lowerQuery) ||
          typeNames[annotation.type]?.includes(query);
      }

      matches = matches && textMatch;
    }

    if (positionFilter) {
      const { xRange, yRange } = positionFilter;
      const pos = annotation.position;

      if (xRange) {
        matches = matches && pos.x >= xRange[0] && pos.x <= xRange[1];
      }

      if (yRange) {
        matches = matches && pos.y >= yRange[0] && pos.y <= yRange[1];
      }
    }

    return matches;
  });
};

export const filterAnnotationsByTime = (
  annotations: any[],
  startTime?: number,
  endTime?: number
): any[] => {
  return annotations.filter(a => {
    const created = a.createdAt;
    let matches = true;
    if (startTime) matches = matches && created >= startTime;
    if (endTime) matches = matches && created <= endTime;
    return matches;
  });
};

export const filterAnnotationsByAuthor = (
  annotations: any[],
  authorIds: string[]
): any[] => {
  if (authorIds.length === 0) return annotations;
  return annotations.filter(a => authorIds.includes(a.authorId));
};
