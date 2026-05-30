package com.migration.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceMetrics {

    private String serviceId;
    private long eurekaRegistrationTimeMs;
    private long nacosRegistrationTimeMs;
    private long eurekaDiscoveryTimeMs;
    private long nacosDiscoveryTimeMs;
    private long eurekaHeartbeatTimeMs;
    private long nacosHeartbeatTimeMs;
    private double eurekaThroughput;
    private double nacosThroughput;
    private double eurekaP99Latency;
    private double nacosP99Latency;
    private long timestamp;
}
