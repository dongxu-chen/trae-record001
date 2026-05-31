package com.tracing.optimizer.core.model;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class CostBudget {

    private double dailyBudgetUsd;
    private double currentSpendUsd;
    private double costPerSpan;
    private double costPerSpanStorage;
    private double costPerSpanNetwork;
    private double costPerSpanCompute;
    private double costPerSpanCpu;
    private double cpuCoreCostPerHourUsd;
    private double spansProcessedPerCoreSecond;
    private double samplingCpuOverheadPercent;
    private Map<String, Double> serviceSpendMap;
    private double alertThresholdPercent;

    public CostBudget() {
        this.serviceSpendMap = new ConcurrentHashMap<>();
        this.alertThresholdPercent = 80.0;
    }

    public CostBudget(double dailyBudgetUsd, double costPerSpan) {
        this();
        this.dailyBudgetUsd = dailyBudgetUsd;
        this.costPerSpan = costPerSpan;
        this.costPerSpanCpu = 0.000008;
        this.cpuCoreCostPerHourUsd = 0.05;
        this.spansProcessedPerCoreSecond = 10000.0;
        this.samplingCpuOverheadPercent = 0.15;
    }

    public double getRemainingBudget() {
        return dailyBudgetUsd - currentSpendUsd;
    }

    public double getBudgetUtilization() {
        if (dailyBudgetUsd <= 0) return 100.0;
        return (currentSpendUsd / dailyBudgetUsd) * 100.0;
    }

    public boolean isOverBudget() {
        return getBudgetUtilization() >= 100.0;
    }

    public boolean isAlertThresholdReached() {
        return getBudgetUtilization() >= alertThresholdPercent;
    }

    public double estimateCost(long spanCount, double samplingRate) {
        long sampledCount = (long) (spanCount * samplingRate);
        return sampledCount * getEffectiveCostPerSpan();
    }

    public double computeMaxAllowedRate(long totalSpansExpected) {
        if (totalSpansExpected <= 0 || getEffectiveCostPerSpan() <= 0) return 1.0;
        double maxRate = getRemainingBudget() / (totalSpansExpected * getEffectiveCostPerSpan());
        return Math.max(0.01, Math.min(1.0, maxRate));
    }

    private double getEffectiveCostPerSpan() {
        return costPerSpan > 0 ? costPerSpan
                : costPerSpanStorage + costPerSpanNetwork + costPerSpanCompute;
    }

    public void recordServiceSpend(String serviceName, double amount) {
        serviceSpendMap.merge(serviceName, amount, Double::sum);
        currentSpendUsd += amount;
    }

    public double getDailyBudgetUsd() { return dailyBudgetUsd; }
    public void setDailyBudgetUsd(double dailyBudgetUsd) { this.dailyBudgetUsd = dailyBudgetUsd; }

    public double getCurrentSpendUsd() { return currentSpendUsd; }
    public void setCurrentSpendUsd(double currentSpendUsd) { this.currentSpendUsd = currentSpendUsd; }

    public double getCostPerSpan() { return costPerSpan; }
    public void setCostPerSpan(double costPerSpan) { this.costPerSpan = costPerSpan; }

    public double getCostPerSpanStorage() { return costPerSpanStorage; }
    public void setCostPerSpanStorage(double costPerSpanStorage) { this.costPerSpanStorage = costPerSpanStorage; }

    public double getCostPerSpanNetwork() { return costPerSpanNetwork; }
    public void setCostPerSpanNetwork(double costPerSpanNetwork) { this.costPerSpanNetwork = costPerSpanNetwork; }

    public double getCostPerSpanCompute() { return costPerSpanCompute; }
    public void setCostPerSpanCompute(double costPerSpanCompute) { this.costPerSpanCompute = costPerSpanCompute; }

    public double getCostPerSpanCpu() { return costPerSpanCpu; }
    public void setCostPerSpanCpu(double costPerSpanCpu) { this.costPerSpanCpu = costPerSpanCpu; }

    public double getCpuCoreCostPerHourUsd() { return cpuCoreCostPerHourUsd; }
    public void setCpuCoreCostPerHourUsd(double c) { this.cpuCoreCostPerHourUsd = c; }

    public double getSpansProcessedPerCoreSecond() { return spansProcessedPerCoreSecond; }
    public void setSpansProcessedPerCoreSecond(double s) { this.spansProcessedPerCoreSecond = s; }

    public double getSamplingCpuOverheadPercent() { return samplingCpuOverheadPercent; }
    public void setSamplingCpuOverheadPercent(double s) { this.samplingCpuOverheadPercent = s; }

    public Map<String, Double> getServiceSpendMap() { return serviceSpendMap; }

    public double getAlertThresholdPercent() { return alertThresholdPercent; }
    public void setAlertThresholdPercent(double alertThresholdPercent) { this.alertThresholdPercent = alertThresholdPercent; }
}
