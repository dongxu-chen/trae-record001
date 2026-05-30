import { ChangeRiskAssessment, ChangeType, RiskFactor, RiskLevel, AnalysisResult } from '@/types';

const CHANGE_TYPE_WEIGHTS: Record<ChangeType, number> = {
  delete: 100,
  type_change: 80,
  rename: 60,
  constraint_change: 40,
  default_change: 20,
};

const CHANGE_TYPE_LABELS: Record<ChangeType, string> = {
  delete: '字段删除',
  type_change: '类型变更',
  rename: '字段重命名',
  constraint_change: '约束变更',
  default_change: '默认值变更',
};

const DEPTH_MULTIPLIER = 1.5;

const RISK_THRESHOLDS = {
  low: 30,
  medium: 60,
  high: 80,
  critical: 100,
};

export const getChangeTypeLabel = (type: ChangeType): string => CHANGE_TYPE_LABELS[type];

export const assessChangeRisk = (
  fieldId: string,
  fieldName: string,
  changeType: ChangeType,
  analysisResult: AnalysisResult
): ChangeRiskAssessment => {
  const baseWeight = CHANGE_TYPE_WEIGHTS[changeType];
  const { statistics, downstreamList, downstreamByDepth } = analysisResult;

  const downstreamImpactScore = Math.min(
    statistics.totalDownstreamNodes * 5,
    30
  );

  const depthScore = Math.min(
    statistics.maxDepth * DEPTH_MULTIPLIER * 5,
    20
  );

  const etlImpactScore = Math.min(statistics.etlTasks * 10, 20);
  const reportImpactScore = Math.min(statistics.reports * 8, 15);
  const ownerScore = Math.min(
    [...new Set([
      ...downstreamList.etlTasks.map(t => t.owner),
      ...downstreamList.reports.map(r => r.owner),
    ])].length * 5,
    15
  );

  const rawScore = baseWeight + downstreamImpactScore + depthScore + etlImpactScore + reportImpactScore + ownerScore;
  const riskScore = Math.min(Math.round(rawScore / 2), 100);

  const riskLevel = getRiskLevel(riskScore);

  const riskFactors = generateRiskFactors(
    changeType,
    statistics,
    downstreamList,
    downstreamByDepth
  );

  const recommendations = generateRecommendations(
    changeType,
    riskLevel,
    statistics,
    downstreamList
  );

  const affectedOwners = [...new Set([
    ...downstreamList.etlTasks.map(t => t.owner),
    ...downstreamList.reports.map(r => r.owner),
  ])];

  const requiresDowntime = changeType === 'delete' || changeType === 'type_change' || riskLevel === 'critical';
  const estimatedRecoveryTime = estimateRecoveryTime(changeType, riskLevel, statistics);

  return {
    fieldId,
    fieldName,
    changeType,
    riskLevel,
    riskScore,
    impactScope: {
      affectedETLTasks: statistics.etlTasks,
      affectedReports: statistics.reports,
      affectedTables: statistics.tables,
      affectedOwners: affectedOwners.length,
      maxDepth: statistics.maxDepth,
    },
    riskFactors,
    recommendations,
    estimatedRecoveryTime,
    requiresDowntime,
  };
};

const getRiskLevel = (score: number): RiskLevel => {
  if (score >= RISK_THRESHOLDS.critical) return 'critical';
  if (score >= RISK_THRESHOLDS.high) return 'high';
  if (score >= RISK_THRESHOLDS.medium) return 'medium';
  return 'low';
};

export const getRiskLevelLabel = (level: RiskLevel): string => {
  const labels: Record<RiskLevel, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
    critical: '极高风险',
  };
  return labels[level];
};

export const getRiskLevelColor = (level: RiskLevel): string => {
  const colors: Record<RiskLevel, string> = {
    low: 'bg-green-100 text-green-700',
    medium: 'bg-yellow-100 text-yellow-700',
    high: 'bg-orange-100 text-orange-700',
    critical: 'bg-red-100 text-red-700',
  };
  return colors[level];
};

export const getRiskLevelBgColor = (level: RiskLevel): string => {
  const colors: Record<RiskLevel, string> = {
    low: 'from-green-50 to-green-100',
    medium: 'from-yellow-50 to-yellow-100',
    high: 'from-orange-50 to-orange-100',
    critical: 'from-red-50 to-red-100',
  };
  return colors[level];
};

export const getRiskLevelTextColor = (level: RiskLevel): string => {
  const colors: Record<RiskLevel, string> = {
    low: 'text-green-600',
    medium: 'text-yellow-600',
    high: 'text-orange-600',
    critical: 'text-red-600',
  };
  return colors[level];
};

const generateRiskFactors = (
  changeType: ChangeType,
  statistics: AnalysisResult['statistics'],
  downstreamList: AnalysisResult['downstreamList'],
  _downstreamByDepth: AnalysisResult['downstreamByDepth']
): RiskFactor[] => {
  const factors: RiskFactor[] = [];

  if (changeType === 'delete' || changeType === 'type_change') {
    factors.push({
      id: `rf-${Date.now()}-1`,
      category: 'data_loss',
      description: `${getChangeTypeLabel(changeType)}可能导致下游数据丢失或写入失败`,
      severity: changeType === 'delete' ? 'critical' : 'high',
      affectedItems: downstreamList.etlTasks.map(t => t.name),
    });
  }

  if (downstreamList.etlTasks.length > 0) {
    factors.push({
      id: `rf-${Date.now()}-2`,
      category: 'logic_break',
      description: `${downstreamList.etlTasks.length}个ETL任务的SQL逻辑可能因字段变更而中断`,
      severity: statistics.etlTasks > 3 ? 'high' : 'medium',
      affectedItems: downstreamList.etlTasks.map(t => t.name),
    });
  }

  if (downstreamList.reports.length > 0) {
    factors.push({
      id: `rf-${Date.now()}-3`,
      category: 'compatibility',
      description: `${downstreamList.reports.length}个报表/看板的数据展示可能受影响`,
      severity: statistics.reports > 2 ? 'high' : 'medium',
      affectedItems: downstreamList.reports.map(r => r.name),
    });
  }

  if (statistics.maxDepth > 3) {
    factors.push({
      id: `rf-${Date.now()}-4`,
      category: 'performance',
      description: `影响链路深度达${statistics.maxDepth}层，变更影响传播范围广`,
      severity: statistics.maxDepth > 5 ? 'high' : 'medium',
      affectedItems: [],
    });
  }

  if (changeType === 'rename') {
    factors.push({
      id: `rf-${Date.now()}-5`,
      category: 'compatibility',
      description: '字段重命名需要同步修改所有引用该字段的SQL脚本和应用程序',
      severity: 'medium',
      affectedItems: downstreamList.etlTasks.map(t => t.script).filter(Boolean),
    });
  }

  return factors;
};

const generateRecommendations = (
  changeType: ChangeType,
  riskLevel: RiskLevel,
  statistics: AnalysisResult['statistics'],
  downstreamList: AnalysisResult['downstreamByDepth']
): string[] => {
  const recs: string[] = [];

  if (riskLevel === 'critical' || riskLevel === 'high') {
    recs.push('建议在变更前召开变更评审会议，与所有下游负责人确认影响');
  }

  if (changeType === 'delete') {
    recs.push('建议先标记字段为废弃（deprecated），观察一段时间后再删除');
    recs.push('删除前确保所有下游ETL任务和报表已迁移到替代字段');
  }

  if (changeType === 'rename') {
    recs.push('建议使用别名机制保持兼容性，逐步迁移下游引用');
  }

  if (changeType === 'type_change') {
    recs.push('建议增加数据类型转换层，确保历史数据兼容');
    recs.push('先在测试环境验证类型变更后的数据完整性');
  }

  if (statistics.etlTasks > 0) {
    recs.push(`需要通知${downstreamList.etlTasks.length}个ETL任务的负责人提前调整脚本`);
  }

  if (statistics.reports > 0) {
    recs.push(`需要通知${downstreamList.reports.length}个报表负责人调整数据源配置`);
  }

  if (riskLevel === 'low') {
    recs.push('影响范围有限，可按正常变更流程执行');
  }

  recs.push('建议在低峰时段执行变更，并准备好回滚方案');

  return recs;
};

const estimateRecoveryTime = (
  changeType: ChangeType,
  riskLevel: RiskLevel,
  statistics: AnalysisResult['statistics']
): string => {
  const baseTime: Record<ChangeType, number> = {
    delete: 8,
    type_change: 6,
    rename: 4,
    constraint_change: 2,
    default_change: 1,
  };

  const riskMultiplier: Record<RiskLevel, number> = {
    low: 1,
    medium: 1.5,
    high: 2,
    critical: 3,
  };

  const hours = Math.round(
    baseTime[changeType] * riskMultiplier[riskLevel] * (1 + statistics.totalDownstreamNodes * 0.1)
  );

  if (hours < 1) return '小于1小时';
  if (hours < 4) return `${hours}小时`;
  if (hours < 24) return `约${Math.round(hours / 4) * 4}小时`;
  return `约${Math.round(hours / 24)}个工作日`;
};
