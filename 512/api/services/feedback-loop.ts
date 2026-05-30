import { saveFeedback, getFeedbacksByRule, getRule, saveRule, incrementId } from './redis.js';
import type { AlertFeedback, ThresholdRule } from '../types.js';

interface FeedbackStats {
  total: number;
  falsePositive: number;
  truePositive: number;
  needsAdjustment: number;
  falsePositiveRate: number;
  lastFeedbackAt?: string;
}

export async function recordFeedback(
  alertId: string,
  ruleId: string,
  feedbackType: 'false_positive' | 'true_positive' | 'needs_adjustment',
  comment?: string
): Promise<AlertFeedback> {
  const id = `feedback-${Date.now()}-${await incrementId('feedback')}`;
  const feedback: AlertFeedback = {
    id,
    alertId,
    ruleId,
    type: feedbackType,
    comment,
    createdAt: new Date().toISOString(),
  };

  await saveFeedback(feedback);
  return feedback;
}

export async function getFeedbackStats(ruleId: string): Promise<FeedbackStats> {
  const feedbacks = await getFeedbacksByRule(ruleId);

  const stats: FeedbackStats = {
    total: feedbacks.length,
    falsePositive: 0,
    truePositive: 0,
    needsAdjustment: 0,
    falsePositiveRate: 0,
  };

  let lastDate: Date | null = null;

  for (const fb of feedbacks) {
    if (fb.type === 'false_positive') {
      stats.falsePositive++;
    } else if (fb.type === 'true_positive') {
      stats.truePositive++;
    } else if (fb.type === 'needs_adjustment') {
      stats.needsAdjustment++;
    }

    const fbDate = new Date(fb.createdAt);
    if (!lastDate || fbDate > lastDate) {
      lastDate = fbDate;
    }
  }

  if (stats.total > 0) {
    stats.falsePositiveRate = stats.falsePositive / stats.total;
  }

  if (lastDate) {
    stats.lastFeedbackAt = lastDate.toISOString();
  }

  return stats;
}

export async function adjustThresholdBasedOnFeedback(ruleId: string): Promise<ThresholdRule | null> {
  const rule = await getRule(ruleId);
  if (!rule) {
    return null;
  }

  const stats = await getFeedbackStats(ruleId);

  if (stats.total < 3) {
    return rule;
  }

  const falsePositiveRate = stats.falsePositiveRate;
  let adjustmentFactor = 1;

  if (falsePositiveRate > 0.5) {
    adjustmentFactor = 1.2;
  } else if (falsePositiveRate > 0.3) {
    adjustmentFactor = 1.1;
  } else if (stats.truePositive > 5 && falsePositiveRate < 0.1) {
    adjustmentFactor = 0.9;
  } else if (stats.needsAdjustment > 2) {
    adjustmentFactor = 0.95;
  }

  if (adjustmentFactor === 1) {
    return rule;
  }

  const updatedConditions = rule.conditions.map((cond) => ({
    ...cond,
    value: Math.round(cond.value * adjustmentFactor * 100) / 100,
  }));

  const updatedRule: ThresholdRule = {
    ...rule,
    conditions: updatedConditions,
    updatedAt: new Date().toISOString(),
  };

  await saveRule(updatedRule);
  return updatedRule;
}
