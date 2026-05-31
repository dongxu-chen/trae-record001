package com.benchmark.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceBaseline {
    private String id;
    private String algorithm;
    private int threadCount;
    private long createdTime;
    private boolean isBest;
    private double avgQps;
    private double peakQps;
    private double avgLatency;
    private double p50Latency;
    private double p95Latency;
    private double p99Latency;
    private double p999Latency;
    private double errorRate;
    private long totalGenerated;
    private long testDurationSeconds;
    private String testId;
}
