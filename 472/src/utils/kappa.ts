import type { Annotation } from '../types';

export interface KappaResult {
  kappa: number;
  agreement: number;
  chanceAgreement: number;
  interpretation: string;
  pairResults: PairKappaResult[];
}

export interface PairKappaResult {
  user1: string;
  user2: string;
  kappa: number;
  agreement: number;
  chanceAgreement: number;
}

export interface ContingencyTable {
  [label: string]: { [label: string]: number };
}

function getInterpretation(kappa: number): string {
  if (kappa < 0) return '一致性差';
  if (kappa < 0.2) return '轻微一致';
  if (kappa < 0.4) return '一般一致';
  if (kappa < 0.6) return '中等一致';
  if (kappa < 0.8) return '实质一致';
  return '几乎完全一致';
}

function calculatePairKappa(
  user1Annotations: Annotation[],
  user2Annotations: Annotation[],
  allDataPointIndices: number[]
): PairKappaResult | null {
  if (user1Annotations.length === 0 || user2Annotations.length === 0) {
    return null;
  }

  const user1Map = new Map<number, string>();
  const user2Map = new Map<number, string>();

  user1Annotations.forEach((a) => user1Map.set(a.dataPointIndex, a.label));
  user2Annotations.forEach((a) => user2Map.set(a.dataPointIndex, a.label));

  const commonDataPoints = allDataPointIndices.filter(
    (index) => user1Map.has(index) && user2Map.has(index)
  );

  if (commonDataPoints.length === 0) {
    return null;
  }

  const labels = new Set<string>();
  commonDataPoints.forEach((index) => {
    labels.add(user1Map.get(index)!);
    labels.add(user2Map.get(index)!);
  });

  const labelArray = Array.from(labels);
  const n = commonDataPoints.length;

  const table: ContingencyTable = {};
  labelArray.forEach((l1) => {
    table[l1] = {};
    labelArray.forEach((l2) => {
      table[l1][l2] = 0;
    });
  });

  let agreement = 0;
  commonDataPoints.forEach((index) => {
    const l1 = user1Map.get(index)!;
    const l2 = user2Map.get(index)!;
    table[l1][l2]++;
    if (l1 === l2) agreement++;
  });

  const observedAgreement = agreement / n;

  let chanceAgreement = 0;
  labelArray.forEach((label) => {
    const rowSum = labelArray.reduce((sum, l) => sum + table[label][l], 0);
    const colSum = labelArray.reduce((sum, l) => sum + table[l][label], 0);
    chanceAgreement += (rowSum / n) * (colSum / n);
  });

  const kappa =
    chanceAgreement === 1 ? 1 : (observedAgreement - chanceAgreement) / (1 - chanceAgreement);

  return {
    user1: user1Annotations[0].createdBy,
    user2: user2Annotations[0].createdBy,
    kappa: isNaN(kappa) ? 0 : Math.max(-1, Math.min(1, kappa)),
    agreement: observedAgreement,
    chanceAgreement,
  };
}

export function calculateKappa(
  annotations: Annotation[],
  dataPointsCount: number
): KappaResult {
  if (annotations.length === 0) {
    return {
      kappa: 0,
      agreement: 0,
      chanceAgreement: 0,
      interpretation: '无数据',
      pairResults: [],
    };
  }

  const userAnnotations = new Map<string, Annotation[]>();
  annotations.forEach((a) => {
    const existing = userAnnotations.get(a.createdBy) || [];
    existing.push(a);
    userAnnotations.set(a.createdBy, existing);
  });

  const users = Array.from(userAnnotations.keys());

  if (users.length < 2) {
    return {
      kappa: 0,
      agreement: 0,
      chanceAgreement: 0,
      interpretation: users.length === 0 ? '无数据' : '单个标注员，无法计算',
      pairResults: [],
    };
  }

  const allDataPointIndices = Array.from(
    { length: dataPointsCount },
    (_, i) => i
  );

  const pairResults: PairKappaResult[] = [];

  for (let i = 0; i < users.length; i++) {
    for (let j = i + 1; j < users.length; j++) {
      const result = calculatePairKappa(
        userAnnotations.get(users[i])!,
        userAnnotations.get(users[j])!,
        allDataPointIndices
      );
      if (result) {
        pairResults.push(result);
      }
    }
  }

  if (pairResults.length === 0) {
    return {
      kappa: 0,
      agreement: 0,
      chanceAgreement: 0,
      interpretation: '无共同标注数据',
      pairResults: [],
    };
  }

  const avgKappa = pairResults.reduce((sum, r) => sum + r.kappa, 0) / pairResults.length;
  const avgAgreement =
    pairResults.reduce((sum, r) => sum + r.agreement, 0) / pairResults.length;
  const avgChanceAgreement =
    pairResults.reduce((sum, r) => sum + r.chanceAgreement, 0) / pairResults.length;

  return {
    kappa: avgKappa,
    agreement: avgAgreement,
    chanceAgreement: avgChanceAgreement,
    interpretation: getInterpretation(avgKappa),
    pairResults,
  };
}

export function getKappaColor(kappa: number): string {
  if (kappa < 0) return '#ef4444';
  if (kappa < 0.2) return '#f97316';
  if (kappa < 0.4) return '#eab308';
  if (kappa < 0.6) return '#84cc16';
  if (kappa < 0.8) return '#22c55e';
  return '#10b981';
}

export function getKappaLabel(kappa: number): string {
  if (kappa < 0) return 'Poor';
  if (kappa < 0.2) return 'Slight';
  if (kappa < 0.4) return 'Fair';
  if (kappa < 0.6) return 'Moderate';
  if (kappa < 0.8) return 'Substantial';
  return 'Almost Perfect';
}
