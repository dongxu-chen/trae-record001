package com.tracing.optimizer.core.evaluation;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class SamplingEffectEvaluator {

    private final Map<String, ServiceEvaluationMetrics> serviceMetrics;
    private final Duration evaluationWindow;
    private final AtomicLong totalProblemsDetected;
    private final AtomicLong totalProblemsMissed;
    private final Map<String, ProblemRecord> problemHistory;

    public SamplingEffectEvaluator() {
        this(Duration.ofHours(24));
    }

    public SamplingEffectEvaluator(Duration evaluationWindow) {
        this.evaluationWindow = evaluationWindow;
        this.serviceMetrics = new ConcurrentHashMap<>();
        this.totalProblemsDetected = new AtomicLong(0);
        this.totalProblemsMissed = new AtomicLong(0);
        this.problemHistory = new ConcurrentHashMap<>();
    }

    public void recordProblem(String problemId, String serviceName, ProblemType type,
                              boolean detectedBySampling, double samplingRateAtTime) {
        ProblemRecord record = new ProblemRecord(problemId, serviceName, type, detectedBySampling, samplingRateAtTime);
        problemHistory.put(problemId, record);

        if (detectedBySampling) {
            totalProblemsDetected.incrementAndGet();
        } else {
            totalProblemsMissed.incrementAndGet();
        }

        ServiceEvaluationMetrics metrics = serviceMetrics.computeIfAbsent(
            serviceName, k -> new ServiceEvaluationMetrics()
        );
        metrics.recordProblem(type, detectedBySampling, samplingRateAtTime);
    }

    public double getOverallDetectionRate() {
        long total = totalProblemsDetected.get() + totalProblemsMissed.get();
        return total > 0 ? (double) totalProblemsDetected.get() / total : 1.0;
    }

    public double getDetectionRateChange(String serviceName, double previousDetectionRate) {
        Double currentRate = getServiceDetectionRate(serviceName);
        return currentRate - previousDetectionRate;
    }

    public Double getServiceDetectionRate(String serviceName) {
        ServiceEvaluationMetrics metrics = serviceMetrics.get(serviceName);
        return metrics != null ? metrics.getDetectionRate() : null;
    }

    public Map<String, Double> getDetectionRateByProblemType() {
        Map<String, Double> rates = new EnumMap<>(ProblemType.class);
        for (ProblemType type : ProblemType.values()) {
            long detected = problemHistory.values().stream()
                .filter(p -> p.type == type && p.detectedBySampling)
                .count();
            long total = problemHistory.values().stream()
                .filter(p -> p.type == type)
                .count();
            rates.put(type.name(), total > 0 ? (double) detected / total : 1.0);
        }
        return rates;
    }

    public Map<Double, Double> getSamplingRateDetectionCorrelation() {
        Map<Double, List<Boolean>> rateToDetection = new HashMap<>();
        for (ProblemRecord record : problemHistory.values()) {
            double bucketRate = Math.round(record.samplingRateAtTime * 10) / 10.0;
            rateToDetection.computeIfAbsent(bucketRate, k -> new ArrayList<>())
                .add(record.detectedBySampling);
        }

        Map<Double, Double> correlation = new TreeMap<>();
        for (Map.Entry<Double, List<Boolean>> entry : rateToDetection.entrySet()) {
            List<Boolean> detections = entry.getValue();
            double rate = detections.stream().filter(b -> b).count() / (double) detections.size();
            correlation.put(entry.getKey(), rate);
        }
        return correlation;
    }

    public double getEffectiveCostEfficiency(String serviceName) {
        ServiceEvaluationMetrics metrics = serviceMetrics.get(serviceName);
        if (metrics == null) return 0.0;

        double detectionRate = metrics.getDetectionRate();
        double avgSamplingRate = metrics.getAverageSamplingRate();
        double baselineRate = 0.1;

        if (avgSamplingRate <= 0) return 0.0;

        double detectionRatio = detectionRate / baselineRate;
        double costRatio = avgSamplingRate / baselineRate;

        return detectionRatio / costRatio;
    }

    public EvaluationReport generateReport(String serviceName) {
        ServiceEvaluationMetrics metrics = serviceMetrics.get(serviceName);
        if (metrics == null) {
            return new EvaluationReport(serviceName, 0, 0, 0, 1.0, 0, new HashMap<>(), 1.0);
        }

        return new EvaluationReport(
            serviceName,
            metrics.totalProblems.get(),
            metrics.problemsDetected.get(),
            metrics.problemsMissed.get(),
            metrics.getDetectionRate(),
            metrics.getDetectionRateChange(),
            metrics.getDetectionByType(),
            metrics.getAverageSamplingRate()
        );
    }

    public Map<String, EvaluationReport> generateAllReports() {
        Map<String, EvaluationReport> reports = new HashMap<>();
        for (String serviceName : serviceMetrics.keySet()) {
            reports.put(serviceName, generateReport(serviceName));
        }
        return reports;
    }

    public void cleanupOldRecords() {
        long cutoff = Instant.now().minus(evaluationWindow).toEpochMilli();
        problemHistory.entrySet().removeIf(e -> e.getValue().timestamp < cutoff);
        serviceMetrics.values().forEach(ServiceEvaluationMetrics::cleanupOldRecords);
    }

    public enum ProblemType {
        ERROR_SPIKE,
        LATENCY_SPIKE,
        BUSINESS_ANOMALY,
        DEPENDENCY_FAILURE,
        RESOURCE_EXHAUSTION,
        UNCLASSIFIED
    }

    public static class ProblemRecord {
        public final String problemId;
        public final String serviceName;
        public final ProblemType type;
        public final boolean detectedBySampling;
        public final double samplingRateAtTime;
        public final long timestamp;

        public ProblemRecord(String problemId, String serviceName, ProblemType type,
                             boolean detectedBySampling, double samplingRateAtTime) {
            this.problemId = problemId;
            this.serviceName = serviceName;
            this.type = type;
            this.detectedBySampling = detectedBySampling;
            this.samplingRateAtTime = samplingRateAtTime;
            this.timestamp = Instant.now().toEpochMilli();
        }
    }

    public static class ServiceEvaluationMetrics {
        private final AtomicLong totalProblems;
        private final AtomicLong problemsDetected;
        private final AtomicLong problemsMissed;
        private final Map<ProblemType, AtomicLong> detectedByType;
        private final List<Double> samplingRateHistory;
        private double previousDetectionRate;

        public ServiceEvaluationMetrics() {
            this.totalProblems = new AtomicLong(0);
            this.problemsDetected = new AtomicLong(0);
            this.problemsMissed = new AtomicLong(0);
            this.detectedByType = new EnumMap<>(ProblemType.class);
            this.samplingRateHistory = Collections.synchronizedList(new ArrayList<>());
            this.previousDetectionRate = 1.0;
        }

        public void recordProblem(ProblemType type, boolean detected, double samplingRate) {
            previousDetectionRate = getDetectionRate();
            totalProblems.incrementAndGet();
            if (detected) {
                problemsDetected.incrementAndGet();
            } else {
                problemsMissed.incrementAndGet();
            }
            detectedByType.computeIfAbsent(type, k -> new AtomicLong(0)).incrementAndGet();
            samplingRateHistory.add(samplingRate);
        }

        public double getDetectionRate() {
            long total = totalProblems.get();
            return total > 0 ? (double) problemsDetected.get() / total : 1.0;
        }

        public double getDetectionRateChange() {
            return getDetectionRate() - previousDetectionRate;
        }

        public double getAverageSamplingRate() {
            if (samplingRateHistory.isEmpty()) return 0.1;
            synchronized (samplingRateHistory) {
                return samplingRateHistory.stream().mapToDouble(Double::doubleValue).average().orElse(0.1);
            }
        }

        public Map<String, Double> getDetectionByType() {
            Map<String, Double> result = new HashMap<>();
            for (Map.Entry<ProblemType, AtomicLong> entry : detectedByType.entrySet()) {
                result.put(entry.getKey().name(), (double) entry.getValue().get());
            }
            return result;
        }

        public void cleanupOldRecords() {
            int keepSize = 1000;
            if (samplingRateHistory.size() > keepSize) {
                synchronized (samplingRateHistory) {
                    while (samplingRateHistory.size() > keepSize) {
                        samplingRateHistory.remove(0);
                    }
                }
            }
        }
    }

    public static class EvaluationReport {
        public final String serviceName;
        public final long totalProblems;
        public final long problemsDetected;
        public final long problemsMissed;
        public final double detectionRate;
        public final double detectionRateChange;
        public final Map<String, Double> detectionByType;
        public final double averageSamplingRate;

        public EvaluationReport(String serviceName, long totalProblems, long problemsDetected,
                                long problemsMissed, double detectionRate, double detectionRateChange,
                                Map<String, Double> detectionByType, double averageSamplingRate) {
            this.serviceName = serviceName;
            this.totalProblems = totalProblems;
            this.problemsDetected = problemsDetected;
            this.problemsMissed = problemsMissed;
            this.detectionRate = detectionRate;
            this.detectionRateChange = detectionRateChange;
            this.detectionByType = detectionByType;
            this.averageSamplingRate = averageSamplingRate;
        }
    }
}
