package com.benchmark.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RealtimeMetrics {
    private long timestamp;
    private long qps;
    private double avgLatency;
    private double p50Latency;
    private double p95Latency;
    private double p99Latency;
    private long generatedCount;
    private int progress;
}
