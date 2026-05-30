package com.ratelimit.recommender.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ServiceEdge {
    private String sourceServiceId;
    private String targetServiceId;
    private String apiPath;
    private double callRate;
    private double avgLatencyMs;
    private double errorRate;
    private int weight;
}
