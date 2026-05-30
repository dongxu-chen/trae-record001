package com.tracing.sampling.sampler;

import com.tracing.sampling.adjuster.AdaptiveRateAdjuster;
import com.tracing.sampling.config.TracingProperties;
import com.tracing.sampling.model.SamplingCostAnalysis;
import com.tracing.sampling.model.SamplingCostAnalysis.CostRecommendation;
import com.tracing.sampling.model.SamplingCostAnalysis.EndpointCostMetrics;
import com.tracing.sampling.model.SamplingDecisionRecord;
import com.tracing.sampling.model.SamplingDecisionTree;
import com.tracing.sampling.model.SamplingDecisionTree.DecisionStep;
import com.tracing.sampling.model.SamplingFeedbackLoop;
import com.tracing.sampling.model.SamplingFeedbackLoop.EstimatedMetrics;
import com.tracing.sampling.model.SamplingStats;
import com.tracing.sampling.store.SamplingConfigStore;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.trace.SpanKind;
import io.opentelemetry.context.Context;
import io.opentelemetry.sdk.trace.data.LinkData;
import io.opentelemetry.sdk.trace.samplers.Sampler;
import io.opentelemetry.sdk.trace.samplers.SamplingDecision;
import io.opentelemetry.sdk.trace.samplers.SamplingResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class IntelligentAdaptiveSampler implements Sampler {

    private static final Logger logger = LoggerFactory.getLogger(IntelligentAdaptiveSampler.class);
    
    private static final AttributeKey<String> SAMPLING_REASON = AttributeKey.stringKey("sampling.reason");
    private static final AttributeKey<Double> SAMPLING_RATE = AttributeKey.doubleKey("sampling.rate");
    private static final AttributeKey<String> SERVICE_IMPORTANCE = AttributeKey.stringKey("service.importance");
    private static final AttributeKey<Long> LATENCY_PREDICTION_MS = AttributeKey.longKey("sampling.latency_prediction_ms");
    private static final AttributeKey<Double> ERROR_RATE_MULTIPLIER = AttributeKey.doubleKey("sampling.error_rate_multiplier");

    private static final int MAX_DECISION_HISTORY = 100;

    private final TracingProperties tracingProperties;
    private final SamplingConfigStore configStore;
    private final AdaptiveRateAdjuster rateAdjuster;
    private final CrossServiceTraceSampler crossServiceSampler;
    private final Random random;
    
    private final AtomicLong totalRequests = new AtomicLong(0);
    private final AtomicLong sampledRequests = new AtomicLong(0);
    private final AtomicLong highLatencySampled = new AtomicLong(0);
    private final AtomicLong errorSampled = new AtomicLong(0);
    private final AtomicLong parentSampled = new AtomicLong(0);
    private final AtomicLong errorRateBoosted = new AtomicLong(0);
    private final AtomicLong crossServiceConsistentSampled = new AtomicLong(0);

    private final Queue<SamplingDecisionRecord> recentDecisions;
    private final ConcurrentHashMap<String, SamplingDecisionTree> decisionTreeCache;
    private final SamplingFeedbackLoop feedbackLoop;
    private final SamplingCostAnalysis costAnalysis;

    private volatile double currentSampleRate;
    private volatile long lastStatsResetTime;

    @Autowired
    public IntelligentAdaptiveSampler(TracingProperties tracingProperties, 
                                      SamplingConfigStore configStore,
                                      AdaptiveRateAdjuster rateAdjuster,
                                      CrossServiceTraceSampler crossServiceSampler) {
        this.tracingProperties = tracingProperties;
        this.configStore = configStore;
        this.rateAdjuster = rateAdjuster;
        this.crossServiceSampler = crossServiceSampler;
        this.random = new Random();
        this.currentSampleRate = tracingProperties.getSampling().getDefaultSampleRate();
        this.lastStatsResetTime = System.currentTimeMillis();
        this.recentDecisions = new LinkedList<>();
        this.decisionTreeCache = new ConcurrentHashMap<>();
        this.feedbackLoop = new SamplingFeedbackLoop();
        this.costAnalysis = new SamplingCostAnalysis();
        
        logger.info("Intelligent Adaptive Sampler initialized with base rate: {}", currentSampleRate);
    }

    @Override
    public SamplingResult shouldSample(Context parentContext, String traceId, String name, 
                                       SpanKind spanKind, Attributes attributes, List<LinkData> parentLinks) {
        
        if (!tracingProperties.getSampling().isEnabled()) {
            return SamplingResult.create(SamplingDecision.DROP);
        }

        totalRequests.incrementAndGet();
        long startTime = System.nanoTime();

        SamplingDecisionReason reason = new SamplingDecisionReason();
        reason.setBaseRate(currentSampleRate);
        reason.setTraceId(traceId);
        reason.setSpanName(name);
        reason.setServiceImportance(tracingProperties.getService().getImportance().name());

        SamplingDecisionTree decisionTree = buildDecisionTree(traceId, name, attributes, parentContext);

        Boolean consistentDecision = crossServiceSampler.getRootSamplingDecision(traceId);
        String serviceName = tracingProperties.getService().getName();
        boolean isRoot = !isParentSampled(parentContext) && spanKind == SpanKind.SERVER;

        if (consistentDecision != null) {
            crossServiceConsistentSampled.incrementAndGet();
            reason.setReason("CROSS_SERVICE_CONSISTENT");
            reason.setCrossServiceConsistent(true);
            decisionTree.setFinalDecision(consistentDecision);
            decisionTree.setFinalReason("CROSS_SERVICE_CONSISTENT");
            
            DecisionStep step = new DecisionStep(0, "跨服务关联采样", 
                    "检查调用链统一采样决策", true, 
                    consistentDecision ? "采样" : "不采样");
            step.addDetail("rootDecision", consistentDecision);
            step.addDetail("consistentSampling", true);
            decisionTree.addDecisionStep(step);
            
            SamplingDecision samplingDecision = consistentDecision 
                    ? SamplingDecision.RECORD_AND_SAMPLE 
                    : SamplingDecision.DROP;
            
            long processingTime = (System.nanoTime() - startTime) / 1_000_000;
            recordCostMetrics(name, samplingDecision == SamplingDecision.RECORD_AND_SAMPLE, 
                    processingTime, currentSampleRate);
            recordFeedbackMetrics(name, samplingDecision == SamplingDecision.RECORD_AND_SAMPLE,
                    0, isErrorRequest(attributes), currentSampleRate);
            crossServiceSampler.recordServiceSpan(traceId, serviceName, 0, isErrorRequest(attributes));
            
            return createSamplingResult(samplingDecision, reason, decisionTree);
        }

        if (isRoot) {
            DecisionStep step = new DecisionStep(0, "跨服务关联采样", 
                    "根Span，设置调用链采样决策", true, "继续判断");
            step.addDetail("isRootSpan", true);
            decisionTree.addDecisionStep(step);
        }

        if (isParentSampled(parentContext)) {
            parentSampled.incrementAndGet();
            reason.setReason("PARENT_SAMPLED");
            reason.setParentSampled(true);
            decisionTree.setFinalDecision(true);
            decisionTree.setFinalReason("PARENT_SAMPLED");
            
            DecisionStep step = new DecisionStep(1, "父链路检查", 
                    "父链路是否已采样", true, "采样");
            step.addDetail("parentSampled", true);
            decisionTree.addDecisionStep(step);
            
            if (isRoot) {
                crossServiceSampler.recordRootSamplingDecision(traceId, true, "PARENT_SAMPLED", serviceName);
            }
            
            long processingTime = (System.nanoTime() - startTime) / 1_000_000;
            recordCostMetrics(name, true, processingTime, currentSampleRate);
            recordFeedbackMetrics(name, true, 0, isErrorRequest(attributes), currentSampleRate);
            crossServiceSampler.recordServiceSpan(traceId, serviceName, 0, isErrorRequest(attributes));
            
            return createSamplingResult(SamplingDecision.RECORD_AND_SAMPLE, reason, decisionTree);
        }

        DecisionStep parentStep = new DecisionStep(1, "父链路检查", 
                "父链路是否已采样", false, "继续判断");
        parentStep.addDetail("parentSampled", false);
        decisionTree.addDecisionStep(parentStep);

        if (isErrorRequest(attributes)) {
            errorSampled.incrementAndGet();
            reason.setReason("ERROR_REQUEST");
            reason.setError(true);
            reason.setFinalRate(tracingProperties.getSampling().getErrorSampleRate());
            sampledRequests.incrementAndGet();
            decisionTree.setFinalDecision(true);
            decisionTree.setFinalReason("ERROR_REQUEST");
            
            DecisionStep step = new DecisionStep(2, "错误检查", 
                    "请求是否为错误请求", true, "采样");
            step.addDetail("isError", true);
            step.addDetail("errorSampleRate", tracingProperties.getSampling().getErrorSampleRate());
            decisionTree.addDecisionStep(step);
            
            if (isRoot) {
                crossServiceSampler.recordRootSamplingDecision(traceId, true, "ERROR_REQUEST", serviceName);
            }
            
            long processingTime = (System.nanoTime() - startTime) / 1_000_000;
            recordCostMetrics(name, true, processingTime, currentSampleRate);
            recordFeedbackMetrics(name, true, 0, true, currentSampleRate);
            crossServiceSampler.recordServiceSpan(traceId, serviceName, 0, true);
            
            return createSamplingResult(SamplingDecision.RECORD_AND_SAMPLE, reason, decisionTree);
        }

        DecisionStep errorStep = new DecisionStep(2, "错误检查", 
                "请求是否为错误请求", false, "继续判断");
        errorStep.addDetail("isError", false);
        decisionTree.addDecisionStep(errorStep);

        long predictedLatency = predictLatency(name, attributes);
        reason.setPredictedLatency(predictedLatency);

        if (predictedLatency >= tracingProperties.getSampling().getHighLatencyThresholdMs()) {
            highLatencySampled.incrementAndGet();
            reason.setReason("HIGH_LATENCY");
            reason.setFinalRate(1.0);
            sampledRequests.incrementAndGet();
            decisionTree.setFinalDecision(true);
            decisionTree.setFinalReason("HIGH_LATENCY");
            
            DecisionStep step = new DecisionStep(3, "高延迟检查", 
                    "预测延迟是否超过阈值", true, "采样");
            step.addDetail("predictedLatency", predictedLatency + "ms");
            step.addDetail("threshold", tracingProperties.getSampling().getHighLatencyThresholdMs() + "ms");
            decisionTree.addDecisionStep(step);
            
            if (isRoot) {
                crossServiceSampler.recordRootSamplingDecision(traceId, true, "HIGH_LATENCY", serviceName);
            }
            
            long processingTime = (System.nanoTime() - startTime) / 1_000_000;
            recordCostMetrics(name, true, processingTime, currentSampleRate);
            recordFeedbackMetrics(name, true, predictedLatency, false, currentSampleRate);
            crossServiceSampler.recordServiceSpan(traceId, serviceName, predictedLatency, false);
            
            return createSamplingResult(SamplingDecision.RECORD_AND_SAMPLE, reason, decisionTree);
        }

        DecisionStep latencyStep = new DecisionStep(3, "高延迟检查", 
                "预测延迟是否超过阈值", false, "继续判断");
        latencyStep.addDetail("predictedLatency", predictedLatency + "ms");
        latencyStep.addDetail("threshold", tracingProperties.getSampling().getHighLatencyThresholdMs() + "ms");
        decisionTree.addDecisionStep(latencyStep);

        double errorRateMultiplier = getErrorRateMultiplier();
        reason.setErrorRateMultiplier(errorRateMultiplier);
        decisionTree.addFactor("errorRateMultiplier", errorRateMultiplier);

        if (errorRateMultiplier > 1.0) {
            errorRateBoosted.incrementAndGet();
        }

        double adjustedRate = calculateAdjustedRate(name, attributes, errorRateMultiplier, reason);
        reason.setFinalRate(adjustedRate);
        decisionTree.setFinalSampleRate(adjustedRate);

        DecisionStep rateStep = new DecisionStep(4, "采样率计算", 
                "计算最终采样率", true, 
                String.format("采样率: %.4f", adjustedRate));
        rateStep.addDetail("baseRate", reason.getBaseRate());
        rateStep.addDetail("importanceMultiplier", reason.getImportanceMultiplier());
        rateStep.addDetail("endpointMultiplier", reason.getEndpointMultiplier());
        rateStep.addDetail("errorRateMultiplier", errorRateMultiplier);
        rateStep.addDetail("finalRate", adjustedRate);
        decisionTree.addDecisionStep(rateStep);

        boolean shouldSample = random.nextDouble() < adjustedRate;
        long processingTime = (System.nanoTime() - startTime) / 1_000_000;
        
        if (shouldSample) {
            sampledRequests.incrementAndGet();
            reason.setReason("PROBABILISTIC");
            decisionTree.setFinalDecision(true);
            decisionTree.setFinalReason("PROBABILISTIC");
            
            DecisionStep step = new DecisionStep(5, "概率采样", 
                    "随机概率是否命中采样率", true, "采样");
            step.addDetail("sampled", true);
            step.addDetail("randomValue", String.format("%.4f", random.nextDouble()));
            step.addDetail("adjustedRate", String.format("%.4f", adjustedRate));
            decisionTree.addDecisionStep(step);
            
            if (isRoot) {
                crossServiceSampler.recordRootSamplingDecision(traceId, true, "PROBABILISTIC", serviceName);
            }
            
            recordCostMetrics(name, true, processingTime, adjustedRate);
            recordFeedbackMetrics(name, true, predictedLatency, false, adjustedRate);
            crossServiceSampler.recordServiceSpan(traceId, serviceName, predictedLatency, false);
            
            return createSamplingResult(SamplingDecision.RECORD_AND_SAMPLE, reason, decisionTree);
        } else {
            reason.setReason("NOT_SAMPLED");
            decisionTree.setFinalDecision(false);
            decisionTree.setFinalReason("NOT_SAMPLED");
            
            DecisionStep step = new DecisionStep(5, "概率采样", 
                    "随机概率是否命中采样率", false, "不采样");
            step.addDetail("sampled", false);
            step.addDetail("adjustedRate", String.format("%.4f", adjustedRate));
            decisionTree.addDecisionStep(step);
            
            if (isRoot) {
                crossServiceSampler.recordRootSamplingDecision(traceId, false, "NOT_SAMPLED", serviceName);
            }
            
            recordCostMetrics(name, false, processingTime, adjustedRate);
            recordFeedbackMetrics(name, false, predictedLatency, false, adjustedRate);
            crossServiceSampler.recordServiceSpan(traceId, serviceName, predictedLatency, false);
            
            return createSamplingResult(SamplingDecision.DROP, reason, decisionTree);
        }
    }

    private void recordCostMetrics(String endpoint, boolean sampled, 
                                   long processingTimeMs, double sampleRate) {
        long estimatedSpanSize = 1024;
        costAnalysis.recordSpan(endpoint, sampled, estimatedSpanSize, processingTimeMs, sampleRate);
    }

    private void recordFeedbackMetrics(String endpoint, boolean sampled, 
                                       long latency, boolean isError, double sampleRate) {
        if (sampled) {
            feedbackLoop.recordSampledRequest(endpoint, latency, isError, sampleRate);
        } else {
            feedbackLoop.recordNonSampledRequest(endpoint, latency, isError, sampleRate);
        }
    }

    private double getErrorRateMultiplier() {
        return rateAdjuster.getErrorRateMultiplier();
    }

    private SamplingDecisionTree buildDecisionTree(String traceId, String name, 
                                                    Attributes attributes, Context parentContext) {
        SamplingDecisionTree tree = new SamplingDecisionTree();
        tree.setTraceId(traceId);
        tree.setSpanName(name);
        tree.setTimestamp(System.currentTimeMillis());
        
        tree.addInputParameter("traceId", traceId);
        tree.addInputParameter("spanName", name);
        tree.addInputParameter("serviceName", tracingProperties.getService().getName());
        tree.addInputParameter("serviceImportance", tracingProperties.getService().getImportance().name());
        
        String endpointKey = buildEndpointKey(name, attributes);
        tree.addInputParameter("endpointKey", endpointKey);
        
        tree.addFactor("baseSampleRate", currentSampleRate);
        tree.addFactor("importanceMultiplier", tracingProperties.getService().getImportance().getMultiplier());
        
        return tree;
    }

    private boolean isParentSampled(Context parentContext) {
        return io.opentelemetry.api.trace.Span.fromContext(parentContext)
                .getSpanContext()
                .isSampled();
    }

    private boolean isErrorRequest(Attributes attributes) {
        Boolean error = attributes.get(AttributeKey.booleanKey("error"));
        if (error != null && error) {
            return true;
        }
        
        Long httpStatus = attributes.get(AttributeKey.longKey("http.status_code"));
        if (httpStatus != null && httpStatus >= 500) {
            return true;
        }
        
        return false;
    }

    private long predictLatency(String spanName, Attributes attributes) {
        String endpointKey = buildEndpointKey(spanName, attributes);
        return configStore.getAverageLatency(endpointKey);
    }

    private double calculateAdjustedRate(String spanName, Attributes attributes, 
                                          double errorRateMultiplier, 
                                          SamplingDecisionReason reason) {
        double baseRate = currentSampleRate;
        double importanceMultiplier = tracingProperties.getService().getImportance().getMultiplier();
        double endpointMultiplier = configStore.getEndpointSampleRateMultiplier(
                buildEndpointKey(spanName, attributes));
        
        reason.setImportanceMultiplier(importanceMultiplier);
        reason.setEndpointMultiplier(endpointMultiplier);
        
        double adjustedRate = baseRate * importanceMultiplier * endpointMultiplier * errorRateMultiplier;
        
        adjustedRate = Math.max(tracingProperties.getSampling().getAdaptive().getMinSampleRate(),
                Math.min(tracingProperties.getSampling().getAdaptive().getMaxSampleRate(), adjustedRate));
        
        return adjustedRate;
    }

    private String buildEndpointKey(String spanName, Attributes attributes) {
        String httpMethod = attributes.get(AttributeKey.stringKey("http.method"));
        String httpRoute = attributes.get(AttributeKey.stringKey("http.route"));
        
        if (httpMethod != null && httpRoute != null) {
            return httpMethod + ":" + httpRoute;
        }
        return spanName;
    }

    private SamplingResult createSamplingResult(SamplingDecision decision, 
                                                 SamplingDecisionReason reason,
                                                 SamplingDecisionTree decisionTree) {
        Attributes attributes = Attributes.builder()
                .put(SAMPLING_REASON, reason.getReason())
                .put(SAMPLING_RATE, reason.getFinalRate())
                .put(SERVICE_IMPORTANCE, tracingProperties.getService().getImportance().name())
                .put(LATENCY_PREDICTION_MS, reason.getPredictedLatency())
                .put(ERROR_RATE_MULTIPLIER, reason.getErrorRateMultiplier())
                .build();

        recordSamplingDecision(reason, decisionTree);

        cacheDecisionTree(decisionTree);

        return SamplingResult.create(decision, attributes);
    }

    private void recordSamplingDecision(SamplingDecisionReason reason, SamplingDecisionTree decisionTree) {
        SamplingDecisionRecord record = new SamplingDecisionRecord(
                System.currentTimeMillis(),
                reason.getReason(),
                reason.getBaseRate(),
                reason.getFinalRate(),
                reason.getPredictedLatency(),
                tracingProperties.getService().getName()
        );
        
        record.setTraceId(reason.getTraceId());
        record.setSpanName(reason.getSpanName());
        record.setServiceImportance(reason.getServiceImportance());
        record.setParentSampled(reason.isParentSampled());
        record.setError(reason.isError());
        record.setImportanceMultiplier(reason.getImportanceMultiplier());
        record.setEndpointMultiplier(reason.getEndpointMultiplier());
        record.setErrorRateMultiplier(reason.getErrorRateMultiplier());
        record.setDecisionSteps(decisionTree.getDecisionSteps());
        record.setDecisionFactors(decisionTree.getFactors());
        
        synchronized (recentDecisions) {
            if (recentDecisions.size() >= MAX_DECISION_HISTORY) {
                recentDecisions.poll();
            }
            recentDecisions.offer(record);
        }
        
        configStore.recordSamplingDecision(record);
    }

    private void cacheDecisionTree(SamplingDecisionTree tree) {
        decisionTreeCache.put(tree.getTraceId(), tree);
        if (decisionTreeCache.size() > MAX_DECISION_HISTORY) {
            String oldestKey = decisionTreeCache.keySet().iterator().next();
            decisionTreeCache.remove(oldestKey);
        }
    }

    public void updateSampleRate(double newRate) {
        double boundedRate = Math.max(
                tracingProperties.getSampling().getAdaptive().getMinSampleRate(),
                Math.min(tracingProperties.getSampling().getAdaptive().getMaxSampleRate(), newRate)
        );
        
        logger.info("Updating sample rate from {} to {}", currentSampleRate, boundedRate);
        this.currentSampleRate = boundedRate;
        configStore.updateCurrentSampleRate(boundedRate);
    }

    public double getCurrentSampleRate() {
        return currentSampleRate;
    }

    public SamplingStats getStats() {
        return new SamplingStats(
                totalRequests.get(),
                sampledRequests.get(),
                highLatencySampled.get(),
                errorSampled.get(),
                parentSampled.get(),
                currentSampleRate,
                lastStatsResetTime
        );
    }

    public List<SamplingDecisionRecord> getRecentDecisions() {
        synchronized (recentDecisions) {
            return new LinkedList<>(recentDecisions);
        }
    }

    public SamplingDecisionTree getDecisionTree(String traceId) {
        return decisionTreeCache.get(traceId);
    }

    public void resetStats() {
        totalRequests.set(0);
        sampledRequests.set(0);
        highLatencySampled.set(0);
        errorSampled.set(0);
        parentSampled.set(0);
        errorRateBoosted.set(0);
        lastStatsResetTime = System.currentTimeMillis();
    }

    public long getErrorRateBoostedCount() {
        return errorRateBoosted.get();
    }

    public long getCrossServiceConsistentSampledCount() {
        return crossServiceConsistentSampled.get();
    }

    public Map<String, Object> getCrossServiceSamplingStats() {
        return crossServiceSampler.getStats();
    }

    public Map<String, Object> getFeedbackLoopStats() {
        return feedbackLoop.getFeedbackStats();
    }

    public Map<String, EstimatedMetrics> getAllEstimatedMetrics() {
        return feedbackLoop.getAllEstimatedMetrics();
    }

    public EstimatedMetrics getAggregatedEstimatedMetrics() {
        return feedbackLoop.getAggregatedMetrics();
    }

    public Map<String, Object> getCostAnalysisSummary() {
        return costAnalysis.getCostSummary();
    }

    public Map<String, EndpointCostMetrics> getAllEndpointCostMetrics() {
        return costAnalysis.getAllEndpointCostMetrics();
    }

    public CostRecommendation getCostOptimizationRecommendation() {
        return costAnalysis.getCostOptimizationRecommendation();
    }

    @Override
    public String getDescription() {
        return String.format("IntelligentAdaptiveSampler{rate=%.4f, importance=%s, errorMultiplier=%.2f, crossService=%d}", 
                currentSampleRate, tracingProperties.getService().getImportance(),
                rateAdjuster.getErrorRateMultiplier(),
                crossServiceConsistentSampled.get());
    }

    public void resetAllStats() {
        resetStats();
        feedbackLoop.reset();
        costAnalysis.reset();
    }

    private static class SamplingDecisionReason {
        private String traceId;
        private String spanName;
        private String reason;
        private double baseRate;
        private double finalRate;
        private long predictedLatency;
        private String serviceImportance;
        private boolean parentSampled;
        private boolean isError;
        private boolean crossServiceConsistent;
        private double importanceMultiplier;
        private double endpointMultiplier;
        private double errorRateMultiplier;

        public String getTraceId() {
            return traceId;
        }

        public void setTraceId(String traceId) {
            this.traceId = traceId;
        }

        public String getSpanName() {
            return spanName;
        }

        public void setSpanName(String spanName) {
            this.spanName = spanName;
        }

        public String getReason() {
            return reason;
        }

        public void setReason(String reason) {
            this.reason = reason;
        }

        public double getBaseRate() {
            return baseRate;
        }

        public void setBaseRate(double baseRate) {
            this.baseRate = baseRate;
            this.finalRate = baseRate;
        }

        public double getFinalRate() {
            return finalRate;
        }

        public void setFinalRate(double finalRate) {
            this.finalRate = finalRate;
        }

        public long getPredictedLatency() {
            return predictedLatency;
        }

        public void setPredictedLatency(long predictedLatency) {
            this.predictedLatency = predictedLatency;
        }

        public String getServiceImportance() {
            return serviceImportance;
        }

        public void setServiceImportance(String serviceImportance) {
            this.serviceImportance = serviceImportance;
        }

        public boolean isParentSampled() {
            return parentSampled;
        }

        public void setParentSampled(boolean parentSampled) {
            this.parentSampled = parentSampled;
        }

        public boolean isError() {
            return isError;
        }

        public void setError(boolean error) {
            isError = error;
        }

        public boolean isCrossServiceConsistent() {
            return crossServiceConsistent;
        }

        public void setCrossServiceConsistent(boolean crossServiceConsistent) {
            this.crossServiceConsistent = crossServiceConsistent;
        }

        public double getImportanceMultiplier() {
            return importanceMultiplier;
        }

        public void setImportanceMultiplier(double importanceMultiplier) {
            this.importanceMultiplier = importanceMultiplier;
        }

        public double getEndpointMultiplier() {
            return endpointMultiplier;
        }

        public void setEndpointMultiplier(double endpointMultiplier) {
            this.endpointMultiplier = endpointMultiplier;
        }

        public double getErrorRateMultiplier() {
            return errorRateMultiplier;
        }

        public void setErrorRateMultiplier(double errorRateMultiplier) {
            this.errorRateMultiplier = errorRateMultiplier;
        }
    }
}
