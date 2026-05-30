package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceMetrics {
    private double avgQps;
    private double peakQps;
    private double avgLatencyMs;
    private double p95LatencyMs;
    private double p99LatencyMs;
    private double errorRate;
    private int instanceCount;
    private double cpuUtilization;
    private double memoryUtilization;
    private long totalRequests;
    private long totalErrors;
}
