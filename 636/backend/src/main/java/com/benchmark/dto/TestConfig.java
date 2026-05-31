package com.benchmark.dto;

import lombok.Data;

@Data
public class TestConfig {
    private String algorithm;
    private int threadCount;
    private int durationSeconds;
    private Long idCount;
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
}
