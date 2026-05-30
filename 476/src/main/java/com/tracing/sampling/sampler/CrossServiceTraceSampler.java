package com.tracing.sampling.sampler;

import com.tracing.sampling.config.TracingProperties;
import com.tracing.sampling.model.TraceSamplingContext;
import com.tracing.sampling.model.TraceSamplingContext.ServiceTraceInfo;
import com.tracing.sampling.store.SamplingConfigStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Component
public class CrossServiceTraceSampler {

    private static final Logger logger = LoggerFactory.getLogger(CrossServiceTraceSampler.class);

    private static final long TRACE_CONTEXT_TTL_MS = 5 * 60 * 1000;
    private static final long CLEANUP_INTERVAL_MS = 60 * 1000;

    private final TracingProperties tracingProperties;
    private final SamplingConfigStore configStore;
    private final Map<String, TraceSamplingContext> traceContextCache;
    private final ScheduledExecutorService cleanupExecutor;

    private volatile long totalCrossServiceTraces = 0;
    private volatile long consistentSamplingApplied = 0;
    private volatile long tracesWithMultipleServices = 0;

    public CrossServiceTraceSampler(TracingProperties tracingProperties, SamplingConfigStore configStore) {
        this.tracingProperties = tracingProperties;
        this.configStore = configStore;
        this.traceContextCache = new ConcurrentHashMap<>();
        this.cleanupExecutor = Executors.newSingleThreadScheduledExecutor();
        
        this.cleanupExecutor.scheduleAtFixedRate(
                this::cleanupExpiredContexts,
                CLEANUP_INTERVAL_MS,
                CLEANUP_INTERVAL_MS,
                TimeUnit.MILLISECONDS
        );
        
        logger.info("CrossServiceTraceSampler initialized with TTL: {}ms", TRACE_CONTEXT_TTL_MS);
    }

    public TraceSamplingContext getOrCreateTraceContext(String traceId) {
        totalCrossServiceTraces++;
        return traceContextCache.computeIfAbsent(traceId, TraceSamplingContext::new);
    }

    public TraceSamplingContext getTraceContext(String traceId) {
        return traceContextCache.get(traceId);
    }

    public boolean shouldApplyConsistentSampling(String traceId, String serviceName, 
                                                 boolean isRoot, boolean isParentSampled) {
        if (!tracingProperties.getSampling().isConsistentSamplingEnabled()) {
            return false;
        }

        TraceSamplingContext context = getOrCreateTraceContext(traceId);
        
        synchronized (context) {
            if (isRoot) {
                context.setInitiatingService(serviceName);
                return false;
            }
            
            if (context.hasRootDecision()) {
                consistentSamplingApplied++;
                return true;
            }
            
            return false;
        }
    }

    public Boolean getRootSamplingDecision(String traceId) {
        TraceSamplingContext context = traceContextCache.get(traceId);
        if (context != null && context.hasRootDecision()) {
            return context.getRootSampled();
        }
        return null;
    }

    public void recordRootSamplingDecision(String traceId, boolean sampled, String reason, String serviceName) {
        TraceSamplingContext context = getOrCreateTraceContext(traceId);
        
        synchronized (context) {
            if (!context.hasRootDecision()) {
                context.setRootSampled(sampled);
                context.setRootDecisionReason(reason);
                context.setInitiatingService(serviceName);
                context.addServiceInfo(serviceName, new ServiceTraceInfo(serviceName));
                
                logger.debug("Recorded root sampling decision for trace {}: {} (reason: {})", 
                        traceId, sampled, reason);
            }
        }
    }

    public void recordServiceSpan(String traceId, String serviceName, long latency, boolean isError) {
        TraceSamplingContext context = getOrCreateTraceContext(traceId);
        
        synchronized (context) {
            ServiceTraceInfo serviceInfo = context.getServiceInfoMap().get(serviceName);
            if (serviceInfo == null) {
                serviceInfo = new ServiceTraceInfo(serviceName);
                context.addServiceInfo(serviceName, serviceInfo);
                
                if (context.getServiceInfoMap().size() > 1) {
                    tracesWithMultipleServices++;
                }
            }
            
            serviceInfo.incrementSpanCount();
            serviceInfo.addLatency(latency);
            if (isError) {
                serviceInfo.incrementErrorCount();
            }
            
            context.setTotalSpans(context.getTotalSpans() + 1);
            if (Boolean.TRUE.equals(context.getRootSampled())) {
                context.setSampledSpans(context.getSampledSpans() + 1);
            }
        }
    }

    public int getActiveTraceCount() {
        return traceContextCache.size();
    }

    public long getTotalCrossServiceTraces() {
        return totalCrossServiceTraces;
    }

    public long getConsistentSamplingApplied() {
        return consistentSamplingApplied;
    }

    public long getTracesWithMultipleServices() {
        return tracesWithMultipleServices;
    }

    public double getConsistentSamplingRate() {
        if (totalCrossServiceTraces == 0) {
            return 0.0;
        }
        return (double) consistentSamplingApplied / totalCrossServiceTraces;
    }

    public Map<String, Object> getStats() {
        Map<String, Object> stats = new java.util.HashMap<>();
        stats.put("activeTraceCount", getActiveTraceCount());
        stats.put("totalCrossServiceTraces", totalCrossServiceTraces);
        stats.put("consistentSamplingApplied", consistentSamplingApplied);
        stats.put("tracesWithMultipleServices", tracesWithMultipleServices);
        stats.put("consistentSamplingRate", getConsistentSamplingRate());
        stats.put("consistentSamplingEnabled", tracingProperties.getSampling().isConsistentSamplingEnabled());
        return stats;
    }

    private void cleanupExpiredContexts() {
        long cutoffTime = System.currentTimeMillis() - TRACE_CONTEXT_TTL_MS;
        
        int removedCount = 0;
        var iterator = traceContextCache.entrySet().iterator();
        
        while (iterator.hasNext()) {
            var entry = iterator.next();
            if (entry.getValue().getRootDecisionTime() < cutoffTime) {
                iterator.remove();
                removedCount++;
            }
        }
        
        if (removedCount > 0) {
            logger.debug("Cleaned up {} expired trace contexts", removedCount);
        }
    }

    public void shutdown() {
        cleanupExecutor.shutdown();
        try {
            if (!cleanupExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                cleanupExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            cleanupExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }
}
