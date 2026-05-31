package com.benchmark.dto;

import lombok.Data;

@Data
public class StabilityTestConfig {
    private String algorithm;
    private int threadCount;
    private long durationHours;
    private long checkpointIntervalMinutes;
    private boolean autoRecovery;
    private double qpsDegradationThreshold;
    private double latencySpikeThreshold;
    private double errorRateThreshold;
    private SnowflakeConfig snowflakeConfig;
    private SegmentConfig segmentConfig;
    private UniquenessCheckConfig uniquenessConfig;

    @Data
    public static class SnowflakeConfig {
        private long workerId = 1;
        private long datacenterId = 1;
        private String clockMode = "NORMAL";
        private long clockOffsetMs = 10;
        private double clockBackProbability = 0.001;
    }

    @Data
    public static class SegmentConfig {
        private long segmentSize = 1000;
    }

    @Data
    public static class UniquenessCheckConfig {
        private int sampleSize = 10000;
        private double falsePositiveProbability = 0.0001;
    }

    public TestConfig toTestConfig() {
        TestConfig config = new TestConfig();
        config.setAlgorithm(algorithm);
        config.setThreadCount(threadCount);
        config.setDurationSeconds((int) Math.min(checkpointIntervalMinutes * 60, 3600));

        if (snowflakeConfig != null) {
            TestConfig.SnowflakeConfig sf = new TestConfig.SnowflakeConfig();
            sf.setWorkerId(snowflakeConfig.getWorkerId());
            sf.setDatacenterId(snowflakeConfig.getDatacenterId());
            sf.setClockMode(snowflakeConfig.getClockMode());
            sf.setClockOffsetMs(snowflakeConfig.getClockOffsetMs());
            sf.setClockBackProbability(snowflakeConfig.getClockBackProbability());
            config.setSnowflakeConfig(sf);
        }

        if (segmentConfig != null) {
            TestConfig.SegmentConfig seg = new TestConfig.SegmentConfig();
            seg.setSegmentSize(segmentConfig.getSegmentSize());
            config.setSegmentConfig(seg);
        }

        if (uniquenessConfig != null) {
            TestConfig.UniquenessCheckConfig uc = new TestConfig.UniquenessCheckConfig();
            uc.setSampleSize(uniquenessConfig.getSampleSize());
            uc.setFalsePositiveProbability(uniquenessConfig.getFalsePositiveProbability());
            config.setUniquenessConfig(uc);
        }

        return config;
    }
}
