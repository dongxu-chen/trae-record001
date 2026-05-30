package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiMetrics {
    private double avgQps;
    private double peakQps;
    private double avgLatencyMs;
    private double p95LatencyMs;
    private double p99LatencyMs;
    private double errorRate;
    private long totalRequests;
    private long totalErrors;
}
