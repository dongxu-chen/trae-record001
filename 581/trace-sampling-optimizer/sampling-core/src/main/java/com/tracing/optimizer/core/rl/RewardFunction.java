package com.tracing.optimizer.core.rl;

import com.tracing.optimizer.core.model.ServiceMetadata;
import com.tracing.optimizer.core.model.TraceMetrics;
import com.tracing.optimizer.core.model.CostBudget;

public class RewardFunction {

    private double observabilityWeight;
    private double costWeight;
    private double errorDetectionWeight;
    private double latencyWeight;
    private double stabilityWeight;

    public RewardFunction() {
        this.observabilityWeight = 0.25;
        this.costWeight = 0.25;
        this.errorDetectionWeight = 0.20;
        this.latencyWeight = 0.15;
        this.stabilityWeight = 0.15;
    }

    public double computeReward(RewardContext context) {
        double obsReward = computeObservabilityReward(context);
        double costReward = computeCostReward(context);
        double errorReward = computeErrorDetectionReward(context);
        double latencyReward = computeLatencyReward(context);
        double stabilityReward = computeStabilityReward(context);

        return observabilityWeight * obsReward
                + costWeight * costReward
                + errorDetectionWeight * errorReward
                + latencyWeight * latencyReward
                + stabilityWeight * stabilityReward;
    }

    private double computeObservabilityReward(RewardContext ctx) {
        double targetCoverage = ctx.getMetadata().computePriorityScore();
        double actualCoverage = ctx.getCurrentSamplingRate();
        double gap = Math.abs(targetCoverage - actualCoverage);
        return 1.0 - gap;
    }

    private double computeCostReward(RewardContext ctx) {
        if (ctx.getBudget() == null) return 0.5;
        double utilization = ctx.getBudget().getBudgetUtilization();
        if (utilization <= 70.0) return 1.0;
        if (utilization <= 90.0) return 1.0 - (utilization - 70.0) / 40.0;
        if (utilization <= 100.0) return -(utilization - 90.0) / 10.0;
        return -1.0 - (utilization - 100.0) / 50.0;
    }

    private double computeErrorDetectionReward(RewardContext ctx) {
        if (ctx.getMetrics() == null) return 0.5;
        double errorRate = ctx.getMetrics().getErrorRate();
        double samplingRate = ctx.getCurrentSamplingRate();
        if (errorRate > 0.05 && samplingRate < 0.3) return -1.0;
        if (errorRate > 0.01 && samplingRate < 0.1) return -0.5;
        if (errorRate < 0.001 && samplingRate > 0.8) return -0.3;
        return 1.0;
    }

    private double computeLatencyReward(RewardContext ctx) {
        if (ctx.getMetrics() == null) return 0.5;
        double p99 = ctx.getMetrics().getP99LatencyMs();
        double samplingRate = ctx.getCurrentSamplingRate();
        if (p99 > 2000 && samplingRate < 0.3) return -0.8;
        if (p99 > 1000 && samplingRate < 0.2) return -0.5;
        return 0.5 + 0.5 * (1.0 - Math.min(p99 / 5000.0, 1.0));
    }

    private double computeStabilityReward(RewardContext ctx) {
        double rateChange = Math.abs(ctx.getCurrentSamplingRate() - ctx.getPreviousSamplingRate());
        if (rateChange < 0.05) return 1.0;
        if (rateChange < 0.15) return 0.5;
        if (rateChange < 0.3) return 0.0;
        return -0.5;
    }

    public static class RewardContext {
        private ServiceMetadata metadata;
        private TraceMetrics metrics;
        private CostBudget budget;
        private double currentSamplingRate;
        private double previousSamplingRate;

        public RewardContext metadata(ServiceMetadata m) { this.metadata = m; return this; }
        public RewardContext metrics(TraceMetrics m) { this.metrics = m; return this; }
        public RewardContext budget(CostBudget b) { this.budget = b; return this; }
        public RewardContext currentSamplingRate(double r) { this.currentSamplingRate = r; return this; }
        public RewardContext previousSamplingRate(double r) { this.previousSamplingRate = r; return this; }

        public ServiceMetadata getMetadata() { return metadata; }
        public TraceMetrics getMetrics() { return metrics; }
        public CostBudget getBudget() { return budget; }
        public double getCurrentSamplingRate() { return currentSamplingRate; }
        public double getPreviousSamplingRate() { return previousSamplingRate; }
    }

    public double getObservabilityWeight() { return observabilityWeight; }
    public void setObservabilityWeight(double w) { this.observabilityWeight = w; }

    public double getCostWeight() { return costWeight; }
    public void setCostWeight(double w) { this.costWeight = w; }

    public double getErrorDetectionWeight() { return errorDetectionWeight; }
    public void setErrorDetectionWeight(double w) { this.errorDetectionWeight = w; }

    public double getLatencyWeight() { return latencyWeight; }
    public void setLatencyWeight(double w) { this.latencyWeight = w; }

    public double getStabilityWeight() { return stabilityWeight; }
    public void setStabilityWeight(double w) { this.stabilityWeight = w; }
}
