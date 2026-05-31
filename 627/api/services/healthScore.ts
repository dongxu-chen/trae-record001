import type { DataQualityRule, RuleScoreDetail, HealthScore } from '../../shared/types.js';
import { executeRule } from './ruleEngine.js';

const RULE_WEIGHTS: Record<string, number> = {
  null_check: 1.5,
  uniqueness: 1.2,
  value_range: 1.0,
  dependency: 0.8,
};

const GRADE_THRESHOLDS = [
  { min: 90, grade: 'A' as const },
  { min: 80, grade: 'B' as const },
  { min: 70, grade: 'C' as const },
  { min: 60, grade: 'D' as const },
  { min: 0, grade: 'F' as const },
];

const DIMENSION_MAP: Record<string, keyof HealthScore['dimensionScores']> = {
  null_check: 'completeness',
  uniqueness: 'uniqueness',
  value_range: 'validity',
  dependency: 'consistency',
};

export function computeHealthScore(rules: DataQualityRule[]): HealthScore {
  const enabledRules = rules.filter(r => r.enabled);

  if (enabledRules.length === 0) {
    return {
      overall: 100,
      grade: 'A',
      ruleScores: [],
      dimensionScores: { completeness: 100, uniqueness: 100, validity: 100, consistency: 100 },
      timestamp: new Date().toISOString(),
    };
  }

  const ruleScores: RuleScoreDetail[] = enabledRules.map(rule => {
    const result = executeRule(rule);
    const weight = RULE_WEIGHTS[rule.type] ?? 1.0;
    const score = result.totalRecords > 0
      ? Math.round(((result.totalRecords - result.failedRecords) / result.totalRecords) * 10000) / 100
      : 100;

    return {
      ruleId: rule.id,
      ruleName: rule.name,
      ruleType: rule.type,
      tableName: rule.tableName,
      columnName: rule.columnName,
      score,
      totalRecords: result.totalRecords,
      failedRecords: result.failedRecords,
      weight,
    };
  });

  const totalWeight = ruleScores.reduce((sum, r) => sum + r.weight, 0);
  const weightedScore = ruleScores.reduce((sum, r) => sum + r.score * r.weight, 0);
  const overall = totalWeight > 0 ? Math.round((weightedScore / totalWeight) * 100) / 100 : 100;

  const dimensionScores = { completeness: 0, uniqueness: 0, validity: 0, consistency: 0 };
  const dimensionCounts = { completeness: 0, uniqueness: 0, validity: 0, consistency: 0 };

  ruleScores.forEach(rs => {
    const dim = DIMENSION_MAP[rs.ruleType];
    if (dim) {
      dimensionScores[dim] += rs.score;
      dimensionCounts[dim]++;
    }
  });

  (Object.keys(dimensionScores) as Array<keyof typeof dimensionScores>).forEach(key => {
    dimensionScores[key] = dimensionCounts[key] > 0
      ? Math.round((dimensionScores[key] / dimensionCounts[key]) * 100) / 100
      : 100;
  });

  const grade = GRADE_THRESHOLDS.find(t => overall >= t.min)?.grade ?? 'F';

  return {
    overall,
    grade,
    ruleScores,
    dimensionScores,
    timestamp: new Date().toISOString(),
  };
}
