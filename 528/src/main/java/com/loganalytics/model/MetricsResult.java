package com.loganalytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MetricsResult implements Serializable {
    private String dimension;
    private String value;
    private long windowStart;
    private long windowEnd;
    private long totalRequests;
    private long errorRequests;
    private double errorRate;
    private double qps;
    private double avgLatency;
    private double minLatency;
    private double maxLatency;
    private double stdDevLatency;
    private double variance;
    private double p50Latency;
    private double p95Latency;
    private double p99Latency;
    private double p999Latency;
    private long timestamp;

    private double errorRateMean;
    private double errorRateStdDev;
    private double latencyMean;
    private double latencyStdDev;
    private double qpsMean;
    private double qpsStdDev;
}
