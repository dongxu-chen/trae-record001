package com.tracing.sampling.model;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class SamplingCostAnalysis {

    private static final long AVG_SPAN_SIZE_BYTES = 1024;
    private static final double SAMPLING_CPU_OVERHEAD_PER_SPAN = 0.001;
    private static final double NON_SAMPLING_CPU_OVERHEAD_PER_SPAN = 0.0001;

    private final Map<String, EndpointCostStats> endpointCostStats;
    private final AtomicLong totalSpansProcessed = new AtomicLong(0);
    private final AtomicLong totalSpansSampled = new AtomicLong(0);
    private final AtomicLong totalSpansDropped = new AtomicLong(0);
    private final AtomicLong totalBytesSaved = new AtomicLong(0);
    private final AtomicLong totalCpuSavedMs = new AtomicLong(0);

    public SamplingCostAnalysis() {
        this.endpointCostStats = new ConcurrentHashMap<>();
    }

    public void recordSpan(String endpoint, boolean sampled, long spanSizeBytes, 
                           long processingTimeMs, double sampleRate) {
        totalSpansProcessed.incrementAndGet();
        
        if (sampled) {
            totalSpansSampled.incrementAndGet();
        } else {
            totalSpansDropped.incrementAndGet();
        }

        EndpointCostStats stats = endpointCostStats.computeIfAbsent(
                endpoint, k -> new EndpointCostStats(endpoint)
        );

        stats.recordSpan(sampled, spanSizeBytes, processingTimeMs, sampleRate);

        if (!sampled) {
            totalBytesSaved.addAndGet(spanSizeBytes);
            long cpuSaved = (long) ((SAMPLING_CPU_OVERHEAD_PER_SPAN - NON_SAMPLING_CPU_OVERHEAD_PER_SPAN) * 1000);
            totalCpuSavedMs.addAndGet(Math.max(0, cpuSaved));
        }
    }

    public CostMetrics getAggregatedCostMetrics() {
        long totalBytes = 0;
        long totalSampledBytes = 0;
        long totalProcessingTime = 0;
        long totalSampledProcessingTime = 0;
        double totalSampleRate = 0.0;
        int count = 0;

        for (EndpointCostStats stats : endpointCostStats.values()) {
            EndpointCostMetrics metrics = stats.getMetrics();
            totalBytes += metrics.getTotalBytesProcessed();
            totalSampledBytes += metrics.getSampledBytes();
            totalProcessingTime += metrics.getTotalProcessingTimeMs();
            totalSampledProcessingTime += metrics.getSampledProcessingTimeMs();
            totalSampleRate += metrics.getEffectiveSampleRate();
            count++;
        }

        double effectiveSampleRate = totalSpansProcessed.get() > 0 
                ? (double) totalSpansSampled.get() / totalSpansProcessed.get() 
                : 0.0;
        double avgSampleRate = count > 0 ? totalSampleRate / count : 0.0;

        long estimatedFullSamplingBytes = totalBytes;
        long actualSampledBytes = totalSampledBytes;
        long storageSavedBytes = estimatedFullSamplingBytes - actualSampledBytes;

        double storageCostSavingsPercent = estimatedFullSamplingBytes > 0 
                ? (double) storageSavedBytes / estimatedFullSamplingBytes * 100 
                : 0.0;

        double cpuCostSavingsPercent = totalProcessingTime > 0 
                ? (double) totalCpuSavedMs.get() / totalProcessingTime * 100 
                : 0.0;

        return new CostMetrics(
                "AGGREGATED",
                totalSpansProcessed.get(),
                totalSpansSampled.get(),
                totalSpansDropped.get(),
                totalBytes,
                actualSampledBytes,
                storageSavedBytes,
                totalProcessingTime,
                totalCpuSavedMs.get(),
                effectiveSampleRate,
                avgSampleRate,
                storageCostSavingsPercent,
                cpuCostSavingsPercent
        );
    }

    public EndpointCostMetrics getEndpointCostMetrics(String endpoint) {
        EndpointCostStats stats = endpointCostStats.get(endpoint);
        if (stats == null) {
            return new EndpointCostMetrics(endpoint, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0);
        }
        return stats.getMetrics();
    }

    public Map<String, EndpointCostMetrics> getAllEndpointCostMetrics() {
        Map<String, EndpointCostMetrics> allMetrics = new HashMap<>();
        for (Map.Entry<String, EndpointCostStats> entry : endpointCostStats.entrySet()) {
            allMetrics.put(entry.getKey(), entry.getValue().getMetrics());
        }
        return allMetrics;
    }

    public Map<String, Object> getCostSummary() {
        CostMetrics aggregated = getAggregatedCostMetrics();
        Map<String, Object> summary = new HashMap<>();
        
        summary.put("totalSpansProcessed", aggregated.getTotalSpans());
        summary.put("totalSpansSampled", aggregated.getSampledSpans());
        summary.put("totalSpansDropped", aggregated.getDroppedSpans());
        summary.put("storageSavedMB", bytesToMB(aggregated.getStorageSavedBytes()));
        summary.put("storageSavedPercent", String.format("%.2f%%", aggregated.getStorageCostSavingsPercent()));
        summary.put("cpuSavedSeconds", msToSeconds(aggregated.getCpuSavedMs()));
        summary.put("cpuSavedPercent", String.format("%.2f%%", aggregated.getCpuCostSavingsPercent()));
        summary.put("effectiveSampleRate", String.format("%.2f%%", aggregated.getEffectiveSampleRate() * 100));
        summary.put("trackedEndpoints", endpointCostStats.size());
        
        return summary;
    }

    public CostRecommendation getCostOptimizationRecommendation() {
        CostMetrics metrics = getAggregatedCostMetrics();
        double effectiveRate = metrics.getEffectiveSampleRate();
        double storageSavings = metrics.getStorageCostSavingsPercent();
        double cpuSavings = metrics.getCpuCostSavingsPercent();

        StringBuilder recommendation = new StringBuilder();
        String priority = "LOW";

        if (effectiveRate > 0.5) {
            recommendation.append("采样率较高，建议降低基础采样率以节省存储成本。");
            priority = "HIGH";
        } else if (effectiveRate < 0.05) {
            recommendation.append("采样率较低，建议提高采样率以获得更全面的数据。");
            priority = "MEDIUM";
        } else {
            recommendation.append("当前采样率配置合理，成本效益平衡良好。");
        }

        if (storageSavings > 80) {
            recommendation.append(" 存储节省显著，当前配置有效。");
        }

        return new CostRecommendation(
                recommendation.toString(),
                priority,
                metrics.getEffectiveSampleRate(),
                storageSavings,
                cpuSavings
        );
    }

    private static double bytesToMB(long bytes) {
        return bytes / (1024.0 * 1024.0);
    }

    private static double msToSeconds(long ms) {
        return ms / 1000.0;
    }

    public void reset() {
        endpointCostStats.clear();
        totalSpansProcessed.set(0);
        totalSpansSampled.set(0);
        totalSpansDropped.set(0);
        totalBytesSaved.set(0);
        totalCpuSavedMs.set(0);
    }

    public static class EndpointCostStats {
        private final String endpoint;
        private final AtomicLong spansProcessed = new AtomicLong(0);
        private final AtomicLong spansSampled = new AtomicLong(0);
        private final AtomicLong spansDropped = new AtomicLong(0);
        private final AtomicLong totalBytes = new AtomicLong(0);
        private final AtomicLong sampledBytes = new AtomicLong(0);
        private final AtomicLong totalProcessingTime = new AtomicLong(0);
        private final AtomicLong sampledProcessingTime = new AtomicLong(0);
        private volatile double cumulativeSampleRate = 0.0;
        private volatile long lastUpdateTime = System.currentTimeMillis();

        public EndpointCostStats(String endpoint) {
            this.endpoint = endpoint;
        }

        public void recordSpan(boolean sampled, long spanSizeBytes, 
                               long processingTimeMs, double sampleRate) {
            spansProcessed.incrementAndGet();
            totalBytes.addAndGet(spanSizeBytes);
            totalProcessingTime.addAndGet(processingTimeMs);
            
            cumulativeSampleRate = (cumulativeSampleRate * (spansProcessed.get() - 1) + sampleRate) 
                    / spansProcessed.get();

            if (sampled) {
                spansSampled.incrementAndGet();
                sampledBytes.addAndGet(spanSizeBytes);
                sampledProcessingTime.addAndGet(processingTimeMs);
            } else {
                spansDropped.incrementAndGet();
            }

            lastUpdateTime = System.currentTimeMillis();
        }

        public EndpointCostMetrics getMetrics() {
            long processed = spansProcessed.get();
            long sampled = spansSampled.get();
            long dropped = spansDropped.get();
            long totalB = totalBytes.get();
            long sampledB = sampledBytes.get();
            long totalTime = totalProcessingTime.get();
            long sampledTime = sampledProcessingTime.get();
            
            double effectiveRate = processed > 0 ? (double) sampled / processed : 0.0;
            long savedB = totalB - sampledB;
            long savedTime = (long) (dropped * (SAMPLING_CPU_OVERHEAD_PER_SPAN - NON_SAMPLING_CPU_OVERHEAD_PER_SPAN) * 1000);
            
            double storageSavingsPercent = totalB > 0 
                    ? (double) savedB / totalB * 100 
                    : 0.0;
            double cpuSavingsPercent = totalTime > 0 
                    ? (double) savedTime / totalTime * 100 
                    : 0.0;

            return new EndpointCostMetrics(
                    endpoint,
                    processed,
                    sampled,
                    dropped,
                    totalB,
                    sampledB,
                    totalTime,
                    sampledTime,
                    effectiveRate,
                    storageSavingsPercent
            );
        }

        public long getLastUpdateTime() {
            return lastUpdateTime;
        }
    }

    public static class EndpointCostMetrics {
        private final String endpoint;
        private final long spansProcessed;
        private final long spansSampled;
        private final long spansDropped;
        private final long totalBytesProcessed;
        private final long sampledBytes;
        private final long totalProcessingTimeMs;
        private final long sampledProcessingTimeMs;
        private final double effectiveSampleRate;
        private final double storageCostSavingsPercent;

        public EndpointCostMetrics(String endpoint, long spansProcessed, long spansSampled,
                                   long spansDropped, long totalBytesProcessed, long sampledBytes,
                                   long totalProcessingTimeMs, long sampledProcessingTimeMs,
                                   double effectiveSampleRate, double storageCostSavingsPercent) {
            this.endpoint = endpoint;
            this.spansProcessed = spansProcessed;
            this.spansSampled = spansSampled;
            this.spansDropped = spansDropped;
            this.totalBytesProcessed = totalBytesProcessed;
            this.sampledBytes = sampledBytes;
            this.totalProcessingTimeMs = totalProcessingTimeMs;
            this.sampledProcessingTimeMs = sampledProcessingTimeMs;
            this.effectiveSampleRate = effectiveSampleRate;
            this.storageCostSavingsPercent = storageCostSavingsPercent;
        }

        public String getEndpoint() {
            return endpoint;
        }

        public long getSpansProcessed() {
            return spansProcessed;
        }

        public long getSpansSampled() {
            return spansSampled;
        }

        public long getSpansDropped() {
            return spansDropped;
        }

        public long getTotalBytesProcessed() {
            return totalBytesProcessed;
        }

        public long getSampledBytes() {
            return sampledBytes;
        }

        public long getTotalProcessingTimeMs() {
            return totalProcessingTimeMs;
        }

        public long getSampledProcessingTimeMs() {
            return sampledProcessingTimeMs;
        }

        public double getEffectiveSampleRate() {
            return effectiveSampleRate;
        }

        public double getStorageCostSavingsPercent() {
            return storageCostSavingsPercent;
        }

        public Map<String, Object> toMap() {
            Map<String, Object> map = new HashMap<>();
            map.put("endpoint", endpoint);
            map.put("spansProcessed", spansProcessed);
            map.put("spansSampled", spansSampled);
            map.put("spansDropped", spansDropped);
            map.put("totalBytesMB", bytesToMB(totalBytesProcessed));
            map.put("sampledBytesMB", bytesToMB(sampledBytes));
            map.put("storageSavedMB", bytesToMB(totalBytesProcessed - sampledBytes));
            map.put("storageSavedPercent", String.format("%.2f%%", storageCostSavingsPercent));
            map.put("effectiveSampleRate", String.format("%.2f%%", effectiveSampleRate * 100));
            return map;
        }

        private double bytesToMB(long bytes) {
            return Math.round(bytes / (1024.0 * 1024.0) * 100) / 100.0;
        }
    }

    public static class CostMetrics {
        private final String name;
        private final long totalSpans;
        private final long sampledSpans;
        private final long droppedSpans;
        private final long totalBytes;
        private final long sampledBytes;
        private final long storageSavedBytes;
        private final long totalProcessingTimeMs;
        private final long cpuSavedMs;
        private final double effectiveSampleRate;
        private final double avgSampleRate;
        private final double storageCostSavingsPercent;
        private final double cpuCostSavingsPercent;

        public CostMetrics(String name, long totalSpans, long sampledSpans, long droppedSpans,
                          long totalBytes, long sampledBytes, long storageSavedBytes,
                          long totalProcessingTimeMs, long cpuSavedMs,
                          double effectiveSampleRate, double avgSampleRate,
                          double storageCostSavingsPercent, double cpuCostSavingsPercent) {
            this.name = name;
            this.totalSpans = totalSpans;
            this.sampledSpans = sampledSpans;
            this.droppedSpans = droppedSpans;
            this.totalBytes = totalBytes;
            this.sampledBytes = sampledBytes;
            this.storageSavedBytes = storageSavedBytes;
            this.totalProcessingTimeMs = totalProcessingTimeMs;
            this.cpuSavedMs = cpuSavedMs;
            this.effectiveSampleRate = effectiveSampleRate;
            this.avgSampleRate = avgSampleRate;
            this.storageCostSavingsPercent = storageCostSavingsPercent;
            this.cpuCostSavingsPercent = cpuCostSavingsPercent;
        }

        public String getName() {
            return name;
        }

        public long getTotalSpans() {
            return totalSpans;
        }

        public long getSampledSpans() {
            return sampledSpans;
        }

        public long getDroppedSpans() {
            return droppedSpans;
        }

        public long getTotalBytes() {
            return totalBytes;
        }

        public long getSampledBytes() {
            return sampledBytes;
        }

        public long getStorageSavedBytes() {
            return storageSavedBytes;
        }

        public long getTotalProcessingTimeMs() {
            return totalProcessingTimeMs;
        }

        public long getCpuSavedMs() {
            return cpuSavedMs;
        }

        public double getEffectiveSampleRate() {
            return effectiveSampleRate;
        }

        public double getAvgSampleRate() {
            return avgSampleRate;
        }

        public double getStorageCostSavingsPercent() {
            return storageCostSavingsPercent;
        }

        public double getCpuCostSavingsPercent() {
            return cpuCostSavingsPercent;
        }
    }

    public static class CostRecommendation {
        private final String recommendation;
        private final String priority;
        private final double currentSampleRate;
        private final double storageSavings;
        private final double cpuSavings;

        public CostRecommendation(String recommendation, String priority,
                                  double currentSampleRate, double storageSavings,
                                  double cpuSavings) {
            this.recommendation = recommendation;
            this.priority = priority;
            this.currentSampleRate = currentSampleRate;
            this.storageSavings = storageSavings;
            this.cpuSavings = cpuSavings;
        }

        public String getRecommendation() {
            return recommendation;
        }

        public String getPriority() {
            return priority;
        }

        public double getCurrentSampleRate() {
            return currentSampleRate;
        }

        public double getStorageSavings() {
            return storageSavings;
        }

        public double getCpuSavings() {
            return cpuSavings;
        }

        public Map<String, Object> toMap() {
            Map<String, Object> map = new HashMap<>();
            map.put("recommendation", recommendation);
            map.put("priority", priority);
            map.put("currentSampleRate", String.format("%.2f%%", currentSampleRate * 100));
            map.put("storageSavingsPercent", String.format("%.2f%%", storageSavings));
            map.put("cpuSavingsPercent", String.format("%.2f%%", cpuSavings));
            return map;
        }
    }
}
