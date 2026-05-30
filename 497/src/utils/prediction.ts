import {
  DataPoint,
  PredictionData,
  LevelData,
  PredictionLevelData,
} from '@/types/drill';

function calculateTrend(historicalValues: number[]): 'up' | 'down' | 'stable' {
  if (historicalValues.length < 2) return 'stable';

  const recent = historicalValues.slice(-3);
  const earlier = historicalValues.slice(0, 3);

  const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
  const earlierAvg = earlier.reduce((a, b) => a + b, 0) / earlier.length;

  const change = (recentAvg - earlierAvg) / earlierAvg;

  if (change > 0.05) return 'up';
  if (change < -0.05) return 'down';
  return 'stable';
}

function calculateConfidence(dataPoints: number[]): number {
  if (dataPoints.length < 2) return 0.5;

  const mean = dataPoints.reduce((a, b) => a + b, 0) / dataPoints.length;
  const variance =
    dataPoints.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / dataPoints.length;
  const stdDev = Math.sqrt(variance);

  const cv = stdDev / mean;
  const confidence = Math.max(0.3, Math.min(0.95, 1 - cv));

  return Math.round(confidence * 100) / 100;
}

function simpleMovingAverage(values: number[], window: number = 3): number {
  const recent = values.slice(-window);
  return recent.reduce((a, b) => a + b, 0) / recent.length;
}

function exponentialMovingAverage(values: number[], alpha: number = 0.3): number {
  if (values.length === 0) return 0;
  if (values.length === 1) return values[0];

  let ema = values[0];
  for (let i = 1; i < values.length; i++) {
    ema = alpha * values[i] + (1 - alpha) * ema;
  }
  return ema;
}

function trendExtrapolation(values: number[]): number {
  if (values.length < 2) return values[0] || 0;

  const n = values.length;
  const sumX = (n * (n - 1)) / 2;
  const sumY = values.reduce((a, b) => a + b, 0);
  const sumXY = values.reduce((acc, val, idx) => acc + idx * val, 0);
  const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6;

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;

  return intercept + slope * n;
}

function weightedEnsemblePrediction(
  values: number[],
  weights: { sma: number; ema: number; trend: number } = {
    sma: 0.3,
    ema: 0.3,
    trend: 0.4,
  }
): number {
  const sma = simpleMovingAverage(values);
  const ema = exponentialMovingAverage(values);
  const trend = trendExtrapolation(values);

  return sma * weights.sma + ema * weights.ema + trend * weights.trend;
}

export function generatePredictionForDataPoint(
  currentValue: number,
  historicalValues: number[] = [],
  method: string = 'ensemble'
): PredictionData {
  const allValues = [...historicalValues, currentValue];
  const trend = calculateTrend(allValues);
  const confidence = calculateConfidence(allValues);

  let predictedValue: number;

  switch (method) {
    case 'sma':
      predictedValue = simpleMovingAverage(allValues);
      break;
    case 'ema':
      predictedValue = exponentialMovingAverage(allValues);
      break;
    case 'trend':
      predictedValue = trendExtrapolation(allValues);
      break;
    case 'ensemble':
    default:
      predictedValue = weightedEnsemblePrediction(allValues);
  }

  const volatility =
    allValues.length > 1
      ? Math.sqrt(
          allValues.reduce(
            (a, b) => a + Math.pow(b - predictedValue, 2),
            0
          ) / allValues.length
        )
      : predictedValue * 0.1;

  const marginOfError = volatility * (1 - confidence) * 1.5;

  const lowerBound = Math.max(0, Math.round(predictedValue - marginOfError));
  const upperBound = Math.round(predictedValue + marginOfError);
  predictedValue = Math.round(predictedValue);

  return {
    predictedValue,
    lowerBound,
    upperBound,
    confidence,
    trend,
    method,
  };
}

export function generatePredictionForLevel(
  currentData: LevelData,
  historicalData: LevelData[] = [],
  method: string = 'ensemble'
): PredictionLevelData {
  const dataWithPredictions = currentData.data.map((item) => {
    const historicalValues = historicalData
      .map((level) => {
        const historicalItem = level.data.find((d) => d.name === item.name);
        return historicalItem?.value || null;
      })
      .filter((v): v is number => v !== null);

    const prediction = generatePredictionForDataPoint(
      item.value,
      historicalValues,
      method
    );

    return {
      ...item,
      prediction,
    };
  });

  return {
    level: currentData.level + 1,
    levelName: `预测 - ${currentData.levelName}`,
    parentId: currentData.parentId,
    data: dataWithPredictions,
  };
}

export function formatPredictionDisplay(prediction: PredictionData): {
  value: string;
  range: string;
  confidence: string;
  trend: string;
  color: string;
} {
  const trendLabels = {
    up: '↑ 上升',
    down: '↓ 下降',
    stable: '→ 稳定',
  };

  const trendColors = {
    up: 'text-green-400',
    down: 'text-red-400',
    stable: 'text-yellow-400',
  };

  return {
    value: prediction.predictedValue.toLocaleString(),
    range: `${prediction.lowerBound.toLocaleString()} - ${prediction.upperBound.toLocaleString()}`,
    confidence: `${Math.round(prediction.confidence * 100)}%`,
    trend: trendLabels[prediction.trend],
    color: trendColors[prediction.trend],
  };
}

export function getPredictionMethodLabel(method: string): string {
  const labels: Record<string, string> = {
    sma: '简单移动平均',
    ema: '指数移动平均',
    trend: '趋势外推',
    ensemble: '加权集成',
  };
  return labels[method] || method;
}
