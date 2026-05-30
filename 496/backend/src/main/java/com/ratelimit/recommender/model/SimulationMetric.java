package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SimulationMetric {
    private LocalDateTime timestamp;
    private double qps;
    private double latencyMs;
    private double errorRate;
    private int queueSize;
    private int rejectedRequests;
}
