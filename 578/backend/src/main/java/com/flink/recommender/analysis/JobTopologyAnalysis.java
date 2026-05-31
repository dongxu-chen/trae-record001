package com.flink.recommender.analysis;

import lombok.Data;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Data
public class JobTopologyAnalysis {

    private String jobId;
    private String jobName;
    private long totalDuration;
    private int totalVertices;
    private int maxParallelism;
    private List<VertexAnalysis> vertexAnalyses = new ArrayList<>();
    private Map<String, Object> dataSkewAnalysis = new HashMap<>();
    private Map<String, Double> resourceUtilization = new HashMap<>();
    private List<String> bottlenecks = new ArrayList<>();
    private List<String> recommendations = new ArrayList<>();

    @Data
    public static class VertexAnalysis {
        private String vertexId;
        private String vertexName;
        private int parallelism;
        private long duration;
        private double durationPercentage;
        private long calibratedDuration;
        private double calibrationError;
        private boolean isDurationCalibrated;
        private long readBytes;
        private long writeBytes;
        private long readRecords;
        private long writeRecords;
        private double recordsPerSecond;
        private double bytesPerSecond;
        private double avgRecordSize;
        private boolean isBottleneck;
        private DataSkewInfo dataSkew;
        private DurationCalibrationInfo durationCalibration;
        private List<SubtaskMetrics> subtaskMetrics = new ArrayList<>();
    }

    @Data
    public static class DurationCalibrationInfo {
        private long historicalAvgDuration;
        private long historicalMedianDuration;
        private long historicalP95Duration;
        private long historicalMinDuration;
        private long historicalMaxDuration;
        private double durationStdDev;
        private int historicalSampleCount;
        private double confidenceLevel;
        private double calibrationFactor;
        private String calibrationMethod;
        private List<String> calibrationReasons = new ArrayList<>();
    }

    @Data
    public static class DataSkewInfo {
        private boolean hasSkew;
        private double skewFactor;
        private double maxRecords;
        private double minRecords;
        private double avgRecords;
        private double stdDevRecords;
        private double coefficientOfVariation;
        private List<Integer> skewedSubtasks = new ArrayList<>();
        private String severity;
        private boolean isFullKeyScanEnabled;
        private boolean samplingVerified;
        private KeyDistributionAnalysis keyDistribution;
        private long totalUniqueKeys;
        private long sampledKeys;
        private double samplingRate;
        private double detectionConfidence;
        private List<HotKeyInfo> hotKeys = new ArrayList<>();
    }

    @Data
    public static class KeyDistributionAnalysis {
        private long totalKeysAnalyzed;
        private long sampledKeyCount;
        private double giniCoefficient;
        private double entropy;
        private double top1KeyPercentage;
        private double top5KeysPercentage;
        private double top10KeysPercentage;
        private List<KeyFrequencyBin> frequencyDistribution = new ArrayList<>();
        private String distributionPattern;
    }

    @Data
    public static class HotKeyInfo {
        private String keyHash;
        private long count;
        private double percentage;
        private int subtaskIndex;
        private boolean verifiedBySampling;
        private String keyType;
    }

    @Data
    public static class KeyFrequencyBin {
        private String range;
        private long keyCount;
        private long recordCount;
        private double percentage;
    }

    @Data
    public static class SubtaskMetrics {
        private int subtaskIndex;
        private String host;
        private long duration;
        private long readBytes;
        private long writeBytes;
        private long readRecords;
        private long writeRecords;
        private long busyTime;
        private long idleTime;
        private double busyRatio;
        private double buffersInPoolUsage;
        private double buffersOutPoolUsage;
    }

    @Data
    public static class JobHealthScore {
        private String jobId;
        private double overallScore;
        private double cpuHealth;
        private double memoryHealth;
        private double networkHealth;
        private double skewHealth;
        private double throughputHealth;
        private String healthLevel;
        private List<String> healthFactors = new ArrayList<>();
        private long timestamp;
        private double predictedScore1h;
        private double predictedScore6h;
        private double predictedScore24h;
    }

    @Data
    public static class ResourceWarning {
        private String warningId;
        private String jobId;
        private String warningType;
        private String severity;
        private String message;
        private String resourceType;
        private double currentValue;
        private double threshold;
        private double predictedValue;
        private long predictedTime;
        private long timestamp;
        private boolean isPrediction;
        private List<String> recommendations = new ArrayList<>();
    }

    @Data
    public static class JobComparison {
        private String groupId;
        private String groupName;
        private int jobCount;
        private List<JobComparisonItem> jobs = new ArrayList<>();
        private JobComparisonSummary summary = new JobComparisonSummary();
        private List<String> optimizationSuggestions = new ArrayList<>();
    }

    @Data
    public static class JobComparisonItem {
        private String jobId;
        private String jobName;
        private double avgCpuUtilization;
        private double avgMemoryUtilization;
        private double avgNetworkUtilization;
        private double throughputPerCore;
        private double costPerRecord;
        private double skewFactor;
        private double efficiencyScore;
        private ResourceConfig currentConfig;
        private Map<String, Object> metrics = new HashMap<>();
        private int rank;
    }

    @Data
    public static class JobComparisonSummary {
        private double avgCpuUtilization;
        private double avgMemoryUtilization;
        private double avgNetworkUtilization;
        private double maxCpuUtilization;
        private double minCpuUtilization;
        private double cpuStdDev;
        private double memoryStdDev;
        private double efficiencyVariance;
        private double bestEfficiencyScore;
        private String bestJobId;
        private String worstJobId;
    }

    @Data
    public static class AutoAdjustmentResult {
        private String jobId;
        private boolean success;
        private String adjustmentId;
        private ResourceConfig previousConfig;
        private ResourceConfig newConfig;
        private String adjustmentReason;
        private List<String> appliedChanges = new ArrayList<>();
        private Map<String, Object> expectedImprovements = new HashMap<>();
        private long timestamp;
        private String status;
        private String errorMessage;
    }
}
