package com.tracing.optimizer.core.edge;

import com.tracing.optimizer.core.model.SamplingRate;
import com.tracing.optimizer.core.model.ServiceMetadata;
import com.tracing.optimizer.core.model.TraceMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

public class EdgeSampler {

    private static final Logger log = LoggerFactory.getLogger(EdgeSampler.class);

    public enum DecisionSource {
        LOCAL_PREDECISION,
        CENTRAL_OVERRIDE,
        HYBRID_FUSED,
        EMERGENCY_OVERRIDE
    }

    public static class EdgeDecisionRecord {
        public final String serviceName;
        public final String traceId;
        public final double globalRate;
        public final double localRate;
        public final double finalRate;
        public final boolean sampled;
        public final DecisionSource source;
        public final long timestampMs;
        public final boolean conflictWithCentral;

        public EdgeDecisionRecord(String serviceName, String traceId, double globalRate,
                                double localRate, double finalRate, boolean sampled,
                                DecisionSource source, long timestampMs, boolean conflictWithCentral) {
            this.serviceName = serviceName;
            this.traceId = traceId;
            this.globalRate = globalRate;
            this.localRate = localRate;
            this.finalRate = finalRate;
            this.sampled = sampled;
            this.source = source;
            this.timestampMs = timestampMs;
            this.conflictWithCentral = conflictWithCentral;
        }
    }

    public static class CentralDecision {
        public final String serviceName;
        public final double samplingRate;
        public final long effectiveTimeMs;
        public final String reason;
        public final double confidence;
        public final String serviceLevel;

        public CentralDecision(String serviceName, double samplingRate, long effectiveTimeMs,
                                String reason, double confidence, String serviceLevel) {
            this.serviceName = serviceName;
            this.samplingRate = samplingRate;
            this.effectiveTimeMs = effectiveTimeMs;
            this.reason = reason;
            this.confidence = confidence;
            this.serviceLevel = serviceLevel;
        }
    }

    private final Map<String, SamplingDecision> localDecisions;
    private final Map<String, ServiceMetadata> serviceMetadataMap;
    private final Map<String, TraceMetrics> metricsMap;
    private final Map<String, CentralDecision> centralDecisions;
    private final BlockingQueue<EdgeDecisionRecord> asyncReportQueue;
    private final ScheduledExecutorService reportScheduler;
    private final long reportIntervalMs;
    private final double errorRateThreshold;
    private final double latencyThresholdMs;
    private final double importanceThreshold;
    private final double centralDecisionTtlMs;
    private final long localDecisionTtlMs;
    private final Random random;
    private final AtomicLong localDecisionsMade;
    private final AtomicLong centralOverridesApplied;
    private final AtomicLong conflictsDetected;
    private final AtomicLong reportsSent;
    private final AtomicLong reportsDropped;
    private volatile boolean running;
    private double localDecisionWeight;

    public EdgeSampler() {
        this(0.05, 2000.0, 0.7, 60000L, 30000L, 5000L);
    }

    public EdgeSampler(double errorRateThreshold, double latencyThresholdMs,
                       double importanceThreshold, long centralTtlMs, long localTtlMs, long reportIntervalMs) {
        this.localDecisions = new ConcurrentHashMap<>();
        this.serviceMetadataMap = new ConcurrentHashMap<>();
        this.metricsMap = new ConcurrentHashMap<>();
        this.centralDecisions = new ConcurrentHashMap<>();
        this.asyncReportQueue = new LinkedBlockingQueue<>(10000);
        this.reportScheduler = Executors.newSingleThreadScheduledExecutor();
        this.errorRateThreshold = errorRateThreshold;
        this.latencyThresholdMs = latencyThresholdMs;
        this.importanceThreshold = importanceThreshold;
        this.centralDecisionTtlMs = centralTtlMs;
        this.localDecisionTtlMs = localTtlMs;
        this.reportIntervalMs = reportIntervalMs;
        this.random = new Random();
        this.localDecisionsMade = new AtomicLong(0);
        this.centralOverridesApplied = new AtomicLong(0);
        this.conflictsDetected = new AtomicLong(0);
        this.reportsSent = new AtomicLong(0);
        this.reportsDropped = new AtomicLong(0);
        this.running = false;
        this.localDecisionWeight = 0.5;
    }

    public void start() {
        if (running) return;
        running = true;
        reportScheduler.scheduleAtFixedRate(this::reportDecisionsAsync,
                reportIntervalMs, reportIntervalMs, TimeUnit.MILLISECONDS);
        reportScheduler.scheduleAtFixedRate(this::cleanExpiredDecisions,
                localDecisionTtlMs / 2, localDecisionTtlMs, TimeUnit.MILLISECONDS);
        log.info("Edge sampler started with report interval {}ms", reportIntervalMs);
    }

    public void stop() {
        running = false;
        reportScheduler.shutdown();
        try {
            if (!reportScheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                reportScheduler.shutdownNow();
            }
        } catch (InterruptedException e) {
            reportScheduler.shutdownNow();
            Thread.currentThread().interrupt();
        }
        log.info("Edge sampler stopped. Total local decisions: {}, central overrides: {}",
                localDecisionsMade.get(), centralOverridesApplied.get());
    }

    public boolean shouldSample(String serviceName, String traceId, double globalRate) {
        double localRate = getLocalRate(serviceName, globalRate);
        CentralDecision centralDecision = centralDecisions.get(serviceName);
        double finalRate;
        DecisionSource source;
        boolean conflictWithCentral = false;

        if (centralDecision != null
                && (System.currentTimeMillis() - centralDecision.effectiveTimeMs) < centralDecisionTtlMs) {
            double localPriority = computeLocalDecisionPriority(serviceName);
            double centralPriority = centralDecision.confidence;
            if (localPriority > centralPriority + 0.2 && localPriority > 0.6) {
                finalRate = localRate;
                source = DecisionSource.LOCAL_PREDECISION;
                conflictWithCentral = true;
                conflictsDetected.incrementAndGet();
                log.debug("Local override for {}: local rate {} vs central rate {}",
                        serviceName, localRate, centralDecision.samplingRate);
            } else if (centralPriority > localPriority + 0.2) {
                finalRate = centralDecision.samplingRate;
                source = DecisionSource.CENTRAL_OVERRIDE;
                centralOverridesApplied.incrementAndGet();
            } else {
                finalRate = fuseDecisions(localRate, centralDecision.samplingRate,
                        localPriority, centralPriority);
                source = DecisionSource.HYBRID_FUSED;
            }
        } else {
            finalRate = localRate;
            source = DecisionSource.LOCAL_PREDECISION;
            localDecisionsMade.incrementAndGet();
        }

        double emergencyRate = checkEmergencyOverride(serviceName, finalRate);
        if (emergencyRate > finalRate) {
            finalRate = emergencyRate;
            source = DecisionSource.EMERGENCY_OVERRIDE;
            log.warn("Emergency override for {}: rate elevated to {}", serviceName, finalRate);
        }

        boolean sampled = random.nextDouble() < finalRate;

        EdgeDecisionRecord record = new EdgeDecisionRecord(
                serviceName, traceId, globalRate, localRate, finalRate,
                sampled, source, System.currentTimeMillis(), conflictWithCentral
        );
        enqueueReport(record);

        SamplingDecision decision = localDecisions.get(serviceName);
        if (decision != null) {
            decision.updateLastUsed();
        }

        return sampled;
    }

    private double getLocalRate(String serviceName, double globalRate) {
        SamplingDecision decision = localDecisions.get(serviceName);
        long now = System.currentTimeMillis();

        if (decision == null || (now - decision.createdAt) > localDecisionTtlMs) {
            SamplingRate rate = computeEdgeRate(serviceName, globalRate);
            decision = new SamplingDecision(rate.getRate(), now);
            localDecisions.put(serviceName, decision);
            log.debug("New local pre-decision for {}: rate={}", serviceName, rate.getRate());
        }

        return decision.effectiveRate;
    }

    private double computeLocalDecisionPriority(String serviceName) {
        ServiceMetadata meta = serviceMetadataMap.get(serviceName);
        if (meta == null) return 0.5;

        double priority = 0.5;
        if (meta.getErrorRate() > errorRateThreshold) {
            priority += 0.25;
        }
        if (meta.getP99LatencyMs() > latencyThresholdMs) {
            priority += 0.2;
        }
        if (meta.getBusinessImportance() >= importanceThreshold) {
            priority += 0.2;
        }

        TraceMetrics metrics = metricsMap.get(serviceName);
        if (metrics != null && metrics.getErrorRate() > errorRateThreshold) {
            priority += 0.15;
        }

        return Math.min(1.0, priority);
    }

    private double fuseDecisions(double localRate, double centralRate,
                                 double localPriority, double centralPriority) {
        double totalPriority = localPriority + centralPriority + 0.001;
        double localW = localPriority / totalPriority;
        double centralW = centralPriority / totalPriority;
        return localW * localRate + centralW * centralRate;
    }

    private double checkEmergencyOverride(String serviceName, double currentRate) {
        TraceMetrics metrics = metricsMap.get(serviceName);
        if (metrics != null && metrics.getErrorRate() > 0.1) {
            return 1.0;
        }
        if (metrics != null && metrics.getP99LatencyMs() > 5000.0) {
            return Math.max(currentRate, 0.7);
        }
        return currentRate;
    }

    private void enqueueReport(EdgeDecisionRecord record) {
        boolean offered = asyncReportQueue.offer(record);
        if (!offered) {
            reportsDropped.incrementAndGet();
            if (reportsDropped.get() % 100 == 0) {
                log.warn("Report queue full, dropped {} reports", reportsDropped.get());
            }
        }
    }

    private void reportDecisionsAsync() {
        if (asyncReportQueue.isEmpty()) return;

        List<EdgeDecisionRecord> batch = new ArrayList<>(Math.min(asyncReportQueue.size(), 1000));
        asyncReportQueue.drainTo(batch);

        if (!batch.isEmpty()) {
            reportsSent.addAndGet(batch.size());
            log.debug("Async reporting {} edge decisions", batch.size());
        }
    }

    private void cleanExpiredDecisions() {
        long now = System.currentTimeMillis();
        localDecisions.entrySet().removeIf(e ->
                (now - e.getValue().createdAt) > localDecisionTtlMs
                        && (now - e.getValue().lastUsedAt) > localDecisionTtlMs / 2);
        centralDecisions.entrySet().removeIf(e ->
                (now - e.getValue().effectiveTimeMs) > centralDecisionTtlMs);
    }

    public SamplingRate computeEdgeRate(String serviceName, double globalRate) {
        ServiceMetadata metadata = serviceMetadataMap.get(serviceName);
        double effectiveRate = globalRate;

        if (metadata != null) {
            effectiveRate = applyEdgeRules(metadata, globalRate);
        }

        SamplingRate rate = new SamplingRate(serviceName, effectiveRate, "edge-optimized");
        rate.setEdgeOptimized(true);
        rate.setConfidenceScore(metadata != null ? computeConfidence(metadata) : 0.5);
        return rate;
    }

    private double applyEdgeRules(ServiceMetadata metadata, double globalRate) {
        double rate = globalRate;

        if (metadata.getErrorRate() > errorRateThreshold) {
            double boost = 1.0 + (metadata.getErrorRate() - errorRateThreshold) * 5.0;
            rate = Math.min(1.0, rate * boost);
        }

        if (metadata.getP99LatencyMs() > latencyThresholdMs) {
            double latencyBoost = 1.0 + (metadata.getP99LatencyMs() - latencyThresholdMs) / latencyThresholdMs;
            rate = Math.min(1.0, rate * latencyBoost);
        }

        if (metadata.getBusinessImportance() >= importanceThreshold) {
            rate = Math.max(rate, importanceThreshold);
        }

        return Math.max(0.01, Math.min(1.0, rate));
    }

    private double computeConfidence(ServiceMetadata metadata) {
        double confidence = 0.5;
        confidence += metadata.getBusinessImportance() * 0.2;
        if (metadata.getErrorRate() > errorRateThreshold) confidence += 0.15;
        if (metadata.getP99LatencyMs() > latencyThresholdMs) confidence += 0.15;
        return Math.min(1.0, confidence);
    }

    public void updateCentralDecision(CentralDecision decision) {
        centralDecisions.put(decision.serviceName, decision);
        log.info("Received central decision for {}: rate={}, confidence={}",
                decision.serviceName, decision.samplingRate, decision.confidence);
    }

    public void updateServiceMetadata(ServiceMetadata metadata) {
        serviceMetadataMap.put(metadata.getServiceName(), metadata);
        localDecisions.remove(metadata.getServiceName());
    }

    public void updateMetrics(TraceMetrics metrics) {
        metricsMap.put(metrics.getServiceName(), metrics);
    }

    public Map<String, SamplingDecision> getLocalDecisions() {
        return Collections.unmodifiableMap(localDecisions);
    }

    public Map<String, CentralDecision> getCentralDecisions() {
        return Collections.unmodifiableMap(centralDecisions);
    }

    public int getReportQueueSize() {
        return asyncReportQueue.size();
    }

    public Map<String, Object> getEdgeStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("localDecisionsMade", localDecisionsMade.get());
        stats.put("centralOverridesApplied", centralOverridesApplied.get());
        stats.put("conflictsDetected", conflictsDetected.get());
        stats.put("reportsSent", reportsSent.get());
        stats.put("reportsDropped", reportsDropped.get());
        stats.put("pendingReports", asyncReportQueue.size());
        stats.put("activeLocalDecisions", localDecisions.size());
        stats.put("activeCentralDecisions", centralDecisions.size());
        stats.put("localDecisionWeight", localDecisionWeight);
        return stats;
    }

    public void setLocalDecisionWeight(double weight) {
        this.localDecisionWeight = Math.max(0.0, Math.min(1.0, weight));
    }

    public static class SamplingDecision {
        public final double effectiveRate;
        public final long createdAt;
        public long lastUsedAt;

        public SamplingDecision(double effectiveRate, long createdAt) {
            this.effectiveRate = effectiveRate;
            this.createdAt = createdAt;
            this.lastUsedAt = createdAt;
        }

        public void updateLastUsed() {
            this.lastUsedAt = System.currentTimeMillis();
        }
    }
}
