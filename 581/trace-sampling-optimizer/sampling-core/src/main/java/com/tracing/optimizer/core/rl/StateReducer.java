package com.tracing.optimizer.core.rl;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class StateReducer {

    private static final Logger log = LoggerFactory.getLogger(StateReducer.class);

    private final int targetDimensions;
    private final int hashBuckets;
    private final double[][] projectionMatrix;
    private final Map<String, Integer> reducedStateCache;
    private final Map<Integer, String> bucketToCentroid;
    private final boolean usePcaProjection;
    private int cacheHits;
    private int cacheMisses;

    public StateReducer() {
        this(16, 1024, false);
    }

    public StateReducer(int targetDimensions, int hashBuckets, boolean usePcaProjection) {
        this.targetDimensions = targetDimensions;
        this.hashBuckets = hashBuckets;
        this.usePcaProjection = usePcaProjection;
        this.projectionMatrix = usePcaProjection ? generateGaussianProjection(targetDimensions, 8) : null;
        this.reducedStateCache = new ConcurrentHashMap<>();
        this.bucketToCentroid = new ConcurrentHashMap<>();
        this.cacheHits = 0;
        this.cacheMisses = 0;
    }

    public int reduceState(SamplingEnvironment.ServiceState state) {
        String rawKey = buildStateKey(state);
        Integer cached = reducedStateCache.get(rawKey);
        if (cached != null) {
            cacheHits++;
            return cached;
        }

        cacheMisses++;
        int reduced;

        if (usePcaProjection) {
            reduced = pcaHashReduce(state);
        } else {
            reduced = featureBucketReduce(state);
        }

        reducedStateCache.put(rawKey, reduced);
        bucketToCentroid.putIfAbsent(reduced, rawKey);

        return reduced;
    }

    private int featureBucketReduce(SamplingEnvironment.ServiceState state) {
        int hash = 7;

        hash = 31 * hash + bucketize(state.businessImportance, 0.2, 5);
        hash = 31 * hash + bucketize(state.errorRate, 0.02, 5);
        hash = 31 * hash + bucketize(state.p99LatencyMs, 500.0, 5);
        hash = 31 * hash + bucketize(state.effectiveErrorRate, 0.02, 3);
        hash = 31 * hash + bucketizeThroughput(state.throughput);
        hash = 31 * hash + bucketize(state.currentSamplingRate, 0.2, 5);
        hash = 31 * hash + (state.serviceName.hashCode() % 100);

        return Math.abs(hash % hashBuckets);
    }

    private int pcaHashReduce(SamplingEnvironment.ServiceState state) {
        double[] featureVector = new double[]{
                state.businessImportance,
                normalize(state.errorRate, 0.0, 0.1),
                normalize(state.p99LatencyMs, 0.0, 5000.0),
                normalize(state.currentSamplingRate, 0.0, 1.0),
                normalize(state.effectiveErrorRate, 0.0, 0.1),
                normalize(state.requestRate, 0.0, 10000.0),
                normalize(state.throughput, 0.0, 100000.0),
                state.serviceName.hashCode() / (double) Integer.MAX_VALUE
        };

        double[] projected = project(featureVector);

        int hash = 0;
        for (int i = 0; i < projected.length; i++) {
            hash = 31 * hash + (projected[i] > 0 ? 1 : 0);
        }

        return Math.abs(hash % hashBuckets);
    }

    private double[] project(double[] featureVector) {
        if (projectionMatrix == null) return featureVector;
        double[] result = new double[targetDimensions];
        for (int i = 0; i < targetDimensions; i++) {
            double sum = 0;
            for (int j = 0; j < featureVector.length; j++) {
                sum += featureVector[j] * projectionMatrix[i][j];
            }
            result[i] = sum;
        }
        return result;
    }

    private double[][] generateGaussianProjection(int rows, int cols) {
        Random rnd = new Random(42);
        double[][] matrix = new double[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                matrix[i][j] = rnd.nextGaussian() / Math.sqrt(cols);
            }
        }
        return matrix;
    }

    private String buildStateKey(SamplingEnvironment.ServiceState state) {
        return String.format("svc=%s|bi=%.2f|er=%.4f|p99=%.0f|sr=%.2f|eer=%.4f|t=%d",
                state.serviceName,
                state.businessImportance,
                state.errorRate,
                state.p99LatencyMs,
                state.currentSamplingRate,
                state.effectiveErrorRate,
                state.throughput);
    }

    private int bucketize(double value, double step, int maxBuckets) {
        int bucket = (int) Math.floor(value / step);
        return Math.min(bucket, maxBuckets);
    }

    private int bucketizeThroughput(long throughput) {
        if (throughput < 100) return 0;
        if (throughput < 1000) return 1;
        if (throughput < 10000) return 2;
        if (throughput < 100000) return 3;
        return 4;
    }

    private double normalize(double value, double min, double max) {
        if (max <= min) return 0.5;
        double normalized = (value - min) / (max - min);
        return Math.max(0.0, Math.min(1.0, normalized));
    }

    public double getCacheHitRate() {
        int total = cacheHits + cacheMisses;
        return total == 0 ? 0.0 : (double) cacheHits / total;
    }

    public int getUniqueStates() {
        return reducedStateCache.size();
    }

    public int getTargetDimensions() { return targetDimensions; }
    public int getHashBuckets() { return hashBuckets; }
    public int getCacheHits() { return cacheHits; }
    public int getCacheMisses() { return cacheMisses; }

    public void clearCache() {
        reducedStateCache.clear();
        bucketToCentroid.clear();
        cacheHits = 0;
        cacheMisses = 0;
        log.info("State reducer cache cleared");
    }
}
