package com.sla.monitor.dto;

import lombok.Data;

@Data
public class ServiceComparisonDTO {
    private String serviceName;
    private Double availability;
    private Double avgLatencyMs;
    private Double errorRate;
    private Double slaAchievementRate;
    private boolean slaViolated;
}
