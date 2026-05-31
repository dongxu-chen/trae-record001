package com.tracing.optimizer.core.engine;

import com.tracing.optimizer.core.cost.CostModel;
import com.tracing.optimizer.core.edge.EdgeSampler;
import com.tracing.optimizer.core.enhanced.AnomalySamplingEnhancer;
import com.tracing.optimizer.core.evaluation.SamplingEffectEvaluator;
import com.tracing.optimizer.core.feedback.FeedbackLoop;
import com.tracing.optimizer.core.model.*;
import com.tracing.optimizer.core.rl.RewardFunction;
import com.tracing.optimizer.core.rl.SamplingAgent;
import com.tracing.optimizer.core.rl.SamplingEnvironment;
import com.tracing.optimizer.core.storage.DynamicStorageStrategy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.*;

public class SamplingOptimizer {

    private static final Logger log = LoggerFactory.getLogger(SamplingOptimizer.class);

    private final SamplingEnvironment environment;
    private final SamplingAgent agent;
    private final RewardFunction rewardFunction;
    private final CostModel costModel;
    private final EdgeSampler edgeSampler;
    private final AnomalySamplingEnhancer anomalyEnhancer;
    private final SamplingEffectEvaluator effectEvaluator;
    private final DynamicStorageStrategy storageStrategy;
    private FeedbackLoop feedbackLoop;
    private final ScheduledExecutorService optimizerScheduler;
    private final long optimizationIntervalMs;
    private final Map<String, SamplingRate> currentSamplingRates;
    private volatile boolean running;

    public SamplingOptimizer(CostModel costModel) {
        this.rewardFunction = new RewardFunction();
        this.environment = new SamplingEnvironment(rewardFunction);
        this.agent = new SamplingAgent();
        this.costModel = costModel;
        this.edgeSampler = new EdgeSampler();
        this.anomalyEnhancer = new AnomalySamplingEnhancer();
        this.effectEvaluator = new SamplingEffectEvaluator();
        this.storageStrategy = new DynamicStorageStrategy();
        this.optimizationIntervalMs = 60000L;
        this.optimizerScheduler = Executors.newScheduledThreadPool(3);
        this.currentSamplingRates = new ConcurrentHashMap<>();
        this.running = false;
    }

    public void initialize() {
        if (costModel.getBudget() != null) {
            environment.setBudget(costModel.getBudget());
        }
        this.feedbackLoop = new FeedbackLoop(agent, environment, optimizationIntervalMs / 2);
        log.info("Sampling optimizer initialized");
    }

    public void start() {
        if (running) return;
        running = true;
        optimizerScheduler.scheduleAtFixedRate(this::optimizeAll,
                optimizationIntervalMs, optimizationIntervalMs, TimeUnit.MILLISECONDS);
        optimizerScheduler.scheduleAtFixedRate(this::pushCentralDecisionsToEdge,
                15000L, 15000L, TimeUnit.MILLISECONDS);
        optimizerScheduler.scheduleAtFixedRate(this::cleanupEnhancers,
                300000L, 300000L, TimeUnit.MILLISECONDS);
        edgeSampler.start();
        feedbackLoop.start();
        log.info("Sampling optimizer started with interval {}ms", optimizationIntervalMs);
    }

    public void stop() {
        running = false;
        optimizerScheduler.shutdown();
        try {
            if (!optimizerScheduler.awaitTermination(10, TimeUnit.SECONDS)) {
                optimizerScheduler.shutdownNow();
            }
        } catch (InterruptedException e) {
            optimizerScheduler.shutdownNow();
            Thread.currentThread().interrupt();
        }
        edgeSampler.stop();
        if (feedbackLoop != null) {
            feedbackLoop.stop();
        }
        log.info("Sampling optimizer stopped");
    }

    public void registerService(ServiceMetadata metadata) {
        double initialRate = costModel.computeOptimalSamplingRate(metadata, null);
        environment.registerService(metadata, initialRate);
        edgeSampler.updateServiceMetadata(metadata);

        SamplingRate rate = new SamplingRate(metadata.getServiceName(), initialRate,
                "initial-cost-based");
        currentSamplingRates.put(metadata.getServiceName(), rate);
        log.info("Registered service {} with initial sampling rate {}",
                metadata.getServiceName(), initialRate);
    }

    public void updateMetrics(TraceMetrics metrics) {
        environment.updateMetrics(metrics.getServiceName(), metrics);
        edgeSampler.updateMetrics(metrics);
        ServiceMetadata meta = environment.getServices().get(metrics.getServiceName());
        if (meta != null) {
            double costRate = costModel.computeOptimalSamplingRate(meta, metrics);
            if (Math.abs(costRate - currentSamplingRates.getOrDefault(
                    metrics.getServiceName(), new SamplingRate()).getRate()) > 0.1) {
                log.info("Cost model suggests different rate for {}: cost={}, current={}",
                        metrics.getServiceName(), costRate,
                        currentSamplingRates.get(metrics.getServiceName()).getRate());
            }
        }
    }

    public Map<String, SamplingRate> optimizeAll() {
        try {
            SamplingEnvironment.State state = environment.observe();
            Map<String, Double> agentActions = agent.selectActions(state);

            Map<String, Double> blendedRates = new LinkedHashMap<>();
            for (Map.Entry<String, Double> entry : agentActions.entrySet()) {
                String svc = entry.getKey();
                double rlRate = entry.getValue();

                ServiceMetadata meta = environment.getServices().get(svc);
                TraceMetrics metrics = state.serviceStates.stream()
                        .filter(ss -> ss.serviceName.equals(svc))
                        .findFirst()
                        .map(ss -> {
                            com.tracing.optimizer.core.model.TraceMetrics m =
                                    new com.tracing.optimizer.core.model.TraceMetrics();
                            m.setServiceName(ss.serviceName);
                            m.setErrorRate(ss.effectiveErrorRate);
                            m.setP99LatencyMs(ss.p99LatencyMs);
                            m.setThroughputPerSecond(ss.throughput);
                            return m;
                        }).orElse(null);

                double costRate = meta != null
                        ? costModel.computeOptimalSamplingRate(meta, metrics) : rlRate;

                double blended = 0.6 * rlRate + 0.4 * costRate;

                CostModel.ComprehensiveCostAssessment assessment =
                        costModel.computeComprehensiveCostAssessment(svc, meta, metrics, blended);
                blended = assessment.recommendedRate;
                log.debug("Comprehensive assessment for {}: score={}, recommendation={}",
                        svc, assessment.compositeScore, assessment.recommendation);

                blendedRates.put(svc, blended);
            }

            Map<String, Double> rewards = environment.step(blendedRates);

            for (Map.Entry<String, Double> entry : rewards.entrySet()) {
                String svc = entry.getKey();
                int actionIdx = agent.rateToActionIndex(blendedRates.get(svc));
                agent.learn(svc, environment.getStepCount(), actionIdx, entry.getValue(),
                        environment.getStepCount() + 1, false);
            }
            agent.decayExploration();

            for (Map.Entry<String, Double> entry : blendedRates.entrySet()) {
                String svc = entry.getKey();
                double newRate = entry.getValue();

                SamplingRate current = currentSamplingRates.get(svc);
                SamplingRate newSamplingRate = new SamplingRate(svc, newRate, "rl-cost-assessment-blended");
                if (current != null) {
                    newSamplingRate.setPreviousRate(current.getRate());
                }

                newSamplingRate.setEdgeOptimized(true);
                newSamplingRate.setConfidenceScore(
                        edgeSampler.computeEdgeRate(svc, newRate).getConfidenceScore()
                );

                currentSamplingRates.put(svc, newSamplingRate);
                edgeSampler.updateServiceMetadata(environment.getServices().get(svc));

                if (newSamplingRate.isSignificantChange(0.05)) {
                    log.info("Significant rate change for {}: {} -> {}",
                            svc, newSamplingRate.getPreviousRate(), newRate);
                }
            }

            recordCosts();
            return Collections.unmodifiableMap(currentSamplingRates);
        } catch (Exception e) {
            log.error("Error during optimization cycle", e);
            return Collections.emptyMap();
        }
    }

    private void recordCosts() {
        Map<String, Double> rates = environment.getCurrentRates();
        for (Map.Entry<String, ServiceMetadata> entry : environment.getServices().entrySet()) {
            String svc = entry.getKey();
            Double rate = rates.getOrDefault(svc, 0.1);
            TraceMetrics metrics = environment.getServices().size() > 0 ? null : null;
            double cost = costModel.estimateDailyCost(svc, 100L, rate);
            costModel.recordActualCost(svc, cost);
        }
    }

    public void pushCentralDecisionsToEdge() {
        for (Map.Entry<String, SamplingRate> entry : currentSamplingRates.entrySet()) {
            String svc = entry.getKey();
            SamplingRate rate = entry.getValue();
            ServiceMetadata meta = environment.getServices().get(svc);
            String serviceLevel = meta != null
                    ? (meta.getBusinessImportance() >= 0.8 ? "CRITICAL"
                            : meta.getBusinessImportance() >= 0.5 ? "IMPORTANT" : "NORMAL")
                    : "NORMAL";

            EdgeSampler.CentralDecision decision = new EdgeSampler.CentralDecision(
                    svc,
                    rate.getRate(),
                    System.currentTimeMillis(),
                    rate.getReason(),
                    rate.getConfidenceScore(),
                    serviceLevel
            );
            edgeSampler.updateCentralDecision(decision);
        }
        log.debug("Pushed {} central decisions to edge sampler", currentSamplingRates.size());
    }

    public void submitFeedback(FeedbackSignal signal) {
        if (feedbackLoop != null) {
            feedbackLoop.submitSignal(signal);
        }
    }

    public SamplingRate getCurrentRate(String serviceName) {
        return currentSamplingRates.get(serviceName);
    }

    public Map<String, SamplingRate> getAllCurrentRates() {
        return Collections.unmodifiableMap(currentSamplingRates);
    }

    public EdgeSampler getEdgeSampler() { return edgeSampler; }
    public CostModel getCostModel() { return costModel; }
    public SamplingAgent getAgent() { return agent; }
    public SamplingEnvironment getEnvironment() { return environment; }
    public FeedbackLoop getFeedbackLoop() { return feedbackLoop; }
    public AnomalySamplingEnhancer getAnomalyEnhancer() { return anomalyEnhancer; }
    public SamplingEffectEvaluator getEffectEvaluator() { return effectEvaluator; }
    public DynamicStorageStrategy getStorageStrategy() { return storageStrategy; }

    public boolean shouldForceSample(String traceId, String serviceName, boolean hasError, int statusCode) {
        return anomalyEnhancer.shouldForceSample(traceId, serviceName, hasError, statusCode);
    }

    public void recordServiceHeat(String serviceName) {
        storageStrategy.recordServiceAccess(serviceName);
    }

    public double applyHeatTierAdjustment(String serviceName, double baseRate) {
        return storageStrategy.getAdjustedSamplingRate(serviceName, baseRate);
    }

    public void recordProblem(String problemId, String serviceName, SamplingEffectEvaluator.ProblemType type,
                              boolean detected, double samplingRate) {
        effectEvaluator.recordProblem(problemId, serviceName, type, detected, samplingRate);
    }

    private void cleanupEnhancers() {
        anomalyEnhancer.cleanupExpiredContexts();
        effectEvaluator.cleanupOldRecords();
        storageStrategy.cleanupIdleMetrics();
        log.debug("Cleaned up enhancer data structures");
    }
}
