package com.tracing.optimizer.core.rl;

import com.tracing.optimizer.core.model.CostBudget;
import com.tracing.optimizer.core.model.ServiceMetadata;
import com.tracing.optimizer.core.model.TraceMetrics;

import java.util.*;

public class SamplingEnvironment {

    private final Map<String, ServiceMetadata> services;
    private final Map<String, TraceMetrics> metricsMap;
    private final Map<String, Double> currentRates;
    private final Map<String, Double> previousRates;
    private CostBudget budget;
    private final RewardFunction rewardFunction;
    private int stepCount;

    public SamplingEnvironment(RewardFunction rewardFunction) {
        this.services = new LinkedHashMap<>();
        this.metricsMap = new LinkedHashMap<>();
        this.currentRates = new LinkedHashMap<>();
        this.previousRates = new LinkedHashMap<>();
        this.rewardFunction = rewardFunction;
        this.stepCount = 0;
    }

    public State observe() {
        State state = new State();
        for (Map.Entry<String, ServiceMetadata> entry : services.entrySet()) {
            String svc = entry.getKey();
            ServiceMetadata meta = entry.getValue();
            TraceMetrics metrics = metricsMap.get(svc);
            double currentRate = currentRates.getOrDefault(svc, 0.1);

            ServiceState ss = new ServiceState();
            ss.serviceName = svc;
            ss.businessImportance = meta.getBusinessImportance();
            ss.errorRate = meta.getErrorRate();
            ss.p99LatencyMs = meta.getP99LatencyMs();
            ss.requestRate = meta.getRequestRate();
            ss.currentSamplingRate = currentRate;
            ss.effectiveErrorRate = metrics != null ? metrics.getErrorRate() : 0.0;
            ss.throughput = metrics != null ? metrics.getThroughputPerSecond() : 0L;
            state.serviceStates.add(ss);
        }
        state.budgetUtilization = budget != null ? budget.getBudgetUtilization() : 0.0;
        state.stepCount = stepCount;
        return state;
    }

    public Map<String, Double> step(Map<String, Double> actionRates) {
        previousRates.putAll(currentRates);
        Map<String, Double> rewards = new LinkedHashMap<>();

        for (Map.Entry<String, Double> entry : actionRates.entrySet()) {
            String svc = entry.getKey();
            double newRate = Math.max(0.01, Math.min(1.0, entry.getValue()));
            double oldRate = currentRates.getOrDefault(svc, 0.1);

            currentRates.put(svc, newRate);

            ServiceMetadata meta = services.get(svc);
            TraceMetrics metrics = metricsMap.get(svc);
            if (meta != null) {
                RewardFunction.RewardContext ctx = new RewardFunction.RewardContext()
                        .metadata(meta)
                        .metrics(metrics)
                        .budget(budget)
                        .currentSamplingRate(newRate)
                        .previousSamplingRate(oldRate);
                rewards.put(svc, rewardFunction.computeReward(ctx));
            }
        }

        stepCount++;
        return rewards;
    }

    public void registerService(ServiceMetadata metadata, double initialRate) {
        services.put(metadata.getServiceName(), metadata);
        currentRates.put(metadata.getServiceName(), initialRate);
        previousRates.put(metadata.getServiceName(), initialRate);
    }

    public void updateMetrics(String serviceName, TraceMetrics metrics) {
        metricsMap.put(serviceName, metrics);
    }

    public void updateServiceMetadata(ServiceMetadata metadata) {
        services.put(metadata.getServiceName(), metadata);
    }

    public Map<String, Double> getCurrentRates() { return Collections.unmodifiableMap(currentRates); }
    public Map<String, ServiceMetadata> getServices() { return Collections.unmodifiableMap(services); }
    public CostBudget getBudget() { return budget; }
    public void setBudget(CostBudget budget) { this.budget = budget; }
    public int getStepCount() { return stepCount; }

    public static class State {
        public List<ServiceState> serviceStates = new ArrayList<>();
        public double budgetUtilization;
        public int stepCount;
    }

    public static class ServiceState {
        public String serviceName;
        public double businessImportance;
        public double errorRate;
        public double p99LatencyMs;
        public long requestRate;
        public double currentSamplingRate;
        public double effectiveErrorRate;
        public long throughput;
    }
}
