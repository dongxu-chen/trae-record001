package com.tracing.sampling.model;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class SamplingFeedbackLoop {

    private final Map<String, EndpointEstimation> endpointEstimations;
    private final AtomicLong totalRequests = new AtomicLong(0);
    private final AtomicLong sampledRequests = new AtomicLong(0);
    private final AtomicLong estimatedRequests = new AtomicLong(0);
    private final AtomicLong totalEstimationError = new AtomicLong(0);

    public SamplingFeedbackLoop() {
        this.endpointEstimations = new ConcurrentHashMap<>();
    }

    public void recordSampledRequest(String endpoint, long latency, boolean isError, double sampleRate) {
        totalRequests.incrementAndGet();
        sampledRequests.incrementAndGet();

        EndpointEstimation estimation = endpointEstimations.computeIfAbsent(
                endpoint, k -> new EndpointEstimation(endpoint)
        );

        estimation.recordSampledRequest(latency, isError, sampleRate);
    }

    public void recordNonSampledRequest(String endpoint, long latency, boolean isError, double sampleRate) {
        totalRequests.incrementAndGet();
        estimatedRequests.incrementAndGet();

        EndpointEstimation estimation = endpointEstimations.computeIfAbsent(
                endpoint, k -> new EndpointEstimation(endpoint)
        );

        estimation.recordNonSampledRequest(latency, isError, sampleRate);
    }

    public EstimatedMetrics getEstimatedMetrics(String endpoint) {
        EndpointEstimation estimation = endpointEstimations.get(endpoint);
        if (estimation == null) {
            return new EstimatedMetrics(endpoint, 0, 0, 0.0, 0.0, 0.0);
        }
        return estimation.getEstimatedMetrics();
    }

    public Map<String, EstimatedMetrics> getAllEstimatedMetrics() {
        Map<String, EstimatedMetrics> allMetrics = new HashMap<>();
        for (Map.Entry<String, EndpointEstimation> entry : endpointEstimations.entrySet()) {
            allMetrics.put(entry.getKey(), entry.getValue().getEstimatedMetrics());
        }
        return allMetrics;
    }

    public EstimatedMetrics getAggregatedMetrics() {
        long totalEstimatedRequests = 0;
        long totalEstimatedErrors = 0;
        double totalEstimatedLatency = 0.0;
        double totalSampleRate = 0.0;
        int count = 0;

        for (EndpointEstimation estimation : endpointEstimations.values()) {
            EstimatedMetrics metrics = estimation.getEstimatedMetrics();
            totalEstimatedRequests += metrics.getEstimatedTotalRequests();
            totalEstimatedErrors += metrics.getEstimatedErrorCount();
            totalEstimatedLatency += metrics.getEstimatedAverageLatency() * metrics.getEstimatedTotalRequests();
            totalSampleRate += metrics.getEffectiveSampleRate();
            count++;
        }

        double avgLatency = totalEstimatedRequests > 0 
                ? totalEstimatedLatency / totalEstimatedRequests 
                : 0.0;
        double avgSampleRate = count > 0 ? totalSampleRate / count : 0.0;
        double errorRate = totalEstimatedRequests > 0 
                ? (double) totalEstimatedErrors / totalEstimatedRequests 
                : 0.0;

        return new EstimatedMetrics(
                "AGGREGATED",
                totalEstimatedRequests,
                totalEstimatedErrors,
                avgLatency,
                errorRate,
                avgSampleRate
        );
    }

    public Map<String, Object> getFeedbackStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalRequests", totalRequests.get());
        stats.put("sampledRequests", sampledRequests.get());
        stats.put("estimatedRequests", estimatedRequests.get());
        stats.put("trackedEndpoints", endpointEstimations.size());
        stats.put("actualSampleRate", totalRequests.get() > 0 
                ? (double) sampledRequests.get() / totalRequests.get() 
                : 0.0);
        
        EstimatedMetrics aggregated = getAggregatedMetrics();
        stats.put("aggregatedMetrics", aggregated);
        
        return stats;
    }

    public List<EstimatedMetrics> getTopEndpointsByEstimatedVolume(int limit) {
        List<EstimatedMetrics> allMetrics = new ArrayList<>(getAllEstimatedMetrics().values());
        allMetrics.sort((a, b) -> Long.compare(b.getEstimatedTotalRequests(), a.getEstimatedTotalRequests()));
        return limit > 0 && limit < allMetrics.size() 
                ? allMetrics.subList(0, limit) 
                : allMetrics;
    }

    public void reset() {
        endpointEstimations.clear();
        totalRequests.set(0);
        sampledRequests.set(0);
        estimatedRequests.set(0);
        totalEstimationError.set(0);
    }

    public static class EndpointEstimation {
        private final String endpoint;
        private final AtomicLong sampledCount = new AtomicLong(0);
        private final AtomicLong nonSampledCount = new AtomicLong(0);
        private final AtomicLong sampledErrorCount = new AtomicLong(0);
        private final AtomicLong nonSampledErrorCount = new AtomicLong(0);
        private final AtomicLong sampledTotalLatency = new AtomicLong(0);
        private final AtomicLong nonSampledTotalLatency = new AtomicLong(0);
        private volatile double cumulativeSampleRate = 0.0;
        private volatile long lastUpdateTime = System.currentTimeMillis();

        public EndpointEstimation(String endpoint) {
            this.endpoint = endpoint;
        }

        public void recordSampledRequest(long latency, boolean isError, double sampleRate) {
            sampledCount.incrementAndGet();
            sampledTotalLatency.addAndGet(latency);
            cumulativeSampleRate = (cumulativeSampleRate * (sampledCount.get() - 1) + sampleRate) / sampledCount.get();
            
            if (isError) {
                sampledErrorCount.incrementAndGet();
            }
            
            lastUpdateTime = System.currentTimeMillis();
        }

        public void recordNonSampledRequest(long latency, boolean isError, double sampleRate) {
            nonSampledCount.incrementAndGet();
            nonSampledTotalLatency.addAndGet(latency);
            
            if (isError) {
                nonSampledErrorCount.incrementAndGet();
            }
            
            lastUpdateTime = System.currentTimeMillis();
        }

        public EstimatedMetrics getEstimatedMetrics() {
            long sampled = sampledCount.get();
            long nonSampled = nonSampledCount.get();
            long total = sampled + nonSampled;

            if (total == 0) {
                return new EstimatedMetrics(endpoint, 0, 0, 0.0, 0.0, cumulativeSampleRate);
            }

            double effectiveRate = sampled > 0 ? cumulativeSampleRate : 1.0;
            long estimatedTotal = nonSampled > 0 
                    ? (long) (sampled / effectiveRate) 
                    : sampled;

            double sampledErrorRate = sampled > 0 
                    ? (double) sampledErrorCount.get() / sampled 
                    : 0.0;
            long estimatedErrors = sampledErrorCount.get() + 
                    (long) (nonSampledErrorCount.get() + (nonSampled * sampledErrorRate));

            double avgSampledLatency = sampled > 0 
                    ? (double) sampledTotalLatency.get() / sampled 
                    : 0.0;
            double estimatedTotalLatency = sampledTotalLatency.get() + 
                    (avgSampledLatency * nonSampled);
            double estimatedAvgLatency = estimatedTotal > 0 
                    ? estimatedTotalLatency / estimatedTotal 
                    : 0.0;

            double estimatedErrorRate = estimatedTotal > 0 
                    ? (double) estimatedErrors / estimatedTotal 
                    : 0.0;

            return new EstimatedMetrics(
                    endpoint,
                    estimatedTotal,
                    estimatedErrors,
                    estimatedAvgLatency,
                    estimatedErrorRate,
                    effectiveRate
            );
        }

        public long getLastUpdateTime() {
            return lastUpdateTime;
        }

        public long getSampledCount() {
            return sampledCount.get();
        }

        public long getNonSampledCount() {
            return nonSampledCount.get();
        }
    }

    public static class EstimatedMetrics {
        private final String endpoint;
        private final long estimatedTotalRequests;
        private final long estimatedErrorCount;
        private final double estimatedAverageLatency;
        private final double estimatedErrorRate;
        private final double effectiveSampleRate;

        public EstimatedMetrics(String endpoint, long estimatedTotalRequests, 
                               long estimatedErrorCount, double estimatedAverageLatency,
                               double estimatedErrorRate, double effectiveSampleRate) {
            this.endpoint = endpoint;
            this.estimatedTotalRequests = estimatedTotalRequests;
            this.estimatedErrorCount = estimatedErrorCount;
            this.estimatedAverageLatency = estimatedAverageLatency;
            this.estimatedErrorRate = estimatedErrorRate;
            this.effectiveSampleRate = effectiveSampleRate;
        }

        public String getEndpoint() {
            return endpoint;
        }

        public long getEstimatedTotalRequests() {
            return estimatedTotalRequests;
        }

        public long getEstimatedErrorCount() {
            return estimatedErrorCount;
        }

        public double getEstimatedAverageLatency() {
            return estimatedAverageLatency;
        }

        public double getEstimatedErrorRate() {
            return estimatedErrorRate;
        }

        public double getEffectiveSampleRate() {
            return effectiveSampleRate;
        }

        public Map<String, Object> toMap() {
            Map<String, Object> map = new HashMap<>();
            map.put("endpoint", endpoint);
            map.put("estimatedTotalRequests", estimatedTotalRequests);
            map.put("estimatedErrorCount", estimatedErrorCount);
            map.put("estimatedAverageLatency", estimatedAverageLatency);
            map.put("estimatedErrorRate", estimatedErrorRate);
            map.put("effectiveSampleRate", effectiveSampleRate);
            return map;
        }
    }
}
