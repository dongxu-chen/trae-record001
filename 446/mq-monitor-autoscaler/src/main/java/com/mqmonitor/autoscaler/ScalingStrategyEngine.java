package com.mqmonitor.autoscaler;

import com.mqmonitor.common.config.AutoScalerConfig;
import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.PredictionResult;
import com.mqmonitor.common.model.QueueMetrics;
import com.mqmonitor.common.util.StatsUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class ScalingStrategyEngine {
    private static final Logger logger = LoggerFactory.getLogger(ScalingStrategyEngine.class);

    private final AutoScalerConfig config;

    public ScalingStrategyEngine(AutoScalerConfig config) {
        this.config = config;
    }

    public ScalingDecision evaluate(MQType mqType, String clusterName, String topic,
                                String consumerGroup, int currentConsumers,
                                List<QueueMetrics> historicalMetrics,
                                PredictionResult predictionResult,
                                long lastScalingTime) {
        AutoScalerConfig.GroupScalingConfig groupConfig =
                config.getGroupConfig(mqType, topic, consumerGroup);

        if (groupConfig != null && !groupConfig.isEffectiveEnabled(config)) {
            return ScalingDecision.noChange(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, "Auto-scaling disabled for group");
        }

        int minConsumers = groupConfig != null ?
                groupConfig.getEffectiveMinConsumers(config) : config.getMinConsumers();
        int maxConsumers = groupConfig != null ?
                groupConfig.getEffectiveMaxConsumers(config) : config.getMaxConsumers();
        int scaleUpStep = groupConfig != null ?
                groupConfig.getEffectiveScaleUpStep(config) : config.getDefaultScaleUpStep();
        int scaleDownStep = groupConfig != null ?
                groupConfig.getEffectiveScaleDownStep(config) : config.getDefaultScaleDownStep();
        long lagThreshold = groupConfig != null ?
                groupConfig.getEffectiveLagThreshold(config) : config.getLagThreshold();
        long p99Threshold = groupConfig != null ?
                groupConfig.getEffectiveP99LatencyThreshold(config) : config.getP99LatencyThresholdMs();

        ScalingDecision decision;
        String strategyName;
        double confidence;

        switch (config.getStrategy()) {
            case LAG_THRESHOLD:
                decision = evaluateLagThreshold(mqType, clusterName, topic, consumerGroup,
                        currentConsumers, historicalMetrics,
                        minConsumers, maxConsumers, scaleUpStep, scaleDownStep,
                        lagThreshold, p99Threshold);
                strategyName = "LAG_THRESHOLD";
                confidence = 0.7;
                break;
            case LAG_RATE:
                decision = evaluateLagRate(mqType, clusterName, topic, consumerGroup,
                        currentConsumers, historicalMetrics,
                        minConsumers, maxConsumers, scaleUpStep, scaleDownStep,
                        lagThreshold, p99Threshold);
                strategyName = "LAG_RATE";
                confidence = 0.75;
                break;
            case PREDICTIVE:
                decision = evaluatePredictive(mqType, clusterName, topic, consumerGroup,
                        currentConsumers, historicalMetrics, predictionResult,
                        minConsumers, maxConsumers, scaleUpStep, scaleDownStep,
                        lagThreshold, p99Threshold);
                strategyName = "PREDICTIVE";
                confidence = 0.8;
                break;
            case HYBRID:
            default:
                decision = evaluateHybrid(mqType, clusterName, topic, consumerGroup,
                        currentConsumers, historicalMetrics, predictionResult,
                        minConsumers, maxConsumers, scaleUpStep, scaleDownStep,
                        lagThreshold, p99Threshold);
                strategyName = "HYBRID";
                confidence = 0.85;
                break;
        }

        decision.setStrategy(strategyName);
        decision.setConfidence(confidence);
        decision.setDryRun(config.isDryRun());

        applyCooldown(decision, lastScalingTime);
        applyRateLimits(decision);
        applySafetyChecks(decision, historicalMetrics);

        return decision;
    }

    private ScalingDecision evaluateLagThreshold(MQType mqType, String clusterName, String topic,
                                                 String consumerGroup, int currentConsumers,
                                                 List<QueueMetrics> historicalMetrics,
                                                 int minConsumers, int maxConsumers,
                                                 int scaleUpStep, int scaleDownStep,
                                                 long lagThreshold, long p99Threshold) {
        if (historicalMetrics == null || historicalMetrics.isEmpty()) {
            return ScalingDecision.noChange(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, "No historical metrics available");
        }

        QueueMetrics latest = historicalMetrics.get(historicalMetrics.size() - 1);

        double lagUtilization = (double) latest.getBacklog() / lagThreshold;
        double p99Utilization = (double) latest.getP99LatencyMs() / p99Threshold;
        double maxUtilization = Math.max(lagUtilization, p99Utilization);

        ScalingDecision decision;
        String reason;

        if (maxUtilization >= config.getScaleUpThreshold()) {
            int target = Math.min(currentConsumers + scaleUpStep, maxConsumers);
            reason = String.format("Utilization %.2f exceeds scale-up threshold %.2f (lag=%d, p99=%dms)",
                    maxUtilization, config.getScaleUpThreshold(),
                    latest.getBacklog(), latest.getP99LatencyMs());
            decision = ScalingDecision.scaleUp(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, target, reason);
        } else if (maxUtilization <= config.getScaleDownThreshold() && currentConsumers > minConsumers) {
            int target = Math.max(currentConsumers - scaleDownStep, minConsumers);
            reason = String.format("Utilization %.2f below scale-down threshold %.2f (lag=%d, p99=%dms)",
                    maxUtilization, config.getScaleDownThreshold(),
                    latest.getBacklog(), latest.getP99LatencyMs());
            decision = ScalingDecision.scaleDown(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, target, reason);
        } else {
            reason = String.format("Utilization %.2f within range (%.2f - %.2f)",
                    maxUtilization, config.getScaleDownThreshold(), config.getScaleUpThreshold());
            decision = ScalingDecision.noChange(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, reason);
        }

        decision.addMetric("currentLag", latest.getBacklog());
        decision.addMetric("p99LatencyMs", latest.getP99LatencyMs());
        decision.addMetric("lagUtilization", lagUtilization);
        decision.addMetric("p99Utilization", p99Utilization);
        decision.addMetric("maxUtilization", maxUtilization);
        decision.addFactor("lagThreshold", lagThreshold);
        decision.addFactor("p99Threshold", p99Threshold);

        return decision;
    }

    private ScalingDecision evaluateLagRate(MQType mqType, String clusterName, String topic,
                                           String consumerGroup, int currentConsumers,
                                           List<QueueMetrics> historicalMetrics,
                                           int minConsumers, int maxConsumers,
                                           int scaleUpStep, int scaleDownStep,
                                           long lagThreshold, long p99Threshold) {
        if (historicalMetrics == null || historicalMetrics.size() < 2) {
            return ScalingDecision.noChange(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, "Insufficient historical metrics for rate calculation");
        }

        QueueMetrics latest = historicalMetrics.get(historicalMetrics.size() - 1);

        double lagRate = calculateLagGrowthRate(historicalMetrics);

        double rateUtilization = Math.abs(lagRate) / config.getLagRateThreshold();

        ScalingDecision decision;
        String reason;

        if (lagRate > config.getLagRateThreshold() && latest.getBacklog() > lagThreshold * 0.5) {
            int target = Math.min(currentConsumers + scaleUpStep, maxConsumers);
            reason = String.format("Lag growth rate %.2f msg/s exceeds threshold %.2f msg/s",
                    lagRate, config.getLagRateThreshold());
            decision = ScalingDecision.scaleUp(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, target, reason);
        } else if (lagRate < -config.getLagRateThreshold() * 0.5 && latest.getBacklog() < lagThreshold * 0.3
                && currentConsumers > minConsumers) {
            int target = Math.max(currentConsumers - scaleDownStep, minConsumers);
            reason = String.format("Lag decreasing rate %.2f msg/s, current lag %d below threshold",
                    lagRate, latest.getBacklog());
            decision = ScalingDecision.scaleDown(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, target, reason);
        } else {
            reason = String.format("Lag growth rate %.2f msg/s within normal range", lagRate);
            decision = ScalingDecision.noChange(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, reason);
        }

        decision.addMetric("lagGrowthRate", lagRate);
        decision.addMetric("currentLag", latest.getBacklog());
        decision.addMetric("rateUtilization", rateUtilization);
        decision.addFactor("lagRateThreshold", config.getLagRateThreshold());

        return decision;
    }

    private ScalingDecision evaluatePredictive(MQType mqType, String clusterName, String topic,
                                            String consumerGroup, int currentConsumers,
                                            List<QueueMetrics> historicalMetrics,
                                            PredictionResult prediction,
                                            int minConsumers, int maxConsumers,
                                            int scaleUpStep, int scaleDownStep,
                                            long lagThreshold, long p99Threshold) {
        if (prediction == null || prediction.getPredictedValues() == null
                || prediction.getPredictedValues().isEmpty()) {
            return evaluateLagThreshold(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, historicalMetrics,
                    minConsumers, maxConsumers, scaleUpStep, scaleDownStep,
                    lagThreshold, p99Threshold);
        }

        QueueMetrics latest = historicalMetrics != null && !historicalMetrics.isEmpty()
                ? historicalMetrics.get(historicalMetrics.size() - 1)
                : null;

        List<Double> predicted = prediction.getPredictedValues();
        double maxPredictedLag = predicted.stream()
                .limit(Math.min(config.getPredictiveHorizonMinutes(), predicted.size()))
                .mapToDouble(Double::doubleValue)
                .max()
                .orElse(0);

        double predictedUtilization = maxPredictedLag / lagThreshold;

        ScalingDecision decision;
        String reason;

        if (predictedUtilization >= config.getScaleUpThreshold()) {
            int target = Math.min(currentConsumers + scaleUpStep, maxConsumers);
            reason = String.format("Predicted max lag %.0f exceeds threshold %d within %d minutes",
                    maxPredictedLag, lagThreshold, config.getPredictiveHorizonMinutes());
            decision = ScalingDecision.scaleUp(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, target, reason);
        } else if (predictedUtilization <= config.getScaleDownThreshold()
                && latest != null
                && latest.getBacklog() < lagThreshold * 0.3
                && currentConsumers > minConsumers) {
            int target = Math.max(currentConsumers - scaleDownStep, minConsumers);
            reason = String.format("Predicted max lag %.0f below threshold %d, current lag %d",
                    maxPredictedLag, lagThreshold, latest.getBacklog());
            decision = ScalingDecision.scaleDown(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, target, reason);
        } else {
            reason = String.format("Predicted max lag %.0f utilization %.2f within range",
                    maxPredictedLag, predictedUtilization);
            decision = ScalingDecision.noChange(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, reason);
        }

        decision.addMetric("predictedMaxLag", maxPredictedLag);
        decision.addMetric("predictedUtilization", predictedUtilization);
        decision.addMetric("burstDetected", prediction.isBurstDetected());
        if (prediction.isBurstDetected()) {
            decision.addMetric("burstMagnitude", prediction.getBurstMagnitude());
            decision.addFactor("burstAdjustmentFactor", prediction.getBurstAdjustmentFactor());
        }
        decision.addFactor("predictiveHorizonMinutes", config.getPredictiveHorizonMinutes());

        return decision;
    }

    private ScalingDecision evaluateHybrid(MQType mqType, String clusterName, String topic,
                                        String consumerGroup,
                                        int currentConsumers,
                                        List<QueueMetrics> historicalMetrics,
                                        PredictionResult predictionResult,
                                        int minConsumers, int maxConsumers,
                                        int scaleUpStep, int scaleDownStep,
                                        long lagThreshold, long p99Threshold) {
        ScalingDecision thresholdDecision = evaluateLagThreshold(mqType, clusterName, topic, consumerGroup,
                currentConsumers, historicalMetrics,
                minConsumers, maxConsumers, scaleUpStep, scaleDownStep,
                lagThreshold, p99Threshold);

        ScalingDecision rateDecision = evaluateLagRate(mqType, clusterName, topic, consumerGroup,
                currentConsumers, historicalMetrics,
                minConsumers, maxConsumers, scaleUpStep, scaleDownStep,
                lagThreshold, p99Threshold);

        ScalingDecision predictiveDecision = evaluatePredictive(mqType, clusterName, topic, consumerGroup,
                currentConsumers, historicalMetrics, predictionResult,
                minConsumers, maxConsumers, scaleUpStep, scaleDownStep,
                lagThreshold, p99Threshold);

        int scaleUpVotes = 0;
        int scaleDownVotes = 0;

        if (thresholdDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP) scaleUpVotes++;
        if (rateDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP) scaleUpVotes++;
        if (predictiveDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP) scaleUpVotes++;

        if (thresholdDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) scaleDownVotes++;
        if (rateDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) scaleDownVotes++;
        if (predictiveDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) scaleDownVotes++;

        ScalingDecision finalDecision;
        double predictiveWeight = config.getPredictiveWeight();
        double thresholdWeight = (1 - predictiveWeight) / 2;
        double rateWeight = (1 - predictiveWeight) / 2;

        double scaleUpScore = 0;
        double scaleDownScore = 0;

        if (thresholdDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP) scaleUpScore += thresholdWeight;
        if (rateDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP) scaleUpScore += rateWeight;
        if (predictiveDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_UP) scaleUpScore += predictiveWeight;

        if (thresholdDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) scaleDownScore += thresholdWeight;
        if (rateDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) scaleDownScore += rateWeight;
        if (predictiveDecision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) scaleDownScore += predictiveWeight;

        if (scaleUpScore > scaleDownScore && scaleUpScore >= 0.4) {
            int maxTarget = Math.max(
                    Math.max(thresholdDecision.getTargetConsumers(),
                            rateDecision.getTargetConsumers()),
                    predictiveDecision.getTargetConsumers());
            String reason = String.format("Hybrid score: scaleUp=%.2f, scaleDown=%.2f (votes: %d up, %d down)",
                    scaleUpScore, scaleDownScore, scaleUpVotes, scaleDownVotes);
            finalDecision = ScalingDecision.scaleUp(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, maxTarget, reason);
        } else if (scaleDownScore > scaleUpScore && scaleDownScore >= 0.4) {
            int minTarget = Math.min(
                    Math.min(thresholdDecision.getTargetConsumers(),
                            rateDecision.getTargetConsumers()),
                    predictiveDecision.getTargetConsumers());
            String reason = String.format("Hybrid score: scaleUp=%.2f, scaleDown=%.2f (votes: %d up, %d down)",
                    scaleUpScore, scaleDownScore, scaleUpVotes, scaleDownVotes);
            finalDecision = ScalingDecision.scaleDown(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, minTarget, reason);
        } else {
            String reason = String.format("Hybrid score: scaleUp=%.2f, scaleDown=%.2f - no consensus",
                    scaleUpScore, scaleDownScore);
            finalDecision = ScalingDecision.noChange(mqType, clusterName, topic, consumerGroup,
                    currentConsumers, reason);
        }

        finalDecision.getMetrics().putAll(thresholdDecision.getMetrics());
        finalDecision.getFactors().putAll(thresholdDecision.getFactors());
        finalDecision.addFactor("thresholdWeight", thresholdWeight);
        finalDecision.addFactor("rateWeight", rateWeight);
        finalDecision.addFactor("predictiveWeight", predictiveWeight);
        finalDecision.addFactor("scaleUpScore", scaleUpScore);
        finalDecision.addFactor("scaleDownScore", scaleDownScore);
        finalDecision.addFactor("scaleUpVotes", scaleUpVotes);
        finalDecision.addFactor("scaleDownVotes", scaleDownVotes);

        return finalDecision;
    }

    private double calculateLagGrowthRate(List<QueueMetrics> metrics) {
        if (metrics.size() < 2) {
            return 0;
        }

        List<Double> lags = new ArrayList<>();
        List<Long> timestamps = new ArrayList<>();

        for (QueueMetrics m : metrics) {
            lags.add((double) m.getBacklog());
            timestamps.add(m.getTimestamp());
        }

        StatsUtil.LinearRegressionResult regression = StatsUtil.linearRegression(timestamps, lags);
        return regression.getSlope() * 1000;
    }

    private void applyCooldown(ScalingDecision decision, long lastScalingTime) {
        long timeSinceLastScaling = System.currentTimeMillis() - lastScalingTime;
        if (lastScalingTime > 0 && timeSinceLastScaling < config.getCooldownPeriodMs()) {
            if (decision.getAction() != AutoScalerConfig.ScalingAction.NO_CHANGE) {
                decision.setAction(AutoScalerConfig.ScalingAction.NO_CHANGE);
                decision.setReason(String.format("In cooldown period: %dms since last scaling (cooldown: %dms)",
                        timeSinceLastScaling, config.getCooldownPeriodMs());
                decision.addWarning("Cooldown active");
                decision.setTargetConsumers(decision.getCurrentConsumers());
                decision.setScaleAmount(0);
            }
        }
    }

    private void applyRateLimits(ScalingDecision decision) {
    }

    private void applySafetyChecks(ScalingDecision decision, List<QueueMetrics> historicalMetrics) {
        if (historicalMetrics == null || historicalMetrics.size() < 3) {
            return;
        }

        QueueMetrics latest = historicalMetrics.get(historicalMetrics.size() - 1);

        if (latest.getLongTailRatio() > config.getLongTailRatioThreshold()) {
            decision.addWarning(String.format("High long tail ratio: %.2f exceeds threshold %.2f",
                    latest.getLongTailRatio(), config.getLongTailRatioThreshold()));
            if (decision.getAction() == AutoScalerConfig.ScalingAction.SCALE_DOWN) {
                decision.setAction(AutoScalerConfig.ScalingAction.NO_CHANGE);
                decision.setReason("Scale-down blocked: high long tail ratio detected");
                decision.setTargetConsumers(decision.getCurrentConsumers());
                decision.setScaleAmount(0);
            }
        }

        if (latest.getMessagesConsumedPerSec() < 1.0 && latest.getBacklog() > 0) {
            decision.addWarning("Very low consumption rate detected");
        }
    }

    public AutoScalerConfig getConfig() {
        return config;
    }
}
