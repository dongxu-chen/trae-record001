import { Router } from 'express';
import { statsRepository } from '../db/repositories.js';
import { rulesRepository, issuesRepository } from '../db/repositories.js';
import { computeHealthScore } from '../services/healthScore.js';
import type { BoardMetrics } from '../../shared/types.js';

const router = Router();

router.get('/overview', (_req, res) => {
  const stats = statsRepository.getOverview();
  res.json(stats);
});

router.get('/trends/quality', (req, res) => {
  const days = parseInt(req.query.days as string) || 7;
  const trends = statsRepository.getQualityTrend(days);
  res.json(trends);
});

router.get('/trends/issues', (req, res) => {
  const days = parseInt(req.query.days as string) || 7;
  const trends = statsRepository.getIssuesTrend(days);
  res.json(trends);
});

router.get('/trends/quality-threshold', (req, res) => {
  const days = parseInt(req.query.days as string) || 7;
  const trends = statsRepository.getQualityTrendWithThreshold(days);
  res.json(trends);
});

router.get('/trends/issues-threshold', (req, res) => {
  const days = parseInt(req.query.days as string) || 7;
  const trends = statsRepository.getIssuesTrendWithThreshold(days);
  res.json(trends);
});

router.get('/board', (_req, res) => {
  const rules = rulesRepository.getAll();
  const healthScore = computeHealthScore(rules);
  const overview = statsRepository.getOverview();
  const recentScores = statsRepository.getQualityTrend(7);
  const allIssues = issuesRepository.getAll();

  const typeLabels: Record<string, string> = {
    null_check: '空值检查',
    uniqueness: '唯一性',
    value_range: '值域范围',
    dependency: '依赖校验',
  };

  const issueDistribution = ['null_check', 'uniqueness', 'value_range', 'dependency'].map(type => ({
    type,
    count: allIssues.filter(i => i.issueType === type).length,
    label: typeLabels[type] ?? type,
  }));

  const boardMetrics: BoardMetrics = {
    healthScore,
    totalRules: overview.totalRules,
    activeRules: overview.activeRules,
    openIssues: overview.openIssues,
    totalRecords: healthScore.ruleScores.reduce((s, r) => s + r.totalRecords, 0),
    failedRecords: healthScore.ruleScores.reduce((s, r) => s + r.failedRecords, 0),
    recentScores,
    issueDistribution,
    lastUpdated: new Date().toISOString(),
  };

  res.json(boardMetrics);
});

export default router;
