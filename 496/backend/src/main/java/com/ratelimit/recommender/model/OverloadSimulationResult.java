package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OverloadSimulationResult {
    private String simulationId;
    private String serviceId;
    private boolean withRateLimit;
    private Map<String, List<SimulationMetric>> metrics;
    private List<String> bottlenecks;
    private double estimatedErrorRate;
    private double estimatedLatencyIncrease;
    private int droppedRequests;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private String conclusion;
}
